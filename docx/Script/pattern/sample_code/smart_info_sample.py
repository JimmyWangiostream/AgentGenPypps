import package_root
from Script import api
from Script.pattern.pattern_template import UFSTC
from Script.pattern.pattern_logger import logger

from Script.api import ExecuteCMD


class Pattern(UFSTC):

    def pre_process(self) -> None:
        pass

    def step1(self) -> None:
        smart_info = api.SmartInfo()
        smart_info.update_smart_info()
        logger.info("Sample 1")
        fw_ver = smart_info.get_value(api.SmartInfoField.FW_VERSION)
        fw_svn = smart_info.get_value(api.SmartInfoField.FW_SVN)
        total_d1_program_cnt = smart_info.get_value(api.SmartInfoField.TOTAL_D1_PROGRAM_COUNT)
        logger.info(f"  {fw_ver=}, {fw_svn=}, {total_d1_program_cnt=}")
        logger.info(f"  {smart_info.data=}")
        logger.info("Sample 2")
        for e in api.SmartInfoField:
            v = smart_info.get_value(e)
            logger.info(f"  {e.name} = {v}")

    def post_process(self) -> None:
        pass


run = Pattern().run
if __name__ == "__main__":
    run()
