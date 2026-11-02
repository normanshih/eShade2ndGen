import logging
import tempfile
import shutil
from pathlib import Path
import sys

'''
RGB2RGB Sandbox (temp disk space within "with usage")
where to put 1. RGB2RGB template folder, 2. input video file, 
and be erased after getting processed output video file(s), process report
'''
class RGB2RGBWorkspaceSandbox:
    FOLDER_RGB2RGB = "RGB2RGB"
    FOLDER_INPUT_VIDEO  = "input_video"
    FOLDER_IMAGE_AFTER_CONVERSION = f"{FOLDER_RGB2RGB}/ImagesAfterConversion"
    FOLDER_IMAGE4UNWARP = f"{FOLDER_RGB2RGB}/Images4Unwarp"
    FOLDER_IMAGE4CHARACTERIZATION = f"{FOLDER_IMAGE4UNWARP}/Images4Characterization"
    FILE_DEVICERGB_ORIGINAL = f"{FOLDER_RGB2RGB}/deviceRGB_Original.txt"
    FILE_COLOR_SPECTRUM = f"{FOLDER_RGB2RGB}/color_spectrum_eShade/ColorChecker_eShade_M0_ModifiedByMCLo_14X10.txt"

    def __init__(self, template_path: str, prefix: str = "eShade"):
        '''
        :param template_path: folder path of RGB2RGB template
        :param prefix: prefix of sandbox random name
        '''
        self.logger = logging.getLogger("Job.RGB2RGBWorkspaceSandbox")
        self.prefix = prefix
        # 💡 將你的範本路徑轉為強型別 Path 物件
        self.template_path = Path(template_path)
        self._temp_dir: Path | None = None

        self.logger.debug(f"self.template_path = {self.template_path}")

    def __enter__(self):
        # 1. 為了不破壞原本的 copytree 邏輯，我們先用 tempfile 取得一個「保證安全的臨時路徑名稱」
        # 但這次我們不用 mkdtemp 建立目錄，我們只拿路徑名字
        try:
            ### 建立 temp folder
            temp_root_str = tempfile.mktemp(prefix=self.prefix)
            self.logger.debug(f'temp_root_str = {temp_root_str}')
            self._temp_dir = Path(temp_root_str)
        except Exception as e:
            self.logger.error(f"Sandbox Error {e}")

        self._createWorkingTree()

        return self

    def _createWorkingTree(self):
        ''''
            # 2. 🔥 核心複製：將現成的目錄，整根複製到剛才設定的實體沙盒空間中
            # 這會把 MyTemplate 裡面的所有目錄結構、甚至預設檔案一併複製過去！
            #shutil.copytree(src=self.template_path, dst=self._temp_dir/self.template_path)
        '''
        try:
            ### 複製 RGB2RGB/ folder
            copied_path = shutil.copytree(src=self.template_path, dst=self._temp_dir / self.FOLDER_RGB2RGB)
            self.logger.debug(f"copied_path = {copied_path}")
            ### 建立 input_video/ folder
            self.original_image_source_folderPath.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"_createWorkingTree Error {e}")

    def backupWorkingTree(self, dest_path):
        backup_path = shutil.copytree(src=self._temp_dir, dst=dest_path)
        self.logger.info(f"backup_path = {backup_path}")

    @property
    def root_folderPath(self):
        return self._temp_dir

    @property
    def rgb2rgb_folderPath(self):
        return self._temp_dir / self.FOLDER_RGB2RGB

    @property
    def image4unwarp_folderPath(self):
        return self._temp_dir / self.FOLDER_IMAGE4UNWARP

    @property
    def images4Characterization(self):
        return self._temp_dir / self.FOLDER_IMAGE4CHARACTERIZATION

    @property
    def original_image_source_folderPath(self):
        ''' from jobConsumer to exePipelineManageAgent '''
        return self._temp_dir / self.FOLDER_INPUT_VIDEO

    @property
    def imageAfterRgb2RgbConversion_folderPath(self)->Path:
        ''' from exePipelineManageAgent to jobConsumer  '''
        return  self._temp_dir / self.FOLDER_IMAGE_AFTER_CONVERSION

    #----------------------------------------
    def save_video_file(self, videoFile:str)->None:
        video_src = Path(videoFile)
        video_dest = self.original_image_source_folderPath / video_src.name
        # 核心指令：物理搬移，塞進沙盒
        shutil.copy(video_src, video_dest)


    @property
    def deviceRGB_Oriinal_filepath(self)->str:
        return self._temp_dir / self.FILE_DEVICERGB_ORIGINAL

    @property
    def color_spectrum_filepath(self)->str:
        return self._temp_dir / self.FILE_COLOR_SPECTRUM


    def __exit__(self, exc_type, exc_val, exc_tb):
        # 3. 冰清玉洁，用完一樣整根拔除，不污染你的現成範本
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)


if __name__ == "__main__":
    try:
        with RGB2RGBWorkspaceSandbox("../../RGB2RGB") as ws:
            # 印出實體儲存空間在 Mac 裡的絕對路徑
            print("\n========================================")
            print(f"🔥 沙盒儲存空間已建立！路徑為：\n{ws._temp_dir}")
            print("========================================")
            print("Forever loop to exit by ctrl-C，這個資料夾就會神秘消失...")

            ws.save_video_file("IMG_0001.CR2")
            files = ws.output_video_filePaths
            print(f'files = {files}')

            print(f"deviceRGB_Original path: {ws.deviceRGB_Oriinal_filepath}")
            while True:
                pass
    except KeyboardInterrupt:
        # 在這裡攔截到 Ctrl+C
        print("\n[偵測到 Ctrl+C] 正在安全關閉程式...")
        # 您可以在這裡執行清理工作（例如關閉資料庫連線、儲存檔案）
    except Exception as e:
        print(f'Exception {e}')
    finally:
        print("主程式已結束。")
        print("\n🛑沙盒已自動銷毀！你可以去檢查它是不是消失了。")
        sys.exit(0)
