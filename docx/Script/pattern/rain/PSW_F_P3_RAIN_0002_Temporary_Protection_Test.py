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

DEBUG_RAW_DATA = False

class Pattern(UFSTC):  
    def pre_process(self) -> None:
        self.TestNormalLun, self.TestEM1Lun, self.TestWBLun, self.flash_setting, self.fw_geometry = rain_pattern_precondition()
        self.max_ce, self.max_plane, self.max_pageline = get_geometry_parameter()
        self.write_record = api.get_empty_write_record()
        self.UECC_pca:List[tuple[project_api.physical_address_info, bool]] = []
        pass

    def step1(self) -> None:
        logger.flow(1, 'Write TLC data more than 8 pagelines')
        lun = self.TestNormalLun
        testMode=TestMode.TEST_TLC
        last_lba, cursor = write_data_more_than_N_pageline(pageline_cnt=8, lun=lun, testMode=testMode, write_record=self.write_record)
        self.UECC_pca.append((get_PCA_and_print(lun=lun, lba=last_lba//2), False))
        pass

    def step2(self) -> None:
        logger.flow(2, 'Write WB data more than 8 pagelines')
        lun = self.TestWBLun
        testMode=TestMode.TEST_WB
        last_lba, cursor = write_data_more_than_N_pageline(pageline_cnt=8, lun=lun, testMode=testMode, write_record=self.write_record)
        self.UECC_pca.append((get_PCA_and_print(lun=lun, lba=last_lba//2), True))
        pass
    
    def step3(self) -> None:
        logger.flow(3, 'Write EM1 data more than 8 pagelines')
        lun = self.TestEM1Lun
        testMode=TestMode.TEST_SLC
        last_lba, cursor = write_data_more_than_N_pageline(pageline_cnt=8, lun=lun, testMode=testMode, write_record=self.write_record)
        self.UECC_pca.append((get_PCA_and_print(lun=lun, lba=last_lba//2), True))
        pass

    def step4(self) -> None:
        logger.flow(4, 'Inject UECC in each VB type')
        for pca, slc_en in self.UECC_pca:
            inject_UECC(pca=pca, SLC_enable=slc_en)
            dire_read_payload = direct_read_raw_data_and_check_status(pca=pca, SLC_enable=slc_en, expect_status=project_api.ReadStatus.UECC)
        pass

    def step5(self) -> None:
        logger.flow(5, 'SPOR')
        api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET, powerdown=False)
        
    def step6(self) -> None:
        logger.flow(6, 'Compare data')
        read_compare_rain_result(write_record=self.write_record)

    def post_process(self) -> None:
        pass

run = Pattern().run
if __name__ == "__main__":
    run()