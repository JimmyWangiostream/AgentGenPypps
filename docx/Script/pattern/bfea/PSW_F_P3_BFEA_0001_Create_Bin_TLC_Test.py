import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.api.ufs_api.vendor_cmd.functions import set_mconfig, get_mconfig, get_flash_setting
from Script.api import shared
from typing import List
import time
from Script.api.ufs_api.defines import CmdParamPatternMode, CompareMethod
from Script.api.ufs_api.descriptors.configuration_desc.functions import print_config, push_write_config

from Script.api.ufs_api.defines.enum_define import QueryResponseCode
from Script.api import shared
from Script.lib import sdk_lib as lib
import random
from Script.api.ufs_api import *
from Script.api.exception import *
from Script.api.ufs_api.rpmb.rpmb import RPMB
from typing import Any, List, cast
from Script.api.ufs_api.vendor_cmd.functions import *
from typing import cast

from dataclasses import is_dataclass, asdict
from typing import Any, Mapping
def check_timeout(start_time: float, timeout_min: int, timeout_sec:int) -> bool:
    current_time = time.time()
    if (current_time - start_time) >= timeout_min * 60 + timeout_sec:
        return True
    else:
        return False
    

def print_object_info_ai(object: Any) -> None:
    logger.info(f'================= [{object.__class__.__name__}]=================')
    fields = [
        (name, field) for name, field in object.__dict__.items()
        if hasattr(field, "start_offset") and hasattr(field, "end_offset") and hasattr(field, "value")
    ]
    fields.sort(key=lambda kv: kv[1].start_offset)
    for name, field in fields:
        logger.info(
            f'Byte[{field.start_offset}:{field.end_offset}]: {name} = {field.value}'
        )     
class Pattern(UFSTC):
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
    def pre_process(self) -> None:
        self.geometry_desc = api.get_geometry_descriptor()
        self.fw_geometry = api.get_fw_geometry()
        self.slc_vb_size = (self.fw_geometry.l84_vb_size_u0 * 512 // 4096)
        self.tlc_vb_size = (self.fw_geometry.l88_vb_size_u1 * 512 // 4096)    
        self.Total_AU_Count = self.geometry_desc.q4_total_raw_device_capacity / (self.geometry_desc.l13_segment_size * self.geometry_desc.b17_allocation_unit_size);
        flash_setting = get_flash_setting()
        self.random_en_lun = random.randint(0, 31)
        self.ce_num = flash_setting.Max_Fdevice
        self.target_ce = 0
        self.next_vb_idx = 0
        self.total_len = 0
        self.start_lba = 0
        self.bin = 3
        self.cur_l2_vb_list:List[int] = []
        self.free_tlc_vb_list:List[int] = []
        self.target_set_bfea_vb_list:List[int] = []
        self.check_vb_list:List[int] = []
        self.check_ce_list:List[int] = []
        self.flow1()

        self.flow2()
        self.flow3()

        self.flow5()
        self.flow6()
        self.flow7()
        self.flow8_9()
        pass
    def print_open_vb_information(self, open_vb_information:project_api.OpenVBInformation) -> None:
        logger.info('================= open_vb_information =================')
        logger.info(f'Byte[{open_vb_information.L2_Open_logical_VB_Host_TLC_number.start_offset}:{open_vb_information.L2_Open_logical_VB_Host_TLC_number.end_offset}]: L2_Open_logical_VB_Host_TLC_number = {open_vb_information.L2_Open_logical_VB_Host_TLC_number.value}')
        logger.info(f'Byte[{open_vb_information.first_free_physical_page_of_L2_Open_logical_VB_Host_TLC.start_offset}:{open_vb_information.first_free_physical_page_of_L2_Open_logical_VB_Host_TLC.end_offset}]: first_free_physical_page_of_L2_Open_logical_VB_Host_TLC = {open_vb_information.first_free_physical_page_of_L2_Open_logical_VB_Host_TLC.value}')
        logger.info(f'Byte[{open_vb_information.open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC.start_offset}:{open_vb_information.open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC.end_offset}]: open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC = {open_vb_information.open_logical_VB_number_for_Normal_Defrag_GC_Open_VB_TLC.value}')
        logger.info(f'Byte[{open_vb_information.first_free_physical_page_for_Normal_Defrag_VB_GC_Open_VB_TLC.start_offset}:{open_vb_information.first_free_physical_page_for_Normal_Defrag_VB_GC_Open_VB_TLC.end_offset}]: first_free_physical_page_for_Normal_Defrag_VB_GC_Open_VB_TLC = {open_vb_information.first_free_physical_page_for_Normal_Defrag_VB_GC_Open_VB_TLC.value}')

        logger.info(f'Byte[{open_vb_information.open_logical_VB_number_for_EM1_L2_Host.start_offset}:{open_vb_information.open_logical_VB_number_for_EM1_L2_Host.end_offset}]: open_logical_VB_number_for_EM1_L2_Host = {open_vb_information.open_logical_VB_number_for_EM1_L2_Host.value}')
        logger.info(f'Byte[{open_vb_information.first_free_physical_page_of_EM1_L2_Host_VB.start_offset}:{open_vb_information.first_free_physical_page_of_EM1_L2_Host_VB.end_offset}]: first_free_physical_page_of_EM1_L2_Host_VB_ = {open_vb_information.first_free_physical_page_of_EM1_L2_Host_VB.value}')
        logger.info(f'Byte[{open_vb_information.open_logical_VB_number_for_EM1_GC.start_offset}:{open_vb_information.open_logical_VB_number_for_EM1_GC.end_offset}]: open_logical_VB_number_for_EM1_GC = {open_vb_information.open_logical_VB_number_for_EM1_GC.value}')
        logger.info(f'Byte[{open_vb_information.first_free_physical_page_of_EM1_GC_VB.start_offset}:{open_vb_information.first_free_physical_page_of_EM1_GC_VB.end_offset}]: first_free_physical_page_of_EM1_GC_VB = {open_vb_information.first_free_physical_page_of_EM1_GC_VB.value}')
        
        
        logger.info(f'Byte[{open_vb_information.open_logical_VB_number_for_Write_Booster_WB_L2.start_offset}:{open_vb_information.open_logical_VB_number_for_Write_Booster_WB_L2.end_offset}]: open_logical_VB_number_for_Write_Booster_WB_L2 = {open_vb_information.open_logical_VB_number_for_Write_Booster_WB_L2.value}')
        logger.info(f'Byte[{open_vb_information.first_free_physical_page_of_Write_Booster_WB_L2.start_offset}:{open_vb_information.first_free_physical_page_of_Write_Booster_WB_L2.end_offset}]: first_free_physical_page_of_Write_Booster_WB_L2 = {open_vb_information.first_free_physical_page_of_Write_Booster_WB_L2.value}')
        logger.info(f'Byte[{open_vb_information.open_Remap_VB_number_for_Write_Booster_WB_L2.start_offset}:{open_vb_information.open_Remap_VB_number_for_Write_Booster_WB_L2.end_offset}]: open_Remap_VB_number_for_Write_Booster_WB_L2 = {open_vb_information.open_Remap_VB_number_for_Write_Booster_WB_L2.value}')
        logger.info(f'Byte[{open_vb_information.open_logical_VB_number_for_RPMB_VB.start_offset}:{open_vb_information.open_logical_VB_number_for_RPMB_VB.end_offset}]: open_logical_VB_number_for_RPMB_VB = {open_vb_information.open_logical_VB_number_for_RPMB_VB.value}')
        logger.info(f'Byte[{open_vb_information.first_free_physical_page_of_RPMB_VB.start_offset}:{open_vb_information.first_free_physical_page_of_RPMB_VB.end_offset}]: first_free_physical_page_of_RPMB_VB = {open_vb_information.first_free_physical_page_of_RPMB_VB.value}')
        logger.info(f'Byte[{open_vb_information.open_Remap_VB_number_for_RPMB_VB.start_offset}:{open_vb_information.open_Remap_VB_number_for_RPMB_VB.end_offset}]: open_Remap_VB_number_for_RPMB_VB = {open_vb_information.open_Remap_VB_number_for_RPMB_VB.value}')
        
        logger.info(f'Byte[{open_vb_information.PTE_Block_VB_number_logical.start_offset}:{open_vb_information.PTE_Block_VB_number_logical.end_offset}]: PTE_Block_VB_number_logical = {open_vb_information.PTE_Block_VB_number_logical.value}')
        logger.info(f'Byte[{open_vb_information.PTE_block_First_free_physical_page.start_offset}:{open_vb_information.PTE_block_First_free_physical_page.end_offset}]: PTE_block_First_free_physical_page = {open_vb_information.PTE_block_First_free_physical_page.value}')
        return 
    def flow1(self) -> None:
        logger.flow(1,f'Lun = {self.random_en_lun} enable = 1, NumAllocUnits = total capacity')
        self.random_config()
        pass
    def flow2(self) -> None:
        logger.flow(2,'erase all card')
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
    def get_and_print_next_open_vb_information(self) -> None:  
        rsp, open_vb_information = project_api.issue_40C1_to_get_open_vb_information()
        self.print_open_vb_information(open_vb_information)    
        self.next_vb_info = open_vb_information
    def flow3(self) -> None:
        free_queue_tlc = 27
        self.free_tlc_vb_list = self.get_target_vb_list(free_queue_tlc)
        self.target_set_bfea_vb_list = self.free_tlc_vb_list
        cur_l2_vb = 7
        self.cur_l2_vb_list = self.get_target_vb_list(cur_l2_vb)
        # response, self.next_vb_info = project_api.issue_40DC_to_get_next_open_vb_information(0)  
        pass
    def flow5(self) -> None:
        logger.flow(5,'Issue 40B0 VUC to BFEA Scan (set BFEA table)')
        for vb in self.target_set_bfea_vb_list:
            for ce in range(self.ce_num):
                rsp = project_api.issue_40B0_Bfea_Scan(2, vb, ce, self.bin)
            logger.flow(5,'Issue 40B0 VUC to BFEA Scan (get BFEA table)')
            for ce in range(self.ce_num):
                payload = project_api.issue_40B0_Bfea_Scan(3, vb, ce, 0)
                logger.flow(9,'Host get Byte[0-3]output of this vendor cmd  should be 0(Bin index)')
                output = int.from_bytes(payload[0:4], byteorder='little')
                expected_value = self.bin
                dumpfile('bfea_scan_vb_rsp.bin',payload)
                if output != expected_value:             
                    logger.error_fp(f'output = {output} != expected_value {expected_value}')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL                
                pass
    def flow6(self) -> None:

        self.total_len = int(self.tlc_vb_size * 3.5)
        logger.flow(6,f'Host issue write cmd with chunk size = 512KB and total size =0.5VB ({self.total_len} 4K)')
        
        chunk_size = 512/4
        lba = 0#self.start_lba
        total_len = self.total_len
        while(total_len):
            write10 = ExecuteCMD.Write10()
            chunk_size = min(int(chunk_size),int(total_len))
            write10.assign(lun=self.random_en_lun, lba=lba, length=chunk_size, fua=1)
            write10.set_option(pattern_mode=CmdParamPatternMode.HW_FIX)
            ExecuteCMD.enqueue(write10)
            logger.flow(6,f'Host write lba = {lba}, chunk_size = {chunk_size}')
            lba += chunk_size
            total_len -= chunk_size   
        ExecuteCMD.send(clear_on_success=False)
        ExecuteCMD.clear()         
        pass
    def flow7(self) -> None:
        logger.flow(7,'Host issue L2P with written range to get CE/VB, Check if VB can match with step3 VB')
        lba = self.total_len - 1
        pca = api.lba_to_pba(self.random_en_lun, lba)
        vb = pca.w10_block.value
        ce = pca.b5_ce.value
        logger.info(f'open vb {vb}')
        self.check_vb_list.append(vb)
        self.check_ce_list.append(ce)
        for section_ten in range(9, 0, -1):
            lba = int(self.total_len * section_ten / 10 - 1)
            logger.info(f'get l2p lba {lba}, section = {section_ten}')
            pca = api.lba_to_pba(self.random_en_lun, lba)
            vb = pca.w10_block.value
            ce = pca.b5_ce.value
            logger.info(f'checking vb {vb}, section = {section_ten}')
            if ((vb not in self.check_vb_list) and (vb not in self.cur_l2_vb_list)):
                self.check_vb_list.append(vb)
                self.check_ce_list.append(ce)
        pass
    def flow8_9(self) -> None:
        logger.flow(8,'Issue 40B0 VUC to BFEA Scan (get BFEA table)')
        for idx in range(len(self.check_vb_list)):
            check_vb = self.check_vb_list[idx]
            check_ce = self.check_ce_list[idx]
            logger.info(f'check vb = {check_vb}, check_vb = {check_vb}')
            payload = project_api.issue_40B0_Bfea_Scan(3, check_vb, check_ce, 0)
            logger.flow(9,'Host get Byte[0-3]output of this vendor cmd  should be 0(Bin index)')
            output = int.from_bytes(payload[0:4], byteorder='little')
            expected_value = 0
            if output != expected_value:             
                logger.error_fp(f'output = {output} != expected_value {expected_value}')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL    
            pass
        open_l2_vb_list = self.get_target_vb_list(7)
        used_l2_vb_list = self.get_target_vb_list(17)
        cur_l2_in_list = False
        used_l2_in_list = False
        for test_vb in self.check_vb_list:
            if test_vb in open_l2_vb_list:
                logger.info(f'{test_vb} in l2')
                cur_l2_in_list = True
            if test_vb in used_l2_vb_list:
                used_l2_in_list = True
        if not used_l2_in_list:
            logger.error_fp(f'vb is not in used vb(17)')
            raise SIGHTING_PBA_UNEXPECTED
        if not cur_l2_in_list:
            logger.error_fp(f'vb is not in cur tlc l2 vb(7)')
            raise SIGHTING_PBA_UNEXPECTED
    def post_process(self) -> None:
        pass
    

run = Pattern().run
if __name__ == "__main__":
    run()