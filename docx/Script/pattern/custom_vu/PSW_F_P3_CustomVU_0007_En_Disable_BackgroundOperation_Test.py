import package_root
import time
from typing import cast
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.api.ufs_api.descriptors.configuration_desc.functions import print_config, push_write_config
from Script.lib.sdk_lib.user.exception import G_TIMEOUT_ALL
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *

B68S_ERASE_CNT_THRESHOLD_TLC = 151

class Access_Mode(int):
    ACCESS_MODE_SLC = 0
    ACCESS_MODE_MLC = 1

class VB_group(int):
    USED_BLK_POOL_MLC = 0x11
    FREE_BLK_QUEUE_MLC = 0X1B

def check_timeout(start_time: float, timeout_min: int) -> bool:
    current_time = time.time()
    if (current_time - start_time) >= timeout_min * 60:
        return True
    else:
        return False

class Pattern(UFSTC):
    def pre_process(self) -> None:
        self._param = api.shared.param
        self._fw_geometry = api.get_fw_geometry()
        pass

    def get_vb_group_list(self, tlc_used_VB_list:list[int], tlc_free_VB_list:list[int]) -> None:
        resp, vb_info = api.ufs_api.vendor_cmd.get_vb_info()
        total_VB_count = self._fw_geometry.l52_total_vb_count
        for i in range(total_VB_count):
            four_bytes = vb_info[i * 4:(i + 1) * 4]
            integer_value = int.from_bytes(four_bytes, byteorder='little')
            vb_group = integer_value & 0x3F
            logger.info(f'VB {i}, group = {vb_group}')
            if vb_group == VB_group.USED_BLK_POOL_MLC:
                tlc_used_VB_list.append(i)
            elif vb_group == VB_group.FREE_BLK_QUEUE_MLC:
                tlc_free_VB_list.append(i)
        logger.info(f'tlc used vb: {tlc_used_VB_list}')
        logger.info(f'tlc free vb: {tlc_free_VB_list}')

    def get_device_ec(self) -> bytearray:
        resp, DebugInfo = api.ufs_api.vendor_cmd.get_debug_info()    
        resp, buffer = api.ufs_api.vendor_cmd.read_Xmemory(sram_address = DebugInfo.VB_list_cycle_address.value)    
        return buffer
    
    def set_ec(self, set_ec:bytearray) -> None:
        total_VB_count = self._fw_geometry.l52_total_vb_count
        data = bytearray(b'\xFF' * 0x4000)
        del set_ec[total_VB_count*4:]
        data[:len(set_ec)] = set_ec

        api.ufs_api.vendor_cmd.access_vendor_mode()
        vuc = ExecuteCMD.VendorCmdWrite()
        vuc.assign(length=api.DATA_SIZE_16K_BYTE, cmd_index=api.VendorCmd.GET_FW_GEOMETRY, cmd_set_type=0x0F)
        vuc.upiu.u16_cdb.b2_rsvd = api.VendorCmdRuleCdb2.CMD_IN_CDB
        vuc.upiu.u16_cdb.b6_cmd2 = 4
        vuc.data = data
        vuc.enqueue()
        ExecuteCMD.send()

    def step1(self) -> None:
        #====================normal case====================#
        logger.flow(1, 'Config WB partition')
        config_descs = api.get_config_descriptors(print=True)
        config_descs[0].header.b2_conf_desc_continue = 1
        config_descs[0].header.b17_write_booster_buffer_type = 1
        config_descs[0].header.b16_write_booster_buffer_preserve_user_space_en = 1
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = 0x1000

        for i in range(4):
            config_descs[i].header.b2_conf_desc_continue = 1 if i != 3 else 0
            push_write_config(config_descs[i], index=i)
        ExecuteCMD.send()

        logger.flow(2, 'Enable WB buffer')
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)

        logger.flow(3, 'Write for fill WB buffer')
        write_record = api.get_empty_write_record()
        start_time = time.time()
        timeout_min = 15
        while True:
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            logger.info(f'Available WB size = {ava_WB_size}')
            if ava_WB_size == 0x0:
                break

            if check_timeout(start_time, timeout_min):
                logger.error_lb('Random write for filling WB buffer')
                logger.error_fp(f'Expect available WB size change into 0x0 within {timeout_min}min but current value is 0x{ava_WB_size:02X}')
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            cmd_count = random.randint(10, 32)
            min_lun = 0
            max_lun = 0
            min_lba = 0
            max_lba = self._param.gLUCapacity[0]
            min_size = api.BLOCK4K_SIZE_64M_BYTE
            max_size = api.BLOCK4K_SIZE_128M_BYTE
            api.random_write(cmd_count=cmd_count, min_lun=min_lun, max_lun=max_lun, min_lba=min_lba, max_lba=max_lba, min_size=min_size, max_size=max_size,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)

        logger.flow(4, 'Enable WB buffer flush')
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN)

        logger.flow(5, 'Polling flush status until completed successfully and available WB size should be 0xA, record spending time')
        polling_cnt = 0
        start_time = time.time()
        while True:
            WB_flush_status = api.read_attribute(idn=api.AttributeIDN.WRITEBOOSTER_BUFFER_FLUSH_STATUS)
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            polling_cnt += 1
            logger.info(f'WB flush status = {WB_flush_status}, Available WB size = {ava_WB_size}, polling count = {polling_cnt}')
            if WB_flush_status == api.WriteBoosterBufferFlushStatus.COMPLETED:
                break
            
            if check_timeout(start_time, timeout_min):
                logger.error_lb('Enable WB flush when available WB size = 0x0 and polling WB flush status')
                logger.error_fp(f'Expect WB flush status change into 0x3(completed) within {timeout_min}min but current value is 0x{WB_flush_status:02X}')
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT

        if ava_WB_size != 0xA:
            logger.error_lb('Check available WB size when WB flush completed')
            logger.error_fp(f'Expect available WB size should be 0xA but current value is 0x{ava_WB_size:02X}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL

        #====================disable background operation====================#
        logger.flow(6, 'Disable WB buffer flush')
        api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN)

        logger.flow(7, 'Write for fill WB buffer')
        start_time = time.time()
        while True:
            if check_timeout(start_time, timeout_min):
                logger.error_lb('Random write for filling WB buffer')
                logger.error_fp(f'Expect available WB size change into 0x0 within {timeout_min}min but current value is 0x{ava_WB_size:02X}')
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            cmd_count = random.randint(10, 32)
            min_lun = 0
            max_lun = 0
            min_lba = 0
            max_lba = self._param.gLUCapacity[0]
            min_size = api.BLOCK4K_SIZE_64M_BYTE
            max_size = api.BLOCK4K_SIZE_128M_BYTE
            api.random_write(cmd_count=cmd_count, min_lun=min_lun, max_lun=max_lun, min_lba=min_lba, max_lba=max_lba, min_size=min_size, max_size=max_size,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)
            
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            logger.info(f'Available WB size = {ava_WB_size}')
            if ava_WB_size == 0:
                break        

        logger.flow(8, 'Enable WB buffer flush')
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN)
        
        logger.flow(9, 'Host issue VU 0xD0FD with value 0x00-disable all the background operations')
        project_api.issue_D0FD_disable_all_the_background_operations()

        logger.flow(10, 'Polling flush status and available WB size, expect flush status should be in progress and available WB size keep value does not descreased within polling times')
        WB_flush_status_backup = api.read_attribute(idn=api.AttributeIDN.WRITEBOOSTER_BUFFER_FLUSH_STATUS)
        ava_WB_size_backup = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
        logger.info(f'WB flush status(backup) = {WB_flush_status_backup}, Available WB size(backup) = {ava_WB_size_backup}, polling count = {polling_cnt}')
        start_time = time.time()
        while True:
            WB_flush_status = api.read_attribute(idn=api.AttributeIDN.WRITEBOOSTER_BUFFER_FLUSH_STATUS)
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            polling_cnt -= 1
            logger.info(f'WB flush status = {WB_flush_status}, Available WB size = {ava_WB_size}, polling count = {polling_cnt}')
            if WB_flush_status_backup != WB_flush_status or ava_WB_size_backup != ava_WB_size:
                logger.error_lb('Enable WB flush when available WB size = 0x0 and polling WB flush status with all the background operations disabled')
                logger.error_fp(f'Expect available WB size keep 0x{ava_WB_size_backup:02X} and WB flush status keep 0x{WB_flush_status_backup:02X}, but current available WB size = 0x{ava_WB_size:02X} and WB flush status = 0x{WB_flush_status:02X}')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            if polling_cnt == 0:
                break

        #====================enable background operation====================#
        logger.flow(11, 'Host issue VU 0xD0FD with value 0x01-enable all the background operations')
        project_api.issue_D0FD_enable_all_the_background_operations()

        logger.flow(12, 'Polling flush status until completed successfully and available WB size should be 0xA')
        start_time = time.time()
        while True:
            if check_timeout(start_time, timeout_min):
                logger.error_lb('Enable all the background operation and polling WB flush status')
                logger.error_fp(f'Expect WB flush status change into 0x3(completed) within {timeout_min}min but current value is 0x{WB_flush_status:02X}')                
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            WB_flush_status = api.read_attribute(idn=api.AttributeIDN.WRITEBOOSTER_BUFFER_FLUSH_STATUS)
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            logger.info(f'WB flush status = {WB_flush_status}, Available WB size = {ava_WB_size}')
            if WB_flush_status == api.WriteBoosterBufferFlushStatus.COMPLETED:
                break

        if ava_WB_size != 0xA:
            logger.error_lb('Check available WB size when WB flush completed')
            logger.error_fp(f'Expect available WB size should be 0xA but current value is 0x{ava_WB_size:02X}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        
        #====================VU disable background operation with powercycle reset====================#
        logger.flow(13, 'Host issue VU 0xD0FD with value 0x00-disable all the background operations')
        project_api.issue_D0FD_disable_all_the_background_operations()

        logger.flow(14, 'HW reset')
        api.init_tester_to_unit_ready(resetmode = api.Dcmd5ResetType.HW_RESET, powerdown = True)

        logger.flow(15, 'Enable WB buffer')
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)

        logger.flow(16, 'Write for fill WB buffer')
        start_time = time.time()
        while True:
            if check_timeout(start_time, timeout_min):
                logger.error_lb('Random write for filling WB buffer')
                logger.error_fp(f'Expect available WB size change into 0x0 within {timeout_min}min but current value is 0x{ava_WB_size:02X}')
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            cmd_count = random.randint(10, 32)
            min_lun = 0
            max_lun = 0
            min_lba = 0
            max_lba = self._param.gLUCapacity[0]
            min_size = api.BLOCK4K_SIZE_64M_BYTE
            max_size = api.BLOCK4K_SIZE_128M_BYTE
            api.random_write(cmd_count=cmd_count, min_lun=min_lun, max_lun=max_lun, min_lba=min_lba, max_lba=max_lba, min_size=min_size, max_size=max_size,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)
            
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            logger.info(f'Available WB size = {ava_WB_size}')
            if ava_WB_size == 0:
                break              

        logger.flow(17, 'Enable WB buffer flush')
        api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_BUFFER_FLUSH_EN)

        logger.flow(18, 'Polling flush status until completed successfully and available WB size should be 0xA')
        start_time = time.time()
        while True:
            if check_timeout(start_time, timeout_min):
                logger.error_lb('Enable WB flush when available WB size = 0x0 and polling WB flush status')
                logger.error_fp(f'Expect WB flush status change into 0x3(completed) within {timeout_min}min but current value is 0x{WB_flush_status:02X}')
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            WB_flush_status = api.read_attribute(idn=api.AttributeIDN.WRITEBOOSTER_BUFFER_FLUSH_STATUS)
            ava_WB_size = api.read_attribute(idn=api.AttributeIDN.AVAILABLE_WRITEBOOSTER_BUFFER_SIZE)
            logger.info(f'WB flush status = {WB_flush_status}, Available WB size = {ava_WB_size}')
            if WB_flush_status == api.WriteBoosterBufferFlushStatus.COMPLETED:
                break

        if ava_WB_size != 0xA:
            logger.error_lb('Check available WB size when WB flush completed')
            logger.error_fp(f'Expect available WB size should be 0xA but current value is 0x{ava_WB_size:02X}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL

        #====================VU disable foreground operation====================#
        logger.flow(19, 'Get current vb erase count table and backup')
        backup_ec_value = self.get_device_ec()
        dumpfile(filename='backup_ec_value', data=backup_ec_value)

        for disable_FG_GC_case in range(2):
            logger.flow(20, 'Set all VB EC as 1 for testing pre-condition')
            set_EC_value = 1
            value_bytes = set_EC_value.to_bytes(4, byteorder='little', signed=False)
            data = bytearray(b'\xFF' * 0x4000)
            data[:(self._fw_geometry.l52_total_vb_count * 4)] = value_bytes * self._fw_geometry.l52_total_vb_count
            setting_ec_value = data.copy()
            self.set_ec(data)

            logger.flow(21, 'Config again to set pre-condition')
            for i in range(4):
                config_descs[i].header.b2_conf_desc_continue = 1 if i != 3 else 0
                push_write_config(config_descs[i], index=i)
            ExecuteCMD.send()

            logger.flow(22, 'Sequential write 5 TLC VB size')
            write_record = api.get_empty_write_record()
            tlc_vb_size = self._fw_geometry.l88_vb_size_u1 >> 3 # menas (var * 512 / 4096) to change unit from sector to blocks
            total_size = 5 * tlc_vb_size
            lba = random.randint(0, self._param.gUnit[0].q11_logical_block_count - total_size)
            chunk_size = api.BLOCK4K_SIZE_128M_BYTE
            api.sequential_write(lun=0, start_lba=lba, total_size=total_size, chunk_size=chunk_size, fua = 0,
                                    need_compare=False, compare_method=api.CompareMethod.SW_COMPARE, write_record=write_record)

            logger.flow(23, 'Get TLC used/free vb list')
            tlc_used_VB_list:list[int] = []
            tlc_free_VB_list:list[int] = []
            self.get_vb_group_list(tlc_used_VB_list=tlc_used_VB_list, tlc_free_VB_list=tlc_free_VB_list)

            logger.flow(24, 'Check BKOPS status should be 0')
            BKOPS_status = api.read_attribute(idn=api.AttributeIDN.BG_OP_STATUS)
            logger.info(f'BKOPS status = {BKOPS_status}')
            if BKOPS_status != 0x0:
                logger.error_lb('Check BKOPS status after write 5 TLC VB size before setting EC to trigger WL GC')
                logger.error_fp(f'Expect BKOPS status should be 0 but current value is {BKOPS_status}')
                logger.info('Recover ec')
                self.set_ec(set_ec=backup_ec_value)
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL

            logger.flow(25, 'Set TLC used/free vb EC to trigger WL GC')
            expect_used_VB_erase_count = 1
            expect_free_VB_erase_count = expect_used_VB_erase_count + B68S_ERASE_CNT_THRESHOLD_TLC + 50
            logger.info(f'expect_used_VB_erase_count = {expect_used_VB_erase_count}, expect_free_VB_erase_count = {expect_free_VB_erase_count}')

            erase_bytes = expect_used_VB_erase_count.to_bytes(4, byteorder='little', signed=False)
            for group_idx in tlc_used_VB_list:
                start = group_idx * 4
                end   = start + 4
                setting_ec_value[start:end] = erase_bytes

            erase_bytes = expect_free_VB_erase_count.to_bytes(4, byteorder='little', signed=False)
            for group_idx in tlc_free_VB_list:
                start = group_idx * 4
                end   = start + 4
                setting_ec_value[start:end] = erase_bytes
            dumpfile(filename='setting_ec_value', data=setting_ec_value)
            self.set_ec(set_ec=setting_ec_value)

            logger.flow(26, 'Host issue VU 0xD0FD with value 0x02-disable all the foreground operations')
            project_api.issue_D0FD_disable_all_the_foreground_operations()

            logger.flow(27, 'Check BKOPS status should not be 0 and polling BKOPS status 1 min should keep value')
            BKOPS_status_backup = api.read_attribute(idn=api.AttributeIDN.BG_OP_STATUS)
            logger.info(f'BKOPS status = {BKOPS_status_backup}')
            if BKOPS_status_backup == 0x0:
                logger.error_lb('Check BKOPS status should not be 0 when WL GC triggered and disable foreground GC')
                logger.error_fp(f'Expect BKOPS status should not be 0 but current value is {BKOPS_status_backup}')
                logger.info('Recover ec')
                self.set_ec(set_ec=backup_ec_value)
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL

            start_time = time.time()
            while True:
                if check_timeout(start_time, 1):
                    break
                BKOPS_status = api.read_attribute(idn=api.AttributeIDN.BG_OP_STATUS)
                logger.info(f'BKOPS status = {BKOPS_status}')
                if BKOPS_status != BKOPS_status_backup:
                    logger.error_lb('Check BKOPS should keep value when foreground GC disabled')
                    logger.error_fp(f'Expect BKOPS status should be {BKOPS_status_backup} but current value is {BKOPS_status}')
                    logger.info('Recover ec')
                    self.set_ec(set_ec=backup_ec_value)
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL

            if disable_FG_GC_case == 0:
                logger.flow(28, 'Host issue VU 0xD0FD with value 0x03-enable all the foreground operations')
                project_api.issue_D0FD_enable_all_the_foreground_operations()
            else:
                logger.flow(28, 'HW reset to reset foreground operations as enabled')
                api.init_tester_to_unit_ready(resetmode = api.Dcmd5ResetType.HW_RESET, powerdown = False)

            logger.flow(29, 'Polling BKOPS status should change into 0 within 1 min')
            start_time = time.time()
            while True:
                if check_timeout(start_time, 1):
                    logger.error_lb('Check BKOPS should change into 0 when foreground GC enabled')
                    logger.error_fp(f'Expect BKOPS status should be 0 within 1 min but current value is {BKOPS_status}')
                    logger.info('Recover ec')
                    self.set_ec(set_ec=backup_ec_value)
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL
                BKOPS_status = api.read_attribute(idn=api.AttributeIDN.BG_OP_STATUS)
                logger.info(f'BKOPS status = {BKOPS_status}')
                if BKOPS_status == 0:
                    break

            logger.flow(30, 'Recover ec and HW reset')
            self.set_ec(set_ec=backup_ec_value)
            api.init_tester_to_unit_ready(resetmode = api.Dcmd5ResetType.HW_RESET, powerdown = True)

        #====================VU disable BG trim====================#

        logger.flow(31, 'Random write some data')
        cmd_count = 100
        min_lun = 0
        max_lun = 0
        min_lba = 0
        max_lba = self._param.gLUCapacity[0]
        min_size = api.BLOCK4K_SIZE_64M_BYTE
        max_size = api.BLOCK4K_SIZE_128M_BYTE
        api.random_write(cmd_count=cmd_count, min_lun=min_lun, max_lun=max_lun, min_lba=min_lba, max_lba=max_lba, min_size=min_size, max_size=max_size,
                    need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)

        logger.flow(32, 'disable BG trim')
        project_api.issue_D0FD_disable_BG_trim()

        try:
            logger.flow(33, 'Format unit and expected timeout occur, device shall stuck')
            ExecuteCMD.FormatUnit().assign(lun=0).enqueue()
            ExecuteCMD.send()
            logger.error_lb('Issue format unit after VU disable BG trim')
            logger.error_fp('Expected timeout occur, device shall stuck but response is success')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        except G_TIMEOUT_ALL:
            ExecuteCMD.clear()

        logger.flow(34, 'HW reset to reset foreground operations as enabled')
        api.init_tester_to_unit_ready(resetmode = api.Dcmd5ResetType.HW_RESET, powerdown = False)

        logger.flow(35, 'Format unit and device response shall be success')
        ExecuteCMD.FormatUnit().assign(lun=0).enqueue()
        ExecuteCMD.send()

        logger.flow(36, 'Random write some data')
        cmd_count = 100
        min_lun = 0
        max_lun = 0
        min_lba = 0
        max_lba = self._param.gLUCapacity[0]
        min_size = api.BLOCK4K_SIZE_64M_BYTE
        max_size = api.BLOCK4K_SIZE_128M_BYTE
        api.random_write(cmd_count=cmd_count, min_lun=min_lun, max_lun=max_lun, min_lba=min_lba, max_lba=max_lba, min_size=min_size, max_size=max_size,
                    need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)

        logger.flow(37, 'disable BG trim')
        project_api.issue_D0FD_disable_BG_trim()

        logger.flow(38, 'enable BG trim')
        project_api.issue_D0FD_enable_BG_trim()

        logger.flow(39, 'Format unit and device response shall be success')
        ExecuteCMD.FormatUnit().assign(lun=0).enqueue()
        ExecuteCMD.send()

        pass

    def post_process(self) -> None:
        pass
    
run = Pattern().run
if __name__ == "__main__":
    run()