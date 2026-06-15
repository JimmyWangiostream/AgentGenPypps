import package_root
from Script import api
from Script.api import cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
from Script.project_api.custom_vu import *
import random
from Script.api.exception import *
from typing import cast
from Script.api import shared
from Script.api.ufs_api import *
from Script.api.cmd_seq import QueryResponse
from Script.api.ufs_api.vendor_cmd.structs import FwGeometry
from typing import Callable
from Script.project_api.structs import micron_vendor_cmd
from Script.project_api.functions import send_data_in_vcmd, send_data_out_vcmd, send_data_in_vcmd
from typing import List, Dict
import time
from Script.api.ufs_api.defines.enum_define import *
import shutil
import configparser

_param = shared.param

class VBPolicy(Enum):
    LOG_PTE_SLC = 1
    LOG_PTE = 2
_VB_RULES = {
    VBPolicy.LOG_PTE_SLC: {"LOG_TAB_BLK", "CURRENT_PTE", "PTE_POOL", "FREE_BLK_QUEUE_TABLE","USED_BLK_POOL_SLC"}, 
    VBPolicy.LOG_PTE: {"LOG_TAB_BLK", "CURRENT_PTE", "PTE_POOL", "FREE_BLK_QUEUE_TABLE"}
}    
class RETIREMENT_TYPE(Enum):
    SGM_LVT_FAIL_AFTER_TOUCHUP = 0x5
    SGM_HVT_FAIL = 0x6
    SGM_LVT = 0x7

def check_vb_in_BBT(vb_number:int, param:Optional[project_api.D017_param] = None) -> bool:
    _, VU_DATA = project_api.issue_405E_to_get_bad_block_information()
    total_BB_count = int.from_bytes(VU_DATA[0:4], 'little')
    logger.info(f'total bb count before trigger SGM = {total_BB_count}')
    die_per_plane = 6
    start = 4
    VU_DATA_map:Dict[int,List[int]] = {}
    for idx in range(total_BB_count):
        BB_retirement_reason = project_api.BB_retirement_reason(VU_DATA[start + idx*8 : start + idx*8 +4])
        PBA = project_api.PBA_format(VU_DATA[start + 4 + idx*8 : start + 4 + idx*8 +4])
        if PBA.blockNum.value == vb_number:
            logger.info(f'idx = {idx},  PBA.block={PBA.blockNum.value}')
            return True
            # plane = PBA.CePlane.value % die_per_plane
            # ce = (PBA.CePlane.value - plane) // die_per_plane
            # logger.info(f'vb = {vb_number} match')
            # logger.info(f'ce = {ce}, plane = {plane}')
            # if ce == param.die.value and plane == param.plane.value:
            #     if param.first_low_vt_scan.value == 0 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_HVT_FAIL
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 1 and param.low_vt_re_scan.value == 0 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 1 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 0:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 1 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 3 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 0:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 3 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 3 and param.low_vt_re_scan.value == 0 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 2 and param.high_vt_scan.value == 0:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 2 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 0 and param.high_vt_scan.value == 0:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if param.first_low_vt_scan.value == 1 and param.switch.value == 0 and param.high_vt_scan.value == 1:
            #         expect_retirement_type = RETIREMENT_TYPE.SGM_LVT
            #     if expect_retirement_type.value == BB_retirement_reason.BlkType.value:
            #         return True
            #     else:
            #         logger.error(f'Expect retiremnt = {expect_retirement_type.name}({expect_retirement_type.value}), but = {BB_retirement_reason.BlkType.value}')
            # else:
            #     logger.error(f'ce/plane not match ce = {param.die.value}, plane={param.plane.value}')
                
    return False

def choose_D017_param(vb_number:int, loop:int, ce:int, plane:int) -> project_api.D017_param:
    param = project_api.D017_param()
    param.block.value = vb_number
    param.scan_type.value = 1
    param.error_inject_enable.value = 1
    param.die.value = random.randint(0, ce-1)
    param.plane.value = random.randint(0, plane-1)
    param.index.value = random.randint(0,1)
    param.touch_up.value = random.randint(0,1)
    case = loop % 13
    logger.info(f'D017 case = {case}')
    if case == 0:
        param.first_low_vt_scan.value = 0
        param.high_vt_scan.value = 1
    elif case == 1:
        param.first_low_vt_scan.value = 1
        param.switch.value = 1
        param.low_vt_re_scan.value = 0
        param.high_vt_scan.value = 1
    elif case == 2:
        param.first_low_vt_scan.value = 1
        param.switch.value = 1
        param.low_vt_re_scan.value = 1
        param.high_vt_scan.value = 0
    elif case == 3:
        param.first_low_vt_scan.value = 1 
        param.switch.value = 1
        param.low_vt_re_scan.value = 1
        param.high_vt_scan.value = 1
    elif case == 4:
        param.first_low_vt_scan.value = 1  #cuf off
        param.switch.value = 3
        param.low_vt_re_scan.value = 1
        param.high_vt_scan.value = 0
    elif case == 5:
        param.first_low_vt_scan.value = 1  #cut off
        param.switch.value = 3
        param.low_vt_re_scan.value = 1
        param.high_vt_scan.value = 1
    elif case == 6:
        param.first_low_vt_scan.value = 1
        param.switch.value = 3
        param.low_vt_re_scan.value = 0 
        param.high_vt_scan.value = 1
    elif case == 7:
        param.first_low_vt_scan.value = 1  #cut off
        param.switch.value = 2
        param.high_vt_scan.value = 0
    elif case == 8:
        param.first_low_vt_scan.value = 1  #cut off
        param.switch.value = 2
        param.high_vt_scan.value = 1
    elif case == 9:
        param.first_low_vt_scan.value = 1
        param.switch.value = 0
        param.high_vt_scan.value = 0
    elif case == 10:
        param.first_low_vt_scan.value = 1
        param.switch.value = 0
        param.high_vt_scan.value = 1
    #pass path
    elif case == 11:
        param.first_low_vt_scan.value = 0
        param.high_vt_scan.value = 0
    elif case == 12:
        param.first_low_vt_scan.value = 1
        param.switch.value = 1
        param.low_vt_re_scan.value = 0
        param.high_vt_scan.value = 0

    print_param(param)
    return param
def check_timeout(start_time: float, timeout_min: int) -> bool:
    current_time = time.time()
    if (current_time - start_time) >= timeout_min * 60:
        return True
    else:
        return False

def purge_operation() ->None:
    api.set_flag(idn=FlagIDN.PURGE_EN)
    purge_timeout = 30 
    
    start_time = time.time()
    while True:
        if check_timeout(start_time, purge_timeout):
            raise PATTERN_ASSERT_STUCK_WHILE_TIMEOUT
        val = api.read_attribute(idn=AttributeIDN.PURGE_STATUS)
        if val == PurgeStatus.PURGE_STS_COMPLETE_SUCCESS:
            break
        time.sleep(1)

def config_lun(slc_au:int, tlc_au:int, wb_au:int = 0) -> tuple[int,int]:
    
    config_descs = api.get_config_descriptors(print=True)
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
                config_descs[table].units[unit].l4_num_alloc_units = slc_au
            elif (table * 8 + unit) == 1:
                config_descs[table].units[unit].b0_lu_enable = 1
                config_descs[table].units[unit].b1_boot_lun_id = 0
                config_descs[table].units[unit].b3_memory_type = api.MemoryType.NORMAL
                config_descs[table].units[unit].l4_num_alloc_units = tlc_au
    
    config_descs[3].header.b2_conf_desc_continue = 0
    config_descs[0].header.b7_secure_removal_type = 0
    config_descs[0].header.b16_write_booster_buffer_preserve_user_space_en = api.WriteBoosterBufferPreserveUserSpaceEn.ENABLE
    config_descs[0].header.b17_write_booster_buffer_type = api.WriteBoosterBufferType.SHARED
    config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = wb_au
    for i in range(4):
        api.push_write_config(config_descs[i], index=i)
    ExecuteCMD.send()
    ExecuteCMD.clear()

    unit_desc_idxes:List[int] = []
    for lun in range(0, _param.gMaxNumberLU):
        unit_descriptor = ExecuteCMD.ReadDescriptor()
        unit_descriptor.assign(DescriptorIDN.UNIT, lun)
        unit_desc_idxes.append(ExecuteCMD.enqueue(unit_descriptor))

    ExecuteCMD.send(clear_on_success=False)
    for index in unit_desc_idxes:
        update_descriptor(DescriptorIDN.UNIT, index, cast(QueryResponse, ExecuteCMD.read_response(index)))
    ExecuteCMD.clear()

    #test unit ready all enable lun
    for lun in range(_param.gMaxNumberLU):
        if _param.gUnit[lun].b3_lu_enable:
            test_unit_ready = ExecuteCMD.CmdSeqTestUnitReady()
            test_unit_ready.set_option(lun)
            ExecuteCMD.enqueue(test_unit_ready)
    ExecuteCMD.send(clear_on_success=False)
    ExecuteCMD.clear()


    slc_lun = 0
    tlc_lun = 1
    return (slc_lun, tlc_lun) 

def compare_value( value:int,expect_value:int, desc:str="") -> None:
    if value != expect_value:
        logger.error(f'Expect {desc}={expect_value}, but = {value}')
        raise SIGHTING_FAIL_DATA_COMPARE_FAIL
    logger.info(f'{desc} val = {value}')

def print_param( param:project_api.D017_param) -> None:
    logger.info(f'die = {param.die.value}')
    logger.info(f'plane = {param.plane.value}')
    logger.info(f'block = {param.block.value}')
    logger.info(f'error_inject_enable = {param.error_inject_enable.value}')
    logger.info(f'scan_type = {param.scan_type.value}')
    logger.info(f'first_low_vt_scan = {param.first_low_vt_scan.value}')
    logger.info(f'touch_up = {param.touch_up.value}')
    logger.info(f'low_vt_re_scan = {param.low_vt_re_scan.value}')
    logger.info(f'high_vt_scan = {param.high_vt_scan.value}')
    logger.info(f'switch = {param.switch.value}')
    logger.info(f'index = {param.index.value}')

def check_is_retirement_case(param:project_api.D017_param) -> bool:
    if param.first_low_vt_scan.value == 0 and param.high_vt_scan.value == 1:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 1 and param.low_vt_re_scan.value == 0 and param.high_vt_scan.value == 1:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 1 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 0:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 1 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 1:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 3 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 0:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 3 and param.low_vt_re_scan.value == 1 and param.high_vt_scan.value == 1:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 3 and param.low_vt_re_scan.value == 0 and param.high_vt_scan.value == 1:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 2 and param.high_vt_scan.value == 0:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 2 and param.high_vt_scan.value == 1:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 0 and param.high_vt_scan.value == 0:
        return True
    if param.first_low_vt_scan.value == 1 and param.switch.value == 0 and param.high_vt_scan.value == 1:
        return True
    return False
def unmap_data( lun:int, start_lba:int, len:int, total_len:int, write_record:List[List[WriteRecordNode]]=[]) -> None:
    while total_len > 0:
        len = min(total_len, len)
        unmap = ExecuteCMD.Unmap()
        unmap.assign(lun=lun, lba=start_lba, length=len)
        ExecuteCMD.enqueue(unmap)
        start_lba += len
        total_len -= len

    ExecuteCMD.send(clear_on_success=False)
    for cmd in ExecuteCMD._cmd_list:
        save_write_info_by_cmd(cmd, write_record)
    ExecuteCMD.clear()
def read_data( lun:int, start_lba:int, len:int, total_len:int) -> None:
    while total_len > 0:
        len = min(total_len, len)
        read10 = ExecuteCMD.Read10()
        read10.assign(lun=lun, lba=start_lba, length=len, fua=0)
        ExecuteCMD.enqueue(read10)
        start_lba += len
        total_len -= len

    ExecuteCMD.send(clear_on_success=False)
    ExecuteCMD.clear()
def write_data( lun:int, start_lba:int, len:int, total_len:int, write_record:List[List[WriteRecordNode]]=[]) -> None:
    while total_len > 0:
        len = min(total_len, len)
        write10 = ExecuteCMD.Write10()
        logger.info(f'start lba = {start_lba}, len = {len}')
        write10.assign(lun=lun, lba=start_lba, length=len, fua=1)
        ExecuteCMD.enqueue(write10)
        start_lba += len
        total_len -= len

    ExecuteCMD.send(timeout=api.UniformTimeout(val=30000, unit=api.TimeResolution.ms), clear_on_success=False)
    if write_record:
        for cmd in ExecuteCMD._cmd_list:
            save_write_info_by_cmd(cmd, write_record)
    ExecuteCMD.clear()
    

def get_bbt_list() -> List[Any]:
    bb_list : List[int] = []
    _, VU_DATA = project_api.issue_405E_to_get_bad_block_information()
    total_BB_count = int.from_bytes(VU_DATA[0:4], 'little')
    logger.info(f'total bb count before trigger SGM = {total_BB_count}')
    start = 4
    VU_DATA_map:Dict[int,List[int]] = {}
    for idx in range(total_BB_count):
        BB_retirement_reason = project_api.BB_retirement_reason(VU_DATA[start + idx*8 : start + idx*8 +4])
        PBA = project_api.PBA_format(VU_DATA[start + 4 + idx*8 : start + 4 + idx*8 +4])
        logger.info(f'idx = {idx}, BB_retirement_reason.BlkType={BB_retirement_reason.BlkType.value}, BB_retirement_reason.Type={BB_retirement_reason.Type.value}, PBA.block={PBA.blockNum.value}, PBA.ceplane = {PBA.CePlane.value}')
        bb_list.append(PBA.blockNum.value)
    return list(set(bb_list))
def choose_free_block(group_list:list[str]) ->int:
    vb_group_name = random.choice(group_list)
    
    vb_info = project_api.VBInfo()
    vb_list = []
    for vb, info in vb_info.list.items():
        if project_api.VBList().vb_group_list()[vb_group_name] == info['group']:
            vb_list.append(vb)
    print(vb_list)
    logger.info(f'{vb_group_name} vb list, len = {len(vb_list)}')

    bbt_list = get_bbt_list()
    filter_vb_list = [vb for vb in vb_list if vb not in bbt_list]
    random_index = random.randint(0, len(filter_vb_list )-1)
    logger.info(f'choosen vb index = {filter_vb_list[random_index]}({vb_group_name})')
    return filter_vb_list[random_index]

def check_vb_in_specific_pool(vb_number:int, vb_group_name:str) ->bool:
    vb_info = project_api.VBInfo()
    vb_list = []
    for vb, info in vb_info.list.items():
        if project_api.VBList().vb_group_list()[vb_group_name] == info['group']:
            vb_list.append(vb)
            logger.debug('vb = %d' % vb)
            logger.debug('partition = %d' % info['partition'])
    logger.info(f'{vb_group_name} vb list, len = {len(vb_list)}')
    if vb_number in vb_list:
        return True
    return False
def compare_payload(payload1:bytearray, payload2:bytearray) -> bool:
    return (payload1 == payload2)

def check_vb_in_which_group(vb_number:int) -> str:
    _, payload = get_vb_info()
    vb_info = project_api.VBInfo()
    vb_number_info = {k: ((int.from_bytes(payload[vb_number * 4:vb_number*4 + 4], 'little') >>
                     v['pos']) & v['mask']) for k, v in vb_info.VB_LIST_DATA_FORMAT.items()}
    target_index = vb_number_info['group']
    target_group_list = [vb_grp_name for vb_grp_name, vb_grp_index in project_api.VBList().vb_group_list().items() if vb_grp_index == target_index]
    logger.info(f' vb number = {vb_number} is in {target_group_list[0]}')
    return target_group_list[0]
def check_vb_in(vb_number:int, policy:VBPolicy) -> bool:
    vb_group_name =  check_vb_in_which_group(vb_number)
    if vb_group_name in _VB_RULES[policy]:
        return True
    return False
def current_pca(ce:int,plane:int,page:int) -> tuple[int, int, int]:
    max_plane = 6
    max_page = 1104
    value = ce * (max_plane * max_page) + plane * max_page + page
    if value == 0:
        raise PATTERN_ASSERT_UNEXPECTED_CONDITION
    value -= 1
    prev_ce = value // (max_plane * max_page)
    value %= (max_plane * max_page)
    prev_plane = value // max_page
    prev_page = value % max_page
    return prev_ce, prev_plane, prev_page

def print_open_vb_information_phison(open_vb_info: OpenVBInfo) -> None:

        logger.info('================= open_vb_information =================')
        # 取得所有屬於 OpenVBInfoUnit 的子單元
        sub_units = {
            name: obj
            for name, obj in open_vb_info.__dict__.items()
            if hasattr(obj, "__dict__")               # 必須是物件
            and any(hasattr(v, "start_offset") for v in obj.__dict__.values())  # 內含欄位
        }

        for unit_name, unit_obj in sub_units.items():
            # 收集該單元內所有具有 start_offset / end_offset / value 的欄位
            fields = [
                (fname, fobj)
                for fname, fobj in unit_obj.__dict__.items()
                if hasattr(fobj, "start_offset")
                and hasattr(fobj, "end_offset")
                and hasattr(fobj, "value")
            ]

            # 依起始位元組排序
            fields.sort(key=lambda kv: kv[1].start_offset)

            # 輸出單元標頭
            logger.info(f'--- {unit_name} ---')
            # 輸出欄位資訊
            for fname, fobj in fields:
                logger.info(
                    f'Byte[{fobj.start_offset}:{fobj.end_offset}]: '
                    f'{unit_name}.{fname} = {fobj.value}'
                )

def open_card()->None:
    
    BASE = Path(__file__).resolve().parent
    src_mp_path = (BASE / "../../../mp_tool").resolve()
    tar_mp_path = (BASE / "./MP_Tool").resolve()

    ini_file_list = []

    if not os.path.exists(tar_mp_path):
        logger.info(f'[MP] copy mp from {src_mp_path} to {tar_mp_path}')
        shutil.copytree(src_mp_path, tar_mp_path)
        logger.info(f'[MP] Modify MP param.ini in dedicated port folder: Set[Options][Preformat_Option_Value] => 8')
        config = configparser.ConfigParser()
        config.optionxform = str.lower # type: ignore

        for item in tar_mp_path.iterdir():
            if item.is_file() and item.suffixes[-1] == '.ini':
                ini_file_list.append(item.name)

        for ini_name in ini_file_list:
            ini_path = os.path.join(tar_mp_path,ini_name)
            config.clear()
            config.read(ini_path)
            
            if config.has_section("Options") != True:
                config.add_section("Options")
            config["Options"]["preformat_option_value"] = "8"

            with open(ini_path, 'w', encoding='cp950') as f:
                config.write(f, space_around_delimiters=False)

    api.MP(mp_tool_path=str(tar_mp_path), mp_tester_fw_path=str(tar_mp_path), sdk_tester_fw_path=str(tar_mp_path)).execute()
    api.first_init_to_max_hs_gear(link_startup_mode=_param.current_speed.link_startup_mode, ref_clk=_param.current_speed.refclk)
