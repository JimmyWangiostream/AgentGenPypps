import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from typing import Dict, List, cast, Optional
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.api.ufs_api.vendor_cmd.functions import *
from enum import Enum, IntEnum
import time
    

    
    
    
    
def get_VB_group(show:bool = False) -> Dict[int, Dict[str, int]]:
    fw_geometry = api.get_fw_geometry()
    vb_list_data_format = {
            'group': {'pos': 0, 'len': 6, 'mask': 0x3f}, 
            'access_mode': {'pos': 6, 'len': 2, 'mask': 0x3}, 
            'dirty': {'pos': 8, 'len': 1, 'mask': 0x1}, 
            'partition': {'pos': 9, 'len': 2, 'mask': 0x3}, 
            'cursor_idx': {'pos': 11, 'len': 1, 'mask': 0x1}, 
            'pte_tbl_mark': {'pos': 12, 'len': 1, 'mask': 0x1}, 
            'host_w_mark': {'pos': 13, 'len': 2, 'mask': 0x3}, 
            'src_uecc': {'pos': 15, 'len': 1, 'mask': 0x1}, 
            'vb_trim': {'pos': 16, 'len': 2, 'mask': 0x3}, 
            'risky_type': {'pos': 18, 'len': 2, 'mask': 0x3}, 
            'rsv': {'pos': 20, 'len': 12, 'mask': 0xFFF}, 
        }
    response, rep_data = api.get_vb_info()
    dumpfile("rep_data.bin", bytearray(rep_data))
    ftl_vb_list_data = dict()

    for vb in range(len(rep_data)):
        if fw_geometry.l52_total_vb_count <= vb:
            break
        if vb *4  >= len(rep_data):
            break

        ftl_vb_list_data.update({vb : {k: (((rep_data[vb*4]|rep_data[vb*4+1]<<8) >> v['pos']) & v['mask']) for k, v in vb_list_data_format.items()}})
    if show:
        for vb, info in ftl_vb_list_data.items():
            group = info['group']
            access_mode = info['access_mode']
            partition = info['partition']
            logger.info(f'VB {vb} grouptype = {group} ({project_api.VB_GROUP(group).name}), access_mode = {access_mode}, partition = {partition}')
    return ftl_vb_list_data


def config_lun() -> tuple[int,int]:
    Total_AU_Count = shared.param.gGeometry.q4_total_raw_device_capacity // (shared.param.gGeometry.l13_segment_size * shared.param.gGeometry.b17_allocation_unit_size)
    config_descs = api.get_config_descriptors(print=False)
    for table in range(4):
        for unit in range(8):
            config_descs[table].header.b2_conf_desc_continue = 1
            config_descs[table].units[unit].b0_lu_enable = 0
            config_descs[table].units[unit].b1_boot_lun_id = 0
            config_descs[table].units[unit].l4_num_alloc_units = 0
            config_descs[table].units[unit].b9_logical_block_size = 0xc
            config_descs[table].units[unit].b10_provisioning_type = api.ProvisioningType.THIN_PROVISIONING_ERASE
            if (table * 8 + unit) == 0:
                config_descs[table].units[unit].b0_lu_enable = 1
                config_descs[table].units[unit].b1_boot_lun_id = 0
                config_descs[table].units[unit].b3_memory_type = api.MemoryType.ENHANCED_1
                config_descs[table].units[unit].l4_num_alloc_units = min(shared.param.gGeometry.l44_enhanced1_max_n_alloc_u, Total_AU_Count//2)
            elif (table * 8 + unit) == 1:
                config_descs[0].units[unit].b0_lu_enable = 1
                config_descs[table].units[unit].b1_boot_lun_id = 0
                config_descs[0].units[unit].b3_memory_type = api.MemoryType.NORMAL
                config_descs[0].units[unit].l4_num_alloc_units = Total_AU_Count//2
    
    config_descs[3].header.b2_conf_desc_continue = 0
    config_descs[0].header.b16_write_booster_buffer_preserve_user_space_en = api.WriteBoosterBufferPreserveUserSpaceEn.ENABLE
    config_descs[0].header.b17_write_booster_buffer_type = api.WriteBoosterBufferType.SHARED
    config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = 0
    for i in range(4):
        api.push_write_config(config_descs[i], index=i)
    ExecuteCMD.send()
    ExecuteCMD.clear()

    unit_desc_idxes:List[int] = []
    for lun in range(0, shared.param.gMaxNumberLU):
        unit_descriptor = ExecuteCMD.ReadDescriptor()
        unit_descriptor.assign(api.DescriptorIDN.UNIT, lun)
        unit_desc_idxes.append(ExecuteCMD.enqueue(unit_descriptor))

    ExecuteCMD.send(clear_on_success=False)
    for index in unit_desc_idxes:
        api.update_descriptor(api.DescriptorIDN.UNIT, index, cast(api.QueryResponse, ExecuteCMD.read_response(index)))
    ExecuteCMD.clear()

    for lun in range(shared.param.gMaxNumberLU):
        if shared.param.gUnit[lun].b3_lu_enable:
            test_unit_ready = ExecuteCMD.CmdSeqTestUnitReady()
            test_unit_ready.set_option(lun)
            ExecuteCMD.enqueue(test_unit_ready)
    ExecuteCMD.send(clear_on_success=False)
    ExecuteCMD.clear()

    slc_lun = 0
    tlc_lun = 1
    return (slc_lun, tlc_lun)

def get_PCA_and_print(lun: int, lba: int, rpmb_region: int = 0) -> PCA:
    _pca = lba_to_pba(lun, lba, rpmb_region)
    pca = PCA()
    pca.from_bytes(bytearray(_pca.payload))
    logger.info(f'Lun{lun}, LBA = {lba}: Block = {(pca.b11_block_h<<8) | (pca.b10_block_l)}, mode = {pca.b4_mode}, CE = {pca.b5_ce}, Plane = {pca.b6_plane}, fPage = {pca.l12_fpage}(pageline = {pca.l12_fpage>>5}), lmu = {pca.b20_lmu}, format = {pca.b7_format}')
    return pca

def print_open_vb_info_cursor(cursor:api.OpenVBInfoUnit, cursor_name:str) -> None:
    logger.info(f"===== {cursor_name} =====")
    logger.info(f"logical_vb: {cursor.logical_vb.value}")
    logger.info(f"physical_vb: {cursor.physical_vb.value}")
    logger.info(f"first_empty_CE: {cursor.first_empty_CE.value}")
    logger.info(f"first_empty_plane: {cursor.first_empty_plane.value}")
    logger.info(f"first_empty_physical_page: {cursor.first_empty_physical_page.value}")
    logger.info(f"first_empty_node: {cursor.first_empty_node.value}")

def polling_bkops(expect_value:int, timeout:int) -> int:
    start_time = time.time()
    while True:
        value_from_attribute = api.read_attribute(idn=api.AttributeIDN.BG_OP_STATUS)
        if value_from_attribute == expect_value:
            break
        if (time.time() - start_time) > timeout:
            logger.error('timeout!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
    return value_from_attribute

def trigger_PSA_refresh(write_record:List[List[api.WriteRecordNode]]) -> None:
    dev_desc = api.get_device_descriptor()
    api.write_attribute(idn=api.AttributeIDN.PSA_DATA_SIZE, val=dev_desc.l37_psa_max_data_size)
    api.write_attribute(idn=api.AttributeIDN.PSA_STATE, val=api.PSAState.PRE_SOLDERING)
    logger.info(f"PSA State = {api.read_attribute(idn=api.AttributeIDN.PSA_STATE)}")
    api.sequential_write(lun=0, start_lba=0, total_size=api.BLOCK4K_SIZE_128M_BYTE, chunk_size=api.BLOCK4K_SIZE_128M_BYTE, fua = 0,
                    need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)
    api.write_attribute(idn=api.AttributeIDN.PSA_STATE, val=api.PSAState.LOADING_COMPLETE)
    api.init_tester_to_unit_ready(resetmode=api.Dcmd5ResetType.HW_RESET)
    logger.info(f"PSA State = {api.read_attribute(idn=api.AttributeIDN.PSA_STATE)}")
    api.random_write(cmd_count=1, min_lun=0, max_lun=0, min_lba=1, max_lba=1, min_size=api.BLOCK4K_SIZE_4K_BYTE, max_size=api.BLOCK4K_SIZE_4K_BYTE,
                    need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=write_record)
    logger.info(f"PSA State = {api.read_attribute(idn=api.AttributeIDN.PSA_STATE)}")
    return


def trigger_BFEA_refresh(VB:int) -> None:
    flash_setting = get_flash_setting()
    payload = project_api.issue_40B0_Bfea_Scan(1, 1, 0, 0)
    logger.flow(6,'Issue 40B0 bfea scan')
    min_bin = 0xFFFFFFFF
    for ce in range(flash_setting.Max_Fdevice):
        logger.info(f'40B0 option = 3, vb = {VB}, ce = {ce}')
        payload = project_api.issue_40B0_Bfea_Scan(3, VB, ce, 0)
        output = int.from_bytes(payload[0:4], byteorder='little')  
        logger.info(f'result = {output}')
        if min_bin > output:
            min_bin = output
    # min_bin_val = min_bin  
    # logger.flow(7,f'Get min bin from vb {VB} from all ce = {min_bin_val}')
    # logger.flow(8,'Issue 40B0 VUC to BFEA Scan to set timer')
    # # self.setting_timer_minutes = 1
    # if min_bin_val <= 1:
    #     grp = 0
    # elif min_bin_val <= 8:
    #     grp = 1
    # elif min_bin_val <= 15:
    #     grp = 2
    # self.grp = grp            
    # logger.info(f'grp = {self.grp}')
    # logger.info(f'40B0 opcode = 9, grp = {grp}, timer minute = {self.setting_timer_minutes}')
    # project_api.issue_40B0_Bfea_Scan(9, grp, self.setting_timer_minutes, 0)
    # logger.flow(9,f'idle {self.setting_timer_minutes} min')
    # sleep(self.setting_timer_minutes * 60)
    
def get_sorted_VB_list() -> Dict[project_api.VBListNum, List[int]]:
    resp = project_api.custom_vu.issue_406D_get_VB_list_info()
    sorted_VB_list_dict:Dict[project_api.VBListNum, List[int]] = {}
    offset = 0
    VB_list = 0
    while offset < len(resp.data):
        vb_count = int.from_bytes(resp.data[offset:offset+2], byteorder='little')
        offset +=2
        for i in range(vb_count):
            vb = int.from_bytes(resp.data[offset:offset+2], byteorder='little')
            if project_api.VBListNum(VB_list) not in sorted_VB_list_dict:
                sorted_VB_list_dict[project_api.VBListNum(VB_list)] = []
            sorted_VB_list_dict[project_api.VBListNum(VB_list)].append(vb)
            offset +=2
        VB_list+=1
    return sorted_VB_list_dict

def polling_bkops_idle() -> None:
    while 1:
        bkops_status = api.read_attribute(idn=api.AttributeIDN.BG_OP_STATUS)
        if bkops_status == 0:
            break
        time.sleep(1)

def get_HP_MP_LP_list(vb_list:List[int], max_cnt:int = 0) -> Dict[project_api.VUC087Paremeter, List[int]]:
    vb_random = vb_list[:]
    random.shuffle(vb_random)
    if max_cnt:
        vb_random = vb_random[:max_cnt]
    HP_list = [vb_random.pop()] if vb_random else []
    MP_list = [vb_random.pop()] if vb_random else []
    LP_list = [vb_random.pop()] if vb_random else []
    for vb in vb_random:
        r = random.randint(0, 2)
        if r == 0:
            HP_list.append(vb)
        elif r == 1:
            MP_list.append(vb)
        else:
            LP_list.append(vb)
    temp = {}
    if HP_list:
        temp[project_api.VUC087Paremeter.HighPriority] =  HP_list
    if MP_list:
        temp[project_api.VUC087Paremeter.MediumPriority] =  MP_list
    if LP_list:
        temp[project_api.VUC087Paremeter.LowPriority] =  LP_list
    return temp

def check_booking_queue(PriorityDict:Dict[project_api.VUC087Paremeter, List[int]]) -> project_api.BookingQueue:
    _, booking_q = project_api.issue_40C5_to_get_booking_queue()
    PriorityDict_temp = copy.deepcopy(PriorityDict)
    if PriorityDict_temp:
        if booking_q.LogicalVBNumberInBookingQueue.value == 0:
            logger.error_lb(f'check LogicalVBNumberInBookingQueue after bkops idle')
            logger.error_fp(f'expect LogicalVBNumberInBookingQueue is not 0, but current value = {booking_q.LogicalVBNumberInBookingQueue.value}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        
        for priority, vb_list in PriorityDict_temp.items():
            logger.info(f'check if {priority.name} has vb {vb_list}')
        for idx, VBs in enumerate(booking_q.BookingQueueVB):
            vb = VBs.LogicalVBNumber.value
            Priority_bit = project_api.BookingUser(VBs.TheBookingUser.value & 0x700)
            if Priority_bit == project_api.BookingUser.BOOKING_IN_HP:
                Priority = project_api.VUC087Paremeter.HighPriority
            elif Priority_bit == project_api.BookingUser.BOOKING_IN_MP:
                Priority = project_api.VUC087Paremeter.MediumPriority
            else:
                Priority = project_api.VUC087Paremeter.LowPriority
            logger.info(f'BookingQ[{idx}]: VB {vb}, TheBookingUser: {project_api.BookingUser(VBs.TheBookingUser.value & project_api.BookingUser.MAX_BOOKING_USER_COUNT-1).name} ({Priority.name})')
            if vb not in PriorityDict_temp[Priority]:
                logger.error_lb(f'check vb {vb} after Booking')
                logger.error_fp(f'VB {vb} is {Priority_bit.name},  but not in {Priority.name} {PriorityDict_temp[Priority]}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            else:
                PriorityDict_temp[Priority].remove(vb)
        for priority, vb_list in PriorityDict_temp.items():
            for vb in vb_list:
                logger.error_lb(f'check vb {vb} after Booking')
                logger.error_fp(f'VB {vb} is not in booking_q, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
    else:
        logger.info(f'check if LogicalVBNumberInBookingQueue is 0')
        if booking_q.LogicalVBNumberInBookingQueue.value != 0:
            logger.error_lb(f'check LogicalVBNumberInBookingQueue after bkops idle')
            logger.error_fp(f'expect LogicalVBNumberInBookingQueue is 0, but current value = {booking_q.LogicalVBNumberInBookingQueue.value}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
    return booking_q

def check_vb_release(PriorityDict:Dict[project_api.VUC087Paremeter, List[int]]) -> Dict[project_api.VBListNum, List[int]]:
    sorted_vb_dict = get_sorted_VB_list()
    for Priority, vb_list in PriorityDict.items():
        for vb in vb_list:
            if vb not in sorted_vb_dict[project_api.VBListNum.FREE_BLK_QUEUE_TLC]:
                current_group = project_api.VBListNum.OTHER
                for group, l in sorted_vb_dict.items():
                    if vb in l:
                        current_group = group                            
                        break
                logger.error_lb(f'check VB {vb} after bkops idle')
                logger.error_fp(f'expect VB {vb} is in FREE_BLK_QUEUE_TLC, but current in the {current_group.name}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
    return sorted_vb_dict