#!/usr/bin/env python3 -u
import sys, os
import shutil
from utils.jsonConfig_model import JsonConfigurer
from utils.myAppBootstrap import MainProgramFacilities
from job.exeProgramExecuterBaseClass import BaseExeProgramExecutorAgent
from job.workspaceSandbox import RGB2RGBWorkspaceSandbox
from imageProcessig.raw_isp import RawImagePipeline
from pathlib import  Path
"""
read config file to get input src file and output destination folder
image process 
"""


class Unwarp_Configurer(JsonConfigurer):
    """RGB2RGB.exe configuration interface"""
    # ==========================================
    # 絕學一：⚡ Property & Setter (單發快擊)
    # - srcPathOriginal             : image input
    # - outputPath                  : unwarped image output
    # - outputDeviceRGBOriginalPath : device RGB value table
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


    @source_image_filepath.setter
    def source_image_filepath(self, value: str):
        config = self._read_from_disk()
        config.srcPathOriginal = str(value)
        self._write_to_disk(config)

    @output_filepath.setter
    def output_filepath(self, value: str):
        config = self._read_from_disk()
        config.outputPath = str(value)
        self._write_to_disk(config)

    @outputAdobePath_filepath.setter
    def outputAdobePath_filepath(self, value: str):
        config = self._read_from_disk()
        config.outputAdobePath = str(value)
        self._write_to_disk(config)


    @srcDeformedResizedOutputPath_filepath.setter
    def srcDeformedResizedOutputPath_filepath(self, value: str):
        config = self._read_from_disk()
        config.srcDeformedResizedOutputPath = str(value)
        self._write_to_disk(config)

    @resizedUnwarpedWithRectPath_filepath.setter
    def resizedUnwarpedWithRectPath_filepath(self, value: str):
        config = self._read_from_disk()
        config.resizedUnwarpedWithRectPath = str(value)
        self._write_to_disk(config)

    @deviceRGB_filepath.setter
    def deviceRGB_filepath(self, value: str):
        config = self._read_from_disk()
        config.outputDeviceRGBOriginalPath = str(value)
        self._write_to_disk(config)



class ExeUnwarpProgramExecuterAgent(BaseExeProgramExecutorAgent):
    """ 專職處理前置資料與狂暴模式設定的代理人"""
    def set_configurations(self,config:Unwarp_Configurer, ws_RGB2RGB:RGB2RGBWorkspaceSandbox):
        ''' unwarp config.json setup '''
        config.deviceRGB_filepath = ws_RGB2RGB.deviceRGB_Oriinal_filepath
        config.output_filepath = Path(ws_RGB2RGB.image4unwarp_folderPath) / "output.tif"
        config.outputAdobePath_filepath = Path(ws_RGB2RGB.images4Characterization) / "adobe.tif"
        config.srcDeformedResizedOutputPath_filepath = Path(ws_RGB2RGB.images4Characterization) / "src_deformed_resized.tif"
        config.resizedUnwarpedWithRectPath_filepath = Path(ws_RGB2RGB.images4Characterization) / "resized_unwarpped_withRectangle.tif"

    def post_process(self, execute_result) -> bool:
        self.logger.debug(" [後處理] 正在驗證擷取 TCC deviceRGB 的核心成果...")
        # 1. 鋼鐵盲檢：檢查回傳 code 是否為 0
        if execute_result.returncode != 0:
            self.logger.error("【NG】UNWARP TCC deviceRGB 失敗！")
        else:
            self.logger.info("【OK】UNWARP TCC deviceRGB 完成")

        # 2. 提取 config 或收割成果檔案
        self.logger.info(f"UNWARP Print:\n{execute_result.stdout}")
        self.logger.info("=====================================================================")
        self.logger.info(f"UNWARP Error:\n: {execute_result.stderr}")
        self.logger.info("=====================================================================\n")

        return (execute_result.returncode == 0)





#---------------------------------------------------------------------------------------------------
class MyEnterpriseApp(MainProgramFacilities):
    def setup_options(self):
        """
        明確、在線（In-line）宣告這支程式要用的 Options，非常易讀！
        self.add_option("-p", "--port", type=int, default=8080, help="服務連接埠")
        """
        self.add_option("-c", "--config", type=str, default="exeSimulator_setup.json", help="設定檔路徑")

    def _init_configure(self, config_filepath):
        config_file = os.path.join(os.getcwd(), config_filepath)
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"❌ 找不到關鍵設定檔 {config_filepath}！")
        self.config = Simulator_Configurer(config_filepath)

    def main(self, args):
        """核心業務邏輯。廠務已經把 args 準備好了，直接享用"""
        self.logger.info(f"🚀 程式 {__file__} 已啟動")

        # 透過 args.xxx 直接存取，完全沒有 local/global 的困擾
        self.logger.info(f"[-] 正在載入設定: {args.config} to self.config")
        if args.verbose:
            self.logger.debug("🔍 [DEBUG] 詳細除錯模式已開啟")

        self.logger.info(f'srcPathOriginal = {self.config.source_image_filepath}')
        self.logger.info(f'outputPath = {self.config.RGB2RGB_ColorData_path}')

        isp = RawImagePipeline()
        try:
            image_buffer = isp.load_image(self.config.source_image_filepath)
            to_filepath = Path(self.config.RGB2RGB_ColorData_path).with_suffix(".tif")
            self.logger.info(f"to_filepath =  {to_filepath}")
            isp.save(to_filepath)
            self.config.RGB2RGB_ColorData_path = to_filepath
            self.logger.info(f"Succefully convert RAW to TIF image to {to_filepath}")
        except Exception as e:
            self.logger.error(f"raw image conversion error {e}")
            # move from input_filepath to output_filepath
            shutil.copy(self.config.source_image_filepath, self.config.RGB2RGB_ColorData_path)



#-------------------------------------------------------------------
if __name__ == "__main__":
    # 執行檔全域進入點
    print(f"🚀 [Mock EXE] 模擬執行檔已啟動... argv={sys.argv}")
    app = MyEnterpriseApp(description="我的 EXE 模擬器")
    try:
        app.run()
    except KeyboardInterrupt:
        # 在這裡攔截到 Ctrl+C
        print("\n[偵測到 Ctrl+C] __main__ 正在安全關閉程式...")
    finally:
        print("-- 主程式已結束 --。")
        sys.exit(0)
