from utils.myAppBootstrap import  MainProgramFacilities
from cloudAgent import CloudAgent
import sys, os
import configparser
from pathlib import Path
import json




#---------------------------------------------------------------------------------------------------
class MyEnterpriseApp(MainProgramFacilities):
    def __init__(self, description: str = "應用程式命令列介面"):
        super().__init__(description)

        self.project_root = Path(__file__).resolve().parents[2]     # eShade2ndGen/src/eShade_cloudApp/main.py is under 3 layers
        print(f"project_root: {self.project_root}")

    def setup_options(self):
        """
        明確、在線（In-line）宣告這支程式要用的 Options，非常易讀！
        self.add_option("-p", "--port", type=int, default=8080, help="服務連接埠")
        """
        self.add_option("-c", "--config", type=str, default="config.ini", help="設定檔路徑")
        self.add_option("-a", "--authentication", type=int, default=3, help="Token認證模式") # 3 or 4 ONLY

    def _init_configure(self, systemConfig_filepath):
        ''' systemConfig is .ini format '''
        self.systemConfig = configparser.ConfigParser()
        self.logger.debug(f"_init_configure: config_filepath={systemConfig_filepath}")

        config_file = Path(__file__).resolve().parent / systemConfig_filepath
        self.logger.debug(f"_init_configure: config_file={config_file}")
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"❌ 找不到關鍵設定檔 {systemConfig_filepath}！")
        self.systemConfig.read(config_file, encoding="utf-8")

        ## 列印 INI config file 內容 in json 格式
        self._ini2json()

    def main(self, args):
        """核心業務邏輯。廠務已經把 args 準備好了，直接享用"""
        self.logger.info(f"🚀 程式 {__file__} 已啟動")

        # 透過 args.xxx 直接存取，完全沒有 local/global 的困擾
        self.logger.debug(f"[-] 正在載入設定: {args.config} to self.config")
        if args.verbose:
            self.logger.debug("🔍 [DEBUG] 詳細除錯模式已開啟")

        self.cloud_agent = CloudAgent(self.systemConfig, args, self.project_root)
        self.cloud_agent.run()

    def stop(self):
        self.cloud_agent.stop()

    def _ini2json(self):
        ## 列印 INI config file 內容 in json 格式
        # 1. 運用字典推導式（Dict Comprehension），動態將整個 INI 內容物件轉成 Dict
        config_dict = {section: dict(self.systemConfig[section]) for section in self.systemConfig.sections()}
        # 2. 使用 json.dumps 進行美化列印 (indent=4 代表縮排 4 個空格)
        # ensure_ascii=False 可以確保你的中文路徑或註解不會變成亂碼 (\u4e2d\u6587)
        beautiful_output = json.dumps(config_dict, indent=4, ensure_ascii=False)
        self.logger.info("=== 動態偵測到的配置樹狀圖 ===")
        self.logger.info(beautiful_output)


#===========================================================================
if __name__ == "__main__":
    # 執行檔全域進入點
    app = MyEnterpriseApp(description="我的高易讀性自動化工具")
    try:
        app.run()
    except KeyboardInterrupt:
        # 在這裡攔截到 Ctrl+C
        print("\n[偵測到 Ctrl+C] __main__ 正在安全關閉程式...")
        app.stop()
    finally:
        print("主程式已結束。")
        sys.exit(0)


