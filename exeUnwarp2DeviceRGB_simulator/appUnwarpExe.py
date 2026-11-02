#!/usr/bin/env python3 -u

import json
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import shutil
import sys
import cv2
from  datetime import datetime

'''
appUnwarpExe 模擬 UNWARP2RGB 程式， 
1. reads TTC image and 
2. grapes RGB values of color patches to update deviceRGB_Original.txt
'''

class JsonConfigurer:
    """頂級架構：同時完美整合 With 機制與 Property/Setter 的實體配置器"""

    def __init__(self, config_filepath: str, base_path:str=""):
        base = Path(base_path)
        self.config_file_path = (base / config_filepath).resolve()

    # ==========================================
    # 🛠️ 核心底層工具（私有方法，不對外暴露）
    # ==========================================
    @property
    def source_image_filepath(self) -> str:
        return self._read_from_disk().srcPathOriginal

    @property
    def output_filepath(self)->str:
        return self._read_from_disk().outputPath

    @property
    def outputAdobePath_filepath(self)->str:
        return self._read_from_disk().outputAdobePath

    @property
    def srcDeformedResizedOutputPath_filepath(self)->str:
        return self._read_from_disk().srcDeformedResizedOutputPath

    @property
    def resizedUnwarpedWithRectPath_filepath(self)->str:
        return self._read_from_disk().resizedUnwarpedWithRectPath

    @property
    def deviceRGB_filepath(self)->str:
        return self._read_from_disk().outputDeviceRGBOriginalPath



    def _read_from_disk(self) -> SimpleNamespace:
        """專職從硬碟搬運 JSON 並升級為點 . 存取盒子"""
        json_str = self.config_file_path.read_text(encoding="utf-8")
        return json.loads(json_str, object_hook=lambda d: SimpleNamespace(**d))

    def _write_to_disk(self, config_obj: SimpleNamespace):
        """專職將點 . 存取盒子變回 JSON 覆寫回硬碟"""
        dict_data = vars(config_obj)
        with open(self.config_file_path, "w", encoding="utf-8") as f:
            json.dump(dict_data, f, indent=4)

    # ==========================================
    # 絕學二：📦 With 脈絡管理器 (多發連擊)
    # ==========================================
    @contextmanager
    def open_config(self):
        """當需要一口氣修改大量欄位時使用"""
        config = self._read_from_disk()  # 1. 只讀一次
        yield config  # 2. 交給你盡情修改
        self._write_to_disk(config)  # 3. 結束時只寫一次


if __name__ == "__main__":
    # 綁定實體應用程式目錄
    print(f"{Path(__file__)} Running ...")
    root = Path(__file__).parent
    configurer = JsonConfigurer(root / "config.json")

    tcc_filepath = configurer.source_image_filepath
    deviceRGB_filepath = configurer.deviceRGB_filepath

    try:
        ### read TCC image from srcPathOriginal
        tcc_image = cv2.imread(tcc_filepath)
        cv2.imshow(f"UNWARP: {Path(tcc_filepath).name}", tcc_image)
        cv2.waitKey(5000)
        cv2.destroyAllWindows()

        ### simulate generating deviceRGB_Original.txt
        with open("deviceRGB_template.txt", "r", encoding='utf-8') as f:
            data = f.read()

        new_data = data + f" on {datetime.now()}"

        with open(deviceRGB_filepath, 'w', encoding='utf-8') as f:
            f.write(new_data)
        #shutil.copy("deviceRGB_template.txt", deviceRGB_filepath)
        print(f"Unwarp and get deviceRGB values Successfully")

        ###
        print(f"srcPathOriginal                : {configurer.source_image_filepath}")
        print(f"outputDeviceRGBOriginalPath    : {configurer.deviceRGB_filepath}")
        print(f"srcDeformedResizedOutputPath   : {configurer.srcDeformedResizedOutputPath_filepath}")
        print(f"resizedUnwarpedWithRectPath    : {configurer.resizedUnwarpedWithRectPath_filepath}")
        print(f"outputAdobePath                : {configurer.outputAdobePath_filepath}")
        print(f"outputPath                     : {configurer.output_filepath}")

    except Exception as e:
        print(f"Exception {e} in processing UNWARP")
        sys.exit(-1)








