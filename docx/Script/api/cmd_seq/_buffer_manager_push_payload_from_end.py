import math
from typing import Final, Tuple

from Script.api.exception import PATTERN_ASSERT_BUFFER_MANAGER_FAIL_BUF_IS_FULL, PATTERN_ASSERT_BUFFER_MANAGER_FAIL_BUF_SIZE_NOT_ALIGN_512, PATTERN_ASSERT_BUFFER_MANAGER_FAIL_ENTRY_SIZE_NOT_ALIGN_72, PATTERN_ASSERT_BUFFER_MANAGER_FAIL_PAYLOAD_SIZE_EXCEEDS_EXPECTATION

ENTRY_SIZE: Final = 72
ALIGN_SIZE_512: Final = 512
ALIGN_SIZE_8K: Final = 8192
BUF_SIZE = 62 * 1024 * 1024
ENTRY_PADDING_SIZE: Final = ALIGN_SIZE_8K % ENTRY_SIZE
GROUP_ENTRY_AMT = ALIGN_SIZE_8K // ENTRY_SIZE
TOTAL_8K_CNT = BUF_SIZE // ALIGN_SIZE_8K
_buffer: bytearray
_entry_ptr: int
_data_ptr: int
_ehs_ptr: int
_entry_safe_zone: int
_data_safe_zone: int

def align_up(value: int, alignment: int) -> int:
    return math.ceil(value / alignment) * alignment

def align_down(value: int, alignment: int) -> int:
    return value // alignment * alignment

def reset_module() -> None:
    global _buffer, _entry_ptr, _data_ptr, _ehs_ptr, _entry_safe_zone, _data_safe_zone
    if BUF_SIZE % ALIGN_SIZE_512 != 0:
        raise PATTERN_ASSERT_BUFFER_MANAGER_FAIL_BUF_SIZE_NOT_ALIGN_512
    _buffer = bytearray([0xFF] * BUF_SIZE)
    _entry_ptr = 0
    _data_ptr = BUF_SIZE - 1
    _ehs_ptr = 0
    _entry_safe_zone = ALIGN_SIZE_8K
    _data_safe_zone = BUF_SIZE - ALIGN_SIZE_8K

def push_cmd(entry: bytearray, payload: bytearray, ehs: bytearray, align_8K: bool) -> Tuple[int, int]:
    data_len = int.from_bytes(entry[46:50]) # Data Length in CMD UPIU Parameter
    if _has_room_for_cmd(data_len, len(ehs)) == False:
        raise PATTERN_ASSERT_BUFFER_MANAGER_FAIL_BUF_IS_FULL # shall not catch, fatal error
    data_start_ptr = _push_payload(data_len, payload, align_8K)
    ehs_start_ptr = _push_ehs(ehs)
    if data_len != 0:
        entry[42:46] = data_start_ptr.to_bytes(4) # Data Address Offset
    if len(ehs) != 0:
        entry[54:58] = ehs_start_ptr.to_bytes(4) # EHS Data Address Offset

    _push_entry(entry)
    return data_start_ptr, ehs_start_ptr

def _has_room_for_cmd(payload_len: int, ehs_len: int) -> bool:
    # _ENTRY_SIZE *2 is to save space for ending cmd
    next_entry_safe_zone = align_up(_entry_ptr + (ENTRY_SIZE * 2), ALIGN_SIZE_8K)
    next_data_safe_zone = align_down(_data_ptr - payload_len, ALIGN_SIZE_8K)
    if next_entry_safe_zone > next_data_safe_zone:
        return False
    
    #todo: if ehs buffer is full:
    #    return False
    return True

def _push_payload(data_len: int, payload: bytearray, align_8K: bool) -> int:
    global _data_ptr, _data_safe_zone
    if len(payload) > data_len:
        raise PATTERN_ASSERT_BUFFER_MANAGER_FAIL_PAYLOAD_SIZE_EXCEEDS_EXPECTATION
    align_len = align_up(data_len, ALIGN_SIZE_512)
    _data_ptr -= align_len
    _data_safe_zone = align_down(_data_ptr, ALIGN_SIZE_8K)

    if align_8K:
        start_ptr = _data_safe_zone
    else:
        start_ptr = _data_ptr + 1
    _buffer[start_ptr: start_ptr + len(payload)] = payload
    
    return start_ptr

def _push_entry(entry: bytearray) -> None:
    global _entry_ptr, _entry_safe_zone
    if len(entry) != ENTRY_SIZE:
        raise PATTERN_ASSERT_BUFFER_MANAGER_FAIL_ENTRY_SIZE_NOT_ALIGN_72
    _buffer[_entry_ptr: _entry_ptr + ENTRY_SIZE] = entry
    # _ENTRY_SIZE *2 is to check if next entry will cross 8K
    if (_entry_ptr + (ENTRY_SIZE * 2)) % ALIGN_SIZE_8K < ENTRY_SIZE:
        _entry_ptr += (ENTRY_SIZE + ENTRY_PADDING_SIZE)
    else:
        _entry_ptr += ENTRY_SIZE

    _entry_safe_zone = align_up(_entry_ptr, ALIGN_SIZE_8K)

def _push_ehs(ehs: bytearray) -> int:
    #todo
    ehs_data_address_offset = 0
    return ehs_data_address_offset

def get_entry(index: int) -> bytearray:
    # From Response info buffer
    group_idx, entry_idx = divmod(index, GROUP_ENTRY_AMT)
    group_offset = (ENTRY_SIZE * GROUP_ENTRY_AMT + ENTRY_PADDING_SIZE) * group_idx
    entry_bytes = _buffer[group_offset + entry_idx : group_offset + entry_idx + ENTRY_SIZE]
    return entry_bytes

def get_payload(offset: int, length: int) -> bytearray:
    payload = _buffer[offset : offset+length]
    return payload


reset_module()