import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.pattern.read_scan.mutual_fun import *
from typing import Any
import time
from Script.project_api.functions import get_physical_layout

class Pattern(UFSTC):
    def pre_process(self) -> None:
        config_lun(normal_list=[0], em1_list=[1])
        self.write_record = api.get_empty_write_record()
        _flash_setting = api.get_flash_setting()
        _fw_geometry = api.get_fw_geometry()
        self.max_ce = _flash_setting.Max_Fdevice
        self.max_plane = _flash_setting.Plane_Per_Die
        self.pageline_block = self.max_ce * self.max_plane * api.BLOCK4K_SIZE_16K_BYTE
        self.WL_block = self.pageline_block * 4 * 3
        self.tlc_vb_size = (_fw_geometry.l88_vb_size_u1 * 512 // 4096)
        pass

    def step1(self) -> None:
        logger.flow(1, 'Write TLC data up to 15 WL')
        self.lba = 0
        total_size = 15 * self.WL_block
        api.sequential_write(lun=0, start_lba=self.lba, total_size=total_size, chunk_size=api.WRITE_10_MAX_BLOCK_LEN, fua = 1,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=self.write_record)
        self.lba += total_size
        _, self.open_vb_info = api.get_open_vb_info()        
        print_open_vb_info_cursor(self.open_vb_info.TLC_L2, "TLC_L2")
        pca = get_PCA_and_print(lun = 0, lba=0)
        self.VB = pca.virtual_block_number.value
        pass
    
    def step2(self) -> None:
        logger.flow(2, 'read status in vu 40BF and check status = 0')
        status = project_api.check_if_current_VB_scan_in_progress_completed(VB=self.VB)
        if status != 0:
            logger.error_lb(f'check status in vu 40BF')
            logger.error_fp(f'expect status equal to 0 when LWWL = 14, but current value = {status}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        pass
        
    def step3(self) -> None:
        logger.flow(3, 'inject UECC in WL0 and WL1 and WL3 and WL9')
        pca = get_PCA_and_print(lun=0, lba=0)
        inject_UECC(pca=pca)
        pca = get_PCA_and_print(lun=0, lba=self.WL_block+1 + api.BLOCK4K_SIZE_16K_BYTE)
        inject_UECC(pca=pca)
        pca = get_PCA_and_print(lun=0, lba=self.WL_block*3+1 + api.BLOCK4K_SIZE_16K_BYTE * 2)
        inject_UECC(pca=pca)
        pca = get_PCA_and_print(lun=0, lba=self.WL_block*9+1 + self.pageline_block*3 + + api.BLOCK4K_SIZE_16K_BYTE * 3)
        inject_UECC(pca=pca)
        pass
        
    def step4(self) -> None:
        logger.flow(4, 'Write TLC data up to 16 WL')
        total_size = 16 * self.WL_block - self.lba
        api.sequential_write(lun=0, start_lba=self.lba, total_size=total_size, chunk_size=api.WRITE_10_MAX_BLOCK_LEN, fua = 1,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=self.write_record)
        self.lba += total_size
        _, self.open_vb_info = api.get_open_vb_info()        
        print_open_vb_info_cursor(self.open_vb_info.TLC_L2, "TLC_L2")
        pass
        
    def step5(self) -> None:
        logger.flow(5, 'SSU Sleep and Awake')
        ssu_sleep_and_active()
        logger.info('SSU Sleep and Awake completed')
        pass
        
    def step6(self) -> None:
        logger.flow(6, 'read status in vu 40BF and check status = 1 and check PageList only WL%3==0 been shown')
        status = project_api.check_if_current_VB_scan_in_progress_completed(VB=self.VB)
        if status != 1:
            logger.error_lb(f'check status in vu 40BF')
            logger.error_fp(f'expect status equal to 1 when LWWL = 15, but current value = {status}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
                
        PageList = project_api.get_Normal_VB_Scan_Pages(RSTriggerBy=project_api.RSTriggerBy.other)
        for page in range(3312):
            pageline, WL_type, phy_WL, SubBlock, FlushGroup, TwoWLGroup, RainGoup = get_physical_layout(pageline=page, block_type="TLC")
            if phy_WL % 3 ==0 and  page in PageList:
                PageList.remove(page)
        if PageList:
            logger.error_lb(f'check PageList in vu 40BF')
            logger.error_fp(f'expect page only scan WL%3==0, but current value = {PageList} not as expected, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        pass
        
        self.old_error_detected_WLs = project_api.get_gc_read_scan_released_scan_pageline()
        if len(self.old_error_detected_WLs) != 2:
            logger.error_lb(f'check error_detected_WLs in vu 40BF')
            logger.error_fp(f'expect error_detected_WLs cnt equal to 2 when read scan occur, but current value = {len(self.old_error_detected_WLs)}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL

        if self.old_error_detected_WLs[0] != 0:
            logger.error_lb(f'check error_detected_WLs in vu 40BF')
            logger.error_fp(f'expect error_detected_WLs equal to 0 when read scan occur, but current value = {self.old_error_detected_WLs[0]}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        
        if self.old_error_detected_WLs[1] != 3:
            logger.error_lb(f'check error_detected_WLs in vu 40BF')
            logger.error_fp(f'expect error_detected_WLs equal to 3 when read scan occur, but current value = {self.old_error_detected_WLs[1]}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        pass
    
    def step7(self) -> None:
        logger.flow(7, 'inject UECC in WL6')
        pca = get_PCA_and_print(lun=0, lba=self.WL_block*6+1)
        inject_UECC(pca=pca)
        pass
    
    def step8(self) -> None:
        logger.flow(8, 'Write TLC data to the last pageline in VB')
        total_size = self.tlc_vb_size - self.lba - 16
        api.sequential_write(lun=0, start_lba=self.lba, total_size=total_size, chunk_size=api.WRITE_10_MAX_BLOCK_LEN, fua = 1,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=self.write_record)
        self.lba += total_size
        pass
    
    def step9(self) -> None:
        logger.flow(9, 'POR')
        api.init_tester_to_unit_ready(api.Dcmd5ResetType.HW_RESET, powerdown=True)
        _, self.open_vb_info_new = api.get_open_vb_info()        
        print_open_vb_info_cursor(self.open_vb_info_new.TLC_L2, "TLC_L2")
        pass
    
    def step10(self) -> None:
        logger.flow(10, 'read status in vu 40BF and check status = 0 and ERROR Detected pageline includes WL0, WL3, WL9')
        status = project_api.check_if_current_VB_scan_in_progress_completed(VB=self.VB)
        if status != 0:
            logger.error_lb(f'check status in vu 40BF')
            logger.error_fp(f'expect status equal to 0 after POR, but current value = {status}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        
        # APL_flag = project_api.get_APL_flag_of_VB(log_VB=self.VB)
        if self.open_vb_info_new.TLC_L2.logical_vb.value == self.open_vb_info.TLC_L2.logical_vb.value:
            new_error_detected_WLs = project_api.get_gc_read_scan_released_scan_pageline()
            if len(new_error_detected_WLs) != 3:
                logger.error_lb(f'check error_detected_WLs in vu 40BF')
                logger.error_fp(f'expect error_detected_WLs cnt equal to 3 when read scan occur, but current value = {len(new_error_detected_WLs)}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            if new_error_detected_WLs[2] != 9:
                logger.error_lb(f'check error_detected_WLs in vu 40BF')
                logger.error_fp(f'expect error_detected_WLs equal to 9 when read scan occur, but current value = {new_error_detected_WLs[2]}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL

        # VB_number = project_api.get_Normal_lock_list_VBs_number()
        # dumpfile("TLC_read_scan_info2.bin", TLC_read_scan_info.payload.copy())
        pass
    
    def step11(self) -> None:
        logger.flow(11, 'Write TLC data to close VB')
        total_size = self.tlc_vb_size - self.lba
        api.sequential_write(lun=0, start_lba=self.lba, total_size=total_size, chunk_size=api.WRITE_10_MAX_BLOCK_LEN, fua = 1,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=self.write_record)
        self.lba += total_size
        _, self.open_vb_info = api.get_open_vb_info()        
        print_open_vb_info_cursor(self.open_vb_info.TLC_L2, "TLC_L2")
        pass
    
    def step12(self) -> None:
        logger.flow(12, 'read status in vu 40BF and check status = 0 and no ERROR Detected pageline')
        status = project_api.check_if_current_VB_scan_in_progress_completed(VB=self.VB)
        if status != 0:
            logger.error_lb(f'check status in vu 40BF')
            logger.error_fp(f'expect status equal to 0 when VB closed, but current value = {status}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL

        new_error_detected_WLs = project_api.get_gc_read_scan_released_scan_pageline()
        if len(new_error_detected_WLs) != 0:
            logger.error_lb(f'check error_detected_WLs in vu 40BF')
            logger.error_fp(f'expect error_detected_WLs cnt equal to 0 while VB is closed, but current value = {len(new_error_detected_WLs)}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        pass

    def post_process(self) -> None:
        logger.info('Post process completed')
        pass
            
    def reconfig_lun(self) -> None:
        config_descs = api.get_config_descriptors(print=False)
        for index in range(4):
            config_descs[index].header.b2_conf_desc_continue = api.ConfDescContinue.DISABLE if index == 3 else api.ConfDescContinue.ENABLE
        for index in range(4):
            api.push_write_config(config_descs[index], index=index)
        ExecuteCMD.send()
        return

run = Pattern().run
if __name__ == "__main__":
    run()