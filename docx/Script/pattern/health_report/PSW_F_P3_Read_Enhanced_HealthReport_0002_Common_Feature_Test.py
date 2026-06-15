import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.vendor_cmd.functions import set_mconfig, get_mconfig
from Script.api.ufs_api.defines.constant_define import *
from Script.api.ufs_api import *
from Script.project_api.health_report.functions import *

ENG2_WA = True

class Pattern(UFSTC):
    def pre_process(self) -> None:
        self.fw_geometry = api.get_fw_geometry()
        self.geometry_desc = api.get_geometry_descriptor()
        self.slc_vb_size = (self.fw_geometry.l84_vb_size_u0 * 512 // 4096)
        self.test_vb = 0
        self.test_ce = 0
        self.tlc_vb_size = (self.fw_geometry.l88_vb_size_u1 * 512 // 4096)      
        self.random_en_lun = 0 #random.randint(0, 31) disable ats bug?
        self.Total_AU_Count = self.geometry_desc.q4_total_raw_device_capacity / (self.geometry_desc.l13_segment_size * self.geometry_desc.b17_allocation_unit_size)        
        pass
    def config_lun(self) -> None:
        self.unit_desc_idxes:List[int] = []
        config_descs = api.get_config_descriptors(print=True)
        config_descs[0].header.l18_num_shared_write_booster_buffer_alloc_units = 0x0
        
        for i in range(4): 
            for unit in range(8):
                if (i * 8 + unit) == 0:
                    config_descs[i].units[unit].b0_lu_enable = 1
                    config_descs[i].units[unit].b1_boot_lun_id = 0
                    config_descs[i].units[unit].b3_memory_type = api.MemoryType.NORMAL
                    config_descs[i].units[unit].l4_num_alloc_units = int(self.Total_AU_Count/3)
                    config_descs[i].units[unit].b9_logical_block_size = api.LogicalBlockSize.SIZE_4KB
                    config_descs[i].units[unit].b10_provisioning_type = api.ProvisioningType.THIN_PROVISIONING_ERASE
                elif (i * 8 + unit) == 3:
                    config_descs[i].units[unit].b0_lu_enable = 1
                    config_descs[i].units[unit].b1_boot_lun_id = 0
                    config_descs[i].units[unit].b3_memory_type = api.MemoryType.ENHANCED_1
                    config_descs[i].units[unit].l4_num_alloc_units = int(self.Total_AU_Count/3)
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
    def get_health_report(self)->None:
        response, self.health_report = project_api.issue_40FE_to_read_enhanced_health_report() 
    def compare_data_show_log(self,variable1_name:str,variable1_val:int, variable2_name:str,variable2_val:int,increase_val:int, compare_method:str = "=")->None:
        if compare_method == "=":
            if(variable1_val != (variable2_val + increase_val)):
                logger.error_fp(f'{variable1_name}({variable1_val}) != {variable2_name}({variable2_val}) + {increase_val}')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL     
        if compare_method == ">":
            if(variable1_val <= (variable2_val + increase_val)):
                logger.error_fp(f'{variable1_name}({variable1_val}) <= {variable2_name}({variable2_val}) + {increase_val}')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL        

    def read_data_size_tlc_test(self):
        logger.info(f'read_data_size_tlc_cnt = {self.health_report.read_data_size_tlc_unit_100mb}')
        original_total_read_size = self.health_report.read_data_size_tlc_unit_100mb.value
        read_data_4k = BLOCK4K_SIZE_100M_BYTE
        self.read_data(0,0,read_data_4k,read_data_4k)
        self.get_health_report()
        current_total_read_size = self.health_report.read_data_size_tlc_unit_100mb.value
        self.compare_data_show_log("current_total_read_size",current_total_read_size,"original_total_write_size",original_total_read_size,1,">")              


    def test123(self):
        logger.info(f'read_data_size_tlc_cnt = {self.health_report.read_data_size_tlc_unit_100mb}')
        original_total_read_size = self.health_report.read_data_size_tlc_unit_100mb.value
        logger.info(f'read_data_size_tlc_unit_100mb = {self.health_report.read_data_size_tlc_unit_100mb.value}')
        logger.info(f'read_data_size_em1_unit_100mb = {self.health_report.read_data_size_for_em1_unit_100mb.value}')
        logger.info(f'write_data_size_tlc_unit_100mb = {self.health_report.write_data_size_tlc_unit_100mb.value}')
        logger.info(f'write_data_size_for_em1_unit_100mb = {self.health_report.write_data_size_for_em1_unit_100mb.value}')        
        read_data_4k = BLOCK4K_SIZE_100M_BYTE
        self.write_data(0,0,read_data_4k,read_data_4k)
        self.read_data(0,0,read_data_4k,read_data_4k)

        self.write_data(3,0,read_data_4k,read_data_4k)
        self.read_data(3,0,read_data_4k,read_data_4k)        
        
        self.get_health_report()
        current_total_read_size = self.health_report.read_data_size_tlc_unit_100mb.value
        logger.info(f'read_data_size_tlc_unit_100mb = {self.health_report.read_data_size_tlc_unit_100mb.value}')
        logger.info(f'read_data_size_em1_unit_100mb = {self.health_report.read_data_size_for_em1_unit_100mb.value}')
        logger.info(f'write_data_size_tlc_unit_100mb = {self.health_report.write_data_size_tlc_unit_100mb.value}')
        logger.info(f'write_data_size_for_em1_unit_100mb = {self.health_report.write_data_size_for_em1_unit_100mb.value}')

    def read_data_size_em1_test(self):
         logger.info(f'read_data_size_em1_cnt = {self.health_report.read_data_size_for_em1_unit_100mb}')


    def spare_block_count_test(self):
         logger.info(f'spare_block_cnt = {self.health_report.spare_block_count_including_the_initial_2_always_reserved_bad_blocks}')
    def step1(self) -> None:
        self.config_lun()
        logger.flow(1, 'get enhanced health report')
        self.get_health_report()
        # doing
        self.test123()
        flow_cnt = 2
        logger.flow(flow_cnt, 'do Initialization_count_success_test: init flow w ssu powerdown')
        self.spare_block_count_test()
        flow_cnt += 1
        logger.flow(flow_cnt, 'do Read data Size TLC')
        self.read_data_size_tlc_test()
        flow_cnt += 1
        logger.flow(flow_cnt, 'do Read data Size EM1')
        self.read_data_size_tlc_test()
        flow_cnt += 1
        # already done

        logger.flow(2, 'do Initialization_count_success_test: init flow w ssu powerdown')
        self.initialization_count_success_test()
        logger.flow(3, 'do Initialization_count_failure_test: : init flow wo ssu powerdown')
        self.initialization_count_failure_test()
        logger.flow(4, 'do write_size_test: write normal partition & em1')
        self.write_size_test()
        logger.flow(5, 'do sleep_cnt_test: ssu sleep')
        self.sleep_cnt_test()       
        logger.flow(6, 'do powerdown_cnt_test: ssu powerdown')
        self.powerdown_cnt_test()                
        logger.flow(7, 'do powerdown_cnt_test: ssu deepsleep')
        self.deepsleep_cnt_test()  
        pass
    def deepsleep_cnt_test(self)->None:
        original_deep_sleep_state_counter = self.health_report.deep_sleep_state_counter.value
        #         self.sleep_state_counter = self.add_field(0x100, 0x103, 'little')
        # self.deep_sleep_state_counter = self.add_field(0x104, 0x107, 'little')
        # self.power_down_state_counter = self.add_field(0x108, 0x10B, 'little')
        SSU = ExecuteCMD.StartStopUnit()
        SSU.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=4, no_flush=0,start=0)
        SSU.set_option(wait_queue_empty=True)
        ExecuteCMD.enqueue(SSU)
        ExecuteCMD.send()
        init_tester_to_unit_ready(resetmode = Dcmd5ResetType.HW_RESET, powerdown = False)
        self.get_health_report()
        current_deep_sleep_state_counter = self.health_report.deep_sleep_state_counter.value
        self.compare_data_show_log("current_deep_sleep_state_counter",current_deep_sleep_state_counter,"original_deep_sleep_state_counter",original_deep_sleep_state_counter,1)    
    def sleep_cnt_test(self)->None:
        original_sleep_state_counter = self.health_report.sleep_state_counter.value
        #         self.sleep_state_counter = self.add_field(0x100, 0x103, 'little')
        # self.deep_sleep_state_counter = self.add_field(0x104, 0x107, 'little')
        # self.power_down_state_counter = self.add_field(0x108, 0x10B, 'little')
        SSU = ExecuteCMD.StartStopUnit()
        SSU.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=2, no_flush=0,start=0)
        SSU.set_option(wait_queue_empty=True)
        ExecuteCMD.enqueue(SSU)
        ExecuteCMD.send()
        SSU.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=1, no_flush=0,start=0)
        ExecuteCMD.enqueue(SSU)
        ExecuteCMD.send()        
        self.get_health_report()
        current_sleep_state_counter = self.health_report.sleep_state_counter.value
        self.compare_data_show_log("current_sleep_state_counter",current_sleep_state_counter,"original_sleep_state_counter",original_sleep_state_counter,1)     
    def powerdown_cnt_test(self)->None:
        original_power_down_state_counter = self.health_report.power_down_state_counter.value
        #         self.sleep_state_counter = self.add_field(0x100, 0x103, 'little')
        # self.deep_sleep_state_counter = self.add_field(0x104, 0x107, 'little')
        # self.power_down_state_counter = self.add_field(0x108, 0x10B, 'little')
        SSU = ExecuteCMD.StartStopUnit()
        SSU.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=3, no_flush=0,start=0)
        SSU.set_option(wait_queue_empty=True)
        ExecuteCMD.enqueue(SSU)
        ExecuteCMD.send()
        SSU.assign(lun=api.WellKnownLUN.UFS_DEVICE, immed=0, power_condition=1, no_flush=0,start=0)
        ExecuteCMD.enqueue(SSU)
        ExecuteCMD.send()        
        self.get_health_report()
        current_power_down_state_counter = self.health_report.power_down_state_counter.value
        self.compare_data_show_log("current_power_down_state_counter",current_power_down_state_counter,"original_power_down_state_counter",original_power_down_state_counter,1)        
    def write_size_test(self)->None:
        original_total_write_size = self.health_report.total_write_size.value
        original_total_tlc_write_size = self.health_report.total_tlc_write_size.value
        write_data_4k = random.randint(1,128)
        self.write_data(0,0,write_data_4k,write_data_4k)
        self.get_health_report()
        current_total_write_size = self.health_report.total_write_size.value
        current_total_tlc_write_size = self.health_report.total_tlc_write_size.value
        self.compare_data_show_log("current_total_write_size",current_total_write_size,"original_total_write_size",original_total_write_size,write_data_4k,">")        
        self.compare_data_show_log("current_total_tlc_write_size",current_total_tlc_write_size,"original_total_tlc_write_size",original_total_tlc_write_size,write_data_4k,">")        
        original_total_write_size = current_total_write_size
        original_total_slc_write_size = self.health_report.total_slc_write_size.value
        write_data_4k = random.randint(1,128)
        self.write_data(3,0,write_data_4k,write_data_4k)        
        self.get_health_report()
        current_total_write_size = self.health_report.total_write_size.value
        current_total_slc_write_size = self.health_report.total_slc_write_size.value 
        self.compare_data_show_log("current_total_write_size",current_total_write_size,"original_total_write_size",original_total_write_size,write_data_4k,">")        
        self.compare_data_show_log("current_total_slc_write_size",current_total_slc_write_size,"original_total_slc_write_size",original_total_slc_write_size,write_data_4k,">")           

    def initialization_count_success_test(self)->None:
        original_init_success_cnt = self.health_report.initialization_count_success.value
        original_safe_shutdown_initialization_count = self.health_report.safe_shutdown_initialization_count.value
        original_init_count_pon = self.health_report.init_count_pon.value

        init_tester_to_unit_ready(resetmode = Dcmd5ResetType.HW_RESET, powerdown = True)
        self.get_health_report()
        current_init_success_cnt = self.health_report.initialization_count_success.value
        current_safe_shutdown_initialization_count = self.health_report.safe_shutdown_initialization_count.value
        current_init_count_pon = self.health_report.init_count_pon.value
        self.compare_data_show_log("current_init_success_cnt",current_init_success_cnt,"original_init_success_cnt",original_init_success_cnt,1)
        self.compare_data_show_log("current_safe_shutdown_initialization_count",current_safe_shutdown_initialization_count,"original_safe_shutdown_initialization_count",original_safe_shutdown_initialization_count,1)
        self.compare_data_show_log("current_init_count_pon",current_init_count_pon,"original_init_count_pon",original_init_count_pon,1)
        
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
    def read_data(self, lun:int, start_lba:int, total_size: int, chunk_size:int) -> None:

        chunk_size = 65535

        lba = start_lba

        total_len = total_size

        while(total_len):

            read10 = ExecuteCMD.Read10()

            chunk_size = min(int(chunk_size),int(total_len))
            ExecuteCMD.Read10().assign(lun = lun, lba=lba, length=chunk_size, fua=0).enqueue()

            total_len -= chunk_size    

            lba += chunk_size

        ExecuteCMD.send(clear_on_success=True)         

    def initialization_count_failure_test(self)->None:
        original_init_failure_cnt = self.health_report.initialization_count_failure.value
        original_init_count_spor = self.health_report.init_count_spor.value
        original_unsafe_shutdown_initialization_count = self.health_report.unsafe_shutdown_initialization_count.value
        # self.init_count_spor 
        # unsafe_shutdown_initialization_count
        self.write_data(0, 0, 128, 65535)
        init_tester_to_unit_ready(resetmode = Dcmd5ResetType.HW_RESET, powerdown = False)
        self.get_health_report()
        current_init_failure_cnt = self.health_report.initialization_count_failure.value
        current_init_count_spor = self.health_report.init_count_spor.value
        current_unsafe_shutdown_initialization_count = self.health_report.unsafe_shutdown_initialization_count.value
        self.compare_data_show_log("current_init_count_spor",current_init_count_spor,"original_init_count_spor",original_init_count_spor,1)
        self.compare_data_show_log("current_unsafe_shutdown_initialization_count",current_unsafe_shutdown_initialization_count,"original_unsafe_shutdown_initialization_count",original_unsafe_shutdown_initialization_count,1)
          
    def post_process(self) -> None:
        pass
    

run = Pattern().run
if __name__ == "__main__":
    run()