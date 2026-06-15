import package_root
from Script import api
from Script.api.util.functions import dumpfile
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.vendor_cmd.functions import set_mconfig, get_mconfig, get_flash_setting
from Script.api.ufs_api.defines.constant_define import *
from Script.api.ufs_api import read_fw_value
import time
from Script.project_api.set_get_temperature.structs import GetNandTemperature, SetNandTemperature
import inspect
from Script.api import  cmd_seq as ExecuteCMD


class Pattern(UFSTC):
    def pre_process(self) -> None:
        self.test_4021()
        pass
    
    def test_4021(self) -> None:
        logger.flow(1,"issue 4021 to get each nand temperature")
        rsp , GetNandTemperature = project_api.issue_4021_get_nand_temperature()
        # normal temperature case
        flash_setting = get_flash_setting()
        ce_num = flash_setting.Max_Fdevice
        #vu set temperature case
        logger.flow(3,"issue D08A to set temperature , with Use_Delayed_fake_tmeperatures = 0, bEnableSetVuTemp = 1,  tempeprature = 20,  , sensor1 (controller) = 85")
        temp_gap = 37
        temp_set = 20
        temp_set_controller = 85
        set_nand_temp = SetNandTemperature()
        set_nand_temp.bEnableSetVuTemp.value = 1
        set_nand_temp.NAND_TEMPERATURE_DIE_0.value = temp_set
        set_nand_temp.UC_TERMAL_SENSOR_1.value = temp_set_controller
        if ce_num >= 2:
            set_nand_temp.NAND_TEMPERATURE_DIE_1.value = temp_set
        if ce_num >= 4:
            set_nand_temp.NAND_TEMPERATURE_DIE_2.value = temp_set
            set_nand_temp.NAND_TEMPERATURE_DIE_3.value = temp_set
        set_nand_temp.Use_Delayed_fake_tmeperatures.value = 0  
        rsp = project_api.issue_D08A_set_vu_temperature(set_nand_temp)
        logger.flow(4,"issue 4021 to get each nand temperature")
        rsp , GetNandTemperature = project_api.issue_4021_get_nand_temperature()
        if (temp_set + temp_gap) != GetNandTemperature.temperature_of_die_0.value:
            logger.error_fp(f'temperature ce0 compare fail')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        if ce_num >= 2:
            if (temp_set + temp_gap)!= GetNandTemperature.temperature_of_die_1.value:
                logger.error_fp(f'temperature ce1 compare fail')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        if ce_num >= 4:
            if (temp_set + temp_gap) != GetNandTemperature.temperature_of_die_2.value:
                logger.error_fp(f'temperature ce2 compare fail')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            if (temp_set + temp_gap) != GetNandTemperature.temperature_of_die_3.value:
                logger.error_fp(f'temperature ce3 compare fail')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL        
        logger.info("issue 40FD to get controller temperature")
        response = project_api.issue_40FD_get_uC_temp()
        sign_bit = (response.data[4] & 0x08) >> 3
        value_bits = response.data[4] & 0x07
        dumpfile('40FD_get_nand_temp',response.data)
        VU_temp = -(int.from_bytes([value_bits, response.data[3]], byteorder='little')) if sign_bit == 1 else int.from_bytes([response.data[3], value_bits], byteorder='little')
        VU_temp = VU_temp * 0.25
        logger.info(f'temp = {VU_temp}')
        ExecuteCMD.clear()
        logger.flow(5,"issue 40FD to get controller temperature")
        rsp, data_temp = project_api.issue_40FD_get_uC_temp_123()
        logger.flow(6,"expected controller temp = 85")
        dumpfile('40FD_get_nand_temp',data_temp)

        if VU_temp != temp_set_controller:
            logger.error_fp(f'temperature controller compare fail, get temp  {VU_temp} != setting temp {temp_set_controller}')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL            
        # recover
        set_nand_temp.bEnableSetVuTemp.value = 0
        set_nand_temp.NAND_TEMPERATURE_DIE_0.value = temp_set
        if ce_num >= 2:
            set_nand_temp.NAND_TEMPERATURE_DIE_1.value = temp_set
        if ce_num >= 4:
            set_nand_temp.NAND_TEMPERATURE_DIE_2.value = temp_set
            set_nand_temp.NAND_TEMPERATURE_DIE_3.value = temp_set
        set_nand_temp.Use_Delayed_fake_tmeperatures.value = 0  
        rsp = project_api.issue_D08A_set_vu_temperature(set_nand_temp)
        pass
    def step1(self) -> None:
        self.test_4021()                 
        pass
    def post_process(self) -> None:
        pass
    



run = Pattern().run
if __name__ == "__main__":
    run()