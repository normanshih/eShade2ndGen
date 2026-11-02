import logging
import time
import argparse

from cloud.oneDriveStorage import OneDriveStorage
from cloud.azureAuthAgent import Mode4RobotAuthAgent, Mode3UserAuthAgent
from cloud.cloudChangeTracker import OneDriveDeltaTracker
from cloud.graphUrlBuilder import GraphUrlBuilder
from job.jobProducer import NewCaseFilter
from job.jobDispatcher import JobDispatcher
from jobConsumer import  JobConsumer
from exePipelineManageAgent import ExeImagePipelineManageAgent

from pathlib import Path


class CloudAgent:
    def __init__(self, systemConfig, args: argparse.Namespace, project_rootpath:Path):
        self.systemConfig = systemConfig
        self.args = args
        self.project_rootpath = project_rootpath
        self.authToken_filepath = project_rootpath / "data" / "token.json"
        self.auth_agent = None
        self.logger = logging.getLogger("eShade.cloudAgent")

    def init_authentication(self):
        # One Drive Azure License Data
        _tenant_id      = self.systemConfig["MICROSOFT_AZURE"]["TENANT_ID"]
        _client_id      = self.systemConfig["MICROSOFT_AZURE"]["CLIENT_ID"]
        _client_secret  = self.systemConfig["MICROSOFT_AZURE"]["CLIENT_SECRET"]
        _user_id        = self.systemConfig["MICROSOFT_AZURE"]["USER_ID"]
        # 2. 初始物件
        if self.args.authentication == 4:
            # Mode4 Robotic
            self.auth_agent = Mode4RobotAuthAgent(_client_id,
                                             _tenant_id,
                                             _client_secret,
                                             _user_id)

        else:
            # Mode3 User Account
            self.auth_agent = Mode3UserAuthAgent(_client_id,
                                                 _tenant_id,
                                                 _user_id,
                                                 self.authToken_filepath)

        self.logger.info(f"Mode{self.args.authentication} auth_agent initiated")

    def init_service(self):
        self.graphUrl_agent = GraphUrlBuilder(self.auth_agent, "eShade_Repository")
        self.storage_agent = OneDriveStorage(self.auth_agent, self.graphUrl_agent)

        deltaToken_filepath = self.project_rootpath / "data" / "delta_token.txt"
        self.change_tracker = OneDriveDeltaTracker(self.storage_agent,self.graphUrl_agent, deltaToken_filepath)

        eShade_Repository_id = self.storage_agent.get_folder_id_by_name("eShade_Repository")
        self.logger.info(f'Main: eShade_Repository folder id = {eShade_Repository_id}')
        ### display basic information
        #itemMeta = DriveItem(self.storage_agent.get_item_metadata_by_id(eShade_Repository_id))
        #self.logger.debug(f"meta = {itemMeta}")

        ## Queue between producer and consumer
        self.jobDispatcher = JobDispatcher()

        ###
        self.exeImagePipelineManageAgent = ExeImagePipelineManageAgent(self.project_rootpath, self.systemConfig)

        ## Job consumer thread
        self.jobConsumerDaemon = JobConsumer(self.jobDispatcher,
                                             self.exeImagePipelineManageAgent,
                                             self.project_rootpath,
                                             self.systemConfig)
        self.jobConsumerDaemon.daemon = True
        self.jobConsumerDaemon.start()

        ## producer: check delta if match new case criteria
        self.newCaseFilterDaemon = NewCaseFilter(self.storage_agent, eShade_Repository_id, "truecolor")


    def new_case_tracking_loop(self):
        self.logger.info(f"start tracking delta ...")
        try:
#            changeItem = self.change_tracker.get_next_changes("eShade_Repository", True)
            while True:
                changes = self.change_tracker.get_next_changes("eShade_Repository", False)
                for changeItem in changes:
                    self.logger.debug(f"change = {changeItem}")
                    self.newCaseFilterDaemon.isValidCase(changeItem, self.jobDispatcher)

                ''' --- after a delta process --- '''
                self.change_tracker.commit_checkpoint()

                # Delta polling period
                #polling_period = int(self.systemConfig["CLOUD_SERVICES"]["TRACKING_PERIOD"])
                polling_period = self.systemConfig.getint("CLOUD_SERVICES","TRACKING_PERIOD", fallback=15)
                self.logger.debug(f"polling_period = {polling_period}")
                time.sleep(polling_period)

        except Exception as e:
            self.logger.warning(f"new_case_tracking_loop: Exception {e}")

    def run(self):
        self.init_authentication()
        self.init_service()
        self.new_case_tracking_loop()

    def stop(self):
        # cloud agent STOP
        self.logger.warning("cloudAgent 正在安全關閉程式...")
        # 您可以在這裡執行清理工作（例如關閉資料庫連線、儲存檔案）
        self.jobConsumerDaemon.stop()
        self.jobConsumerDaemon.join(3)
