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
from Script.api.ufs_api.descriptors.configuration_desc.functions import print_config, push_write_config

from Script.api.ufs_api.defines.enum_define import QueryResponseCode
from Script.api import shared
from Script.lib import sdk_lib as lib
import random
from Script.api.ufs_api import *
from Script.api.exception import *
from Script.api.ufs_api.rpmb.rpmb import RPMB
from Script.api.ufs_api.vendor_cmd.functions import *
from typing import cast
from Script.lib.sdk_lib.user.exception import  DLL_STATUS_FAIL

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
        self.slc_vb_size = (self.fw_geometry.l84_vb_size_u0 * 512 // 4096)
        self.test_vb = 0
        self.test_ce = 0
        self.tlc_vb_size = (self.fw_geometry.l88_vb_size_u1 * 512 // 4096)      
        self.target_set_bfea_vb_list:List[int] = []
        self.check_vb_list:List[int] = []
        self.check_ce_list:List[int] = []
        self.correct_ec = 0
        self.flow1()
        #test wb case 
        # self.flow2(4)
        # self.flow3(4)
        # self.flow4(4)
        # self.flow5_6()        
        self.flow2()
        for case_id in range(1,2):
            self.flow3(case_id)
            self.flow4(case_id)
        self.flow5()
        pass

    def config_lun(self) -> None:
        self.Total_AU_Count = shared.param.gGeometry.q4_total_raw_device_capacity // (shared.param.gGeometry.l13_segment_size * shared.param.gGeometry.b17_allocation_unit_size) 
        self.unit_desc_idxes:List[int] = []
        config_descs = api.get_config_descriptors(print=True)
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = 0x0
        
        for i in range(4): 
            for unit in range(8):
                if (i * 8 + unit) == 0:
                    config_descs[i].units[unit].b0_lu_enable = 1
                    config_descs[i].units[unit].b1_boot_lun_id = 0
                    config_descs[i].units[unit].b3_memory_type = api.MemoryType.NORMAL
                    config_descs[i].units[unit].l4_num_alloc_units = int(self.Total_AU_Count)
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
    def rpmb_key_programming(self) -> None:
        try:
            write_counter = self.rpmb.rpmb_read_counter()
        except SPEC_ASSERT_RPMB_KEY_NOT_PROGRAMMED_YET as e:
            self.rpmb.rpmb_key_programming()
            write_counter = self.rpmb.rpmb_read_counter()
                    
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
        logger.flow(1,'config lun')
        self.config_lun()
        self.dev_desc = api.get_device_descriptor()
        self.rpmb = RPMB(self.rpmb_region0)
        self.rpmb_key_programming()
    def flow2(self) -> None:
        logger.flow(2,'Host get output from 404A')
        self.backup_bin_404A = project_api.issue_404A_Get_Bfea_Bin_Offset()
    def flow3(self, case_num:int) -> None:
        logger.flow(3,'Host get output from 404A')
        if case_num == 1:
            setting_N = random.randint(0,15)
            self.backup_N = setting_N
        elif case_num == 2:
            setting_N = 16
        self.setting_N = setting_N
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
        if case_num == 2:
            setting_EC_Interval = random.randint(1,4)
            logger.info(f'setting_N = {setting_N}, setting_EC_Interval = {setting_EC_Interval}, setting_SLC_L1 = {setting_SLC_L1}, setting_MLC_L1 = {setting_MLC_L1}\
                        setting_MLC_L2 = {setting_MLC_L2}, setting_MLC_L3 = {setting_MLC_L3}, setting_TLC_L1 = {setting_TLC_L1}, setting_TLC_L2 = {setting_TLC_L2}, \
                            setting_TLC_L3 = {setting_TLC_L3}, setting_TLC_L4 = {setting_TLC_L4}, setting_TLC_L5 = {setting_TLC_L5}, setting_TLC_L6 = {setting_TLC_L6}\
                                setting_TLC_L7 = {setting_TLC_L7}')
            try:
                project_api.issue_D04A_Set_Bin_Offset(setting_N, setting_EC_Interval, setting_SLC_L1, setting_MLC_L1, setting_MLC_L2, setting_MLC_L3, setting_TLC_L1, setting_TLC_L2, setting_TLC_L3, setting_TLC_L4, setting_TLC_L5, setting_TLC_L6, setting_TLC_L7)
            except DLL_RESPONSE_ERROR:
                logger.info
                ExecuteCMD.clear()   
        else:
            for setting_EC_Interval in range(1,5):
                project_api.issue_D04A_Set_Bin_Offset(setting_N, setting_EC_Interval, setting_SLC_L1, setting_MLC_L1, setting_MLC_L2, setting_MLC_L3, setting_TLC_L1, setting_TLC_L2, setting_TLC_L3, setting_TLC_L4, setting_TLC_L5, setting_TLC_L6, setting_TLC_L7)
    def flow4(self, case_num:int) -> None:
        logger.flow(4,'Host get output from 404A')
         
        if case_num == 1:
            self.cur_bin_404A = project_api.issue_404A_Get_Bfea_Bin_Offset() 
            for i in range(11):
                if self.cur_bin_404A.payload[self.setting_N*11 + i] != 128:
                    logger.error_fp(f'self.cur_bin_404A.payload[self.setting_N*11 + i]({self.cur_bin_404A.payload[self.setting_N*11 + i]}) != 128')
                    raise SIGHTING_FAIL_DATA_COMPARE_FAIL   
        elif case_num ==2 :
            pass
    def flow5(self)->None:
        for setting_EC_Interval in range(1,5):
            setting_SLC_L1 = self.backup_bin_404A.payload[self.backup_N*11]
            #settinh_EC_interval = 1 # ask
            setting_MLC_L1 = self.backup_bin_404A.payload[self.backup_N*11 + 1]
            setting_MLC_L2 = self.backup_bin_404A.payload[self.backup_N*11 + 2]
            setting_MLC_L3 = self.backup_bin_404A.payload[self.backup_N*11 + 3]
            setting_TLC_L1 = self.backup_bin_404A.payload[self.backup_N*11 + 4]
            setting_TLC_L2 = self.backup_bin_404A.payload[self.backup_N*11 + 5]
            setting_TLC_L3 = self.backup_bin_404A.payload[self.backup_N*11 + 6]
            setting_TLC_L4 = self.backup_bin_404A.payload[self.backup_N*11 + 7]
            setting_TLC_L5 = self.backup_bin_404A.payload[self.backup_N*11 + 8]
            setting_TLC_L6 = self.backup_bin_404A.payload[self.backup_N*11 + 9]
            setting_TLC_L7 = self.backup_bin_404A.payload[self.backup_N*11 + 10]
            project_api.issue_D04A_Set_Bin_Offset(self.backup_N, setting_EC_Interval , setting_SLC_L1, setting_MLC_L1, setting_MLC_L2, setting_MLC_L3, setting_TLC_L1, setting_TLC_L2, setting_TLC_L3, setting_TLC_L4, setting_TLC_L5, setting_TLC_L6, setting_TLC_L7)        
    def post_process(self) -> None:
        pass
    

run = Pattern().run
if __name__ == "__main__":
    run()