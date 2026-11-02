from cloud.cloudStorage import CloudStorage
from cloud.azureAuthAgent import AzureAuthAgent
from cloud.graphUrlBuilder import GraphUrlBuilder
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import os
import logging
from email.message import Message
import inspect

class OneDriveStorage(CloudStorage):
    """
    職責：Storage resource agent
    核心哲學：系統的『倉儲物流工』。找貨品、搬貨品
    """

    def __init__(self, authAgent:AzureAuthAgent, urlBuilder:GraphUrlBuilder):
        self.logger = logging.getLogger("eShade.Storage")
        self.authAgent = authAgent
        self.urlBuilder = urlBuilder

        # 🔧 【維護邊界】未來微軟如果改版網址，你只需要改這三行類別常數
        self._graph_base_uri = self.authAgent.GRAPH_API_BASE_URI

        # 2. 定義 urllib3 的重試策略
        # 這邊是關鍵：它會專門捕捉 429 狀態碼，並自動聽從微軟告知的 Retry-After 秒數進行 sleep
        retry_strategy = Retry(
            total=5,  # 最大重試次數（包含所有錯誤）
            status_forcelist=[429, 500, 502, 503, 504],  # 遇到這些狀態碼才重試
            allowed_methods=["GET", "POST"],  # 允許重試的 HTTP 方法
            backoff_factor=1,  # 如果微軟沒給 Retry-After，則啟用指數退避（1s, 2s, 4s...）
            raise_on_status=False,  # 超過重試次數後，不要直接噴 urllib3 異常，讓 requests 處理
            respect_retry_after_header=True  # ⭐ 超級關鍵：強制遵守微軟回傳的 Retry-After 標頭秒數！
        )
        # 3. 建立一個具有自動重試功能的 requests Session
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        # 將這個策略掛載到所有 https:// 的微軟 Graph API 請求上
        self.session.mount("https://", adapter)

    def send_http_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """【底層通訊兵】負責發送 HTTP 請求與超時防禦"""
        try:
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {self.authAgent.get_access_token}"  # 動態塞入新鮮的機器人 Token
            kwargs["headers"] = headers
            kwargs["timeout"] = kwargs.get("timeout", 30)

            #print(f"📡 機器人實際發送的完整網址是: {url}")
            #response = requests.request(method, url, **kwargs)
            response = self.session.request(method, url, **kwargs)

            response.raise_for_status()
            return response
        except RuntimeError as auth_err:
            # 🎯 攔截【看門狗因為微軟端出問題】導致的認證死當錯誤！
            self.logger.error(f"🚨 [Daemon 警告] 微軟驗證伺服器目前無法連線或報錯：{auth_err}")
            self.logger.error("⏳ 這是網路或伺服器短暫異常，背景程式將保持運行，並在下一輪任務重新嘗試。")
            return None # 傳回 None，告訴外層這一輪任務失敗了，但程式沒死
        except requests.exceptions.HTTPError as http_err:
            # 1. 取得當前的 frame
            current_frame = inspect.currentframe()
            # 2. 透過 .f_back 退回到「呼叫 target_method 的那個人」
            caller_frame = current_frame.f_back
            # 3. 取得該呼叫者的函數名稱
            caller_name = caller_frame.f_code.co_name
            # 如果最終失敗（如 Token 徹底失效 401，或限流次數爆表），記錄結構化 JSON Log
            self.logger.error(
                f"OneDrive API 請求(by {caller_name})最終失敗 Error code: {http_err.response.status_code}",
                extra={
                    "event": "API_FINAL_FAILED",
                    "method": method,
                    "url": url,
                    "status_code": http_err.response.status_code
                }
            )
        except Exception as net_err:
            # 攔截其他像是下載到一半網路斷線的 HTTP 錯誤
            self.logger.error(f"🚨 [Daemon 警告] 傳輸中途網路斷線或微軟出錯：{net_err}")
            return None


    # =========================================================================
    # 公開業務方法：與外部微軟變動完全隔離的乾淨世界
    # =========================================================================
    def get_folder_id_by_name(self, folder_path: str) -> str:
        """
        【基礎建設盤點能力】
        職責：拿着人類肉眼看得到的『資料夾名字』，去微軟倉庫盤點、查出它對應的『實體 ID 亂碼』。
        """
        """
        【基礎建設頂級盤點能力】
        職責：拿着人類肉眼看得到的『無限層深度文字路徑』，去微軟雲端直接精準刨出它的實體 ID 亂碼！
        支援格式：
            - 第一層: "eShade_Repository"
            - 兩層以上: "eShade_Repository/ProjectA/WorkDir"
        """
        # 1. 🧼 搜身清洗：切除路徑前後多餘的斜線，防止接班人手震多打了斜線
        clean_path = folder_path.strip("/") if folder_path else ""
        self.logger.debug(f"get_folder_id_by_name: clean_path = {clean_path}")
        if not clean_path:
            self.logger.error("❌ [總海關盤點] 傳入的路徑是空的，無法換算 ID！")
            return ""

        # 🎯 🎯 🎯 2. 【真．大腦自覺：反向剝皮一層】 🎯 🎯 🎯
        # 使用 os.path.split，它會自動以『最後一根斜線』為界線，精準切成兩半！
        # 例子一: "eShade_Repository"     -> parent_path="",     target_name="eShade_Repository"
        # 例子二: "eShade_Repository/Abc" -> parent_path="eShade_Repository", target_name="Abc"
        parent_path, target_name = os.path.split(clean_path)

        root_uri = self.authAgent.get_drive_endpoint
        url = f"{root_uri}:/{parent_path}:/children" if parent_path else f"{root_uri}/children"

        # 2. 寄信請微軟把最外層所有的箱子清單（JSON 大禮包）吐回來
        response = self.send_http_request("GET", url, timeout=10)
        if response is None:
            return ""

        items = response.json().get("value", [])

        # 3. 🔍 【純物理比對】：在清單裡尋找有沒有哪一個箱子的名字，正好對齊我們要的文字！
        for item in items:
            if "folder" in item and item.get("name") == target_name:
                self.logger.debug(f"📁 [盤點成功] 找到資料夾【{target_name}】，其中實體 ID 身分證為: {item.get('id')}")
                return item.get("id")  # 🎯 查明真相！大方回傳這串英文加數字的唯一 ID 亂碼！

        self.logger.error(f"❌ [盤點失敗] 在雲端最外層找不到名為【{target_name}】的資料夾！")
        return ""

    def get_item_metadata_by_id(self, item_id: str) -> dict:
        """
        【基礎建設盤點能力】
        職責：盲目地拿著 file_id 去向微軟倉庫查明真身，把洗乾淨的特徵字典奉還給外界。
        """
        # 🎯 語意高雅對齊：命令工廠幫我做一條只看【名字、體積、家長特徵】的精簡 OData 網址！
        url = self.urlBuilder.build_item_meta_url(
            item_id=item_id,
            fields=["name", "id", "size", "file", "folder", "deleted","parentReference"]  # 🔒
        )

        self.logger.debug(f"🔍 [總海關盤點] 正在用身分證直接空降調閱檔案特徵...")
        self.logger.debug(f"📡 實體發射網址: {url}")

        # 🚀 出兵！自動享受 15 秒超時與斷線自動退讓重試 3 次的最高保護！
        response = self.send_http_request("GET", url, timeout=15)
        if response is None:
            return {}

        # 帶回洗得乾乾淨淨、香噴噴的特徵字典大禮包
        return response.json()

    def download(self, remote_file_path: str, local_dest_path: str) -> str:
        """下載影像"""
        url = self.urlBuilder.build_item_download_url(remote_file_path)
        response = None
        try:
            response = self.send_http_request("GET", url, stream=True)

            if response is not None:
                try:
                    # 當未指定 local_dest_path, 自動由 response 中取得原來 file name
                    if not local_dest_path:
                        content_disposition = response.headers.get('Content-Disposition')
                        # 1. 建立一個空的 Message 物件並塞入 Header
                        msg = Message()
                        msg['Content-Disposition'] = content_disposition
                        # 2. 直接呼叫 get_filename()，Python 會自動幫你搞定所有解碼與優先權判斷！
                        local_dest_path = msg.get_filename()
                        self.logger.debug(f"download original file name = {local_dest_path}")
                    with open(local_dest_path, "wb") as f:
                        f.write(response.content)
                    return local_dest_path
                except Exception as e:
                    self.logger.error(f"Download file Error: {e}")


        except requests.exceptions.Timeout:
            print("🚨 網路超時了！微軟伺服器可能太忙，先不要死當，下一輪再試。")
        except requests.exceptions.HTTPError:
            print("🚨 微軟 API 報錯（例如 404 找不到檔案）。")
        except OSError:
            print("🚨 本地硬碟爆滿或權限不足，無法寫入檔案！")

        return False

    def upload(self, local_file_path: str, remote_dest_path: str) -> str:
        """上傳影像"""
        url = self.urlBuilder.build_children_url(remote_dest_path)
        try:
            with open(local_file_path, "rb") as f:
                file_data = f.read()
            response = self.send_http_request("PUT", url, data=file_data)
            uploaded_file_id = ''
            if response:
                # 2. 🎯 一秒刨出新誕生檔案的真身 ID！
                res_json = response.json()
                uploaded_file_id = res_json.get("id", "")
                uploaded_file_sha1 = res_json.get("file", {}).get("hashes", {}).get("sha1Hash", "")

                # 3. 📝 物理級對帳日誌！這才是高品質、好交接代碼的品味！
                self.logger.debug(f"🎉 [任務特種兵] 成品交付全線大圓滿！")
                self.logger.debug(f"   - 雲端成品 ID : {uploaded_file_id}")
                self.logger.debug(f"   - 雲端物理指紋 : {uploaded_file_sha1}")

                # 未來如果要把這個成品 ID 寫進本地的資料庫、或者是丟給下一個微服務去發送 LINE 通知，
                # 手裡直接拿著這串身分證 ID，全系統在一微秒內就能空降對齊、絕對不漏單！ [1.1]

            self.logger.debug(f"✅ [機器人] 成功將資料推回雲端: id={uploaded_file_id}")
            return uploaded_file_id

        except Exception as e:
            self.logger.warning(f" {local_file_path} upload to {remote_dest_path} Failed due to Error {e}")
        return False

    def upload2FolderId(self, local_file_path: str, remote_folder_id: str, filename:str) -> str:
        """上傳影像"""
        url = self.urlBuilder.build_upload_by_folder_id_url(remote_folder_id, filename)
        self.logger.debug(f"✅ [upload2FolderId] 成功將資料推回雲端目錄id: {remote_folder_id} filename={filename}")
        try:
            with open(local_file_path, "rb") as f:
                file_data = f.read()
            response = self.send_http_request("PUT", url, data=file_data)
            uploaded_file_id = ''
            if response:
                # 2. 🎯 一秒刨出新誕生檔案的真身 ID！
                res_json = response.json()
                uploaded_file_id = res_json.get("id", "")
                uploaded_file_sha1 = res_json.get("file", {}).get("hashes", {}).get("sha1Hash", "")

                # 3. 📝 物理級對帳日誌！這才是高品質、好交接代碼的品味！
                self.logger.debug(f"🎉 [任務特種兵] 成品交付全線大圓滿！")
                self.logger.debug(f"   - 雲端成品 ID : {uploaded_file_id}")
                self.logger.debug(f"   - 雲端物理指紋 : {uploaded_file_sha1}")

                # 未來如果要把這個成品 ID 寫進本地的資料庫、或者是丟給下一個微服務去發送 LINE 通知，
                # 手裡直接拿著這串身分證 ID，全系統在一微秒內就能空降對齊、絕對不漏單！ [1.1]

            self.logger.debug(f"✅ [機器人] 成功將資料推回雲端: id={uploaded_file_id}")
            return uploaded_file_id

        except Exception as e:
            self.logger.warning(f" {local_file_path} upload to {remote_folder_id} Failed due to Error {e}")
        return False


    def list_dir_contents(self, remote_path: str = "") -> list:
        """
        公開方法：巡邏多層目錄。
        回傳的清單中，每一個項目都是一個標準的 DriveItem 物件，不再只是純文字！
        """
        url = self.urlBuilder.build_children_url(remote_endpoint=remote_path)
        response = self.send_http_request("GET", url)
        items=[]
        if response:
            items = response.json().get("value", [])

        return items

    def create_folder(self, parent_folder: str, new_folder_name: str) -> str:
        """
        【基礎建設造房能力】
        職責：前往雲端指定的父親路徑下建立一個新資料夾。
        回傳：成功後，微軟會核發這間新房間的『實體亂碼 ID 身分證』，雙手奉還給外界！
        """
        # 1. 🎯 語意高雅對齊：命令工廠幫我拼出對準父親肚子的網址
        url = self.urlBuilder.build_create_folder_url(parent_folder)

        # 2. 📦 【微軟官方鋼鐵規格】：必須帶有 "folder": {} 靈魂面具，微軟才知道你要建的是資料夾而不是檔案！
        payload = {
            "name": new_folder_name.strip(),
            "folder": {},  # 📁 告訴微軟：我是個目錄！
            # 🎯 🎯 🎯 【就是這行微軟官方黑科技！】 🎯 🎯 🎯
            # fail:   如果重名，微軟直接噴 409 報錯。
            # rename: 如果重名，微軟自動幫你改名叫 "result 1"。
            # replace:如果重名，微軟會自覺化身為『溫柔的捕手』。它不會重複建立！
            #         它會自動去把那個『已經存在的舊資料夾 ID』刨出來，在 Response 裡開開心心地回傳給你！
            "@microsoft.graph.conflictBehavior": "replace"
            #"@microsoft.graph.conflictBehavior": "rename"  # 🛡️ 防撞牆機制：萬一重名了，微軟自動幫你改名叫 "新名字 1" 防止系統死當！
        }

        self.logger.debug(f"🏗️ [總海關物流] 準備前往路徑【{parent_folder}】下建立新資料夾【{new_folder_name}】...")

        # 3. 🚀 發射 POST 請求！自動享受全系統最安全的『斷線自動退讓重試 3 次』鋼鐵防護網！
        response = self.send_http_request("POST", url, json=payload, timeout=15)

        if response is None:
            return ""

        # 4. 完美大收割！
        res_json = response.json()
        new_folder_id = res_json.get("id", "")

        self.logger.debug(f"📁 [建夾大成功] 雲端房間建造完畢！微軟核發的身分證 ID 為: {new_folder_id}")
        return new_folder_id  # 🎯 把這個 ID 傳回去，下一關的 upload 就能直接用 ID 空降定址！



