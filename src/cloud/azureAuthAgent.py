from abc import ABC, abstractmethod
from msal import ConfidentialClientApplication, SerializableTokenCache, PublicClientApplication     # pip install msal
import os
import logging

class AzureAuthAgent(ABC):
    """【認證管家合約】必須同時管理該模式的『認證行為』與『大門口地址』"""
    GRAPH_API_BASE_URI = f"https://graph.microsoft.com/v1.0"
    AUTHORITY_URL = "https://login.microsoftonline.com"

    @property
    @abstractmethod
    def get_access_token(self) -> str:
        """負責去跟微軟要鑰匙"""
        pass

    @abstractmethod
    def get_drive_endpoint(self) -> str:
        """負責決定大門口是 /me 還是 /users/{id}"""
        pass


class Mode3UserAuthAgent(AzureAuthAgent):
    """【模式 3 管家】
    使用 service (user) account
    """
    SCOPES = ["Files.ReadWrite.All"]

    def __init__(self, client_id, tenant_id, user_email, cache_path=""):
        self.logger = logging.getLogger("eShade.Mode3AzureAuthenticator")

        self._user_email = user_email
        self._cache_path = cache_path
        self._client_id = client_id
        self._tenant_id = tenant_id
        self._user_email = user_email.lower().strip()

        # 🎯 模式 3 標準的雲端起點：走 me 置物櫃路線
        self._endpoint_prefix = f"{self.GRAPH_API_BASE_URI}/me/drive/root"
        self._scopes = Mode3UserAuthAgent.SCOPES
        self._authority_url = f"{self.AUTHORITY_URL}/{self._tenant_id}"

        # 🧠 【大腦永續化第一步】在記憶體中建立大腦快取物件
        self._cache = SerializableTokenCache()

        # 💾 【大腦永續化第二步】如果硬碟有上一次的記憶檔案，立刻灌注靈魂（繼承登入狀態）
        self._load_cache_from_disk()

        # 🏢 【大腦永續化第三步】誕生公開客戶端應用程式（模式 3 專用類別，並把大腦快取塞給它）
        self._app = PublicClientApplication(
            client_id=self._client_id,
            authority=self._authority_url,
            token_cache=self._cache
        )

    def _load_cache_from_disk(self) -> None:
        """私有輔助兵：負責從硬碟撈取歷史記憶"""
        if os.path.exists(self._cache_path):
            try:
                with open(self._cache_path, "r") as f:
                    self._cache.deserialize(f.read())
                print(f"💾 [管家3] 成功從硬碟載入記憶檔案 ({self._cache_path})！")
            except Exception as e:
                print(f"⚠️ [管家3] 讀取快取檔案失敗，將建立乾淨記憶: {e}")

    def _save_cache_to_disk(self) -> None:
        """如果快取狀態改變（背景自動續命成功），自動將大腦記憶封存回硬碟"""
        if self._cache.has_state_changed:
            try:
                with open(self._cache_path, "w") as f:
                    f.write(self._cache.serialize())
                print(f"💾 [管家3] 偵測到 Token 背景更新，已自動同步回硬碟檔案 ({self._cache_path})。")
            except Exception as e:
                print(f"❌ [管家3] 無法將快取大腦寫回硬碟: {e}")


    # =========================================================================
    # 接下來，我們要去實現合約要求的兩個公開屬性 (get_drive_endpoint 與 access_token)
    # =========================================================================

    @property
    def get_drive_endpoint(self) -> str:
        """履行合約：大方交出模式 3 專屬的 /me 路線大門口"""
        return self._endpoint_prefix

    @property
    def get_access_token(self):
        # 執行模式 3 的 Cache 續命與人類網頁互動
        """【看門狗屬性】履行合約：動態確保拿到新鮮 Token，徹底消滅強迫症彈出視窗"""
        # 1. 轉頭去大腦快取裡指認有沒有上一次登入成功的『熟面孔帳號』
        accounts = self._app.get_accounts()

        if accounts:
            chosen_account = accounts[0]
            username = chosen_account.get("username", "未知帳號")
            self.logger.debug(f"🔄 [管家3] 偵測到歷史紀錄: {username}，正在嘗試背景無感登入...")

            # 🎯 核心防線：嘗試在背景用 Refresh Token 默默續命（100% 完全不跳網頁）
            result = self._app.acquire_token_silent(self._scopes, account=chosen_account)

            if result and "access_token" in result:
                self._save_cache_to_disk()  # 檢查大腦是否需要同步回硬碟
                return result["access_token"]

        # 🚨 2. 只有當硬碟沒檔案（第一天在新電腦部署），才逼不得已跳一次網頁視窗
        print("🚨 [管家3] 快取大腦空空如也，必須進行第一次人工選擇帳號與手機驗證...")
        result = self._app.acquire_token_interactive(self._scopes, port=8080)

        if "access_token" in result:
            self._save_cache_to_disk()  # 第一次人工成功，立刻把記憶寫入硬碟，換取未來的無人值守！
            return result["access_token"]

        raise RuntimeError(f"❌ [管家3] 認證失敗: {result.get('error_description')}")

class Mode4RobotAuthAgent(AzureAuthAgent):
    """【模式 4 管家】
    自動機器人
    """
    SCOPES = ['https://graph.microsoft.com/.default']

    def __init__(self, client_id, tenant_id, client_secret, user_email):
        self._user_email = user_email
        # 這裡面初始化 ConfidentialClientApplication (機器人) ...

        self._authority_url = f'{self.AUTHORITY_URL}/{tenant_id}'
        # 🤖 誕生模式 4 的無人值守機器人主體 (Confidential)
        self._app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self._authority_url
        )

    @property
    def get_access_token(self):
        # 執行模式 4 的背景 Client Secret 密碼換領
        # 💡 關鍵修正：呼叫模式 4 專用的 acquire_token_for_client 函式！
        # MSAL 內部會自動判斷：記憶體內的 Token 沒過期就直接用；過期了就在背景拿 Secret 去換新，完全無感。
        result = self._app.acquire_token_for_client(scopes=Mode4RobotAuthAgent.SCOPES)

        if result and "access_token" in result:
            return result["access_token"]

        raise RuntimeError(f"❌ [OneDrive] 機器人背景認證失敗！原因: {result.get('error_description')}")

    @property
    def get_drive_endpoint(self)->str:
        # 🎯 模式 4 專屬大門口：世界上沒有 me，精準空降 Email
        return f"{self.GRAPH_API_BASE_URI}/users/{self._user_email}/drive/root"

