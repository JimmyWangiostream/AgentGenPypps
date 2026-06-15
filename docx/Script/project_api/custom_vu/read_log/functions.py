import inspect
from Script.api import shared
import random
from Script.project_api.custom_vu.read_log.structs import *
from Script.project_api.functions import send_data_in_vcmd
from Script.api.cmd_seq.response import CommandResponse

_log = shared.logger


def issue_4080_read_log_from_nand(para_0:int, para_1:int, para_2:int, para_4:int, transfer_length:int = 0x4000, keep_error:bool = False) -> tuple[CommandResponse, bytearray]:
    _log.info(f"{inspect.currentframe().f_code.co_name}()")  # type: ignore
    vu = micron_vu_4080()
    vu.b0_opcode.value = 0x80
    vu.b1_func.value = 0x40
    vu.w2_transfer_length.value = transfer_length
    vu.d4_random_stamp.value = random.randint(0x1, 0xFFFFFFFF)

    vu.para_0.value = para_0
    vu.para_1.value = para_1
    vu.para_2.value = para_2
    vu.para_4.value = para_4

    return send_data_in_vcmd(micron_vendor_cmd=vu, keep_error=keep_error)
