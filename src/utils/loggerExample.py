import os
import time
import logging
from logging.handlers import RotatingFileHandler

'''
• Logger 層級：決定哪些訊息「可以被進一步處理」（總閘門）。
• Handler 層級：決定被處理的訊息中，哪些「要輸出到特定目的地」（分閘門）。
• 當總閘門（預設 WARNING）比你的訊息（DEBUG）還要高時，分閘門開再大都收不到任何東西。

'''

# =========================================================================
# 🧱 第一層：內部核心類別（完全不綁定檔案、完全不知道 service.log 存在）
# =========================================================================

class MockCloudStorage:
    """模擬的雲端管家：只管專心呼叫專科監聽官"""

    def __init__(self):
        # 💡 宣告專屬於自己地盤的名字，不用括號，不決定檔案！
        self.logger = logging.getLogger("Pipeline.Storage")

    def download_image(self, customer_name: str):
        # 噴出日常包裹 (INFO)
        self.logger.info(f"🤖 [雲端] 成功下載顧客【{customer_name}】的原始影像。")


class MockImageEngine:
    """模擬的計算引擎：只管專心盯著 6 stages 的 exe 行程"""

    def __init__(self):
        # 💡 宣告專屬於自己地盤的名字
        self.logger = logging.getLogger("Pipeline.Engine")

    def run_6_stages(self, customer_name: str):
        self.logger.info(f"🚀 [引擎] 開始執行顧客【{customer_name}】的 6 stages 流水線...")

        # 模擬 Stage 1 成功，噴出碎碎念包裹 (DEBUG)
        self.logger.debug(f"⚙️ [Stage 1] Raw2Tif.exe 執行成功。")

        # 💡 模擬奇異輸入：如果名字叫做 "林先生"，就故意觸發一個異常現象！
        if customer_name == "林先生":
            self.logger.error(f"❌ [Stage 2] Scaler.exe 計算失敗！奇異輸入導致除以零！")
            return False

        self.logger.debug(f"⚙️ [Stage 2] Scaler.exe 執行成功。")
        return True


# =========================================================================
# 🎛️ 第二層：最外層主程式（上帝視角：負責動態配置 Console 與 File 交通警察）
# =========================================================================

def setup_dynamic_logger(enable_debug_mode: bool = False):
    """
    【動態日誌工廠】
    職責：在程式啟動的當下一秒，動態插拔 Console 喇叭與 File 黑盒子！
    """
    # 1. 抓到老祖宗 Root Logger（抓取全域控制權）
    root_logger = logging.getLogger()

    # 💡 動態看手錶、看設定：如果開啟 debug 模式，全系統音量調到最低的 DEBUG，否則維持 INFO
    if enable_debug_mode:
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    # 🧼 清理防禦：防止在某些環境下重複執行時掛載太多重複的交通警察
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 🎯 2. 【動態插拔輸出端 A】：設定螢幕輸出 (Console)
    console_handler = logging.StreamHandler()
    # 螢幕上講話要精簡、漂亮 [▶️ INFO | 訊息]
    console_formatter = logging.Formatter("▶️ %(levelname)-8s | %(message)s")
    console_handler.setFormatter(console_formatter)

    # 🛡️ 螢幕防禦：不論全域開多大，螢幕上「永遠只印 INFO 以上」的日常報告，拒絕 DEBUG 碎碎念刷屏！
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # 🎯 3. 【動態插拔輸出端 B】：設定自動切碎的實體硬碟黑盒子 (File)
    # 滿 10MB 自動切碎，硬碟裡永遠只留最近 5 份歷史檔案，生生世世不塞爆 HDD [1]
    file_handler = RotatingFileHandler(
        "../service.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    # 硬碟記錄要絕對精準：包含【時間、級別、是哪一個物件噴的、內文】
    file_formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    file_handler.setFormatter(file_formatter)

    # 🛡️ 硬碟防禦：硬碟是黑盒子，默默吞下包含 DEBUG 碎碎念在內的所有秘密
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    print(f"📡 [日誌工廠] 配置完畢。全域監聽音量: {'DEBUG (全開)' if enable_debug_mode else 'INFO (日常)'}")
    print("----------------------------------------------------------------")


# =========================================================================
# 🔄 第三層：您的永遠運行微服務 Main Loop
# =========================================================================

def main_loop():
    """模擬 24 小時不間斷運行的資料調度大 Pipeline 核心迴圈"""
    # 🧩 1. 誕生核心零件
    storage = MockCloudStorage()
    engine = MockImageEngine()

    # 模擬排隊進來的奇異輸入顧客名單
    customer_queue = ["張先生", "林先生", "陳小姐"]

    print("🚀 微服務正式啟動，進入不間斷巡邏任務...")

    # 🔄 2. 啟動永遠運行的迴圈
    for customer in customer_queue:
        try:
            # 步驟一：雲端管家下載
            storage.download_image(customer)
            time.sleep(0.5)  # 模擬任務間隔

            # 步驟二：運算引擎執行 6 stages
            success = engine.run_6_stages(customer)

            # 步驟三：大 Pipeline 根據 True/False 做出業務層級的乾淨判斷
            if success:
                logging.getLogger("Pipeline.Main").info(f"🎉 顧客【{customer}】全線通關！結果已安全上傳。\n")
            else:
                # 🎯 遇到奇異輸入爆掉時，大 Pipeline 進行局部就地隔離，但不死當！
                logging.getLogger("Pipeline.Main").critical( f"🚨 警告：顧客【{customer}】計算失敗，觸發隔離機制，跳向下一位！\n")

        except Exception as unknown_error:
            # 終極全知兜底捕手：抓取不在世界觀中的未知異常，確保 Daemon 永不死退出！
            logging.getLogger("Pipeline.Main").exception(f"💥 發生了從沒看過的未知重大異常：{unknown_error}")

        time.sleep(1)


# =========================================================================
# 🎬 實驗現場：您可以手動切換開關，見證動態路由的降維打擊
# =========================================================================
if __name__ == "__main__":
    # 🔬 實驗一：【晴天日常模式】
    # 請保持 enable_debug_mode=False 執行一次，觀察螢幕與實體 service.log 的差異。
    setup_dynamic_logger(enable_debug_mode=False)

    # 🔬 實驗二：【半夜拆彈模式】
    # 請將下方改成 True 重新執行！您會看見 Python 核心代碼一字未改，
    # 但實體 service.log 裡面會像開了透視眼一樣，把原本隱藏的 [Stage 1] 碎碎念全部撈出來！
    # setup_dynamic_logger(enable_debug_mode=True)

    # 啟動微服務大輪迴
    main_loop()
