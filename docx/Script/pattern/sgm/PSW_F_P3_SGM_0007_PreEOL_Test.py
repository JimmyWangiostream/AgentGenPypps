import package_root
from Script import api
from Script.api import cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random

from Script.api.exception import *
from Script.api.ufs_api.vendor_cmd.functions import set_mconfig, get_mconfig
from Script.api.ufs_api.defines.constant_define import *
from Script.pattern.sgm.mutual_fun import *

from typing import TypeAlias, cast

class TestCases(IntEnum):
    TLC_L2 = 0
    WB_L2 = 1
    SLC_L2 = 2

class Pattern(UFSTC):
    def make_a_bb_cnt(self) -> None:
        group_list = ["FREE_BLK_QUEUE_MLC"]
        free_block = choose_free_block(group_list)
        case = random.randint(0,10)
        flashsetting = api.get_flash_setting() 
        self.CE = flashsetting.FLH_Quantity * (BIT0 << flashsetting.Parallel)
        self.PLANE_PER_DIE = flashsetting.Plane_Per_Die
        D017_param = choose_D017_param(free_block, case, self.CE, self.PLANE_PER_DIE)
        project_api.issue_D017_to_create_SGM_fail(D017_param)
        result = project_api.issue_404B_to_erase_with_SGM_enabled(D017_param.block.value,enable_retirement=1)
    def get_preeol(self) -> None:
        dev_desc = api.get_device_health_descriptor()
        self.pre_eol = dev_desc.b2_pre_eol_info        
    def show_device_bb_info(self)  ->None:
        self.bbtmax_revoke_cnt = read_fw_value('gUfsApiStruct.ftl->bbt.max_revoke_cnt')
        self.revoke_cnt = read_fw_value('gUfsApiStruct.ftl->bbt.revoke_cnt')
        dev_desc = api.get_device_health_descriptor()
        self.pre_eol = dev_desc.b2_pre_eol_info
        logger.info(f'bbtmax_revoke_cnt = {self.bbtmax_revoke_cnt}')# 25
        logger.info(f'revoke_cnt = {self.revoke_cnt}')#         
        logger.info(f'PreEOL = {self.pre_eol}')        
    def pre_process(self) -> None:
        # GME Test
        self.hw_setting = api.HwSetting.get_instance()
        self.hw_setting.update_from_device()          
        backup_val = self.hw_setting.get_local_val(api.HwSettingField.FW_DEBUG_MODE)
        logger.info(f'set hw setting debug mode = 0')   
        self.hw_setting.set_local_val(api.HwSettingField.FW_DEBUG_MODE, 0)                  
        self.hw_setting.set_to_device()          
        timeout_min = 240
        start_time = time.time()

        
        target_val = 4 
        self.show_device_bb_info() 
        while(self.pre_eol<target_val):
            try:
                self.make_a_bb_cnt()
                self.show_device_bb_info() 
                if check_timeout(start_time, timeout_min):
                    raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            
            except:
                logger.info('send command TO')
                ExecuteCMD.clear()                      
                init_tester_to_unit_ready(Dcmd5ResetType.HW_RESET)
                self.get_preeol()
                if self.pre_eol != target_val:
                    raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
                break
        pass        
        # while(self.pre_eol<target_val):
        #     self.make_a_bb_cnt()
        #     self.show_device_bb_info() 
        #     if check_timeout(start_time, timeout_min):
        #         raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
        #     assert_num = api.get_fw_assert_number()
        #     if assert_num != 0:
        #         init_tester_to_unit_ready(Dcmd5ResetType.HW_RESET)
        #         self.show_device_bb_info()
        #         if self.pre_eol != target_val:
        #             raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
        #         break
        # pass

        open_card()
        self.hw_setting.set_local_val(api.HwSettingField.FW_DEBUG_MODE, backup_val)                  
        self.hw_setting.set_to_device()  
        pass
    def step1(self) -> None:
        return


    def post_process(self) -> None:

        pass


run = Pattern().run
if __name__ == "__main__":
    run()