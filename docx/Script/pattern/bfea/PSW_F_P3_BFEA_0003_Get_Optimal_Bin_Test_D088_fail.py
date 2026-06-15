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

def check_timeout(start_time: float, timeout_min: int, timeout_sec:int) -> bool:
    current_time = time.time()
    if (current_time - start_time) >= timeout_min * 60 + timeout_sec:
        return True
    else:
        return False
    
class Pattern(UFSTC):
    def pre_process(self) -> None:
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
        self.random_en_lun = random.randint(0, 31) #disable ats bug?
        self.Total_AU_Count = self.geometry_desc.q4_total_raw_device_capacity / (self.geometry_desc.l13_segment_size * self.geometry_desc.b17_allocation_unit_size);
        self.flow1()
        self.flow2()
        self.flow3()
        self.flow4()
        self.flow5_6()
        self.flow7()
        for case_id in range(1,3):#range (1,4) PSA
            self.flow8(case_id)
            self.flow9(case_id)
            self.flow10()
            self.flow11()
        self.flow12()
        for case_id in range(5,7):
            self.flow13_15(case_id)
        pass
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
                    config_descs[i].units[unit].l4_num_alloc_units = int(self.Total_AU_Count / 2)
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
    def flow1(self) -> None:
        logger.flow(1,f'Lun = {self.random_en_lun} enable = 1, NumAllocUnits = total capacity')
        self.random_config()
        pass
    def flow2(self) -> None:
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
            if purge_status is 0x03:
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
         
    def flow3(self)->None:
        logger.flow(3,'write 1 TLC VB')
        self.write_data(self.random_en_lun, 0, self.tlc_vb_size, 65535)
        pca = api.lba_to_pba(self.random_en_lun, 0)
        vb = pca.w10_block.value
        ce = pca.b5_ce.value         
        free_vb_list = self.get_target_vb_list(27)
        pass
    def flow4(self) -> None:
        logger.flow(4,'Host issue L2P with written range to get CE/VB')
        pca = api.lba_to_pba(self.random_en_lun, 0)
        vb = pca.w10_block.value
        ce = pca.b5_ce.value
        self.test_vb = vb
        self.test_ce = ce        
        pass
    def flow8(self, case_num:int)->None:
        if case_num == 1:
            logger.flow(8,'config lun0 EM1 with total au, write 1 slc vb')
        elif case_num == 2:
            logger.flow(8,'config lun0 EM1 with bootlun , write lun 0 capacity')            
        elif case_num == 3:
            pass # PSA not in ENG3   
        self.config_case(case_num)
    def flow9(self,case_num:int)->None:
        _param = shared.param
        if(case_num == 1):
            self.write_data(0,0,self.tlc_vb_size,BLOCK4K_SIZE_512K_BYTE)
        elif(case_num == 2):
            self.write_data(0,0,_param.gLUCapacity[0],BLOCK4K_SIZE_512K_BYTE)
        elif case_num == 3:
            pass # PSA not in ENG3   
    def flow10(self)->None:
        pca = api.lba_to_pba(0, 0)
        vb = pca.w10_block.value
        ce = pca.b5_ce.value
        self.test_vb = vb
        self.test_ce = ce     
        pass      
    def issue_40B1_then_expected_result(self, expected_value:int)->None:
        logger.flow(11,'Issue 40B1 VUC to get best BFEA bin')
        payload = project_api.issue_40B1_Get_Best_Bfea_Scan(self.test_vb, self.test_ce)
        logger.info('check result')
        result = int.from_bytes(payload[0:4], byteorder='little')
        if result != expected_value:             
            logger.error_fp(f'result[0:3] = {result} != expected_value {expected_value}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL          
    def flow11(self)->None:
        logger.flow(11,'Issue 40B1 VUC to get best BFEA bin')
        self.issue_40B1_then_expected_result(2)   
    def flow12(self)->None:
        logger.flow(12,'erase all card + disable ATS')
        self.flow2()      
        self.random_en_lun = random.randint(0, 31)
        logger.flow(12,f'random config lun = {self.random_en_lun}')
        self.random_config()
    def flow13_15(self, case_num:int)->None:
        if(case_num == 5):
            logger.flow(13,f'case 5, write 0.5 tlc vb')
            self.write_data(self.random_en_lun,0,int(0.5*self.tlc_vb_size),BLOCK4K_SIZE_512K_BYTE)
            pca = api.lba_to_pba(0, 0)
            vb = pca.w10_block.value
            ce = pca.b5_ce.value
            self.test_vb = vb
            self.test_ce = ce
            self.issue_40B1_then_expected_result(1)
        else:
            logger.flow(13,f'case 6, do nothing')
            free_queue_tlc = 27
            free_vb_list = self.get_target_vb_list(free_queue_tlc)
            self.test_vb = free_vb_list[random.randint(0,len(free_vb_list))]
            self.test_ce = random.randint(0,self.ce_num-1)
            self.issue_40B1_then_expected_result(1)
    def flow7(self)->None:
        logger.flow(7,'erase all card + disable ATS')
        self.flow2()
    def flow5_6(self)->None:
        logger.flow(5,'Issue 40B1 VUC to get best BFEA bin')
        payload = project_api.issue_40B1_Get_Best_Bfea_Scan(self.test_vb, self.test_ce)
        logger.flow(6,'check result')
        result = int.from_bytes(payload[0:4], byteorder='little')
        expected_value = 0
        if result != expected_value:             
            logger.error_fp(f'result[0:3] = {result} != expected_value {expected_value}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL    
        best_bin = int.from_bytes(payload[4:8], byteorder='little')
        expected_value = 16
        if best_bin >= expected_value:             
            logger.error_fp(f'result[4:7] = {best_bin} < expected_value {expected_value}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL    
        best_error_bit = int.from_bytes(payload[8:12], byteorder='little')
        expected_value = 0xFFFFFFFF
        if best_error_bit == expected_value:             
            logger.error_fp(f'result[8:11] = {best_error_bit} = expected_value {expected_value}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL    
        bin_result:List[int] = []

        logger.flow(5,'Issue 4067 VU command to single read with bin option')
        for bin_idx in range(16):
            payload = project_api.issue_4067_Single_Read_With_Bin_Option(self.test_ce,self.test_vb,bin_idx,0,0)
            bin_result.append(payload[0])   
        mini_bin_result = 0xFF

        for res in bin_result:
            if res < mini_bin_result:
                mini_bin_result = res
        mini_bin_idx_list:List[int] = []
        for bin_idx in range(16):
            if bin_result[bin_idx] == bin_idx:
                mini_bin_idx_list.append(bin_idx)
        if best_error_bit != mini_bin_result:
            logger.error_fp(f'best_error_bit = {best_error_bit} != mini_bin_result {mini_bin_result}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL   
        if best_bin not in mini_bin_idx_list:
            logger.error_fp(f'best_bin = {best_bin} != mini_bin_idx_list {mini_bin_idx_list}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL   
    def post_process(self) -> None:
        pass
    

run = Pattern().run
if __name__ == "__main__":
    run()