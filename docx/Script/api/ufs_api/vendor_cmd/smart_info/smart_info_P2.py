from ctypes import LittleEndianStructure, c_uint8
import Script.api.shared as shared
from Script.api.ufs_api.vendor_cmd.smart_info.field_defines import SmartInfoField as Field

_log = shared.logger


class SmartInfoStruct(LittleEndianStructure):

    _fields_ = [
        (Field.TOTAL_D1_PROGRAM_COUNT.name,                     c_uint8 * 8),
        (Field.SLC_L2_VB_COUNT.name,                            c_uint8 * 4),
        (Field.TLC_L2_VB_COUNT.name,                            c_uint8 * 4),
        (Field.RPMB_BLOCK_COUNT.name,                           c_uint8 * 4),
        (Field.SLC_PARTITION_SLC_L2_DATA.name,                  c_uint8 * 8),
        (Field.SLC_PARTITION_SLC_L2_PARITY.name,                c_uint8 * 8),
        (Field.SLC_PARTITION_SLC_L2_DUMMY.name,                 c_uint8 * 8),
        (Field.TLC_PARTITION_SLC_L1_DATA.name,                  c_uint8 * 8),
        (Field.TLC_PARTITION_SLC_L1_PARITY.name,                c_uint8 * 8),
        (Field.TLC_PARTITION_SLC_L1_DUMMY.name,                 c_uint8 * 8),
        (Field.TLC_PARTITION_TLC_L2_DATA.name,                  c_uint8 * 8),
        (Field.TLC_PARTITION_TLC_L2_PARITY.name,                c_uint8 * 8),
        (Field.TLC_PARTITION_TLC_L2_DUMMY.name,                 c_uint8 * 8),
        (Field.TLC_ERASE_COUNT.name,                            c_uint8 * 4),
        (Field.SLC_ERASE_COUNT.name,                            c_uint8 * 4),
        (Field.TABLE_ERASE_COUNT.name,                          c_uint8 * 4),
        (Field.SSU_ACTIVE_COUNT.name,                           c_uint8 * 4),
        (Field.SSU_SLEEP_COUNT.name,                            c_uint8 * 4),
        (Field.SSU_POWER_DOWN_COUNT.name,                       c_uint8 * 4),
        (Field.SSU_DEEP_SLEEP_COUNT.name,                       c_uint8 * 4),
        (Field.BBT_LAST_SLC_POOL_VB.name,                       c_uint8 * 2),
        (Field.FW_VERSION.name,                                 c_uint8 * 2),
        (Field.FW_SVN.name,                                     c_uint8 * 4),
        (Field.DATA_GC_TRIGGER_COUNT.name,                      c_uint8 * 4),
        (Field.FORCE_SLC_GC_TRIGGER_COUNT.name,                 c_uint8 * 4),
        (Field.FORCE_TLC_GC_TRIGGER_COUNT.name,                 c_uint8 * 4),
        (Field.WL_SLC_GC_TRIGGER_COUNT.name,                    c_uint8 * 4),
        (Field.WL_TLC_GC_TRIGGER_COUNT.name,                    c_uint8 * 4),
        (Field.RD_SLC_GC_TRIGGER_COUNT.name,                    c_uint8 * 4),
        (Field.RD_TLC_GC_TRIGGER_COUNT.name,                    c_uint8 * 4),
        (Field.PURGE_SLC_GC_TRIGGER_COUNT.name,                 c_uint8 * 4),
        (Field.PURGE_TLC_GC_TRIGGER_COUNT.name,                 c_uint8 * 4),
        (Field.REFRESH_ENABLE_COUNT.name,                       c_uint8 * 4),
        (Field.FAST_RELEASE_VC_ZERO_SOURCE_COUNT.name,          c_uint8 * 4),
        (Field.GC_RESELECT_SOURCE_TRIGGER_COUNT.name,           c_uint8 * 4),
        (Field.TOTAL_D3_PROGRAM_COUNT.name,                     c_uint8 * 8),
        (Field.GC_READ_BACK_VERIFY_PASS.name,                   c_uint8 * 2),
        (Field.GC_READ_BACK_VERIFY_FAIL.name,                   c_uint8 * 2),
        (Field.BBT_LAST_TABLE_AREA_VB.name,                     c_uint8 * 2),
        (Field.TOTAL_READ_BACK_ENCODE_COUNT.name,               c_uint8 * 4),
        (Field.TOTAL_LAST_PLANE_VERIFY_COUNT.name,              c_uint8 * 4),
    ]
