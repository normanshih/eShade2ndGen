import json
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager


class JsonConfigurer:
    """頂級架構：同時完美整合 With 機制與 Property/Setter 的實體配置器"""

    def __init__(self, config_filepath: str, base_path:str=""):
        base = Path(base_path)
        self.config_file_path = (base / config_filepath).resolve()

    # ==========================================
    # 🛠️ 核心底層工具（私有方法，不對外暴露）
    # ==========================================
    def _read_from_disk(self) -> SimpleNamespace:
        """專職從硬碟搬運 JSON 並升級為點 . 存取盒子"""
        json_str = self.config_file_path.read_text(encoding="utf-8")
        return json.loads(json_str, object_hook=lambda d: SimpleNamespace(**d))

    def _write_to_disk(self, config_obj: SimpleNamespace):
        """專職將點 . 存取盒子變回 JSON 覆寫回硬碟"""
        dict_data = vars(config_obj)
        with open(self.config_file_path, "w", encoding="utf-8") as f:
            json.dump(dict_data, f, indent=4)

    # ==========================================
    # 絕學二：📦 With 脈絡管理器 (多發連擊)
    # ==========================================
    @contextmanager
    def open_config(self):
        """當需要一口氣修改大量欄位時使用"""
        config = self._read_from_disk()  # 1. 只讀一次
        yield config  # 2. 交給你盡情修改
        self._write_to_disk(config)  # 3. 結束時只寫一次


if __name__ == "__main__":
    # 綁定實體應用程式目錄
    app_manager = JsonConfigurer("../../Exec/execute_setup.json")

    # --- 情況 A：今天只想快速改一個小地方，用 Setter 閃擊 ---
    app_manager.threads = 16
    # 這一行等號，直接觸發：讀 -> 改成 16 -> 寫，一氣呵成！

    # --- 情況 B：今天要把整個設定大換血，用 With 陣列轟炸 ---
    with app_manager.open_config() as config:
        # 在這裡，所有的修改都只發生在記憶體中，效能極高
        print(f"model = {config.model}")
        config.model = 1
        config.debug_mode = False
        config.last_processor = "MacSimulator"
        config.max_retry = 3
    # 門關上的瞬間，底層才會將這 4 個修改一口氣「合併一次寫入」硬碟！