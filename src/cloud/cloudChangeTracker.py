from abc import ABC, abstractmethod
import os
import logging
from cloud.graphUrlBuilder import GraphUrlBuilder
from cloud.cloudStorage import CloudStorage


class CloudChangeTracker(ABC):
    """【變更追蹤器合約】無論底層是 Delta 還是 Scan，外界調度它的方式生生世世不變！"""

    @abstractmethod
    def get_next_changes(self, resource_path:str, latest:bool=False) -> list:
        """負責感知並撈出『這段期間新上傳/變動』的檔案大禮包 JSON 清單"""
        pass

    @abstractmethod
    def commit_checkpoint(self) -> None:
        """任務處理完後，負責把目前的『 Checkpoint 進度（或 DeltaToken）』封存起來"""
        pass


class OneDriveDeltaTracker(CloudChangeTracker):
    """
    職責：方案一 ── 專門利用微軟 Delta Query 與本地硬碟記憶，進行增量變更追踪。
    維護哲學：開機時自動翻閱硬碟遺言，絕不漏掉關機真空期的任何一張客戶單子！
    """

    def __init__(self, storage_agent: CloudStorage, url_builder:GraphUrlBuilder, token_file: str = "delta_token.txt"):
        self.logger = logging.getLogger("eShade.DeltaChangeTracker")
        self.url_builder = url_builder
        self.storage_agent = storage_agent
        self.token_file = token_file
        self._current_delta_url = self._load_token_from_disk()

    def _load_token_from_disk(self) -> str:
        """私有防線：開機時翻閱硬碟，繼承離線前的時空記憶"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r", encoding="utf-8") as f:
                    saved_url = f.read().strip()
                if saved_url:
                    self.logger.info(f"💾 [追蹤器] 成功從硬碟讀取 Delta 記憶節點，將無縫接軌離線真空期任務！")
                    return saved_url
            except Exception as e:
                self.logger.error(f"⚠️ [追蹤器] 讀取 Delta 檔案失敗: {e}")

        self.logger.debug("ℹ️ [追蹤器] 硬碟無歷史記憶（第一天通電），本輪將建立全新 Delta 初始基準點。")
        return ""

    def _build_url(self, work_path:str, deltaTarget:str="", latest:bool=False) -> str:
        clean_path = deltaTarget.strip("/")
        # 組合出工作目錄下的完整相對路徑
        #full_path = f"{work_path}/{clean_path}delta?token=latest" if work_path else clean_path
        if latest:
            full_path = f" https://graph.microsoft.com/v1.0/me/drive/items/{deltaTarget}/delta?token=latest"
        else:
            full_path = f" https://graph.microsoft.com/v1.0/me/drive/items/{deltaTarget}/delta"
        return full_path

    def get_next_changes(self, resource_path:str, latest:bool=False) -> list:
        """履行合約：打通網路，幫大 Pipeline 撈出最新變更"""
        # 🤖 1. 自覺判定大門口：如果口袋有舊網址，就用舊網址接關；沒有，就跟微軟要全新的起點 [6, 7]
        if self._current_delta_url:
            url = self._current_delta_url
        else:
            # 呼叫您 OneDriveStorage 內部的組合器，拼出最初的 .../drive/root/delta
            id = self.storage_agent.get_folder_id_by_name(resource_path)
            self.logger.debug(f"resource_path({resource_path} id = {id})")
            url = self.url_builder.build_delta_url(id)

        self.logger.debug(f"📡 [追蹤器] 向微軟發動變更巡邏，發送網址: {url}")

        try:
            # 2. 借用雲端管家的通訊兵發送 GET 請求
            response = self.storage_agent.send_http_request("GET", url)
            if response is None:
                return []

            res_json = response.json()
            items = res_json.get("value", [])

            # 🎯 3. 【真．自癒防線】微軟官方規定，如果 Delta Token 超過 7 天失效，會吐出這個特定錯誤 [7]
            if "error" in res_json and res_json["error"].get("code") == "resyncRequired":
                self.logger.critical(
                    "🚨 [追蹤器致命警告] Delta 憑證已遭微軟後台報廢（失效超過7天）！啟動全盤大掃描自癒防線...")
                self._current_delta_url = ""  # 清空 Token [7]
                return self.get_next_changes(self.storage_agent)  # 遞迴自我重整，100% 絕不死當！ [7]

            # 4. 暫存微軟回傳的下一動記憶連結 [6, 7]
            # 微軟會把新的 Checkpoint 網址塞在 @odata.deltaLink 或 @odata.nextLink 欄位裡 [6]
            self._next_checkpoint_url = res_json.get("@odata.deltaLink", res_json.get("@odata.nextLink", ""))
            self.logger.debug(f"_next_checkpoint_url = {self._next_checkpoint_url}")


            #self._current_delta_url = self._next_checkpoint_url
            return items

        except Exception as e:
            self.logger.error(f"🚨 [追蹤器] 巡邏變更時發生未預期錯誤: {e}")
            return []

    def commit_checkpoint(self) -> None:
        """履行合約：當大 Pipeline 安全算完影像後，才把記憶蓋章寫入硬碟（斷電不漏單防線）"""
        if self._next_checkpoint_url:
            self._current_delta_url = self._next_checkpoint_url
            try:
                # 🎯 實體封存：寫入硬碟，生生世世不失憶！
                with open(self.token_file, "w", encoding="utf-8") as f:
                    f.write(self._current_delta_url)
                self.logger.debug("💾 [追蹤器] 最新 Delta Checkpoint 已安全寫入硬碟。")
            except Exception as e:
                self.logger.error(f"❌ [追蹤器] 無法將 Checkpoint 封存至硬碟: {e}")



## -------------------------------------------------------------------------------------------
if __name__ == "__main__":
    pass