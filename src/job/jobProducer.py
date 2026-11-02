from cloud.driveItems import DriveItem
from cloud.cloudStorage import CloudStorage
import logging

from job.jobDispatcher import JobDispatcher
from job.jobDescriptor import JobDescriptor, CaseInfo

'''
eShadeCloudApplication
定義 JobDescriptor 經由 JobDispatcher 傳遞 Job to JobProcess, e.g. ImageProcess
JobDescriptior 包含必要資訊與方法 
'''

UPLOAD_TRUECOLOR_FOLFDER = "truecolor"

class NewCaseFilter:
    ''' 
    .../eShade_Repository/<customer_folder>/<case_folder>/<case_file>
       <<grand grand>>    <<grand>>         <<parent>>    <<self>>
    '''
    def __init__(self, cloudStorage: CloudStorage, repository_id:str, uploadFolderPath:str):
        self.logger = logging.getLogger("eShade.NewCaseFilter")
        self._cloudStorage = cloudStorage
        self._repository_id = repository_id
        self._uploadFolderPath = uploadFolderPath
        self.jobId = 0

    def isValidCase(self, item: dict, jobDispatcher:JobDispatcher):
        ''' not deletedt && grandparent_id==eShade_Repository id '''
        self._driveItem = DriveItem(item)
        if self._driveItem.is_deleted:
            return False

        parent_id = self._driveItem.parentId
        if not parent_id:
            return False
        parentItem = self._cloudStorage.get_item_metadata_by_id(parent_id)

        parentDriveItem = DriveItem(parentItem)
        grandParent_id = parentDriveItem.parentId
        if not grandParent_id:
            return False

        grandParentItem = self._cloudStorage.get_item_metadata_by_id(grandParent_id)
        grandParentDriveItem = DriveItem(grandParentItem)
        grandGrandParent_id = grandParentDriveItem.parentId
        if not grandGrandParent_id:
           return False

        grandGrandParentItem = self._cloudStorage.get_item_metadata_by_id(grandGrandParent_id)
        grandGrandParentDriveItem = DriveItem(grandGrandParentItem)

        grandGrandParent_name = grandGrandParentDriveItem.name
        grandGrandParent_id   = grandGrandParentDriveItem.id


        self.logger.debug(f"item name: {self._driveItem.name}, item id: {self._driveItem.id}, deleted:{self._driveItem.is_deleted}, is_file: {self._driveItem.is_file}")
        self.logger.debug(f"parent name: {parentDriveItem.name}, parent id: {parentDriveItem.id}")
        self.logger.debug(f"grand name: {grandParentDriveItem.name}, grand id: {grandParentDriveItem.id}")
        self.logger.debug(f"grandGrand name: {grandGrandParentDriveItem.name}, grandGrand id: {grandGrandParentDriveItem.id}")
        self.logger.debug(f"------------------------------------------------------------------------")

        '''
        ------------- Developing SandBox ------------------------
        '''
        if grandParentDriveItem.name != "eShade_upload_norman":
            self.logger.debug(f'❌ NOT IN THE SANDBOX ❌')
            return False
        '''
        ============= Developing SandBox ==========================
        '''

        if (not self._driveItem.is_deleted) and (self._driveItem.is_file) and (grandGrandParent_id == self._repository_id):
            self.logger.debug(f"{self._driveItem.name} was uploaded ...")
            self.logger.debug(f"------------------------------------------------------------------------")

            dest_uploadFolderId = self._cloudStorage.create_folder(parent_id, UPLOAD_TRUECOLOR_FOLFDER)
            self.logger.debug(f'----------{UPLOAD_TRUECOLOR_FOLFDER} dest_uploadFolderId = {dest_uploadFolderId}')

            caseInfo = CaseInfo(grandParentDriveItem.name, parentDriveItem.name, self._driveItem.name)
            result = self.produceJob(caseInfo,
                                     self._driveItem.id,
                                     dest_uploadFolderId,
                                     jobDispatcher)

            return result

        else:
            self.logger.debug(
                f"FALSE: Grand2 Parent id: {grandGrandParent_id}, repository_id: {self._repository_id}")
            self.logger.debug(f"------------------------------------------------------------------------")
            return False


    def produceJob(self,caseInfo:CaseInfo, src_downloadFromFile_id, dest_uploadToFolder_id,job_dispatcher):
        storageOps = self._cloudStorage
        jobDescriptor = JobDescriptor(caseInfo,
                                      src_downloadFromFileId=src_downloadFromFile_id,
                                      dest_uploadToFolderId=dest_uploadToFolder_id,
                                      storageServices=storageOps,
                                      jobId=self.jobId)
        self.jobId += 1

        result = job_dispatcher.submit_job(jobDescriptor)
        return result