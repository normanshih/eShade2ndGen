import logging
import time

from job.workspaceSandbox import RGB2RGBWorkspaceSandbox
from exeApplication_agents.exeSimulator_app import Simulator_Configurer, ExeSimulatorProgranExecuterAgent
from exeApplication_agents.exeUnwarp_agent import Unwarp_Configurer, ExeUnwarpProgramExecuterAgent
from exeApplication_agents.exeRGB2RGB_agent import RGB2RGB_Configurer, ExeRGB2RGBProgramExecuterAgent

from imageProcessig.raw_isp import RawImagePipeline
from imageProcessig.tcc_finder import TCC_CARD_FINDER
from utils.system_info import  get_ram_size_gb
from imageProcessig.imageEnhancer import ResizeByTotalPixelsFilter
from utils.errorStatusReport import Result, report_error_via_filename
from pathlib import Path
import shutil
from typing import NamedTuple

import cv2


'''
exeImagePipelineManageAgent is a management agent (called by JobConsumer thread) in which 
- interface between consumer 實際任務處理
manage exeAgents
職責：image pipeline 統合者，包含 inline 處理 and/or exe外部執行程式 間的控制與資料串流
    1. Load Image (either RAW or standard imae format) File to memory buffer
    2. Aruco Mark detection to 取得 & save TCC Colorchecker, e.g. tcc.tif image file
    3. Resizing image (according to Limit of computing power DRAM size) to save file
    4. UNWARP read TCC image file to get RGB value of TCC to save  (update) to deviceRGB_Original.txt file
    5. RGB2RGB converts image to truecolor image
'''

#RAM_GB_TABLE = [{8:1}, {16:3}, {24:4}, {32:5}, {64:10}]     # define  DRAM to  max image size M pixels {DRAMGB:MegaPixel}
RAM_GB_TABLE = [{8:1}, {16:3}, {24:4}, {32:5}, {64:10}]     # define  DRAM to  max image size M pixels {DRAMGB:MegaPixel}

class ExeImagePipelineManageAgent:
    """
    統合管理程式
    """
    def __init__(self, project_rootpath, systemConfig):
        self.logger = logging.getLogger("eShade.jobConsumer.ExeImagePipelineManageAgent")
        self.project_rootpath = project_rootpath
        self.systemConfig = systemConfig

        exe_rootPath = Path(self.project_rootpath) / self.systemConfig["EXE_SERVICES"]["EXE_PATH_PREFIX"]
        self.logger.debug(f"exe_rootPath = {exe_rootPath}")

        exeUnwarpPath = exe_rootPath / self.systemConfig["EXE_SERVICES.UNWARP"]["EXE_APP_PATH"]
        exeUwarpApp = self.systemConfig["EXE_SERVICES.UNWARP"]["EXE_APP_NAME"]
        configUwarp = self.systemConfig["EXE_SERVICES.UNWARP"]["CONFIG_NAME"]
        self.logger.info(f"UNWARP.exe program INFO: \n"
                         f"located at    : {exeUnwarpPath},\n"
                         f"program name  : {exeUwarpApp},\n"
                         f"setup file    : {configUwarp}")

        self.unwarpConfigurer = Unwarp_Configurer(configUwarp, exeUnwarpPath)
        self.exeUnwarpAgent = ExeUnwarpProgramExecuterAgent(exeUnwarpPath, exeUwarpApp, 180,[f"{configUwarp}"])

        #exeRGB2RGBPath = exe_rootPath / self.systemConfig["EXE_SERVICES.RGB2RGB"]["EXE_APP_PATH"]
        exeRGB2RGBPath = exe_rootPath / self.systemConfig.get("EXE_SERVICES.RGB2RGB","EXE_APP_PATH")
        exeRGB2RGBApp = self.systemConfig["EXE_SERVICES.RGB2RGB"]["EXE_APP_NAME"]
        configRGB2RGB = self.systemConfig["EXE_SERVICES.RGB2RGB"]["CONFIG_NAME"]
        self.logger.info(f"RGB2RGB.exe program INFO: \n"
                         f"located at  : {exeRGB2RGBPath},\n"
                         f"program name: {exeRGB2RGBApp},\n"
                         f"setup file  :{configRGB2RGB}")

        self.rgb2rgbConfigurer = RGB2RGB_Configurer(configRGB2RGB, exeRGB2RGBPath)
        self.exeRgb2rgbAgent = ExeRGB2RGBProgramExecuterAgent(exeRGB2RGBPath, exeRGB2RGBApp, 300,[f"{configRGB2RGB}"])


        # ============= EXE Simulator Agents ===============================================================
        agent_rooptath = Path(self.project_rootpath / "src/exeApplication_Agents")
        self.simulatorConfigurer = Simulator_Configurer(agent_rooptath / "exeSimulator_setup.json")
        self.exeSimulatorAgent = ExeSimulatorProgranExecuterAgent(agent_rooptath,
                                                         "exeSimulator_app.py",
                                                                  300,
                                                                  ['-v', '-c', 'exeSimulator_setup.json'])


    def runJob(self, ws_RGB2RGB:RGB2RGBWorkspaceSandbox,
               original_source_image_filepath: Path,
               final_output_upload_path:Path)->Result[None]:
        ''' called by jobConsumer._processJob,
        執行  任務步驟( raw2image, findTCC, unawarp2GetOriginalDeviceRgb, RGB2RGB)
        '''
        self.logger.debug(f"Original source image       : {original_source_image_filepath}")
        self.logger.debug(f"Final output upload folder  : {final_output_upload_path}")
        image = None
        image_stemname = Path(original_source_image_filepath).stem
        image_filemname = Path(original_source_image_filepath).name
        try:
            # 1. ----- Load image -----
            raw_isp = RawImagePipeline()
            result = raw_isp.load_image(original_source_image_filepath)
            if result:
                image = result.value
            else:
                # 失敗時，你可以根據 error_code 決定要怎麼處理
                self.logger.info(f"❌ 錯誤代碼: {result.error_code}")
                self.logger.info(f"📝 錯誤原因: {result.error_message}")
                report_error_via_filename(image_filemname, result.error_message, final_output_upload_path)
                return result

            # 2. ----- Find TCC -----
            tcc_finder = TCC_CARD_FINDER()
            tccResult = tcc_finder.run(image)
            if tccResult:
                tcc_image = tccResult.value
                ### captured TCC image save in image4unwarp folder with TCC_ prefix
                tcc_filepath = Path(ws_RGB2RGB.image4unwarp_folderPath) / f"TCC_{image_stemname}.TIF"
                self.logger.info(f"TCC is found successfully")
                tcc_finder.save(tcc_filepath)

                # ONLY for DEVELOPING
                #test_filepath = Path(final_output_upload_path) / f"TCC_{image_stemname}.TIF"
                #tcc_finder.save(test_filepath)
            else:
                self.logger.info(f"❌ 錯誤代碼: {tccResult.error_code}")
                self.logger.info(f"📝 錯誤原因: {tccResult.error_message}")
                report_error_via_filename(image_filemname, tccResult.error_message, final_output_upload_path)
                return tccResult

            # 3. ----- Resize the image to meet computer RAM size -----
            max_pixels, ram_GB = self.getMaxImagaeResolution()
            resized_image = ResizeByTotalPixelsFilter(image, max_pixels)
            ###
            toBeRgb2rgbConversionImage_filepath = Path(original_source_image_filepath).parent / f"ResizedImage_{image_stemname}.tif"
            success = cv2.imwrite(toBeRgb2rgbConversionImage_filepath, resized_image)
            if success:
                self.logger.info(f"Image is reshaped to fit {ram_GB}GB RAM ")

            ### ONLY for developing
            #resized_image_filepath = Path(final_output_upload_path) / f"ResizedImage_{image_stemname}.tif"
            #success = cv2.imwrite(resized_image_filepath, resized_image)
            #self.logger.debug(f"Save resized image successfully: {success}")

        except Exception as e:
            self.logger.error(f"Load image file {original_source_image_filepath} with {e} error")
            error_message=f"影像前處理轉換過程中發生未預期錯誤: {str(e)}"
            report_error_via_filename(image_filemname, error_message, final_output_upload_path)
            return Result.fail(
                error_code="Image Preprocessing Failed!",
                error_message=error_message,
                exception=e
            )

        # ----- 4. Unwarp: -----
        # TCC image (tcc_filepath) to get deviceRGB values and save to deviceRGB_Original.txt
        try:
            # 設定 UNWAR2RGB config.json
            self.unwarpConfigurer.source_image_filepath = tcc_filepath
            self.exeUnwarpAgent.set_configurations(self.unwarpConfigurer, ws_RGB2RGB)

            # 執行 UNWARP2RGB
            self.logger.debug(f'exeUnwarpAgent.run()')
            result = self.exeUnwarpAgent.run()
            self.exeUnwarpAgent.post_process(result)
            if not result.is_success:
                error_message = f"處理 Unwarp TCC card 過程中發生未預期錯誤"
                report_error_via_filename(image_filemname, error_message, final_output_upload_path)
                return Result.fail(
                    error_code="Unwarp Preprocessing Failed!",
                    error_message=error_message,
                )

        except Exception as e:
            error_message = f"處理 Unwarp TCC card 過程中發生未預期錯誤 eexception {e}"
            self.logger.error(error_message)
            report_error_via_filename(image_filemname, error_message, final_output_upload_path)
            return Result.fail(
                error_code="Unwarp Preprocessing Failed!",
                error_message=error_message,
                exception=e
            )

        # 5. ----- RGB2RGB -----
        # RGB2RGB output truecolor image to imageAfterRgb2RgbConversion/ folder of RGB2RGB_ColorData_path (in json)
        try:
            self.logger.debug(f"RGB2RGB.output_video_path = {ws_RGB2RGB.imageAfterRgb2RgbConversion_folderPath}")
            self.logger.debug(f"inputVideo_filepath = {original_source_image_filepath}")

            self.rgb2rgbConfigurer.source_image_filepath = toBeRgb2rgbConversionImage_filepath
            self.rgb2rgbConfigurer.RGB2RGB_ColorData_path = Path(self.unwarpConfigurer.deviceRGB_filepath).parent
            self.rgb2rgbConfigurer.color_spectrum_filepath = ws_RGB2RGB.color_spectrum_filepath

            result = self.exeRgb2rgbAgent.run()
            self.exeRgb2rgbAgent.post_process(result)
            if not result.is_success:
                error_message = f"處理 RGB2RGB Truecolor 過程中發生未預期錯誤"
                self.logger.error(error_message)
                report_error_via_filename(image_filemname, error_message, final_output_upload_path)
                return Result.fail(
                    error_code="RGB2RGB Preprocessing Failed!",
                    error_message=error_message,
                )

        except Exception as e:
            error_message = f"處理 RGB2RGB Truecolor 過程中發生未預期錯誤 exception {e}"
            self.logger.error(error_message)
            report_error_via_filename(image_filemname, error_message, final_output_upload_path)
            return Result.fail(
                error_code="RGB2RGB Preprocessing Failed!",
                error_message=error_message,
                exception=e
            )

        '''
        ### 6. exeSimulator (NOT needed in the future)
        try:
            output_filepath = ws_RGB2RGB.imageAfterRgb2RgbConversion_folderPath / Path(original_source_image_filepath).name
            self.logger.debug(f"exeAgent output_filepath = {output_filepath}")
            self.simulatorConfigurer.input_filepath = original_source_image_filepath # TBD
            self.simulatorConfigurer.output_filepath = output_filepath # TBD

            # exeAgent Pipeline process
            result = self.exeSimulatorAgent.run()
            status = self.exeSimulatorAgent.post_process(result)

        except Exception as e:
            self.logger.error(f"exeSimulatorAgent with {e} error")
            return Result.fail(
                error_code="exeSimulatorAgent Failed!",
                error_message=f"exeSimulatorAgent 過程中發生未預期錯誤: {str(e)}",
                exception=e
            )
        '''

        return Result.success(None)

    @property
    def output_filepath(self):
        ''' Assign output filepath for jobConsumer to upload '''
        return self.exeSimulatorAgent.output_filepath


    def getMaxImagaeResolution(self):
        ram_GB = get_ram_size_gb()

        final_MP = 1*(1024**2)
        for GB2MP in RAM_GB_TABLE:
            gb, MP = next(iter(GB2MP.items()))
            if ram_GB >= gb:
                final_MP = MP * (1024 ** 2)
            else:
                break
        return final_MP, ram_GB



