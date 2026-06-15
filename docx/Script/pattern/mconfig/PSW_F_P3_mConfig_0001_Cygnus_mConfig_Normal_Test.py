import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.pattern.mconfig.mutual_fun import *
import time
FFU_READY = False

class Pattern(UFSTC):
    def pre_process(self) -> None:
        config_lun()
        self.mConfig_in_FW_HW_BIN_offset = 0
        self.pConfig_in_FW_HW_BIN_offset = 1024
        # flashsettingdata = api.get_flash_setting()
        self.hw_setting = api.HwSetting.get_instance()
        self.hw_setting.update_from_device()
        self.hw_setting.backup()
        pass

    def step1(self) -> None:
        offset = 0
        if self.hw_setting.ce_num == 1:
            offset = 0
        elif self.hw_setting.ce_num == 2:
            offset = DATA_SIZE_4K_BYTE
        elif self.hw_setting.ce_num == 4:
            offset = DATA_SIZE_8K_BYTE
        elif self.hw_setting.ce_num == 8:
            offset = DATA_SIZE_12K_BYTE
        
        _, mConfig_in_vu_bkup = project_api.get_mConfig_data()
        _, pConfig_in_vu_bkup = project_api.get_pConfig_data()
        mConfig, pConfig = load_mConfig_pConfig_from_xlsx(OTP_value = mConfig_in_vu_bkup.OTP_value.value)
        
        logger.flow(1, 'search bin and get mconfig follow mConfig Format in FFU bin')
        current_bin = bytearray(4096)
        # current_bin = api.api.search_ffu_bin(api.api.FFUBinType.FW_BIN, api.api.FFUSvnType.CURRENT_SVN_BIN)
        # mConfig_in_bin, pConfig_in_bin = get_m_p_config_in_FW_HW_BIN(current_bin)
        # compare_payload(mConfig_pConfig_dict=mConfig, payload=mConfig_in_bin.payload.copy())
        # compare_payload(mConfig_pConfig_dict=pConfig, payload=pConfig_in_bin.payload.copy())

        
        logger.flow(1, 'issue 4056 mconfig data & pconfig data are same as xlsx')
        compare_payload(mConfig_pConfig_dict=mConfig, payload=mConfig_in_vu_bkup.payload.copy())
        compare_payload(mConfig_pConfig_dict=pConfig, payload=pConfig_in_vu_bkup.payload.copy())

        ffu_case = [1,2,3]
        for case in range(1, 6+1):
            logger.info(f'======================= test case {case} =======================') #ENG2
            if not FFU_READY:
                if case in ffu_case:
                    continue
            temp_mConfig = project_api.mConfig(mConfig_in_vu_bkup.payload.copy())
            temp_pConfig = project_api.pConfig(pConfig_in_vu_bkup.payload.copy())
            temp_HW_page = self.hw_setting._backup_data[offset: offset + 0x1000].copy()
            temp_bin = current_bin.copy()
            temp_mConfig.payload[0:7] = "MCONFIG".encode("ascii")
            temp_pConfig.payload[0:7] = "PCONFIG".encode("ascii")
            
            logger.flow(2, 'HW Setting Enable FFU update / same SVN')
            if case in ffu_case: #FFU case
                self.hw_setting.set_to_device(api.HwSettingField.FFU_FEATURE, api.FFUFeature.FFU_SAMVE_SVN_BACKWARD_EN)
            
            logger.flow(3, 'mConfig Test Case')
            randversion = random.randint(1, 0xFF)
            if case == 1:
                logger.info('mConfig Case 1: write FFU bin') #ENG2
                api.send_ffu_write_buffer(len(temp_bin), 0, temp_bin)
                temp_mConfig, temp_pConfig = get_m_p_config_in_FW_HW_BIN(temp_bin)
            elif case == 2:
                logger.info('mConfig Case 2: write FFU bin  mConfig_VU with changeable (mconfig version)') #ENG2
                temp_bin[self.mConfig_in_FW_HW_BIN_offset] = randversion
                api.send_ffu_write_buffer(len(temp_bin), 0, temp_bin)
                temp_mConfig, temp_pConfig = get_m_p_config_in_FW_HW_BIN(temp_bin)
            elif case == 3:
                logger.info('mConfig Case 3: write FFU bin  mConfig_VU with changeable (pconfig version)') #ENG2
                temp_bin[self.pConfig_in_FW_HW_BIN_offset] = randversion
                api.send_ffu_write_buffer(len(temp_bin), 0, temp_bin)
                temp_mConfig, temp_pConfig = get_m_p_config_in_FW_HW_BIN(temp_bin)
            elif case == 4:
                logger.info('mConfig Case 4: C056 mConfig_VU with changeable mconfig (mconfig version)') #ENG2, use 0x09
                temp_mConfig.mConfig_Version.value = randversion
                project_api.set_mConfig_data(mConfig=temp_mConfig)
            elif case == 5:
                logger.info('mConfig Case 5: C056 mConfig_VU with changeable pconfig ([config version)') #ENG2, use 0x09
                temp_pConfig.pConfig_version.value = randversion
                project_api.set_pConfig_data(pConfig=temp_pConfig)
            elif case == 6:
                logger.info('mConfig Case 6: C056 mConfig_VU moconfig in write FFU bin') #ENG2, use 0x09
                project_api.set_HW_page_config_data(data_payload=temp_HW_page)
        
            logger.flow(4, 'Host issue init flow with HWReset or ResetN')
            resetmode = random.choice([api.Dcmd5ResetType.HW_RESET, api.Dcmd5ResetType.RESET_N])
            api.init_tester_to_unit_ready(resetmode=resetmode)

            if case == 6:
                logger.flow(5, 'Host get HW page and check data') #only mconfig, pconfig use 0x83
                _, HW_page_vu = project_api.get_HW_page_config_data()
                self.hw_setting.update_from_device()
                if self.hw_setting._data[offset: offset + 0x1000] != HW_page_vu:
                    dumpfile('hw_setting.bin', self.hw_setting._data[offset: offset + 0x1000])
                    dumpfile('4056.bin', HW_page_vu)
                    logger.error_lb(f'check HW_page after setting')
                    logger.error_fp(f'data conpare fail, please check dump file')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            else:
                logger.flow(5, 'Host issue 4056 get mConfig data as mConfig_VU') #only mconfig, pconfig use 0x83
                _, mConfig_in_vu = project_api.get_mConfig_data()
                _, pConfig_in_vu = project_api.get_pConfig_data()
                compare_mConfig_data(get_mConfig=mConfig_in_vu, set_mConfig=temp_mConfig)
                compare_pConfig_data(get_pConfig=pConfig_in_vu, set_pConfig=temp_pConfig)
            
        
            logger.flow(6, 'recover mConfig pConfig')
            mConfig_in_vu_bkup.payload[0:7] = "MCONFIG".encode("ascii")
            pConfig_in_vu_bkup.payload[0:7] = "PCONFIG".encode("ascii")
            self.hw_setting.recover()
            project_api.set_mConfig_data(mConfig=mConfig_in_vu_bkup)
            project_api.set_pConfig_data(pConfig=pConfig_in_vu_bkup)
            api.init_tester_to_unit_ready(resetmode=resetmode)
            _, mConfig_in_vu = project_api.get_mConfig_data()
            _, pConfig_in_vu = project_api.get_pConfig_data()
            compare_mConfig_data(get_mConfig=mConfig_in_vu, set_mConfig=mConfig_in_vu_bkup)
            compare_pConfig_data(get_pConfig=pConfig_in_vu, set_pConfig=pConfig_in_vu_bkup)
        pass

    def step2(self) -> None:
        access_vendor_mode()
        for flow in range(7, 10+1):
            fw_value_str = ""
            flow_str = ""
            if flow == 7:
                fw_value_str = "gUfsApiStruct.mconfig->m_reserved_9"
                flow_str = "L1 mconfig Test"
            elif flow == 8:
                fw_value_str = "gUfsApiStruct.mconfig->p_reserved_9[0]"
                flow_str = "L1 pconfig Test"
            elif flow == 9:
                fw_value_str = "gUfsApiStruct.mconfig->m_reserved_9"
                flow_str = "L2 mconfig Test"
            elif flow == 10:
                fw_value_str = "gUfsApiStruct.mconfig->p_reserved_9[0]"
                flow_str = "L2 pconfig Test"
                
            logger.flow(flow, flow_str)
            addr = api.get_fw_address(fw_value_str)
            if not addr:
                logger.error_lb(f'read fw addr : {fw_value_str}')
                logger.error_fp(f'addr is None, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            addr = addr.address
            logger.info(f"read fw addr: {fw_value_str},  addr = {addr} (0x{addr:X})")
            _, data = api.read_Xmemory(sram_address=addr)
            logger.info(f"read X memory: addr = {addr} (0x{addr:X}), value = {int.from_bytes(data[0:4],'little')}")
        
            payload = bytearray(data)
            randvalue = random.randint(0, 0xFE)
            
            payload[0:4] = (randvalue).to_bytes(4, 'little')
            api.write_Xmemory(sram_address=addr, data_buffer=payload)
            if flow <= 8:
                ats_times = self.get_ast_times()
                time.sleep(15)
                ats_times_after = self.get_ast_times()
                if ats_times_after <= ats_times:
                    logger.error_lb(f'check ats_times should increase')
                    logger.error_fp(f'expect ats_times increased, but current value = {ats_times_after}, before value = {ats_times}, result Fail!')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            else:
                ExecuteCMD.StartStopUnit().assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=0x02, no_flush=0, start=0).set_option(wait_queue_empty=True).enqueue()
                ExecuteCMD.StartStopUnit().assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=0x01, no_flush=0, start=0).set_option(wait_queue_empty=True).enqueue()
                ExecuteCMD.send(QD=1,clear_on_success=True)
        
            _, data_after = api.read_Xmemory(sram_address=addr)
            value_after = int.from_bytes(data_after[0:4], 'little')
            logger.info(f"read X memory: addr = {addr} (0x{addr:X}), value = {value_after}")
            if value_after != randvalue:
                dumpfile('data_after.bin',data_after)
                dumpfile('data.bin',data)
                logger.error_lb(f'check addr value after {flow_str}')
                logger.error_fp(f'expect value match set value {randvalue}, but current value = {int.from_bytes(data_after[0:4],"little")}, before value = {int.from_bytes(data[0:4],"little")}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL        
        pass
    
    def post_process(self) -> None:
        pass
    
    def get_ast_times(self) -> int:
        payload_get = project_api.get_smart_info()
        offset_ats_timer = 0x4a8
        data_size_byte = 8
        ats_times_payload = payload_get[offset_ats_timer: offset_ats_timer + data_size_byte]
        ats_times = int.from_bytes(ats_times_payload, 'little')
        logger.info(f'ats_times = {ats_times}')
        dumpfile('smart_info.bin',payload_get)
        return ats_times

run = Pattern().run
if __name__ == "__main__":
    run()