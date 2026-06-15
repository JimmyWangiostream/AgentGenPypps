import inspect
from typing import cast, List

from Script.api import shared, util, cmd_seq as ExecuteCMD

import random
from Script.project_api.structs import micron_vendor_cmd
from Script.project_api.functions import send_data_in_vcmd, send_data_out_vcmd, send_no_data_vcmd
from Script.api.cmd_seq.response import CommandResponse


_log = shared.logger

def issue_406D_get_VB_list_info() -> CommandResponse:
    _log.info(f"{inspect.currentframe().f_code.co_name}()")  # type: ignore
    vu = micron_vendor_cmd()
    vu.b0_opcode.value = 0x6D
    vu.b1_func.value = 0x40
    vu.w2_transfer_length.value = 0x1000
    response, buf = send_data_in_vcmd(micron_vendor_cmd=vu)
    return response
