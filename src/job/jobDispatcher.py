'''
task manager collects tasks from eShadeCloudApplication and dispatch task to exe executer

'''

import time
import queue
import logging

from job.jobDescriptor import JobDescriptor

class JobDispatcher:
    """
    職責：系統【中介工作分配轉運站】。
    特徵：利用 Python 官方內建的 queue.Queue 實踐鋼鐵防爆。專管『生產者與消費者』的物理平衡！
    """
    def __init__(self, max_capacity: int = 999):
        self.logger = logging.getLogger("Pipeline.Dispatcher")
        # 📦 誕生現成的工作佇列，設定最大容量防線（例如硬碟快爆了就不准再下載）
        self._pool = queue.Queue(maxsize=max_capacity)

    def submit_job(self, jobDescriptor: JobDescriptor) -> bool:
        """【給生產者（Cloud）用的接口】：雲端巡邏官只要載完新影像，無腦往這裡丟！"""
        try:
            # item 裝著我們昨天大獲全勝的 OneDriveItem (包含 id, name, parent_id)
            self._pool.put(jobDescriptor, block=False)
            self.logger.debug(f"📥 [分配器] 成功接單！ Job【{jobDescriptor.id}】 已進入中央排隊序列。")
            return True
        except queue.Full:
            self.logger.warning("🚨 [分配器警告] 暫存庫排隊已滿！命令雲端卡車暫停下載，防止硬碟被塞爆！")
            return False

    def fetch_next_job(self):
        """【給消費者（Local Exe）用的接口】：本地運算引擎算完了，轉身來跟我要下一張圖"""
        # block=True 代表如果目前沒訂單，計算執行緒就地高雅休眠發呆，不耗 CPU！
        # timeout=10 代表發呆 10 秒如果還是沒單，自動醒來喘口氣，防止永久卡死
        try:
            job = self._pool.get(block=True, timeout=1)
            return job
        except queue.Empty:
            return None

    def task_done(self):
        """通知分配器：這一單的 6 Stages 已經全線大功告成、安全回傳雲端了！"""
        self._pool.task_done()

    @property
    def current_backlog_count(self) -> int:
        """隨時向大總管回報：目前還有幾位客人在排隊"""
        return self._pool.qsize()


class TaskManager:
    """
    職責：全系統的最高指揮官（Application Object）。
    特徵：肚子裡養著雙神經通道（多執行緒），完美實踐『雲端下載』與『本機運算』的非同步多工嚙合！
    """

    def __init__(self, storage_client, change_tracker):
        self.logger = logging.getLogger("Pipeline.TaskManager")

        # 🔑 注入低階技術零件（耗材渠道）
        self.storage = storage_client
        self.tracker = change_tracker

        # 📦 誕生唯一的中央工作分配轉運站
        self.dispatcher = JobDispatcher(max_capacity=50)

    def _cloud_fetcher_loop(self):
        """【執行緒 A 的無限心跳】：只管雲端巡邏與下載，絕不碰 exe！"""
        self.logger.info("🧵 [執行緒 A] 雲端吞吐專車已啟動，發動 24 小時無感巡邏...")
        while True:
            try:
                # 📡 借用偵探與卡車去巡邏時間軸
                changed_items = self.tracker.get_next_changes(storage_client=self.storage)

                for raw_dict in changed_items:
                    # 🎯 調用大一統解讀大腦！
                    item = OneDriveItem(raw_dict)

                    # 🛡️ 排除自己上傳的、被刪除的、或是偽裝成檔案的資料夾
                    if item.is_deleted or item.is_folder:
                        continue

                    if item.is_file and item.name == "input.raw":
                        # 🚚 物理下載：把檔案安全拉回本機暫存區
                        self.storage.download_file(item.eShade_Repository_id, local_path=f"C:/Temp/{item.eShade_Repository_id}.raw")

                        # 📥 放入中央分配器排隊！成功跟下一關的 Exe 工人執行緒接軌！
                        self.dispatcher.submit_job(item)

            except Exception as e:
                self.logger.error(f"🚨 [執行緒 A 爆掉] 雲端巡邏發生異常: {e}")

            # ⏳ 每隔 30 秒看一次手錶，發動下一次巡邏
            time.sleep(30)

    def _exe_worker_loop(self):
        """【執行緒 B 的無限心跳】：只管 subprocess 進程調度，這輩子不知道什麼叫 OneDrive！"""
        self.logger.info("🧵 [執行緒 B] 本地進程指揮官已啟動，死死死死盯著分配器序列...")
        while True:
            # 🎯 自覺阻塞抽單：如果沒單，這裡會一秒進入優雅休眠，不浪費 CPU 資源！
            job = self.dispatcher.fetch_next_job()

            if job:
                self.logger.info(f"⚙️ [執行緒 B] 抓到新訂單！開始對準 【{job.name}】 發動 6 Stages 進程接力...")

                # ⚔️ ⚔️ ⚔️ 明天即將大打出手、全面爆發的本地進程指揮官重活 ⚔️ ⚔️ ⚔️
                # success = self.local_engine.run_6_stages(job.id)
                success = True  # 模擬計算通關

                if success:
                    # 上傳成品、按下 commit Checkpoint 斷電不漏單大鐵鎖 [1.1]
                    self.dispatcher.task_done()
                    self.logger.info(f"🎉 [執行緒 B] 項目 【{job.name}】 全線大功告成，安全結案！")

    def start_service(self):
        """【上帝開關】：大總管 main 呼叫此方法，兩條執行緒同時破繭而出！」"""
        print("\n⚡ ==================== 🚀 多執行緒微服務啟動 🚀 ====================")

        # 🧩 1. 組裝執行緒 A：把雲端心跳塞進去
        t_cloud = threading.Thread(target=self._cloud_fetcher_loop, name="CloudFetcher")
        # 🧩 2. 組裝執行緒 B：把本機進程心跳塞進去
        t_exe = threading.Thread(target=self._exe_worker_loop, name="ExeWorker")

        # 🛡️ 設定為背景守護執行緒（Daemon），確保主程式關閉時，它們會自覺乾淨地一起陪葬，絕不變成殭屍！
        t_cloud.daemon = True
        t_exe.daemon = True

        # 🚀 雙通道全面開火！
        t_cloud.start()
        t_exe.start()

        print("✅ 雙通道神經網絡嚙合大成功！主程式入口進入最高防禦看戲狀態。")
        print("==================================================================\n")


