import package_root
from Script import api
from Script.api import dumpfile, cmd_seq as ExecuteCMD
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger
from Script import project_api
import random
from Script.api.exception import *
from Script.api.ufs_api.defines.constant_define import *
from Script.pattern.read_disturb.mutual_fun import *
from Script.project_api.functions import print_object_info_ai

class Pattern(UFSTC):
    def pre_process(self) -> None:
        leave_inhibition_mode()
        self.fw_geometry = api.get_fw_geometry()
        self.write_record = api.get_empty_write_record()
        _, self.debug_info = api.get_debug_info()
        self.slc_vb_size = (self.fw_geometry.l84_vb_size_u0 * 512 // 4096)
        self.tlc_vb_size = (self.fw_geometry.l88_vb_size_u1 * 512 // 4096)
        self.TestNormalLun = 0
        self.TestEM1Lun = 1
        self.TestWBLun = 2
        config_lun(normal_list=[self.TestNormalLun, self.TestWBLun], em1_list=[self.TestEM1Lun])
        self.startLBA: Dict[int, int] = {self.TestNormalLun: 0, self.TestEM1Lun:0}
        _, self.mConfig_in_vu = project_api.get_mConfig_data()
        pass

    def step1(self) -> None:
        logger.flow(1, f"write data to create TLC/SLC block")
        total_size = int(self.tlc_vb_size*4.5)
        lun = self.TestNormalLun
        api.sequential_write(lun=lun, start_lba=self.startLBA[lun], total_size=total_size, chunk_size=api.BLOCK4K_SIZE_128M_BYTE, fua = 0,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=self.write_record)
        self.startLBA[lun] += total_size
        total_size = int(self.slc_vb_size*4.5)
        lun = self.TestEM1Lun
        api.sequential_write(lun=lun, start_lba=self.startLBA[lun], total_size=total_size, chunk_size=api.BLOCK4K_SIZE_128M_BYTE, fua = 0,
                        need_compare=False, compare_method=api.CompareMethod.HW_COMPARE, write_record=self.write_record)
        self.startLBA[lun] += total_size
        pass
    
    def step2(self) -> None:
        logger.flow(2, f"issue VU C088 to stop refresh")
        project_api.issue_C088_to_start_or_stop_refresh(bParameter0=project_api.VUC088Paremeter.StopRefreshRefreshCanStillBeEnqueue)
        pass
                
    def step3(self) -> None:
        logger.flow(3, f"set some RC of VB = 0xFFFFFFFF (MAX_VALUE)")
        read_cnt_of_vb_before = project_api.get_all_VB_read_count()
        self.sorted_VB_list_dict_before = get_sorted_VB_list()
        self.refresh_vbs = []
        data_payload = bytearray(4096)
        self.set_vb_list = []
        
        for type, vb_list in self.sorted_VB_list_dict_before.items():
            if type in [project_api.VBListNum.CURRENT_L2_TLC, 
                        project_api.VBListNum.CURRENT_L2_EM1, 
                        project_api.VBListNum.USED_BLK_POOL_TLC, 
                        project_api.VBListNum.USED_BLK_POOL_EM1]:
                self.set_vb_list += vb_list
        for vb in range(self.fw_geometry.l52_total_vb_count):
            if vb in self.set_vb_list:
                set_value = 0xFFFFFFFF-1
                logger.info(f"Set RC of VB{vb} = {set_value}")
                data_payload[vb*4:(vb+1)*4] = (set_value).to_bytes(4, 'little')
                self.refresh_vbs.append(vb)
            else:
                data_payload[vb*4:(vb+1)*4] = read_cnt_of_vb_before[vb].to_bytes(4, 'little')
        project_api.set_all_VB_read_count(data_payload=data_payload)
        pass
    
    def step4(self) -> None:
        logger.flow(4, f"Reading data leads to an increase in RC.")
        api.read_compare(write_record = self.write_record)
        pass
    
    def step5(self) -> None:
        logger.flow(5, f"issue VU 40C5 to check the refresh booking queue")
        _, booking_q = project_api.issue_40C5_to_get_booking_queue()
        if booking_q.LogicalVBNumberInBookingQueue.value == 0:
            logger.error_lb(f'check LogicalVBNumberInBookingQueue after RC[VB] reaches max value 0xFFFFFFFF')
            logger.error_fp(f'expect LogicalVBNumberInBookingQueue is not 0, but current value = {booking_q.LogicalVBNumberInBookingQueue.value}, result Fail!')
            raise SIGHTING_FAIL_DATA_COMPARE_FAIL
        for idx, VBs in enumerate(booking_q.BookingQueueVB):
            vb = VBs.LogicalVBNumber.value
            Priority_bit = project_api.BookingUser(VBs.TheBookingUser.value & 0x700)
            if Priority_bit == project_api.BookingUser.BOOKING_IN_HP:
                Priority = project_api.VUC087Paremeter.HighPriority
            elif Priority_bit == project_api.BookingUser.BOOKING_IN_MP:
                Priority = project_api.VUC087Paremeter.MediumPriority
            else:
                Priority = project_api.VUC087Paremeter.LowPriority
            TheBookingUser = project_api.BookingUser(VBs.TheBookingUser.value & project_api.BookingUser.MAX_BOOKING_USER_COUNT-1)
            logger.info(f'BookingQ[{idx}]: VB {vb}, TheBookingUser: {TheBookingUser.name} ({Priority.name})')
            expect_user = project_api.BookingUser.RD_SCAN_BOOKING_0
            expect_priority = project_api.VUC087Paremeter.HighPriority
            if vb not in self.refresh_vbs:
                logger.error_lb(f'check vb {vb} after Booking')
                logger.error_fp(f'VB {vb} is {Priority_bit.name},  but not in expect list {self.refresh_vbs}, result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            if expect_user != TheBookingUser or expect_priority != Priority:
                logger.error_lb(f'check vb {vb} after Booking')
                logger.error_fp(f'expect VB {vb} is {expect_user.name} ({expect_priority.name}),  but current is {TheBookingUser.name} ({Priority.name}), result Fail!')
                raise SIGHTING_FAIL_DATA_COMPARE_FAIL
            pass
        
    def step6(self) -> None:
        logger.flow(6, f"issue VU C088 to start refresh and polling bkops idle")
        project_api.issue_C088_to_start_or_stop_refresh(bParameter0=project_api.VUC088Paremeter.StartRefresh)
        polling_bkops_idle()
        pass

    def post_process(self) -> None:
        pass
    
    

run = Pattern().run
if __name__ == "__main__":
    run()