import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.api.ufs_api.rpmb.rpmb import RPMB
from Script.api import shared
from Script.api.ufs_api.defines import enum_define
from Script.api.ufs_api.vendor_cmd.functions import set_mconfig, get_mconfig, get_flash_setting
from Script.api.ufs_api.defines import CmdParamPatternMode, CompareMethod
from Script.api.ufs_api.defines import WellKnownLUN, ScsiStatus, RPMBMsgType, RPMBOperationResult
import time
from Script.api.ufs_api.defines.enum_define import QueryResponseCode
from Script.api import shared
from Script.lib import sdk_lib as lib
import random
from Script.api.ufs_api import *
from Script.api.exception import *
from Script.api.ufs_api.rpmb.rpmb import RPMB
from Script.api.ufs_api.vendor_cmd.functions import *
from typing import cast
from time import sleep


def check_timeout(start_time: float, timeout_min: int, timeout_sec:int) -> bool:
    current_time = time.time()
    if (current_time - start_time) >= timeout_min * 60 + timeout_sec:
        return True
    else:
        return False
    
class Pattern(UFSTC):
    def pre_process(self) -> None:
        # payload = project_api.issue_40B0_Bfea_Scan(1, 1, 0, 0)
        # payload = project_api.issue_40B0_Bfea_Scan(1, 1, 0, 0)
        #self.bu_bfea_regular_scan_group_trig_count_0 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[0]'))
        # f = ExecuteCMD.StartStopUnit()
        # #f.assign(lun=0x00, immed=1, power_condition=0x01, no_flush=1, start=1)
        # f.assign(lun=0x00, immed=1, power_condition=0x00, no_flush=0, start=1)
        # #f.upiu.b1_flags = 0x45
        # #f.upiu.u16_cdb.b1_immed = 1

        # ExecuteCMD.enqueue(f)      
        # ExecuteCMD.send(clear_on_success=True)
        # test end
        self.five_hundred_MB_au = 0x100 / 1024 * 500
        self.boot_au_limit = 3
        self.rpmb_region0 = 0x0001
        self.next_vb_idx = 0
        flash_setting = get_flash_setting()
        self.ce_num = flash_setting.Max_Fdevice
        self.bin = 3
        self.fw_geometry = api.get_fw_geometry()
        self.geometry_desc = api.get_geometry_descriptor()
        self.slc_vb_size = (self.fw_geometry.l84_vb_size_u0 * 512 // 4096)
        self.test_vb = 0
        self.test_ce = 0
        self.tlc_vb_size = (self.fw_geometry.l88_vb_size_u1 * 512 // 4096)      
        self.random_en_lun = 0 #random.randint(0, 31) disable ats bug?
        self.Total_AU_Count = self.geometry_desc.q4_total_raw_device_capacity / (self.geometry_desc.l13_segment_size * self.geometry_desc.b17_allocation_unit_size);
        self.flow1()
        #enable bfea
        #payload = project_api.issue_40B0_Bfea_Scan(1, 1, 0, 0)
# DEBUG

        # case_num = 10
        # self.flow2()
        # self.flow3(case_num)
        # self.flow4(case_num)
        # self.flow5()
        # self.flow6_7()
        # self.flow8()
        # self.flow9()
        # self.flow10(case_num)
        # self.flow11(case_num)
        # self.recover_bfea_scan_make_offset()
# DEBUG


        for case_num in range(1,10):
            self.flow2()
            self.flow3(case_num)
            self.flow4(case_num)
            self.flow5()
            self.flow6_7()
            self.flow8()
            self.flow9()
            self.flow10(case_num)
            self.flow11(case_num)
            if(case_num == 10):
                self.recover_bfea_scan_make_offset()
    def flow1(self) -> None:
        logger.flow(1,f'4056 get mconfig data')
        _, mConfig_in_vu = project_api.get_mConfig_data()
        self.FB_SCAN_WL_MIN = mConfig_in_vu.FB_SCAN_WL_MIN.value
        self.PB_SCAN_PAGE = mConfig_in_vu.PB_SCAN_PAGE.value
        self.FB_SCAN_WL_MAX = mConfig_in_vu.FB_SCAN_WL_MAX.value
        self.PB_SCAN_ENABLE_PAGE_GAP = mConfig_in_vu.PB_SCAN_ENABLE_PAGE_GAP.value
        logger.info(f'self.FB_SCAN_WL_MIN = {self.FB_SCAN_WL_MIN}, self.PB_SCAN_PAGE = {self.PB_SCAN_PAGE}, self.FB_SCAN_WL_MAX = {self.FB_SCAN_WL_MAX}, self.PB_SCAN_ENABLE_PAGE_GAP = {self.PB_SCAN_ENABLE_PAGE_GAP}')
    def random_config(self) -> None:
        self.unit_desc_idxes:List[int] = []
        config_descs = api.get_config_descriptors(print=True)
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = 0x0
        
        for i in range(4): 
            for unit in range(8):
                if (i * 8 + unit) == self.random_en_lun:
                    config_descs[i].units[unit].b0_lu_enable = 1
                    config_descs[i].units[unit].b1_boot_lun_id = 0
                    config_descs[i].units[unit].b3_memory_type = api.MemoryType.NORMAL
                    config_descs[i].units[unit].l4_num_alloc_units = int(self.Total_AU_Count )
                    config_descs[i].units[unit].b9_logical_block_size = api.LogicalBlockSize.SIZE_4KB
                    config_descs[i].units[unit].b10_provisioning_type = api.ProvisioningType.THIN_PROVISIONING_ERASE
                else:
                    config_descs[i].units[unit].b0_lu_enable = 0
                    config_descs[i].units[unit].l4_num_alloc_units = 0
            if i == 3:
                config_descs[i].header.b2_conf_desc_continue = 0
            else:
                config_descs[i].header.b2_conf_desc_continue = 1
            push_write_config(config_descs[i], index=i)
        ExecuteCMD.send()
        _param = api.shared.param
        for lun in range(0, _param.gMaxNumberLU):
            unit_descriptor = ExecuteCMD.ReadDescriptor()
            unit_descriptor.assign(DescriptorIDN.UNIT, lun)
            self.unit_desc_idxes.append(ExecuteCMD.enqueue(unit_descriptor))

        ExecuteCMD.send(clear_on_success=False)
        for index in self.unit_desc_idxes:
            update_descriptor(DescriptorIDN.UNIT, index, cast(QueryResponse, ExecuteCMD.read_response(index)))
        ExecuteCMD.clear()
        #test unit ready all enable lun
        for lun in range(_param.gMaxNumberLU):
            if  _param.gUnit[lun].b3_lu_enable:
                test_unit_ready = ExecuteCMD.CmdSeqTestUnitReady()
                test_unit_ready.set_option(lun)
                ExecuteCMD.enqueue(test_unit_ready)
        ExecuteCMD.send(clear_on_success=False)
        ExecuteCMD.clear()
        pass
    def polling_bfea_idle(self)-> None:
        timeout_min = 0
        timeout_sec = 2000
        start_time = time.time()   
        logger.info(f'polling_bfea_idle')  
        while True:
            if check_timeout(start_time, timeout_min, timeout_sec):
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            payload = project_api.issue_40B0_Bfea_Scan(5,0,0,0)
            output = int.from_bytes(payload[0:4], byteorder='little')      
            if output != 1:
                logger.info(f'output = {output}, continue polling')
                time.sleep(1)
            else:
                logger.info(f'output = {output}, already idle')
                break       
    def set_bin_on_target_vb(self, set_bin_val:int,set_bin_vb:int)->None:
        logger.info(f'Issue 40B0 VUC to BFEA Scan (set BFEA table): set_bin_val = {set_bin_val}, set_bin_vb = {set_bin_vb}')
        for ce in range(self.ce_num):
            rsp = project_api.issue_40B0_Bfea_Scan(2, set_bin_vb, ce, set_bin_val)
        logger.flow(5,'Issue 40B0 VUC to BFEA Scan (get BFEA table)')
        for ce in range(self.ce_num):
            payload = project_api.issue_40B0_Bfea_Scan(3, set_bin_vb, ce, 0)
            logger.flow(9,'Host get Byte[0-3]output of this vendor cmd  should be 0(Bin index)')
            output = int.from_bytes(payload[0:4], byteorder='little')
            expected_value = set_bin_val
            dumpfile('bfea_scan_vb_rsp.bin',payload)
            if output != expected_value:             
                logger.error_fp(f'output = {output} != expected_value {expected_value}')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL                
            pass        
    def check_vb_bin_cnt_expected(self,expect_bin_val:int, check_vb:int)->bool:
        logger.info(f'check_vb_bin_cnt, expected bin val = {expect_bin_val}, check vb = {check_vb}')
        for ce in range(self.ce_num):
            payload = project_api.issue_40B0_Bfea_Scan(3, check_vb, ce, 0)
            logger.flow(9,'Host get Byte[0-3]output of this vendor cmd  should be 0(Bin index)')
            output = int.from_bytes(payload[0:4], byteorder='little')
            logger.info(f'expect_bin_val = {expect_bin_val}, outputbin = {output}')
            if expect_bin_val != output:
                return False
        return True
    def get_vb_bin_cnt(self, vb:int,ce:int)->int:
        logger.info(f'get bin val from vb{vb}, ce{ce}')
        payload = project_api.issue_40B0_Bfea_Scan(3, vb, ce, 0)
        logger.flow(9,'Host get Byte[0-3]output of this vendor cmd  should be 0(Bin index)')
        output = int.from_bytes(payload[0:4], byteorder='little')
        logger.info(f'bin val = {output}')
        return output
    def config_case(self,case_num :int) -> None:
        config_descs = api.get_config_descriptors(print=True)
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = 0x0
        
        for i in range(4): 
            for unit in range(8):
                if (i * 8 + unit) == 0:
                    
                    config_descs[i].units[unit].b0_lu_enable = 1
                    config_descs[i].units[unit].b1_boot_lun_id = 0
                    if(case_num == 1 or case_num == 2):
                        config_descs[i].units[unit].b3_memory_type = api.MemoryType.ENHANCED_1
                        if(case_num == 1):
                            config_descs[i].units[unit].l4_num_alloc_units = int(self.Total_AU_Count)
                        if(case_num == 2):
                            config_descs[i].units[unit].l4_num_alloc_units = 4
                            config_descs[i].units[unit].b1_boot_lun_id = api.BootLUNID.BOOT_LUN_A
                    config_descs[i].units[unit].b9_logical_block_size = api.LogicalBlockSize.SIZE_4KB
                    config_descs[i].units[unit].b10_provisioning_type = api.ProvisioningType.THIN_PROVISIONING_ERASE
                else:
                    config_descs[i].units[unit].b0_lu_enable = 0
                    config_descs[i].units[unit].l4_num_alloc_units = 0
            if i == 3:
                config_descs[i].header.b2_conf_desc_continue = 0
            else:
                config_descs[i].header.b2_conf_desc_continue = 1
            push_write_config(config_descs[i], index=i)
        ExecuteCMD.send()
        _param = api.shared.param
        for lun in range(0, _param.gMaxNumberLU):
            unit_descriptor = ExecuteCMD.ReadDescriptor()
            unit_descriptor.assign(DescriptorIDN.UNIT, lun)
            self.unit_desc_idxes.append(ExecuteCMD.enqueue(unit_descriptor))

        ExecuteCMD.send(clear_on_success=False)
        for index in self.unit_desc_idxes:
            update_descriptor(DescriptorIDN.UNIT, index, cast(QueryResponse, ExecuteCMD.read_response(index)))
        ExecuteCMD.clear()
        #test unit ready all enable lun
        for lun in range(_param.gMaxNumberLU):
            if  _param.gUnit[lun].b3_lu_enable:
                test_unit_ready = ExecuteCMD.CmdSeqTestUnitReady()
                test_unit_ready.set_option(lun)
                ExecuteCMD.enqueue(test_unit_ready)
        ExecuteCMD.send(clear_on_success=False)
        ExecuteCMD.clear()
        if(case_num == 1):
            api.write_attribute(idn=api.AttributeIDN.BOOT_LUN_EN, val=api.BootLUNID.BOOT_LUN_A)  
        pass    
    def get_target_vb_list(self, group:int)-> List[int]:
        retval = 0
        vb_list = []
        vb_list_data_format = {
            'group': {'pos': 0, 'len': 6, 'mask': 0x3f}, 
            'access_mode': {'pos': 6, 'len': 2, 'mask': 0x3}, 
            'dirty': {'pos': 8, 'len': 1, 'mask': 0x1}, 
        }
        response, rep_data = get_vb_info()
        dumpfile("rep_data.bin", bytearray(rep_data))
        ftl_vb_list_data = dict()

        for vb in range(len(rep_data)):
            if self.fw_geometry.l52_total_vb_count <= vb:
                break
            if vb *4  >= len(rep_data):
                break

            ftl_vb_list_data.update({vb : {k: (((rep_data[vb*4]|rep_data[vb*4+1]<<8) >> v['pos']) & v['mask']) for k, v in vb_list_data_format.items()}})
        used_mlc_cout = 0
        map_vb_cnt = {} # type: ignore
        logger.info(f'[show all vb info at begin]')
        for vb, vb_info in ftl_vb_list_data.items():
            last_type = vb_info['group']
            dirtybit = vb_info['dirty']
            if last_type in map_vb_cnt:
                map_vb_cnt[last_type] += 1
            else:
                map_vb_cnt[last_type] = 1
            logger.info(f'[vb = {vb}, group type = {last_type}, dirtybit = {dirtybit}]')
            if last_type == group:
                vb_list.append(vb)
        for k,v in map_vb_cnt.items():
            logger.info(f'group type = {k}, cnt = {v}]')
        logger.info(f'get target vb list of vb {group} cnt = {len(vb_list)}')
        return vb_list          
    
    def set_bfea_scan_make_offset_all_128(self)->None:
        self.backup_bin_404A = project_api.issue_404A_Get_Bfea_Bin_Offset()
        # logger.info('Issue 40B1 VUC to get best BFEA bin')
        # logger.info(f'self.test_vb = {self.test_vb}, self.test_ce = {self.test_ce}')
        for setting_N in range(15, -1, -1):
            logger.info(f'set bin {setting_N} offset to 128')
            for setting_EC_Interval in range(1,5):
                setting_SLC_L1 = 128
                setting_MLC_L1 = 128
                setting_MLC_L2 = 128
                setting_MLC_L3 = 128
                setting_TLC_L1 = 128
                setting_TLC_L2 = 128
                setting_TLC_L3 = 128
                setting_TLC_L4 = 128
                setting_TLC_L5 = 128
                setting_TLC_L6 = 128
                setting_TLC_L7 = 128                     
                project_api.issue_D04A_Set_Bin_Offset(setting_N, setting_EC_Interval, setting_SLC_L1, setting_MLC_L1, setting_MLC_L2, setting_MLC_L3, setting_TLC_L1, setting_TLC_L2, setting_TLC_L3, setting_TLC_L4, setting_TLC_L5, setting_TLC_L6, setting_TLC_L7)
    def recover_bfea_scan_make_offset(self)->None:           
        for backup_N in range(16):
            logger.info(f'set bin {backup_N} offset recover')        
            for setting_EC_Interval in range(1,5):
                setting_SLC_L1 = self.backup_bin_404A.payload[backup_N*11]
                setting_MLC_L1 = self.backup_bin_404A.payload[backup_N*11 + 1]
                setting_MLC_L2 = self.backup_bin_404A.payload[backup_N*11 + 2]
                setting_MLC_L3 = self.backup_bin_404A.payload[backup_N*11 + 3]
                setting_TLC_L1 = self.backup_bin_404A.payload[backup_N*11 + 4]
                setting_TLC_L2 = self.backup_bin_404A.payload[backup_N*11 + 5]
                setting_TLC_L3 = self.backup_bin_404A.payload[backup_N*11 + 6]
                setting_TLC_L4 = self.backup_bin_404A.payload[backup_N*11 + 7]
                setting_TLC_L5 = self.backup_bin_404A.payload[backup_N*11 + 8]
                setting_TLC_L6 = self.backup_bin_404A.payload[backup_N*11 + 9]
                setting_TLC_L7 = self.backup_bin_404A.payload[backup_N*11 + 10]
                project_api.issue_D04A_Set_Bin_Offset(backup_N, setting_EC_Interval , setting_SLC_L1, setting_MLC_L1, setting_MLC_L2, setting_MLC_L3, setting_TLC_L1, setting_TLC_L2, setting_TLC_L3, setting_TLC_L4, setting_TLC_L5, setting_TLC_L6, setting_TLC_L7)         

    def flow2(self) -> None:
        logger.flow(2,'random config') # wait MR
        self.random_config()
        logger.flow(2,'erase all card + disable ATS') # wait MR
        start_lba = 0
        data_len = 65535
        _param = shared.param
        continue_push_unmap = True
        while continue_push_unmap:
            start_lba = min(start_lba, _param.gLUCapacity[self.random_en_lun])
            if (start_lba + data_len) > _param.gLUCapacity[self.random_en_lun]:
                data_len = _param.gLUCapacity[self.random_en_lun] - start_lba
                continue_push_unmap = False
            logger.info(f'unmap, start_lba = {start_lba}, data_len = {data_len}')
            unmap = ExecuteCMD.Unmap()
            unmap.assign(lun=self.random_en_lun, lba=start_lba, length=data_len)
            ExecuteCMD.enqueue(unmap)      
            start_lba += data_len
        ExecuteCMD.send(clear_on_success=True)
        idn = api.FlagIDN.PURGE_EN
        set_flag = ExecuteCMD.SetFlag().assign(idn).enqueue()
        ExecuteCMD.send(clear_on_success=True)
        timeout_min = 0
        timeout_sec = 2000
        start_time = time.time()
        polling_cnt = 0
        while True:
            if check_timeout(start_time, timeout_min, timeout_sec):
                raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
            purge_status = api.read_attribute(idn=api.AttributeIDN.PURGE_STATUS)
            polling_cnt += 1
            logger.info(f'purge status = {purge_status}, polling count = {polling_cnt}')
            if purge_status == 0x03:
                logger.info(f'purge status = {purge_status}, complete')
                break
        pass
        logger.info(f'disable ats')
        #project_api.issue_D088_enable_disable_auto_standby(1)
        project_api.issue_D088_enable_disable_auto_standby(0)
    def write_data(self, lun:int, start_lba:int, total_size: int, chunk_size:int) -> None:
        chunk_size = 65535
        lba = start_lba
        total_len = total_size
        while(total_len):
            write10 = ExecuteCMD.Write10()
            chunk_size = min(int(chunk_size),int(total_len))
            write10.assign(lun=lun, lba=lba, length=chunk_size, fua=0)
            write10.set_option(pattern_mode=CmdParamPatternMode.HW_FIX)
            ExecuteCMD.enqueue(write10)
            total_len -= chunk_size     
            lba += chunk_size
        ExecuteCMD.send(clear_on_success=True)
         
    def flow3(self,case_num:int)->None:
        if case_num == 1:
            logger.flow(3,'write 3 TLC VB')
            self.write_data(self.random_en_lun, 0, 3*self.tlc_vb_size, 65535)
        if case_num == 2: # no trigger
            write_data_size4k = (self.FB_SCAN_WL_MIN - 1) * 3 * 4
            logger.flow(3,f'write {write_data_size4k} 4k')
            self.write_data(self.random_en_lun, 0, write_data_size4k, 65535)            
        if case_num == 3:
            write_data_size4k = (self.FB_SCAN_WL_MIN) * 3 * 4
            logger.flow(3,f'write {write_data_size4k} 4k')
            self.write_data(self.random_en_lun, 0, write_data_size4k, 65535)        
        if case_num == 4:
            write_data_size4k = (self.FB_SCAN_WL_MAX) * 3 * 4
            logger.flow(3,f'write {write_data_size4k} 4k')
            self.write_data(self.random_en_lun, 0, write_data_size4k, 65535)                        
        if case_num == 5:
            write_data_size4k = (self.PB_SCAN_PAGE + self.PB_SCAN_ENABLE_PAGE_GAP) *  6 * self.ce_num * 4
            #(self.PB_SCAN_PAGE) * 4 # Page = 4k
            logger.flow(3,f'write {write_data_size4k} 4k')
            self.write_data(self.random_en_lun, 0, write_data_size4k, 65535)                            
        if case_num == 6:
            write_data_size4k = (self.PB_SCAN_ENABLE_PAGE_GAP) * 4 # Page = 4k
            logger.flow(3,f'write {write_data_size4k} 4k')
            self.write_data(self.random_en_lun, 0, write_data_size4k, 65535)    
        if case_num == 7:
            project_api.issue_D018_Disable_Enable_DM_Bg_Task_In_Bank(0)
            logger.flow(3,'D018 disable flag, write 3 TLC VB')
            self.write_data(self.random_en_lun, 0, 3*self.tlc_vb_size, 65535)
        if case_num == 8:
            init_tester_to_unit_ready(Dcmd5ResetType.HW_RESET,powerdown=True)
            project_api.issue_D088_enable_disable_auto_standby(0)
            project_api.issue_40B0_Bfea_Scan(1, 1, 0, 0)
            logger.flow(3,'POWER CYCLE, write 3 TLC VB')
            self.write_data(self.random_en_lun, 0, 3*self.tlc_vb_size, 65535)
        if case_num == 9:
            project_api.issue_40B0_Bfea_Scan(1,0,0,0)
            logger.flow(3,'40B0 disable bfea, write 3 TLC VB')
            self.write_data(self.random_en_lun, 0, 3*self.tlc_vb_size, 65535)  
        if case_num == 10:
            write_data_size4k = (self.PB_SCAN_PAGE + self.PB_SCAN_ENABLE_PAGE_GAP) *  6 * self.ce_num * 4
            logger.flow(3,f'write {write_data_size4k} 4k')
            self.write_data(self.random_en_lun, 0, write_data_size4k, 65535)    
            self.set_bfea_scan_make_offset_all_128()
        free_vb_list = self.get_target_vb_list(17)          
        pass
    def get_one_val_exclude(self, low:int, high:int, exclude:int)->int:
        x = exclude
        while x == exclude:
            x = random.randint(low, high)
        return x

    def flow4(self, case_num:int) -> None:
        logger.flow(4,'Host issue L2P with written range to get CE/VB')
        pca = api.lba_to_pba(self.random_en_lun, 0)
        vb = pca.w10_block.value
        ce = pca.b5_ce.value
        self.test_vb = vb
        self.test_ce = ce  
        if case_num == 10:
            self.debug_show_best_bin()
        # logger.info(f'get bin')
        if( (case_num == 2) or (case_num == 6) or (case_num == 7) or (case_num == 9)):
            get_bin = self.get_vb_bin_cnt(vb,ce)
            if get_bin <= 1:
                self.set_bin_old_val  = self.get_one_val_exclude(0,1,get_bin)
            elif get_bin <= 8:
                self.set_bin_old_val  = self.get_one_val_exclude(2,8,get_bin)
            elif get_bin <= 15:
                self.set_bin_old_val  = self.get_one_val_exclude(9,15,get_bin)            
            self.set_bin_on_target_vb(self.set_bin_old_val, vb)
        pass  
    def issue_40B1_then_expected_result(self, expected_value:int)->None:
        logger.flow(11,'Issue 40B1 VUC to get best BFEA bin')
        payload = project_api.issue_40B1_Get_Best_Bfea_Scan(self.test_vb, self.test_ce)
        logger.info('check result')
        result = int.from_bytes(payload[0:4], byteorder='little')
        if result != expected_value:             
            logger.error_fp(f'result[0:3] = {result} != expected_value {expected_value}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL          


    def flow5(self)->None:
        logger.flow(5,'backup trigger count')
        self.bu_bfea_regular_scan_group_trig_count_0 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[0]'))
        self.bu_bfea_regular_scan_group_done_count_0 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_done_count[0]'))
        self.bu_bfea_regular_scan_group_trig_count_1 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[1]'))
        self.bu_bfea_regular_scan_group_done_count_1 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_done_count[1]'))
        self.bu_bfea_regular_scan_group_trig_count_2 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[2]'))
        self.bu_bfea_regular_scan_group_done_count_2 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_done_count[2]'))
        logger.info(f'bfea_regular_scan_group_trig_count_0 = {self.bu_bfea_regular_scan_group_trig_count_0}')               
        logger.info(f'bfea_regular_scan_group_trig_count_1 = {self.bu_bfea_regular_scan_group_trig_count_1}')               
        logger.info(f'bfea_regular_scan_group_trig_count_2 = {self.bu_bfea_regular_scan_group_trig_count_2}')               
        logger.info(f'bfea_regular_scan_group_done_count_0 = {self.bu_bfea_regular_scan_group_done_count_0}')               
        logger.info(f'bfea_regular_scan_group_done_count_1 = {self.bu_bfea_regular_scan_group_done_count_1}')               
        logger.info(f'bfea_regular_scan_group_done_count_2 = {self.bu_bfea_regular_scan_group_done_count_2}')               
        
    def flow6_7(self)->None:
        logger.flow(6,'Issue 40B0 bfea scan')
        min_bin = 0xFFFFFFFF
        for ce in range(self.ce_num):
            logger.info(f'40B0 option = 3, vb = {self.test_vb}, ce = {ce}')
            payload = project_api.issue_40B0_Bfea_Scan(3, self.test_vb, ce, 0)
            output = int.from_bytes(payload[0:4], byteorder='little')  
            logger.info(f'result = {output}')
            if min_bin > output:
                min_bin = output
        self.min_bin_val = min_bin  
        logger.flow(7,f'Get min bin from vb {self.test_vb} from all ce = {self.min_bin_val}')
    def flow8(self) -> None:
        logger.flow(8,'Issue 40B0 VUC to BFEA Scan to set timer')
        self.setting_timer_minutes = 1
        if self.min_bin_val <= 1:
            grp = 0
        elif self.min_bin_val <= 8:
            grp = 1
        elif self.min_bin_val <= 15:
            grp = 2
        self.grp = grp            
        logger.info(f'grp = {self.grp}')
        self.time_gap_min = 20
        logger.info(f'40B0 opcode = 9, grp = {grp}, timer minute = {self.time_gap_min - self.setting_timer_minutes}')
        project_api.issue_40B0_Bfea_Scan(9, grp, (20  - self.setting_timer_minutes) * 60, 0) # will be 20 * 60 - 1*60 = 19 * 60 (sec)
    def flow9(self)->None:
        logger.flow(9,f'idle {self.setting_timer_minutes} min')
        sleep(self.setting_timer_minutes * 60)
    def debug_show_best_bin(self)->None:
        logger.flow(66,'Issue 40B1 VUC to get best BFEA bin')
        logger.info(f'self.test_vb = {self.test_vb}, self.test_ce = {self.test_ce}')
        payload = project_api.issue_40B1_Get_Best_Bfea_Scan(self.test_vb, self.test_ce)
        logger.flow(6,'check result')
        result = int.from_bytes(payload[0:4], byteorder='little')
        logger.info(f'40B1 result [0:3] = {result}')
        best_bin = int.from_bytes(payload[4:8], byteorder='little')
        logger.info(f'40B1 result [4:7] best bin = {result}')

        logger.info(f'best error bit = {best_bin}')  
        bin_result:List[int] = []

        logger.flow(5,'Issue 4067 VU command to single read with bin option')
        for bin_idx in range(16):
            logger.info(f'send 4067, ce = {self.test_ce}, vb = {self.test_vb}, bin = {bin_idx}')
            payload = project_api.issue_4067_Single_Read_With_Bin_Option(self.test_ce,self.test_vb,bin_idx,0,0)
            logger.info(f'4067 ce = {self.test_ce}, vb = {self.test_vb}, bin = {bin_idx} get bin result = {payload[0]}')
            bin_result.append(payload[0])   
        mini_bin_result = 0xFF

        for res in bin_result:
            if res < mini_bin_result:
                mini_bin_result = res
        mini_bin_idx_list:List[int] = []
        for bin_idx in range(16):
            if bin_result[bin_idx] == mini_bin_result:
                mini_bin_idx_list.append(bin_idx)
        logger.info(f'best_bin = {best_bin} , mini_bin_idx_list = {mini_bin_idx_list}')

    def flow10(self, case_num:int)->None:
        self.polling_bfea_idle()
        #self.cur_bfea_change_bin_ce_blk_cnt = read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_change_bin_ce_blk_cnt')
        self.cur_bfea_regular_scan_group_trig_count_0 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[0]'))
        self.cur_bfea_regular_scan_group_done_count_0 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_done_count[0]'))
        self.cur_bfea_regular_scan_group_trig_count_1 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[1]'))
        self.cur_bfea_regular_scan_group_done_count_1 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_done_count[1]'))
        self.cur_bfea_regular_scan_group_trig_count_2 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_trig_count[2]'))
        self.cur_bfea_regular_scan_group_done_count_2 = cast(int,read_fw_value('gUfsApiStruct.ftl->split_info->smart_info_2.bfea_regular_scan_group_done_count[2]'))     
        logger.info(f'bfea_regular_scan_group_trig_count_0 = {self.cur_bfea_regular_scan_group_trig_count_0}')               
        logger.info(f'bfea_regular_scan_group_trig_count_1 = {self.cur_bfea_regular_scan_group_trig_count_1}')               
        logger.info(f'bfea_regular_scan_group_trig_count_2 = {self.cur_bfea_regular_scan_group_trig_count_2}')               
        logger.info(f'bfea_regular_scan_group_done_count_0 = {self.cur_bfea_regular_scan_group_done_count_0}')               
        logger.info(f'bfea_regular_scan_group_done_count_1 = {self.cur_bfea_regular_scan_group_done_count_1}')               
        logger.info(f'bfea_regular_scan_group_done_count_2 = {self.cur_bfea_regular_scan_group_done_count_2}') 
        logger.info(f'self.grp = {self.grp}, self.min_bin_val = {self.min_bin_val}')   
        if case_num == 1 or case_num == 3 or case_num == 4 or case_num == 5 or case_num == 8 or case_num == 10:
            if self.grp == 0:
                if(int(self.cur_bfea_regular_scan_group_trig_count_0) != (int(self.bu_bfea_regular_scan_group_trig_count_0) + 1)):
                    logger.error_fp(f'self.cur_bfea_regular_scan_group_trig_count_0 = {self.cur_bfea_regular_scan_group_trig_count_0} != self.bu_bfea_regular_scan_group_trig_count_0({self.bu_bfea_regular_scan_group_trig_count_0}) + 1 ')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL  
                if(int(self.cur_bfea_regular_scan_group_done_count_0) != (int(self.bu_bfea_regular_scan_group_done_count_0) + 1)):
                    logger.error_fp(f'self.cur_bfea_regular_scan_group_done_count_0 = {self.cur_bfea_regular_scan_group_done_count_0} != self.bu_bfea_regular_scan_group_done_count_0({self.bu_bfea_regular_scan_group_done_count_0}) + 1 ')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL                      
            if self.grp == 1:
                if(int(self.cur_bfea_regular_scan_group_trig_count_1) != (int(self.bu_bfea_regular_scan_group_trig_count_1) + 1)):
                    logger.error_fp(f'self.cur_bfea_regular_scan_group_trig_count_1 = {self.cur_bfea_regular_scan_group_trig_count_1} != self.bu_bfea_regular_scan_group_trig_count_1({self.bu_bfea_regular_scan_group_trig_count_1}) + 1 ')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL  
                if(int(self.cur_bfea_regular_scan_group_done_count_1) != (int(self.bu_bfea_regular_scan_group_done_count_1) + 1)):
                    logger.error_fp(f'self.cur_bfea_regular_scan_group_done_count_1 = {self.cur_bfea_regular_scan_group_done_count_1} != self.bu_bfea_regular_scan_group_done_count_0({self.bu_bfea_regular_scan_group_done_count_1}) + 1 ')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL                
            if self.grp == 2:
                if(int(self.cur_bfea_regular_scan_group_trig_count_2) != (int(self.bu_bfea_regular_scan_group_trig_count_2) + 1)):
                    logger.error_fp(f'self.cur_bfea_regular_scan_group_trig_count_2 = {self.cur_bfea_regular_scan_group_trig_count_2} != self.bu_bfea_regular_scan_group_trig_count_1({self.bu_bfea_regular_scan_group_trig_count_2}) + 1 ')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL  
                if(int(self.cur_bfea_regular_scan_group_done_count_2) != (int(self.bu_bfea_regular_scan_group_done_count_2) + 1)):
                    logger.error_fp(f'self.cur_bfea_regular_scan_group_done_count_2 = {self.cur_bfea_regular_scan_group_done_count_2} != self.bu_bfea_regular_scan_group_done_count_0({self.bu_bfea_regular_scan_group_done_count_2}) + 1 ')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL  
        cur_bin_val = self.get_vb_bin_cnt(self.test_vb, self.test_ce)                                
        if (case_num == 1) or (case_num == 3) or (case_num == 4) or (case_num == 5) or (case_num == 8) or (case_num == 10):
            pass # because not
            # if cur_bin_val == self.set_bin_old_val:
            #     logger.error_fp(f'cur_bin_val {cur_bin_val} = self.set_bin_old_val {self.set_bin_old_val}, but expected trigger bfea')
            #     raise SIGHTING_FAIL_DATA_COMPARE_FAIL                
        else:
            if cur_bin_val != self.set_bin_old_val:
                logger.error_fp(f'cur_bin_val {cur_bin_val} != self.set_bin_old_val {self.set_bin_old_val}, but expected not trigger bfea')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL     
    def flow11(self,case_num:int)->None:
        payload = project_api.issue_40C5_to_get_booking_queue()
        output = int.from_bytes(payload[12:16], byteorder='little')  
        logger.info(f'output = {output}')
        expect_val = 0
        bit_position = 18
        mask = 1 << bit_position
        bfea_booking = (output & mask) >> bit_position
        if case_num == 10:
            expect_val = 18
        if bfea_booking != expect_val:
            logger.error_fp(f'bfea_booking({bfea_booking}) != expect_val ({expect_val})')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL  
        if case_num == 10:
            expect_val = 1        
        bit_position = 8
        mask = 1 << bit_position
        priority = (output & mask) >> bit_position
        if priority != expect_val:
            logger.error_fp(f'priority({bfea_booking}) != expect_val ({expect_val})')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL                       
    def post_process(self) -> None:
        pass
    

run = Pattern().run
if __name__ == "__main__":
    run()