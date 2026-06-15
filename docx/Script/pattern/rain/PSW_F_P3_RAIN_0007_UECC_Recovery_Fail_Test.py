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
import copy

class Pattern(UFSTC):
    def pre_process(self) -> None:
        self.TestNormalLun, self.TestEM1Lun, self.TestWBLun, self.flash_setting, self.fw_geometry = rain_pattern_precondition()
        self.max_ce, self.max_plane, self.max_pageline = get_geometry_parameter()
        self.write_record = api.get_empty_write_record()
        pass

    def step1(self) -> None:
        for testMode in [TestMode.TEST_TLC, TestMode.TEST_SLC, TestMode.TEST_WB, TestMode.TEST_PTE]:
            for closed_vb in [False, True]:
                lun, mode_str = get_general_parameter(testMode)            
                rain_goup_cnt, rain_user = get_rain_parity_parameter(testMode)
                logger.info(f'============ Test {mode_str} {"closed" if closed_vb else "open"} VB ============')
                logger.flow(1, f'Write until {mode_str} VB has enough data')
                if rain_user == project_api.RainUser.WB_RAIN:
                    api.set_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
                else:
                    api.clear_flag(idn=api.FlagIDN.WRITEBOOSTER_EN)
                
                if closed_vb:
                    if testMode == TestMode.TEST_PTE:
                        continue
                    cursor = get_specific_open_vb_cursor(testMode)
                    last_lba, vb = create_closed_vb(testMode=testMode, lun=lun, write_record=self.write_record)
                else:
                    last_lba, cursor = write_data_more_than_N_pageline(pageline_cnt=3, lun=lun, testMode=testMode, write_record=self.write_record)
                
                logger.flow(2, f'inject 2 UECC in same rain group')
                if testMode == TestMode.TEST_PTE:
                    uecc_pca = self.inject_2_UECC_by_open_vb_info(cursor=cursor, testMode = testMode)
                else:
                    uecc_pca = self.inject_2_UECC_by_lun(lun=lun)

                logger.flow(3, f'direct read and check read status is UECC')
                for idx,(pca, SLC_en) in enumerate(uecc_pca):
                    dire_read_payload = direct_read_raw_data_and_check_status(pca=pca, SLC_enable=SLC_en, expect_status= project_api.ReadStatus.UECC, REH_Enable=True)

                logger.flow(4, f'Erase all data')
                reconfig_to_erase_all_lun(write_record=self.write_record)
                pass

    def post_process(self) -> None:
        pass

    def inject_2_UECC_by_lun(self, lun:int) -> List[tuple[project_api.physical_address_info, bool]]:
        SLC_en = lun != self.TestNormalLun
        uecc_pca:List[tuple[project_api.physical_address_info, bool]] = []
        invalid_plane_list = get_invalid_plane_list()
        pca = get_PCA_and_print(lun=lun, lba=0)
        uecc_pca.append((copy.deepcopy(pca), SLC_en))
        pca = get_PCA_and_print(lun=lun, lba=api.BLOCK4K_SIZE_16K_BYTE)
        uecc_pca.append((copy.deepcopy(pca), SLC_en))
        for pca, SLC_en  in uecc_pca:
            inject_UECC(pca=pca, SLC_enable=SLC_en)
        return uecc_pca
    
    def inject_2_UECC_by_open_vb_info(self, cursor:api.OpenVBInfoUnit, testMode:TestMode) -> List[tuple[project_api.physical_address_info, bool]]:
        SLC_en = testMode != TestMode.TEST_TLC
        uecc_pca:List[tuple[project_api.physical_address_info, bool]] = []
        invalid_plane_list = get_invalid_plane_list()
        block = cursor.logical_vb.value
        ce_plane = self.max_plane * cursor.first_empty_CE.value + cursor.first_empty_plane.value - 1
        pageline = cursor.first_empty_physical_page.value
        if invalid_plane_list[block] == ce_plane:
            ce_plane -= 1
        if ce_plane < 0:
            ce_plane += self.max_plane*self.max_ce
            pageline -= 1

        pca = project_api.physical_address_info()
        pca.die.value = ce_plane // self.max_plane
        pca.plane.value = ce_plane % self.max_plane
        pca.physical_block_number_w_BBT.value = block
        pca.page.value = pageline

        uecc_pca.append((copy.deepcopy(pca), SLC_en))
        
        ce_plane -= 1
        if invalid_plane_list[block] == ce_plane:
            ce_plane -= 1
        if ce_plane < 0:
            ce_plane += self.max_plane*self.max_ce
            pageline -= 1

        pca.die.value = ce_plane // self.max_plane
        pca.plane.value = ce_plane % self.max_plane
        uecc_pca.append((copy.deepcopy(pca), SLC_en))
        for pca, SLC_en  in uecc_pca:
            inject_UECC(pca=pca, SLC_enable=SLC_en)
        return uecc_pca


run = Pattern().run
if __name__ == "__main__":
    run()