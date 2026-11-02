from abc import ABC, abstractmethod
import requests

class CloudStorage(ABC):
    """
    這是一個『合約（介面）』。
    它告訴整個系統：任何儲存管家，都必須學會下載與上傳。
    """
    @abstractmethod
    def get_item_metadata_by_id(self, item_id: str) -> dict:
        pass

    @abstractmethod
    def get_folder_id_by_name(self, folder_path: str) -> str:
        pass

    @abstractmethod
    def download(self, remote_path: str, local_dest: str) -> bool:
        pass

    @abstractmethod
    def upload(self, local_path: str, remote_dest: str) -> bool:
        pass

    @abstractmethod
    def upload2FolderId(self, local_file_path: str, remote_folder_id: str, filename:str) -> bool:
        pass

    @abstractmethod
    def create_folder(self, parent_folder: str, new_folder_name: str) -> str:
        pass

