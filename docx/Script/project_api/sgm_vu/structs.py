import struct
from Script.api.struct_helper import *
from typing import List, Tuple, Dict

class D017_param(PacketParserComposerABC):
    def __init__(self, payload: bytearray = bytearray(20), start_offset:int = AUTO_OFFSET, end_offset:int = AUTO_OFFSET) -> None:
        super().__init__(payload = payload, start_offset = start_offset, end_offset = end_offset)
        self.die = self.add_field(0,0,'little')
        self.plane = self.add_field(1,1,'little')
        self.block = self.add_field(2,3,'little')
        self.error_inject_enable = self.add_field(4,4,'little')
        self.scan_type = self.add_field(5,5,'little')
        self.first_low_vt_scan = self.add_field(6,6,'little')
        self.touch_up = self.add_field(7,7,'little')
        self.low_vt_re_scan = self.add_field(8,8,'little')
        self.high_vt_scan = self.add_field(9,9,'little')
        self.switch = self.add_field(10,10,'little')
        self.index = self.add_field(11,11,'little')
        self.rev = self.add_field(12,19,'little')
class C071_param(PacketParserComposerABC):
    def __init__(self, payload: bytearray = bytearray(64), start_offset:int = AUTO_OFFSET, end_offset:int = AUTO_OFFSET) -> None:
        super().__init__(payload = payload, start_offset = start_offset, end_offset = end_offset)
        self.sgs_scan_dynamic_read_count = self.add_field(0,7,'little')
        self.sgs_scan_dynamic_event_cnt: list[BaseField] = []
        self.sgs_scan_static_event_cnt: list[BaseField] = []
        dynamic_offset = 8
        for i in range(6):
            self.sgs_scan_dynamic_event_cnt.append(self.add_field(dynamic_offset+ i*4,dynamic_offset+i*4+3,'little'))
        static_offset = 32
        for i in range(6):
            self.sgs_scan_static_event_cnt.append(self.add_field(static_offset+ i*4,static_offset+i*4+3,'little'))
        self.sgs_scan_static_read_count = self.add_field(56,63,'little')


class VU_4071_struct(PacketParserComposerABC):
    def __init__(self, payload: bytearray = bytearray(3240), start_offset:int = AUTO_OFFSET, end_offset:int = AUTO_OFFSET) -> None:
        super().__init__(payload = payload, start_offset = start_offset, end_offset = end_offset)
        self.curr_read_count_TLC = self.add_field(0,7,'little')
        self.remain_read_count_trigger_sgs_TLC = self.add_field(8,15,'little')
        self.sgs_read_count_threshold = self.add_field(16,23,'little')
        self.sgs_read_count_threshold_list:list[BaseField] = []
        rc_thres_offset = 24
        for i in range(4):
            self.sgs_read_count_threshold_list.append(self.add_field(rc_thres_offset+ i*8,rc_thres_offset+i*8+7,'little'))

        self.sgs_scan_window_list : list[BaseField] = []
        scan_window_offset = 56
        for i in range(5):
            self.sgs_scan_window_list.append(self.add_field(scan_window_offset+ i*4,scan_window_offset+i*4+3,'little'))
        self.sgs_scan_event_cnt_TLC:list[BaseField] = []
        event_tlc_offset = 76
        for i in range(6):
            self.sgs_scan_event_cnt_TLC.append(self.add_field(event_tlc_offset+ i*4,event_tlc_offset+i*4+3,'little'))

        self.sgs_scan_flagged_physical_vb_cnt = self.add_field(100,103,'little')
        self.sgs_scan_flagged_physical_vbNumb:list[BaseField] = []
        vbnumb_offset = 104
        for i in range(774):
            self.sgs_scan_flagged_physical_vbNumb.append(self.add_field(vbnumb_offset+ i*4,vbnumb_offset+i*4+3,'little'))
        
        self.remain_read_count_trigger_sgs_SLC = self.add_field(3200,3207,'little') 
        self.curr_read_count_SLC = self.add_field(3208,3215,'little') 
        self.sgs_scan_event_cnt_SLC:list[BaseField] = []
        event_slc_offset = 3216
        for i in range(6):
            self.sgs_scan_event_cnt_SLC.append(self.add_field(event_slc_offset+ i*4,event_slc_offset+i*4+3,'little'))



        

        
