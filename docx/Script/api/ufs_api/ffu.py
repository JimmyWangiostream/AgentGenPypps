from enum import IntEnum
from pathlib import Path
from Script.api import shared
import os
from Script.api.exception import ENVIRONMENT_ASSERT_FFU_RESOURCE_FAIL
from Script.api.ufs_api.defines.enum_define import FFUBinType, FFUSvnType
from Script.api.ufs_api.vendor_cmd.functions import get_flash_setting
import Script.api.cmd_seq as ExecuteCMD

_log = shared.logger

ffu_path = Path(r'\\172.23.99.220\pps_card\FFU\UFS')
# ffu_path = r'D:\FFU_BIN'

FW_FFU_HEADER_SIZE = 4096
FW_MP_HEADER_SIZE = 4096
FW_B_CODE_HEADER_SIZE = 4096
FW_HW_PAGE_SIZE = 4096

BIN_Data_M1 = 0x1000
BIN_Data_M2 = 0x1001
BIN_Data_SVN = 0x1004
BIN_Data_FW_Vendor = 0x100C
BIN_Data_UFS_Version = 0x1019

FFU_BIN_Header_IC_Version = 0x02

def search_ffu_bin(ffu_bin_type:FFUBinType, ffu_bin_svn_type:FFUSvnType) -> bytearray:

    if ffu_bin_type == FFUBinType.HW_BIN:
        raise ENVIRONMENT_ASSERT_FFU_RESOURCE_FAIL
    flashsettingdata = get_flash_setting()
    ic_path = os.path.join(ffu_path, str(flashsettingdata.IC_Version))

    if ffu_bin_type == FFUBinType.FW_HW_BIN:
        hw_page_size = FW_HW_PAGE_SIZE * 4
    elif ffu_bin_type == FFUBinType.FW_BIN:
        hw_page_size = 0

    b_bin_offset = FW_FFU_HEADER_SIZE + hw_page_size + FW_MP_HEADER_SIZE + FW_B_CODE_HEADER_SIZE

    svn_offset = b_bin_offset + BIN_Data_SVN
    fw_vendor_offset = b_bin_offset + BIN_Data_FW_Vendor
    ufs_version_offset = b_bin_offset + BIN_Data_UFS_Version
    m1_offset = b_bin_offset + BIN_Data_M1
    m2_offset = b_bin_offset + BIN_Data_M2

    for root, dirs, files in os.walk(ic_path):
        dirs.sort(key = lambda d:os.path.getctime(os.path.join(root, d)), reverse=True)
        for bin_file in files:
            if ffu_bin_type.value in bin_file:
                if ffu_bin_type == FFUBinType.FW_BIN:
                    if FFUBinType.FW_HW_BIN.value in bin_file:
                        continue
                bin_file = os.path.join(root, bin_file)
                with open(bin_file, 'rb') as f:
                    bin_data = f.read()

                bin_svn = int.from_bytes(bin_data[svn_offset:svn_offset + 4], 'little')
                bin_ic_version = int.from_bytes(bin_data[FFU_BIN_Header_IC_Version:FFU_BIN_Header_IC_Version + 2], 'little')
                bin_fw_vendor = bin_data[fw_vendor_offset]
                ufs_version = bin_data[ufs_version_offset]
                bin_m1 = bin_data[m1_offset]
                bin_m2 = bin_data[m2_offset]
                if ffu_bin_svn_type == FFUSvnType.CURRENT_SVN_BIN:
                    if bin_svn == flashsettingdata.FW_SVN and bin_ic_version == flashsettingdata.IC_Version and bin_fw_vendor == flashsettingdata.FW_Vendor and ufs_version == flashsettingdata.FW_UFS_version_M3_128 and bin_m1 == flashsettingdata.M1 and bin_m2 == flashsettingdata.M2:
                        _log.info(f"current svn file match, file = {bin_file}")
                        _log.info(f"current svn file match, bin info {bin_svn=}, {bin_ic_version=}, {bin_fw_vendor=}, {ufs_version=}, {bin_m1=}, {bin_m2=}")
                        return bytearray(bin_data)
                elif ffu_bin_svn_type == FFUSvnType.OLD_SVN_BIN:
                    if bin_svn < flashsettingdata.FW_SVN and bin_ic_version == flashsettingdata.IC_Version and bin_fw_vendor == flashsettingdata.FW_Vendor and ufs_version == flashsettingdata.FW_UFS_version_M3_128 and bin_m1 == flashsettingdata.M1 and bin_m2 == flashsettingdata.M2:
                        _log.info(f"old svn file match, file = {bin_file}")
                        _log.info(f"old svn file match, bin info {bin_svn=}, {bin_ic_version=}, {bin_fw_vendor=}, {ufs_version=}, {bin_m1=}, {bin_m2=}")
                        return bytearray(bin_data)
                elif ffu_bin_svn_type == FFUSvnType.NEW_SVN_BIN:
                    if bin_svn > flashsettingdata.FW_SVN and bin_ic_version == flashsettingdata.IC_Version and bin_fw_vendor == flashsettingdata.FW_Vendor and ufs_version == flashsettingdata.FW_UFS_version_M3_128 and bin_m1 == flashsettingdata.M1 and bin_m2 == flashsettingdata.M2:
                        _log.info(f"new svn file match, file = {bin_file}")
                        _log.info(f"new svn file match, bin info {bin_svn=}, {bin_ic_version=}, {bin_fw_vendor=}, {ufs_version=}, {bin_m1=}, {bin_m2=}")
                        return bytearray(bin_data)
                _log.info(f"not match file = {bin_file}")        
                _log.info(f"not match bin info {bin_svn=}, {bin_ic_version=}, {bin_fw_vendor=}, {ufs_version=}, {bin_m1=}, {bin_m2=}")
                _log.info(f"expect bin info bin_ic_version = {flashsettingdata.IC_Version}, bin_fw_vendor = {flashsettingdata.FW_Vendor}, ufs_version = {flashsettingdata.FW_UFS_version_M3_128}, bin_m1 = {flashsettingdata.M1}, bin_m2 = {flashsettingdata.M2}")         
    raise ENVIRONMENT_ASSERT_FFU_RESOURCE_FAIL

def send_ffu_write_buffer(chunksize:int, bin_offset:int, bin_buff:bytearray) -> None:
    write_buffer = ExecuteCMD.WriteBuffer()
    write_buffer.assign(lun=0, mode=0x0E, buffer_id=0, buffer_offset=bin_offset, length=chunksize, vendor=False)
    write_buffer.data = bin_buff[bin_offset:]
    ExecuteCMD.enqueue(write_buffer)
    ExecuteCMD.send()    
