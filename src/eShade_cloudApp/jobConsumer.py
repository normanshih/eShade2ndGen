import datetime
import threading
import logging
import time

from job.jobDispatcher import JobDispatcher
from job.jobDescriptor import JobDescriptor, CaseInfo
from job.workspaceSandbox import RGB2RGBWorkspaceSandbox
from utils.mail import MAIL_SERVER, MailMessage

from exePipelineManageAgent import ExeImagePipelineManageAgent
from utils.errorStatusReport import Result
from utils.messageTask import MessageTask

from pathlib import Path
import configparser


# ==========================================
# 2. 背景消費者執行緒 (JobConsumer)
#    independent thread which read queue to get job
#   職責：收取 Job 與回覆處理的結果
#
# ==========================================
class JobConsumer(threading.Thread):
    def __init__(self, jobDispatcher: JobDispatcher,
                 exeImagePipelineManageAgent:ExeImagePipelineManageAgent ,
                 project_rootpath:Path,
                 systemConfig):
        # 💡 呼叫父類別建構子，並設定執行緒名稱方便 debug
        super().__init__(name="JobConsumer-Thread")
        self.logger = logging.getLogger("eShade.jobConsumer")
        self._jobDispatcher = jobDispatcher
        self._exeImagePipelineManageAgent = exeImagePipelineManageAgent
        self.project_rootpath = project_rootpath
        self.systemConfig:configparser.ConfigParser = systemConfig

        # 💡 使用 Event 物件來控制執行緒的生命週期，比用 bool 變數更安全、具備線程同步性
        self._shutdown_event = threading.Event()
        self.logger.debug("🤖 消費者執行緒已建立")

        self._install_message_notifier()


    def _install_message_notifier(self):
        ### email
        self.mailServer = MAIL_SERVER(self.systemConfig.get("SYS_LOG","MAIL_LOGIN"),
                                      self.systemConfig.get("SYS_LOG", "MAIL_PWD"))
        admin_mailList = self.systemConfig["SYS_LOG"]["ADMIN_MAIL_LIST"]
        self.logger.info(f"admin_mailList: {admin_mailList}")

        self.admin_addresses = self.systemConfig.get("SYS_LOG", "ADMIN_MAIL_LIST")


    def run(self) -> None:
        """執行緒啟動後的核心無窮迴圈"""
        self.logger.info("🤖 消費者執行緒已成功啟動，開始監聽任務佇列...")

        # 只要沒有收到停機訊號，就持續運作
        while not self._shutdown_event.is_set():
            try:
                # 💡 關鍵嚴謹設計：設定 timeout=1 秒
                # 這樣做可以讓執行緒每隔一秒就醒來檢查一次 shutdown_event 是否被點亮
                # 避免因為 Queue 是空的而無限期卡死在 get()，導致整個程式無法關閉
                job: JobDescriptor = self._jobDispatcher.fetch_next_job()
                if job:
                    self.logger.debug(f"消費者執行緒 fetch a jobDescriptor id = {job.id} ")
                    # 進入實際處理邏輯
                    self._process_job(job)

                    # 💡 告訴 Queue 該任務已安全處理完畢
                    self._jobDispatcher.task_done()
                else:
                    continue
            except Exception as e:
                # 🛡️ 防禦性補捉：避免單一任務的商業邏輯崩潰導致整個消費者執行緒死掉
                self.logger.error(f"💥 處理任務時發生非預期錯誤: {e}", exc_info=True)

        self.logger.info("👋 消費者執行緒已安全退出迴圈，正式結束。")

    def _process_job(self, job: JobDescriptor) -> None:
        '''
        從 Dispatcher (Queue) 取得 JobDescriptor (任務的資訊）,
        建立 任務 Sandbox，download image(job.filename) to sandbox.input_dir
        執行任務
        '''
        self.logger.info("\n--------------------------------------------------------------------")
        self.logger.info(f"⏳ [開始處理] 任務 ID: {job.id}，@ {datetime.datetime.now()} 資料內容: ")
        self.logger.info(f"⏳ [客戶資料] : {job.customer} ")
        self.logger.info(f"⏳ [病人資料] : {job.patient} ")
        self.logger.info(f"⏳ [檔案資料] : {job.filename} ")

        try:
            # 1. create workspace sandbox
            with RGB2RGBWorkspaceSandbox(self.project_rootpath / "RGB2RGB") as ws:
                self.logger.debug(f"!!! Sandbox created: {ws._temp_dir} ")

                # 2. download file to sandbox/input_video
                fileDownloaded = job.download(job.src_downloadFromFileId,
                                              f"{ws.original_image_source_folderPath / job.filename}")
                self.logger.debug(f"[消費者執行緒] source file download to: {fileDownloaded}")
                self.logger.debug(f"[消費者執行緒] 輸出成果目錄      : {ws.imageAfterRgb2RgbConversion_folderPath}")

                startTime = time.time()
                # 3. 交付工作，輸入 input video filepath & 告知 成果輸出的目錄
                pipelineResult: Result = self._exeImagePipelineManageAgent.runJob(ws_RGB2RGB=ws,
                                                                                  original_source_image_filepath=fileDownloaded,
                                                                                  final_output_upload_path=ws.imageAfterRgb2RgbConversion_folderPath)
                processTime = time.time() - startTime
                self.logger.info(f"[消費者執行緒] _exeImagePipelineManageAnegnt 執行 {processTime:.1f} 秒")

                # 4.1. upload the processed file(s) to cloud
                files = [f for f in ws.imageAfterRgb2RgbConversion_folderPath.iterdir() if f.is_file()]
                self.logger.debug(f"[消費者執行緒] output_folderPath file list: {files}")
                for filepath in files:
                    filename = Path(filepath).name
                    file_id = job.upload(filepath, filename)
                    self.logger.debug(f'[消費者執行緒]: uploaded {filename} to cloud id={file_id}')

                # 4.2. update CRM statistic
                if pipelineResult:
                    self.logger.info(f"Job is processed successfully!")
                else:
                    self.logger.error(f"Job is NOT done because {pipelineResult.error_message} !!!")
                    # send warning message to administer
                    if self.admin_addresses:
                        mail = MailMessage(to_address=self.admin_addresses,
                                           subject=f"eShade Error: {job.customer}: {job.patient}: {job.filename}")
                        mail.content(f"{pipelineResult.error_message}" )
                        self.mailServer.send(mail)

                    # backup sandbox
                    backup_path = self.systemConfig.get("SYS_LOG", "BACKUP_PATH",fallback="")
                    if backup_path:
                        dest_path = Path(backup_path) / f"{job.customer}_{job.patient}_{job.filename}_{datetime.datetime.now()}"
                        ws.backupWorkingTree(dest_path)

            self.logger.info("--------------------------------------------------------------------\n")

        except Exception as e:
            self.logger.error(f"job process error w/ Exception {e}")


    def stop(self) -> None:
        """提供給外部（如 Main）呼叫的優雅停機介面"""
        self.logger.info("🛑 消費者收到停機指令，正在通知消費者執行緒準備收尾...")
        self._shutdown_event.set()


# ==========================================
# 3. 主程式模擬 (Main Loop / Dispatcher 視角)
# ==========================================
if __name__ == "__main__":
    pass