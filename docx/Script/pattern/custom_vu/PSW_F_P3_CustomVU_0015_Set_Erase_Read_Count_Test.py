import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from typing import Dict, List, cast, Optional
from Script.api.ufs_api.rpmb.rpmb import RPMB
from Script.api.ufs_api.vendor_cmd.functions import *
from time import sleep

ENG2_WA = True

class Pattern(UFSTC):
    def pre_process(self) -> None:
        self.fw_geometry = api.get_fw_geometry()
        _, self.debug_info = api.get_debug_info()
        self.flash_setting_buffer = api.get_flash_setting_buffer()
        self.flash_setting = FlashSetting()
        self.flash_setting.from_bytes(self.flash_setting_buffer)
        dumpfile('debug_info.bin', self.debug_info.payload)
        pass
    
    def step1(self) -> None:
        logger.flow(1, 'get EC table / RC table for backup')
        _, self.erase_cnt_buffer_backup = api.read_Xmemory(sram_address=self.debug_info.VB_list_cycle_address.value)
        self.read_cnt_of_vb_backup = project_api.get_all_VB_read_count()
        pass
    
    def step2(self) -> None:
        logger.flow(2, 'set EC table in ram')
        random_value = random.randint(0x1, 0x1000)
        payload = self.get_payload_with_value(random_value)
        project_api.set_all_VB_erase_count(data_payload=payload, set_in_ram=True)
        _, erase_cnt_buffer = api.read_Xmemory(sram_address=self.debug_info.VB_list_cycle_address.value)
        for vb in range(self.fw_geometry.l52_total_vb_count):
            erase_cnt_from_Xmemory = int.from_bytes(erase_cnt_buffer[vb*4 : (vb+1)*4], 'little')
            if erase_cnt_from_Xmemory != random_value:
                dumpfile('erase_cnt_buffer_from_SRAM.bin', erase_cnt_buffer)
                logger.error_lb(f'check erase cnt of VB{vb}')
                logger.error_fp(f'expect EC from SRAM equal to random_value, but SRAM value = {erase_cnt_from_Xmemory}, random_value value = {random_value}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            
        api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET)
        _, erase_cnt_buffer = api.read_Xmemory(sram_address=self.debug_info.VB_list_cycle_address.value)
        if erase_cnt_buffer != self.erase_cnt_buffer_backup:
            dumpfile('erase_cnt_buffer_from_SRAM.bin', erase_cnt_buffer)
            dumpfile('erase_cnt_buffer_from_SRAM_backup.bin', self.erase_cnt_buffer_backup)
            logger.error_lb(f'check erase cnt recovered after SPOR')
            logger.error_fp(f'expect EC from SRAM equal to erase_cnt_buffer_backup but result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        pass
    
    def step3(self) -> None:
        logger.flow(3, 'set EC table')
        random_value = random.randint(0x1, 0x1000)
        payload = self.get_payload_with_value(random_value)
        project_api.set_all_VB_erase_count(data_payload=payload, set_in_ram=False)
            
        api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET)
        _, erase_cnt_buffer = api.read_Xmemory(sram_address=self.debug_info.VB_list_cycle_address.value)
        for vb in range(self.fw_geometry.l52_total_vb_count):
            erase_cnt_from_Xmemory = int.from_bytes(erase_cnt_buffer[vb*4 : (vb+1)*4], 'little')
            if erase_cnt_from_Xmemory != random_value:
                dumpfile('erase_cnt_buffer_from_SRAM.bin', erase_cnt_buffer)
                logger.error_lb(f'check erase cnt of VB{vb}')
                logger.error_fp(f'expect EC from SRAM equal to random_value, but SRAM value = {erase_cnt_from_Xmemory}, random_value value = {random_value}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        pass
    
    def step4(self) -> None:
        logger.flow(4, 'recover EC table')
        project_api.set_all_VB_erase_count(data_payload=self.erase_cnt_buffer_backup, set_in_ram=False)
        pass

    def post_process(self) -> None:
        pass
    
    def get_payload_with_value(self, value:int) -> bytearray:
        field_offset = 4
        payload = bytearray(DATA_SIZE_4K_BYTE)
        bytes_val = value.to_bytes(field_offset, 'little')
        for i in range(self.fw_geometry.l52_total_vb_count):
            payload[i * field_offset : (i+1)*field_offset] = bytes_val
        return payload



run = Pattern().run
if __name__ == "__main__":
    run()