from typing import NamedTuple
from abc import ABC, abstractmethod

import subprocess
import logging

import sys
from pathlib import Path
from typing import List




class SubProcessExecutorCommandFactory:
    """
    專職處理實體跨平台指令組裝的智慧工廠（支援流暢動態參數注入）
    app_root_path
    exe_program_name
    """
    def __init__(self, app_root_path: str, exe_name: str):
        self.app_root = Path(app_root_path).resolve()
        self.exe_name = exe_name
        # 🎯 專職儲存不定數量引數的「參數物流池」
        self._extra_args: List[str] = []

    def add_argument(self, arg: str) -> "SubProcessExecutorCommandFactory":
        """
        🔥 流暢建造者方法：動態注入一個參數。
        傳回 self 可以讓我們連續點 . 連續串接！
        """
        if arg:
            self._extra_args.append(str(arg))
        return self  # 💡 關鍵：回傳自己，達成流暢介面

    def build_args(self) -> List[str]:
        """將『絕對路徑執行檔』與『不定數量的動態參數』華麗咬合"""
        full_exe_path = (self.app_root / self.exe_name).resolve()

        if not full_exe_path.exists():
            raise FileNotFoundError(f"【核心阻斷】找不到執行檔: {full_exe_path}")

        # 2. 鋼鐵結合：[ 執行檔絕對路徑 ] + [ 外部隨意追加的不定數量參數 ]
        # 徹底杜絕開 shell=True 的字串拼湊，防範 Shell Injection 攻擊
        return [str(full_exe_path)] + self._extra_args

    @property
    def cwd(self) -> str:
        return str(self.app_root)

class ProcessResult(NamedTuple):
    """
        冰清玉潔的執行結果物件，將底層數據升級為商務領域語言
        • 💖 NamedTuple：既可以用數字索引（result[0]），也可以像一般物件一樣用點 . 存取（result.returncode）！
    """
    returncode: int
    stdout: str
    stderr: str

    @property
    def is_success(self) -> bool:
        """[易理解] 上層只需要問：執行成功了嗎？"""
        return self.returncode == 0

    @property
    def error_message(self) -> str:
        """[易維護] 自動去頭去尾、乾淨的錯誤回報訊息"""
        return self.stderr.strip()



class ProcessRunner:
    """
    專職無狀態執行外部指令的防禦型引擎

    """

    def __init__(self, default_timeout_seconds: int = 60):
        # 🎯 預設 60 秒逾時控制，防止老舊 exe 無限卡死硬碟
        self.default_timeout = default_timeout_seconds
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute(self, cmd_factory: SubProcessExecutorCommandFactory) -> ProcessResult:
        """
        🔥 鋼鐵執行大絕：
        上層只需要把『指令工廠』丟進來，剩下的安全防禦完全由引擎私下解決。
        """
        # 1. 向工廠伸手拿組裝好的跨平台指令與工作目錄
        args = cmd_factory.build_args()
        cwd = cmd_factory.cwd

        try:
            # 2. 物理發射：一律關閉 shell=False 杜絕注入攻擊，一律捕獲輸出
            completed_process = subprocess.run(
                args,                           # execute arguments, e.g. program.exe setup_config.json
                cwd=cwd,                        # set executor Process current working directory
                capture_output=True,            # 自動幫你抓 stdout / stderr
                text=True,                      # 自動把 binary 轉成人类看得懂的字串
                encoding="utf-8",
                timeout=self.default_timeout,   # 鋼鐵時限控制
                shell=False                     # 安全鐵律 (default False)
            )

            # 3. 完美打包回傳
            return ProcessResult(
                returncode=completed_process.returncode,
                stdout=completed_process.stdout,
                stderr=completed_process.stderr
            )

        except subprocess.TimeoutExpired as e:
            # 💡 防禦機制：如果 exe 卡死超過 60 秒，這裡會強行擊落它，並記錄慘案現場
            self.logger.error(f"❌ 外部程序執行逾時，已強制擊落！指令: {' '.join(args)}")
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=f"Subprocess TimeoutExpired after {self.default_timeout} seconds."
            )
        except Exception as e:
            # 處理系統級未預期異常（例如找不到執行檔）
            return ProcessResult(
                returncode=-99,
                stdout="",
                stderr=f"System Unexpected Error: {str(e)}"
            )



class BaseExeProgramExecutorAgent(ABC):
    """ 所有外部實體 .exe 機器的鋼鐵代理人基底, 以「任務」為Scope
        職責： 自主運行 .exe 檔
        1. app_path         : app path
        2. exe_app_filename : exe application file name
        3. config_filename  : config file name (MUST at the same exe_app_path)          :
    """

    def __init__(self, app_path:str,
                 exe_app_filename:str,
                 exe_timeout_sec:int,
                 extra_args:List[str]=None):

        self._app_path = app_path
        self._exe_app_filename = exe_app_filename

        self.logger = logging.getLogger(f"Agent.{self.__class__.__name__}")
        self.logger.debug(f"{self.__class__.__name__} Constructed")
        self._cmd_factory = SubProcessExecutorCommandFactory(self._app_path, self._exe_app_filename)
        if extra_args is not None:
            for arg in extra_args:
                self._cmd_factory.add_argument(arg)
        self._runner = ProcessRunner(exe_timeout_sec)


    # 🔥 核心大絕：樣板方法。上層只要呼叫 .run_pipeline()，一條龍物流自動咬合！
    def run(self, *args, **kwargs) -> ProcessResult:
        """上層唯一可見的商務介面，內部完美貫徹前處理與後處理的鋼鐵紀律"""
        # 3. 發射指令並捕獲結果
        try:
            res = self._runner.execute(self._cmd_factory)
            return res
        except Exception as e:
            self.logger.error(f"Agent run @ eException {e}")


#================================================================================================
if __name__ == "__main__":
    # 1. 綁定常駐在硬碟的實體應用程式目錄
    APP_DIR = "../exeApplication_agents"

    # 2. 初始化我們的 OO 智慧工具小隊
    #configurator = SmartAppConfigurator(APP_DIR)

    agent = BaseExeProgramExecutorAgent(app_path=APP_DIR,
                                        exe_app_filename="exeSimulator_app.py",
                                        exe_timeout_sec=180,
                                        extra_args=["-c", "exeSimulator_setup.json"])


    # ========================================================
    # 🚀 易理解、易維護的商務管線工作流
    # ========================================================

    # 第一步：修改設定（使用你體悟出的 dot 大絕與防腐層）
    '''
    with configurator.open_config() as config:
        config.threads = 8
        config.debug_mode = False
    print("📥 [OK] 實體 config.json 參數配置完畢。")
    '''

    # 第二步：交給引擎物理發射（上層完全不需要寫 subprocess 髒代碼）
    print("🚀 外部 .exe 指令發射中...")
    result = agent.run()

    # 第三步：商務 NG 盲檢規則判斷
    if result.is_success:
        print(f"🔍 現場回報訊息為: {result.stdout}")
        print(f"🔍 現場回報錯誤為: {result.stderr}")
        print("🎉 【OK商業串接】外部 APP 執行成功！準備通知下一棒物流...")
    else:
        print(f"❌ 【NG商業補償】外部 APP 失敗！拋出異常或派發至中央轉運站...")
        print(f"🔍 慘案現場報錯訊息為: {result.error_message}")
