from typing import Protocol, Any
class StorageOps(Protocol):
    """ cloud access interfaces, e.g. download and upload  """
    def upload2FolderId(self, local_file_path: str, remote_folder_id: str, filename:str) -> str:...
    def download(self, remote_file_path: str, local_dest_path: str) -> str:...

class CaseInfo:
    def __init__(self, customer_folder:str, patient_folder:str, filename:str):
        self.customer_folder = customer_folder
        self.patient_folder = patient_folder
        self.file_name = filename

    @property
    def customer(self):
        return self.customer_folder

    @property
    def patient(self):
        return self.patient_folder

    @property
    def filename(self):
        return self.file_name

class JobDescriptor:
    """
    self-contained job in which includes data and operations
    data:
    filename            : src filename
    downloadFromFile    : src file id where to download the case file
    uploadToFolder      : dest folder id where to upload the processed data

    operations          : storageServices
    """
    def __init__(self, caseInfo:CaseInfo,
                 src_downloadFromFileId:str,
                 dest_uploadToFolderId:str,
                 storageServices:StorageOps,
                 jobId:str= "0000"):

        self.caseInfo = caseInfo
        self.downloadFromFileId = src_downloadFromFileId
        self.uploadToFolderId = dest_uploadToFolderId
        self.storageServices = storageServices
        self.jobId = jobId


    def upload(self, local_file_path: str, filename: str) -> str:
        return self.storageServices.upload2FolderId(local_file_path, self.uploadToFolderId, filename)

    def download(self, remote_file_path: str, local_dest_path: str) -> str:
        return self.storageServices.download(remote_file_path, local_dest_path)

    @property
    def id(self):
        return self.jobId

    @property
    def filename(self):
        return self.caseInfo.filename

    @property
    def patient(self):
        return self.caseInfo.patient

    @property
    def customer(self):
        return self.caseInfo.customer

    @property
    def src_downloadFromFileId(self):
        return self.downloadFromFileId

    @property
    def dest_uploadToFolderId(self):
        return self.uploadToFolderId