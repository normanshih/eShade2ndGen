from utils.jsonConfig_model import JsonConfigurer


class RGB2RGB_Configurer(JsonConfigurer):
    """RGB2RGB.exe configuration interface"""

    def __init__(self, execute_setup: str):
        #self.config_file_path = Path(execute_setup)
        super().__init__(execute_setup)

    # ==========================================
    # 絕學一：⚡ Property & Setter (單發快擊)
    # ==========================================
    @property
    def color_patch_filepath(self) -> str:
        return self._read_from_disk().SRs_sequential_patches_path

    @property
    def input_video_path(self)->str:
        return self._read_from_disk().casesDirPath


    @color_patch_filepath.setter
    def color_patch_filepath(self, value: str):
        config = self._read_from_disk()
        config.color_patch_filepath = str(value)
        self._write_to_disk(config)

    @input_video_path.setter
    def input_video_path(self, value: str):
        config = self._read_from_disk()
        config.casesDirPath = str(value)
        self._write_to_disk(config)


if __name__ == "__main__":
    # 綁定實體應用程式目錄
    config = RGB2RGB_Configurer("Exec/execute_setup.json")

    # --- 情況 A：今天只想快速改一個小地方，用 Setter 閃擊 ---
    input_video_path = config.input_video_path
    print(f'input_video_path={input_video_path}')

    config.input_video_path = "a/a/a"
    # 這一行等號，直接觸發：讀 -> 改成 16 -> 寫，一氣呵成！

