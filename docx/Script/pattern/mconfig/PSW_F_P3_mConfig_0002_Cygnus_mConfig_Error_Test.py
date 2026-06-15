import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.api.ufs_api.defines import UPIUResponse, ScsiStatus
from Script.api.cmd_seq.response import CommandResponse, get_scsi_status_str, get_sense_key_str, get_asc_ascq_description
from typing import Union
from Script.pattern.mconfig.mutual_fun import *


FFU_READY = False
PCONFIG_IN_4056 = False

class Pattern(UFSTC):
    def pre_process(self) -> None:
        config_lun()
        self.mConfig_in_FW_HW_BIN_offset = 0
        self.pConfig_in_FW_HW_BIN_offset = 1024
        # flashsettingdata = api.get_flash_setting()
        self.hw_setting = api.HwSetting.get_instance()
        self.hw_setting.update_from_device()
        self.hw_setting.backup()
        pass

    def step1(self) -> None:
        offset = 0
        if self.hw_setting.ce_num == 1:
            offset = 0
        elif self.hw_setting.ce_num == 2:
            offset = DATA_SIZE_4K_BYTE
        elif self.hw_setting.ce_num == 4:
            offset = DATA_SIZE_8K_BYTE
        elif self.hw_setting.ce_num == 8:
            offset = DATA_SIZE_12K_BYTE
        _, mConfig_in_vu_bkup = project_api.get_mConfig_data()
        _, pConfig_in_vu_bkup = project_api.get_pConfig_data()
        mConfig, pConfig = load_mConfig_pConfig_from_xlsx(OTP_value = mConfig_in_vu_bkup.OTP_value.value)

        logger.flow(1, 'search bin and get mconfig follow mConfig Format in FFU bin')
        current_bin = bytearray(4096)
        # current_bin_bkup = api.api.search_ffu_bin(api.api.FFUBinType.FW_BIN, api.api.FFUSvnType.CURRENT_SVN_BIN)
        # mConfig_in_bin, pConfig_in_bin = get_m_p_config_in_FW_HW_BIN(current_bin)
        # compare_payload(mConfig_pConfig_dict=mConfig, payload=mConfig_in_bin.payload.copy())
        # compare_payload(mConfig_pConfig_dict=pConfig, payload=pConfig_in_bin.payload.copy())
        error_OTP = [145, 146, 147, 148]
        error_OTP.remove(mConfig_in_vu_bkup.OTP_value.value)
        mConfig_in_vu_bkup.payload[0:7] = "MCONFIG".encode("ascii")
        pConfig_in_vu_bkup.payload[0:7] = "PCONFIG".encode("ascii")
        
        ffu_case = [1,2,7,8,9]
        for case in range(1, 11+1):
            logger.info(f'======================= test case {case} =======================') #ENG2
            if not FFU_READY:
                if case in ffu_case:
                    continue
            temp_mConfig = project_api.mConfig(mConfig_in_vu_bkup.payload.copy())
            temp_pConfig = project_api.pConfig(pConfig_in_vu_bkup.payload.copy())
            temp_HW_page = self.hw_setting._backup_data[offset: offset + 0x1000].copy()
            temp_bin = current_bin.copy()
            temp_mConfig.payload[0:7] = "MCONFIG".encode("ascii")
            temp_pConfig.payload[0:7] = "PCONFIG".encode("ascii")
            
            logger.flow(2, 'HW Setting Enable FFU update / same SVN')
            if case in ffu_case: #FFU case
                self.hw_setting.set_to_device(api.HwSettingField.FFU_FEATURE, api.FFUFeature.FFU_SAMVE_SVN_BACKWARD_EN)
            
            logger.flow(3, 'mConfig Test Case')
            error_value = random.randint(1, 0xFF)
            error_value2 = random.randint(1, 0xFF)
            if case == 1:
                logger.info('mConfig Case 1: write FFU bin with wrong OPT value for mconfig') #ENG2
            elif case == 2:
                logger.info('mConfig Case 2: write FFU bin with wrong OPT value for pconfig') #ENG2
            elif case == 3:
                logger.info('mConfig Case 3: C056 mConfig_VU with wrong OPT value with mconfig') #ENG2, use 0x09
                temp_mConfig.OTP_value.value = error_OTP[random.randint(0,len(error_OTP)-1)]
                self.set_mConfig_pConfig_data_and_check_resp(input=temp_mConfig, error_case=True)
            elif case == 4:
                logger.info('mConfig Case 4: C056 mConfig_VU with wrong OPT value with pconfig') #ENG2, use 0x09
                temp_pConfig.OTP_value.value = error_OTP[random.randint(0,len(error_OTP)-1)]
                self.set_mConfig_pConfig_data_and_check_resp(input=temp_pConfig, error_case=True)
            elif case == 5:
                logger.info('mConfig Case 5: C056 mConfig_VU with corr OTP value  byte[12]option = 3')
                self.set_mConfig_pConfig_data_and_check_resp(input=0x3, error_case=True)
            elif case == 6:
                logger.info('mConfig Case 5: C056 mConfig_VU with corr  OTP value  byte[12]option = 0xFF')
                self.set_mConfig_pConfig_data_and_check_resp(input=0xFF, error_case=True)
            elif case == 7:
                logger.info('mConfig Case 7: write FFU bin  mConfig_VU with unchangeable mconfig from (File Signature)') #ENG2
                current_bin[self.mConfig_in_FW_HW_BIN_offset] = error_value
                api.send_ffu_write_buffer(len(current_bin), 0, current_bin)
            elif case == 8:
                logger.info('mConfig Case 8: write FFU bin  mConfig_VU with unchangeable pconfig from (File Signature)') #ENG2
                current_bin[self.mConfig_in_FW_HW_BIN_offset] = error_value
                api.send_ffu_write_buffer(len(current_bin), 0, current_bin)
            elif case == 9:
                logger.info('mConfig Case 9: write FFU bin  mConfig_VU with unchangeable pconfig & mconfig from (File Signature)') #ENG2
                current_bin[self.mConfig_in_FW_HW_BIN_offset] = error_value
                api.send_ffu_write_buffer(len(current_bin), 0, current_bin)
            elif case == 10:
                logger.info('mConfig Case 10: C056 mConfig_VU with unchangeable mconfig(File Signature)') #ENG2, use 0x09
                temp_mConfig.Name_1.value = error_value
                self.set_mConfig_pConfig_data_and_check_resp(input=temp_mConfig, error_case=True)
            elif case == 11:
                logger.info('mConfig Case 11: C056 mConfig_VU with unchangeable pconfig(File Signature)') #ENG2, use 0x09
                temp_pConfig.Name_1.value = error_value
                self.set_mConfig_pConfig_data_and_check_resp(input=temp_pConfig, error_case=True)

        
            logger.flow(4, 'Host issue init flow with HWReset or ResetN')
            resetmode = random.choice([api.Dcmd5ResetType.HW_RESET, api.Dcmd5ResetType.RESET_N])
            api.init_tester_to_unit_ready(resetmode=resetmode)
        
            logger.flow(5, 'Host issue 4056 get mConfig data as mConfig_VU') #only mconfig, pconfig use 0x83
            _, mConfig_in_vu = project_api.get_mConfig_data()
            _, pConfig_in_vu = project_api.get_pConfig_data()
            compare_mConfig_data(get_mConfig=mConfig_in_vu, set_mConfig=mConfig_in_vu_bkup)
            compare_pConfig_data(get_pConfig=pConfig_in_vu, set_pConfig=pConfig_in_vu_bkup)
            
            logger.flow(6, 'recover mConfig pConfig')
            mConfig_in_vu_bkup.payload[0:7] = "MCONFIG".encode("ascii")
            pConfig_in_vu_bkup.payload[0:7] = "PCONFIG".encode("ascii")
            self.hw_setting.recover()
            project_api.set_mConfig_data(mConfig=mConfig_in_vu_bkup)
            project_api.set_pConfig_data(pConfig=pConfig_in_vu_bkup)
            api.init_tester_to_unit_ready(resetmode=resetmode)
            _, mConfig_in_vu = project_api.get_mConfig_data()
            _, pConfig_in_vu = project_api.get_pConfig_data()
            compare_mConfig_data(get_mConfig=mConfig_in_vu, set_mConfig=mConfig_in_vu_bkup)
            compare_pConfig_data(get_pConfig=pConfig_in_vu, set_pConfig=pConfig_in_vu_bkup)
        pass

    def post_process(self) -> None:
        pass

    def set_mConfig_pConfig_data_and_check_resp(self,input:Union[project_api.mConfig, project_api.pConfig, int], error_case:bool = False) -> None:
        # logger.info(f"{inspect.currentframe().f_code.co_name}()")  # type: ignore
        if isinstance(input, project_api.mConfig):
            response = project_api.set_mConfig_data(mConfig=input, keep_error=error_case)
        elif isinstance(input, project_api.pConfig):
            response = project_api.set_pConfig_data(pConfig=input, keep_error=error_case)
        elif isinstance(input, int):
            response =  project_api.issue_C056_to_set_mConfig_data(set_option=input, payload=bytearray(4096), keep_error=error_case)
        else:
            raise PATTERN_ASSERT_ATTR_NOT_FOUND
        if error_case:
            if not (response.upiu.b6_response == UPIUResponse.TARGET_FAILURE and response.upiu.b7_status == ScsiStatus.CHECK_CONDITION):
                logger.error_lb(f'issue set mconfig data with wrong parameter')
                logger.error_fp(f'expect response fail, but status = {get_scsi_status_str(response)}, sense_key = {get_sense_key_str(response)}, asc = {get_asc_ascq_description(response)}')
                raise SIGHTING_RESPONSE_UNEXPECTED
        pass

run = Pattern().run
if __name__ == "__main__":
    run()