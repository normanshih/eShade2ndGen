import json
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import shutil
import sys






class JsonConfigurer:
    """頂級架構：同時完美整合 With 機制與 Property/Setter 的實體配置器"""

    def __init__(self, config_filepath: str, base_path:str=""):
        base = Path(base_path)
        self.config_file_path = (base / config_filepath).resolve()
        print(f"config_file_path = {self.config_file_path}")

    def _read_from_disk(self) -> SimpleNamespace:
        """專職從硬碟搬運 JSON 並升級為點 . 存取盒子"""
        json_str = self.config_file_path.read_text(encoding="utf-8")
        return json.loads(json_str, object_hook=lambda d: SimpleNamespace(**d))

    def _write_to_disk(self, config_obj: SimpleNamespace):
        """專職將點 . 存取盒子變回 JSON 覆寫回硬碟"""
        dict_data = vars(config_obj)
        with open(self.config_file_path, "w", encoding="utf-8") as f:
            json.dump(dict_data, f, indent=4)

    @property
    def targetCCSG_Ref_WBPath(self)->str:
        return self._read_from_disk().targetCCSG_Ref_WBPath

    @targetCCSG_Ref_WBPath.setter
    def targetCCSG_Ref_WBPath(self, value: str):
        config = self._read_from_disk()
        config.targetCCSG_Ref_WBPath = str(value)
        self._write_to_disk(config)


    @property
    def targetCCSG_Ref_BBPath(self)->str:
        return self._read_from_disk().targetCCSG_Ref_BBPath

    @targetCCSG_Ref_BBPath.setter
    def targetCCSG_Ref_BBPath(self, value: str):
        config = self._read_from_disk()
        config.targetCCSG_Ref_BBPath = str(value)
        self._write_to_disk(config)


    @property
    def colorCheckerM014x10Path(self)->str:
        return self._read_from_disk().colorCheckerM014x10Path

    @colorCheckerM014x10Path.setter
    def colorCheckerM014x10Path(self, value: str):
        config = self._read_from_disk()
        config.colorCheckerM014x10Path = str(value)
        self._write_to_disk(config)


if __name__ == "__main__":
    print(f'UNWARP config.json setup Utility must installed in the same folder with unwarp.exe')
    root = Path(__file__)
    configurer = JsonConfigurer(root.parent / "config.json")

    reference_WB = "assets/target_CCSG_Reference_WB.tif"
    reference_BB = "assets/target_CCSG_Reference_BB.tif"
    spectrum = "assets/color_spectrum_eShade/ColorChecker_eShade_M0_Rearranged_14X10.txt"

    configurer.targetCCSG_Ref_WBPath = reference_WB
    configurer.targetCCSG_Ref_BBPath = reference_BB
    configurer.colorCheckerM014x10Path = spectrum

    print(f"targetCCSG_Ref_WBPath = {configurer.targetCCSG_Ref_WBPath}")
    print(f"targetCCSG_Ref_BBPath = {configurer.targetCCSG_Ref_BBPath}")
    print(f"colorCheckerM014x10Path = {configurer.colorCheckerM014x10Path}")