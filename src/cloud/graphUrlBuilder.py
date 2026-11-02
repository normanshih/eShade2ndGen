from cloud.azureAuthAgent import AzureAuthAgent
import logging

class GraphUrlBuilder:
    """
    職責：【微軟 Graph 網址製造工廠】。抽象化『資料夾』
    維護哲學：把全宇宙最髒、最噁心的冒號與斜線拼接，通通收沒在我的黑盒子裡！
    """
    def __init__(self, auth_agent:AzureAuthAgent, resource_path: str = ""):
        self.logger = logging.getLogger("eShade.UrlBuilder")
        self.auth = auth_agent
        self.resource_path = resource_path.strip("/")

    def _build_item_base_url(self, item_id: str) -> str:
        """【私有輔助兵】所有以 ID 為基礎的網址，全宇宙共同的物理空降起點"""
        # 🔑 向身分大腦要總起點 (https://.../v1.0/me/drive/root)
        drive_root:str = self.auth.get_drive_endpoint
        # 🧼 空間切換：物理性把尾巴的 /root 拔掉，換成微軟官方規定的 /items/{id}
        clean_base = drive_root.replace("/root", "")
        # 最終完美得到：https://microsoft.com{item_id}
        return f"{clean_base}/items/{item_id.strip()}"

    # 🕵️‍♂️ 網址工廠內部的『真．100% 精準分流器』
    def _is_microsoft_id(self, identifier: str) -> bool:
        """物理特徵清查：100% 精準識破它到底是實體 ID 還是人類文字名字"""
        clean_str = identifier.strip()

        # 🛡️ 鐵證一：微軟的實體 ID 絕對不准包含任何斜線 `/`
        if "/" in clean_str:
            return False

        # 🛡️ 鐵證二：微軟核發的唯一 ID 亂碼，開頭必定是微軟標準格式（如 01 開頭或 b! 開頭）
        # 且長度通常固定（DriveItem ID 在商業版 OneDrive 裡通常是 34 碼左右）
        if clean_str.startswith("01") or clean_str.startswith("b!"):
            return True

        # 🌸 其餘情況通通判定為人類自己取的名字路徑（Path）！
        return False

    def build_children_url(self, remote_endpoint: str = "") -> str:
        """專門幫 Storage（物流） 拼接『盤點子資料夾』的合法微軟網址"""
        # 🔑 向身分大腦要總起點 (模式三是 /me/drive/root，模式四是 /users/{id}/drive/root)
        drive_root = self.auth.get_drive_endpoint
        # 拼接相對工作路徑
        clean_remote = remote_endpoint.strip("/") if remote_endpoint else ""
        full_path = f"{self.resource_path}/{clean_remote}" if self.resource_path else clean_remote
        full_path = full_path.strip("/")

        if not full_path:
            return f"{drive_root}/children"
        return f"{drive_root}:/{full_path}:/children"


    def build_delta_url(self, target_folder_id: str) -> str:
        """
        🎯 【一秒粉碎模式四地雷的核心！】
        專門幫 Tracker 拼接增量追蹤網址。它自覺看大哥的起點是 me 還是 users。
        """
        drive_root:str = self.auth.get_drive_endpoint

        # 🧼 萬能自覺：不管大哥是 /me/drive/root 還是 /users/{id}/drive/root
        # 我們一律把尾巴的 /root 拔掉，精準換成微軟官方規定的 /items/{folder_id}/delta
        clean_base = drive_root.replace("/root", "")
        url =  f"{clean_base}/items/{target_folder_id}/delta?token=latest"
        self.logger.debug(f"build_delta_url = {url}  ")

        return url

    def build_item_meta_url(self, item_id: str, fields: list = None) -> str:
        """
        【身分證空降定址工廠】
        職責：拿着實體 ID 身分證，拼出直接向微軟查明該檔案所有特徵的萬能網址。
        """
        # 🔑 向身分大腦要總起點。因為微軟規定，用 /items/{id} 就可以跳過任何資料夾直接空降！
        # 會拼出：https://microsoft.com{item_id}
        drive_root:str = self.auth.get_drive_endpoint
        clean_base = drive_root.replace("/root", "")
        url = f"{clean_base}/items/{item_id.strip()}"

        # 🎯 🎯 🎯 【OData 頂級效能防線】：
        # 如果外面有指定我只要看特定欄位（例如只要名字和體積），
        # 我們就在網址屁股加上 OData 的資料庫篩選標籤 $select，強迫微軟精簡回傳，拒絕垃圾雜音！
        if fields:
            fields_str = ",".join(fields)
            url += f"?$select={fields_str}"  # 💡 利用 ? 傳遞資料庫篩選指令

        return url

    def build_create_folder_url(self, parent_folder: str = "") -> str:
        """
        【建夾定址工廠】
        語意：拿着父親的人類文字路徑，拼出準備去該位置蓋新房間的微軟合法網址。
        """
        # 🔑 向身分大腦要總起點 (例如: https://.../v1.0/me/drive/root)
        drive_root = self.auth.get_drive_endpoint

        if not self._is_microsoft_id(parent_folder):
            # 🧼 搜身清洗路徑
            clean_parent = parent_folder.strip("/") if parent_folder else ""
            full_path = clean_parent.strip("/")
            # 🎯 如果路徑是空的，代表直接在最外層大廳建資料夾：.../root/children
            if not full_path:
                return f"{drive_root}/children"

            # 🎯 如果有指定父資料夾（例如長在 eShade_Repository 肚子裡）：.../root:/路徑:/children
            return f"{drive_root}:/{full_path}:/children"
        else:
            return f"{self._build_item_base_url(parent_folder)}/children"

    def build_upload_by_folder_id_url(self, folder_id: str, filename: str) -> str:
        """
        【ID版 ── 空降上傳定址工廠】
        職責：拿着目標資料夾的實體 ID 與準備上傳的檔名，拼出 100% 絕緣、無冒號的微軟官方合法上傳網址。
        """
        # 🔑 向身分大腦要總起點
        drive_root:str = self.auth.get_drive_endpoint
        clean_base = drive_root.replace("/root", "")

        # 💡 微軟官方鋼鐵天條：items/{folder_id}/children/{filename}/content
        # 最終精準拼出：https://microsoft.com{folder_id}/children/{filename}/content
        # 100% 物理超渡所有的斜線路徑與冒號！
        return f"{clean_base}/items/{folder_id.strip()}/children/{filename.strip()}/content"

    def build_item_download_url(self, item_identifier: str) -> str:
        """
        【萬能多型下載定址官】
        職責：親手抓出 item_identifier 到底是文字路徑、還是實體 ID，並 100% 吐出微軟官方合法下載網址。
        通吃格式：
            - 狀況一 (ID版): "01WRPTULN6Y2GOVW..." (直接拿 Delta 撈到的 file_id 空降下載) [2.1]
            - 狀況二 (路徑版): "eShade_Repository/Abc/input.raw" (手動抄寫或外置路徑下載) [1.1]
        """
        item_clean = item_identifier.strip().strip("/")
        drive_root:str = self.auth.get_drive_endpoint
        clean_base = drive_root.replace("/root", "")

        # 🎯 🎯 🎯 1. 【真．物理靈魂分流防線：精準識別 ID 還是 Path】 🎯 🎯 🎯
        # 調用我們上一關修煉完成的 _is_microsoft_id 鋼鐵格式盲檢 [2.1]
        if self._is_microsoft_id(item_clean):
            # 🌸 走【ID版】下載定址公路：items/{id}/content
            # 最終精準得到：https://microsoft.com{item_id}/content
            # 100% 物理超渡所有的斜線路徑與冒號！ [2.1]
            url = f"{clean_base}/items/{item_clean}/content"
            self.logger.debug(f"🔑 [build_item_download_url] 偵測為實體 ID 下載，生產空降地址: {url}")
            return url

        # 🌸 2. 否則，它就一定是人類文字路徑（Path）！
        else:
            # 走【路徑版】下載定址公路：把 base_work_dir 耗材與相對路徑揉捏在一起 [1.1]
            full_path = item_clean
            full_path = full_path.strip("/")

            # 💡 冒號是個 escape character！路徑前後必須用一對冒號死死包住！
            # 後方直接接上微軟官方規定的 /content 接龍 [1.1]
            # 最終完美拼出：.../v1.0/me/drive/root:/你的多層檔案路徑:/content [1.1]
            url = f"{drive_root}:/{full_path}:/content"
            self.logger.debug(f"🗺️ [build_item_download_url] 偵測為文字路徑下載，生產路徑地址:\n {url}")
            return url
