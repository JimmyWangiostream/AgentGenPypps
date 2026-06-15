from importlib import import_module
from ctypes import LittleEndianStructure
from Script.api import shared
from Script.api.ufs_api.vendor_cmd.functions import get_smart_info_data
from Script.api.util.dut import Dut
from Script.api.ufs_api.vendor_cmd.smart_info.field_defines import SmartInfoField as Field
from Script.api.exception import PATTERN_ASSERT_MODULE_NOT_FOUND, PATTERN_ASSERT_ATTR_NOT_FOUND

_log = shared.logger
_mod_dir = 'Script.api.ufs_api.vendor_cmd.smart_info'


class SmartInfo:
    def __init__(self) -> None:
        self.data = bytearray()
        self.structure: LittleEndianStructure | None = None

    def update_smart_info(self) -> None:
        self.data = get_smart_info_data()
        dut = Dut.get_instance()
        mod_name = 'smart_info_' + dut.project_sn
        if dut.project_sn == "undefined":
            mod_name = 'smart_info_' + dut.name
        mod_path = _mod_dir + '.' + mod_name
        try:
            smart_info_struct = import_module(mod_path).SmartInfoStruct
            self.structure = smart_info_struct.from_buffer_copy(self.data)
        except ModuleNotFoundError:
            _log.error(f"Module not found: {mod_path}")
            raise PATTERN_ASSERT_MODULE_NOT_FOUND
        except AttributeError:
            _log.error(f"Attribute not found: SmartInfoStruct")
            raise PATTERN_ASSERT_ATTR_NOT_FOUND

    def get_value(self, field: Field) -> int:
        val = object.__getattribute__(self.structure, field.name)
        # FW support 4-byte endian ordering only
        if len(val) > 4:
            l = []
            for i in range(len(val) // 4):
                v = int.from_bytes(bytes(val[i*4:i*4+4]), byteorder='little')
                l.append(v)
            val = 0
            # Left-shift ordered values
            for i, v in enumerate(l[::-1]):
                val += (v << i * 4)
        else:
            val = int.from_bytes(bytes(val), byteorder='little')
        return val
