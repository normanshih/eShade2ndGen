#!/usr/bin/env python3 -u

import json
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
import shutil
import sys
import cv2

'''
appRgb2rgbExe 模擬 RGB2RGB 程式， 
1. reads resized source image 
2. convert the color domain from deviceRGB to trueRGB (Adobe RGB)
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
        return self._read_from_disk().device_img_path

    @property
    def RGB2RGB_ColorData_path(self) -> str:
        return self._read_from_disk().RGB2RGB_ColorData_path

    @property
    def color_spectrum_filepath(self) -> str:
        return self._read_from_disk().SRs_sequential_patches_path


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
    configurer = JsonConfigurer(root / "execute_setup.json")

    image_filepath = configurer.source_image_filepath
    color_spectrum_filepath = configurer.color_spectrum_filepath
    print(f"color_spectrum_filepath: {color_spectrum_filepath}")
    rgb2rgbFolder_path = Path(configurer.RGB2RGB_ColorData_path)
    deviceRGB_Original_filepath = rgb2rgbFolder_path / "deviceRGB_Original.txt"
    truecolor_filename = "truecolor_" + Path(image_filepath).name
    truecolor_image_filepath = rgb2rgbFolder_path / "ImagesAfterConversion"  / truecolor_filename
    print(f"RGB2RGB truecolor_image_filepath: {truecolor_image_filepath}")
    try:
        image = cv2.imread(image_filepath)

        cv2.imshow(f"RGB2RGB: {Path(image_filepath).name}", image)
        cv2.waitKey(5000)
        cv2.destroyAllWindows()

        with open(deviceRGB_Original_filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"RGB2RGB reads deviceRGB_Original: {content}")
        # simulator convert truecolor image
        shutil.copy(image_filepath, truecolor_image_filepath)
    except Exception as e:
        print(f"Exception {e} in processing RGB2RGB")
        sys.exit(-1)







