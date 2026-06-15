import random
from typing import Any

import package_root
from Script import api
from Script.api import shared
from Script.api import cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger


class Pattern(UFSTC):
    """PF010_0310 Write Booster SSU/POR/LINKSTARTUP reset validation.

    Generation model: flow-level stateful generation.
    - One TC generated one Pattern folder and one Pattern .py.
    - Each TC phase was generated as a flow-level method so ordered steps,
      variables, reset_type, expected values, write_record, and flag state are
      preserved inside the same flow context.
    - Step-level retrieval was merged into flow-level decision records in
      PF010_0310_Normalize.retrieval.md.
    """

    # Grounded by /home/weikai/Script/api/ufs_api/defines/enum_define.py.
    WB_ENABLE_FLAG = api.FlagIDN.WRITEBOOSTER_EN
    WB_FLUSH_ENABLE_FLAG = api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN

    # TODO_REVIEW: TC Appendix names fWriteBoosterSupport as IDN 0x15, but the
    # current PyPPS FlagIDN enum does not expose this flag name.
    WB_SUPPORT_FLAG_IDN = 0x15

    # TODO_REVIEW: TC names dLUNumWriteBoosterBufferAllocUnits as IDN 0x17, but
    # current PyPPS AttributeIDN enum maps 0x17 to REF_CLK_GATING_WAIT_TIME.
    WB_ALLOC_UNITS_ATTR_IDN_FROM_TC = 0x17

    RESET_SEQUENCE = ("SSU", "POR", "LINKSTARTUP")

    def pre_process(self) -> None:
        self.seed = int(self.tcsargs.get("seed", "310"))
        random.seed(self.seed)
        self.burn_in_loop = int(self.tcsargs.get("burn_in_loop", "1"))
        self.cmd_count = int(self.tcsargs.get("cmd_count", "8"))
        self.min_transfer_blocks = int(self.tcsargs.get("min_transfer_blocks", "1"))
        self.max_transfer_blocks = int(self.tcsargs.get("max_transfer_blocks", "256"))
        self.enable_ffu_flow = str(self.tcsargs.get("enable_ffu_flow", "0")) == "1"
        self.write_record = api.get_empty_write_record()
        self.test_lun = self._pick_max_capacity_enabled_lun()
        self.flow_state = {
            "global": {
                "seed": self.seed,
                "test_lun": self.test_lun,
                "write_record": "self.write_record",
                "transfer_length_blocks": [self.min_transfer_blocks, self.max_transfer_blocks],
            }
        }
        logger.info(f"PF010_0310 seed={self.seed}")
        logger.info(f"PF010_0310 test_lun={self.test_lun}")
        logger.info(f"PF010_0310 burn_in_loop={self.burn_in_loop}, cmd_count={self.cmd_count}")

    def is_support(self) -> bool:
        try:
            support = api.read_flag(idn=self.WB_SUPPORT_FLAG_IDN)
            logger.info(f"fWriteBoosterSupport(0x15)={support}")
            return support == 1
        except Exception as exc:
            # TODO_REVIEW: verify fWriteBoosterSupport IDN/API mapping for this PyPPS branch.
            logger.warning(f"TODO_REVIEW: cannot read fWriteBoosterSupport(0x15): {exc!r}; continue")
            return True

    def step1(self) -> None:
        """Flow 0: setup / preconditions.

        Flow state dependencies:
        - Produces selected LUN and LBA range for all W/R flows.
        - Checks WB support before WriteBooster flows.
        - Intentionally does not write dLUNumWriteBoosterBufferAllocUnits until
          the AttributeIDN mapping is grounded.
        """
        flow = "flow_0_setup"
        self.flow_state[flow] = {
            "tc_steps": ["0.1", "0.2", "0.3", "0.4"],
            "produces": ["test_lun", "lba_range", "wb_support"],
            "todo_review": [],
        }
        logger.info("Flow 0 / Step 0.1: TEST UNIT READY is covered by UFSTC initialization")
        logger.info("Flow 0 / Step 0.2: READ CAPACITY is covered by shared.param.gLUCapacity")
        min_lba, max_lba = self._lba_range()
        self.flow_state[flow]["lba_range"] = [min_lba, max_lba]
        logger.info(f"Selected LUN {self.test_lun}, LBA range={min_lba}..{max_lba}")

        try:
            support = api.read_flag(idn=self.WB_SUPPORT_FLAG_IDN)
            self.flow_state[flow]["wb_support"] = support
            if support != 1:
                raise api.UFS_NON_SUPPORT
        except Exception as exc:
            self.flow_state[flow]["todo_review"].append("fWriteBoosterSupport IDN/API mapping")
            logger.warning(f"TODO_REVIEW: support flag 0x15 could not be confirmed: {exc!r}; continuing")

        self.flow_state[flow]["todo_review"].append("dLUNumWriteBoosterBufferAllocUnits API/IDN mapping")
        logger.warning(
            "TODO_REVIEW: dLUNumWriteBoosterBufferAllocUnits IDN 0x17 conflicts with "
            "current PyPPS AttributeIDN. Attribute READ/WRITE is skipped."
        )

    def step2(self) -> None:
        """Flow 1: WriteBooster enabled W/R compare and reset validation.

        This whole flow is generated as one stateful unit: SET FLAG produces the
        WB-enabled pre-state, random_write updates write_record, reset_type drives
        both the reset primitive and expected flag value.
        """
        self._maybe_ffu_flow_checkpoint()
        flow = "flow_1_enable_reset"
        self.flow_state[flow] = {
            "tc_steps": ["1.1", "1.2", "1.3", "1.4", "1.5"],
            "reads": ["test_lun", "write_record", "RESET_SEQUENCE"],
            "writes": ["wb_enable_state", "last_reset_type", "expected_wb_enable"],
            "dependency_edges": [
                "1.2/1.3 use write_record produced by random_write",
                "1.5 expected value depends on reset_type from 1.4",
            ],
        }
        for loop_idx in range(self.burn_in_loop):
            self._set_wb_enable()
            self._expect_flag(self.WB_ENABLE_FLAG, 1, "Flow 1 after SET FLAG fWriteBoosterEnable")
            self._random_write_and_compare(f"Flow 1 loop {loop_idx}: WB enabled W/R compare")
            for reset_type in self.RESET_SEQUENCE:
                self.flow_state[flow]["last_reset_type"] = reset_type
                self._set_wb_enable()
                self._random_write_and_compare(f"Flow 1 loop {loop_idx}: before {reset_type}")
                self._do_reset(reset_type)
                expected = self._expected_volatile_flag_after_reset(reset_type)
                self.flow_state[flow]["expected_wb_enable"] = expected
                self._expect_flag(self.WB_ENABLE_FLAG, expected, f"Flow 1 after {reset_type} reset")

    def step3(self) -> None:
        """Flow 2: WriteBooster disabled read/compare and reset validation.

        The CLEAR FLAG state is preserved through the ordered flow. The READ(10)
        compare consumes write_record from the previous random write in the same
        flow and verifies data consistency after disabled-state reset coverage.
        """
        flow = "flow_2_disable_reset"
        self.flow_state[flow] = {
            "tc_steps": ["2.1", "2.2", "2.3", "2.4", "2.5"],
            "reads": ["test_lun", "write_record", "RESET_SEQUENCE"],
            "writes": ["wb_enable_state", "last_reset_type", "expected_wb_enable"],
            "dependency_edges": [
                "2.3 READ compare consumes write data produced by 2.1",
                "2.5 expected value depends on 2.2 CLEAR FLAG plus 2.4 reset_type",
            ],
        }
        for loop_idx in range(self.burn_in_loop):
            self._set_wb_enable()
            self._random_write_and_compare(f"Flow 2 loop {loop_idx}: before CLEAR FLAG")
            self._clear_wb_enable()
            self._expect_flag(self.WB_ENABLE_FLAG, 0, "Flow 2 after CLEAR FLAG fWriteBoosterEnable")
            self._random_read_compare(f"Flow 2 loop {loop_idx}: WB disabled data compare")
            for reset_type in self.RESET_SEQUENCE:
                self.flow_state[flow]["last_reset_type"] = reset_type
                self._clear_wb_enable()
                self._do_reset(reset_type)
                self.flow_state[flow]["expected_wb_enable"] = 0
                self._expect_flag(self.WB_ENABLE_FLAG, 0, f"Flow 2 after {reset_type} reset while WB disabled")
                self._random_read_compare(f"Flow 2 loop {loop_idx}: after {reset_type}")

    def step4(self) -> None:
        """Flow 3: Flush enable and reset validation.

        SET FLAG fWriteBoosterBufferFlushEn, reset primitive, and expected value
        are generated together so the reset_type variable cannot be detached from
        its expected flag-state assertion.
        """
        flow = "flow_3_flush_reset"
        self.flow_state[flow] = {
            "tc_steps": ["3.1", "3.2", "3.3"],
            "reads": ["RESET_SEQUENCE"],
            "writes": ["flush_enable_state", "last_reset_type", "expected_flush_enable"],
            "dependency_edges": ["3.3 expected value depends on reset_type from 3.2"],
        }
        for loop_idx in range(self.burn_in_loop):
            for reset_type in self.RESET_SEQUENCE:
                self.flow_state[flow]["last_reset_type"] = reset_type
                api.set_flag(idn=self.WB_FLUSH_ENABLE_FLAG)
                self._expect_flag(self.WB_FLUSH_ENABLE_FLAG, 1, "Flow 3 after SET FLAG fWriteBoosterBufferFlushEn")
                self._do_reset(reset_type)
                expected = self._expected_volatile_flag_after_reset(reset_type)
                self.flow_state[flow]["expected_flush_enable"] = expected
                self._expect_flag(self.WB_FLUSH_ENABLE_FLAG, expected, f"Flow 3 after {reset_type} reset")

    def post_process(self) -> None:
        try:
            api.clear_flag(idn=self.WB_ENABLE_FLAG)
        except Exception as exc:
            logger.warning(f"cleanup clear fWriteBoosterEnable failed: {exc!r}")
        try:
            api.clear_flag(idn=self.WB_FLUSH_ENABLE_FLAG)
        except Exception as exc:
            logger.warning(f"cleanup clear fWriteBoosterBufferFlushEn failed: {exc!r}")

    def _maybe_ffu_flow_checkpoint(self) -> None:
        """Flow X placeholder: TC mentions FFU at burn-in 1/3.

        TODO_REVIEW: no firmware image path, target version, transfer length, or
        trigger policy is provided by the TC. Keep this flow disabled unless the
        user supplies FFU implementation details via tcsargs and reviews it.
        """
        flow = "flow_x_ffu"
        if flow not in self.flow_state:
            self.flow_state[flow] = {
                "tc_steps": ["X.1", "X.2", "X.3"],
                "status": "disabled_todo_review",
                "todo_review": ["FFU firmware path/version/trigger policy missing"],
            }
        if self.enable_ffu_flow:
            # TODO_REVIEW: implement FFU only after firmware path/version and PyPPS WRITE BUFFER
            # recipe are explicitly grounded for this project.
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(
                "TODO_REVIEW: enable_ffu_flow requested but FFU implementation details are not grounded"
            )

    def _pick_max_capacity_enabled_lun(self) -> int:
        _param = shared.param
        max_cap = -1
        selected = 0
        for lun in range(_param.gMaxNumberLU):
            if _param.gUnit[lun].b3_lu_enable and _param.gLUCapacity[lun] > max_cap:
                max_cap = _param.gLUCapacity[lun]
                selected = lun
        return selected

    def _lba_range(self) -> tuple[int, int]:
        max_lba = max(0, shared.param.gLUCapacity[self.test_lun] - 1)
        return 0, max_lba

    def _set_wb_enable(self) -> None:
        api.set_flag(idn=self.WB_ENABLE_FLAG)

    def _clear_wb_enable(self) -> None:
        api.clear_flag(idn=self.WB_ENABLE_FLAG)

    def _expect_flag(self, idn: int, expected: int, context: str) -> None:
        actual = api.read_flag(idn=idn)
        logger.info(f"{context}: flag {idn} actual={actual}, expected={expected}")
        if actual != expected:
            raise api.SIGHTING_RESPONSE_UNEXPECTED

    def _random_write_and_compare(self, context: str) -> None:
        logger.info(context)
        min_lba, max_lba = self._lba_range()
        api.random_write(
            cmd_count=self.cmd_count,
            min_lun=self.test_lun,
            max_lun=self.test_lun,
            min_lba=min_lba,
            max_lba=max_lba,
            min_size=self.min_transfer_blocks,
            max_size=self.max_transfer_blocks,
            need_compare=True,
            compare_method=api.CompareMethod.HW_COMPARE,
            write_record=self.write_record,
            fua=0,
        )

    def _random_read_compare(self, context: str) -> None:
        logger.info(context)
        min_lba, max_lba = self._lba_range()
        api.random_read(
            cmd_count=self.cmd_count,
            min_lun=self.test_lun,
            max_lun=self.test_lun,
            min_lba=min_lba,
            max_lba=max_lba,
            min_size=self.min_transfer_blocks,
            max_size=self.max_transfer_blocks,
            need_compare=True,
            write_record=self.write_record,
        )

    def _expected_volatile_flag_after_reset(self, reset_type: str) -> int:
        if reset_type == "SSU":
            return 1
        return 0

    def _do_reset(self, reset_type: str) -> None:
        if reset_type == "SSU":
            self._ssu_sleep_active()
        elif reset_type == "POR":
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET, powerdown=True)
        elif reset_type == "LINKSTARTUP":
            # TODO_REVIEW: TC says LINKSTARTUP Reset. Current grounded PyPPS reset enum exposes
            # UNIPRO_RESET; using it as the closest link-level reset primitive.
            api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.UNIPRO_RESET)
        else:
            raise api.PATTERN_ASSERT_UNEXPECTED_CONDITION(f"Unknown reset_type={reset_type}")

    def _ssu_sleep_active(self) -> None:
        sleep = ExecuteCMD.StartStopUnit()
        sleep.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=0x02, no_flush=0, start=0)
        sleep.set_option(wait_queue_empty=True).enqueue()
        active = ExecuteCMD.StartStopUnit()
        active.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=0x01, no_flush=0, start=0)
        active.set_option(wait_queue_empty=True).enqueue()
        ExecuteCMD.send(clear_on_success=True)


run = Pattern().run
if __name__ == "__main__":
    run()
