import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.pattern.rain.mutual_fun import *

class Pattern(UFSTC):
    def pre_process(self) -> None:       
        self.TestNormalLun, self.TestEM1Lun, self.TestWBLun, self.flash_setting, self.fw_geometry = rain_pattern_precondition()
        self.max_ce, self.max_plane, self.max_pageline = get_geometry_parameter()
        self.write_record = api.get_empty_write_record()
        self._param = shared.param
        pass

    def step1(self) -> None:
        for testMode in [TestMode.TEST_TLC, TestMode.TEST_SLC, TestMode.TEST_WB]:
            SLC_en = testMode != TestMode.TEST_TLC
            Table_and_S_CHK_rain = cast(int, project_api.RainVB.ALL)
            Host_Permanent_Rain = cast(int, project_api.RainVB.ALL)
            Host_Simple_Rain = cast(int, project_api.RainVB.ALL)
            host_full_block_protection_rain = cast(int, project_api.RainVB.ALL)
            
            lun, mode_str = get_general_parameter(testMode)            
            rain_flush_swap, data_recovery = get_rain_enable_disable_parameter(testMode)            
            rain_goup_cnt, rain_user = get_rain_parity_parameter(testMode)            
            logger.info(f'============ Test {mode_str} VB ============')
            if rain_user == project_api.RainUser.WB_RAIN:
                api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
            else:
                api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
                
            logger.flow(1, f'issue VU D08B BYTE 16 host full block protection rain Disable BIT0/1/2')
            host_full_block_protection_rain &= ~cast(int, rain_flush_swap)
            project_api.issue_D08B_to_enable_or_disable_Rain(Table_and_S_CHK_rain, Host_Permanent_Rain, Host_Simple_Rain, host_full_block_protection_rain)
            _, rain_info = project_api.issue_4054_to_get_rain_info(currentCE=self.max_ce)
            print_rain_info(rain_info=rain_info)
            
            logger.flow(2, f'write {mode_str} data more than 6 pageline')
            last_lba, cursor = write_data_more_than_N_pageline(pageline_cnt=6, lun=lun, testMode=testMode, write_record=self.write_record)
            
            logger.flow(3, f'SPOR')
            api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET, powerdown=False)
            host_full_block_protection_rain = cast(int, project_api.RainVB.ALL)
            
            logger.flow(4, f'issue VU 4055 to check if no parity')
            _, fw_spare_list, get_parity = project_api.issue_4055_to_get_rain_parity(rain_user=rain_user, group=0)
            if get_parity[0:8] != bytearray(8):
                logger.error_lb(f'issue VU4055 to get parity')
                logger.error_fp(f'expect parity is empty after disable rain, but get_parity = {format_bytearray(get_parity[0:8])}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            
            logger.flow(5, f'Erase all data')
            reconfig_to_erase_all_lun(write_record=self.write_record)
                
            logger.flow(6, f'write {mode_str} data more than 6 pageline')
            cursor = get_specific_open_vb_cursor(testMode)
            if cursor.logical_vb.value == 0xFFFFFFFF:
                cursor.first_empty_physical_page.value = 0
            pageline_cnt = cursor.first_empty_physical_page.value + 6
            if rain_user == project_api.RainUser.WB_RAIN:
                api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
            else:
                api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
            last_lba, cursor = write_data_more_than_N_pageline(pageline_cnt=pageline_cnt, lun=lun, testMode=testMode, write_record=self.write_record)
            
            logger.flow(7, f'Inject UECC on the written page')
            pca = get_PCA_and_print(lun=lun, lba=0)
            inject_UECC(pca=pca, SLC_enable=SLC_en)
            
            logger.flow(8, f'SPOR')
            api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET, powerdown=False)
            
            logger.flow(9, f'issue VU D08B BYTE 16 host full block protection rain Disable BIT4/5/6')
            host_full_block_protection_rain &= ~cast(int, data_recovery)
            project_api.issue_D08B_to_enable_or_disable_Rain(Table_and_S_CHK_rain, Host_Permanent_Rain, Host_Simple_Rain, host_full_block_protection_rain)
            _, rain_info = project_api.issue_4054_to_get_rain_info(currentCE=self.max_ce)
            print_rain_info(rain_info=rain_info)
            
            logger.flow(10, f'read status expect UECC')
            dire_read_payload = direct_read_raw_data_and_check_status(pca=pca, SLC_enable=SLC_en, expect_status= project_api.ReadStatus.UECC, REH_Enable=True)
            
            logger.flow(11, f'issue VU D08B BYTE 16 host full block protection rain Enable BIT4/5/6')
            host_full_block_protection_rain |= cast(int, data_recovery)
            project_api.issue_D08B_to_enable_or_disable_Rain(Table_and_S_CHK_rain, Host_Permanent_Rain, Host_Simple_Rain, host_full_block_protection_rain)
            _, rain_info = project_api.issue_4054_to_get_rain_info(currentCE=self.max_ce)
            print_rain_info(rain_info=rain_info)
            
            logger.flow(12, f'read compare expect pass')
            read_compare_rain_result(write_record=self.write_record, expect_error=False)
        pass
    
    def post_process(self) -> None:
        pass
    

run = Pattern().run
if __name__ == "__main__":
    run()