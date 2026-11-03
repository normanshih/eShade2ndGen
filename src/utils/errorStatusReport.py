import string
from pathlib import Path

from dataclasses import dataclass
from typing import TypeVar, Generic, Optional, Any, Callable



# 定義泛型 T，代表成功時回傳的資料型態（例如 bytes, str, dict 等）
T = TypeVar('T')

@dataclass(frozen=True) # frozen=True 讓物件唯讀且不可變，安全又防呆
class Result(Generic[T]):
    is_success: bool
    _value: Optional[T] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    exception: Optional[Exception] = None  # 可選：保留原始的 Exception 堆疊供 Debug 追蹤

    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """快速建立成功結果的工廠方法"""
        return cls(is_success=True, _value=value)

    @classmethod
    def fail(cls, error_code: str, error_message: str, exception: Optional[Exception] = None) -> 'Result[Any]':
        """快速建立失敗結果的工廠方法"""
        return cls(is_success=False, error_code=error_code, error_message=error_message, exception=exception)

    @property
    def value(self) -> T:
        """取得數值，如果失敗則拋出異常（安全防禦機制）"""
        if not self.is_success:
            raise ValueError(f"無法取得數值：目前的 Result 是失敗狀態 ({self.error_code}: {self.error_message})")
        return self._value  # type: ignore

    def unwrap_or(self, default: T) -> T:
        """如果成功就回傳數值，失敗則回傳你指定的預設值（極好用！）"""
        return self._value if self.is_success else default

    def __bool__(self) -> bool:
        """讓物件可以直接用在 if 判斷式中，如：if result:"""
        return self.is_success





def report_error_via_filename(original_file, error_reason, output_dir=None):
    """利用產生空檔案的「檔名」來回報錯誤原因。

    :param original_file: 發生錯誤的原始檔案路徑 (例如: 'photo.NEF')
    :param error_reason: 錯誤原因字串 (例如: 'Unsupported File Format')
    :param output_dir: 錯誤標記檔要存放的資料夾，若為 None 則放在原檔案同目錄
    """
    orig_path = Path(original_file)

    # 1. 清洗錯誤字串：檔名不能包含特殊字元（如 / \ : * ? " < > |）
    # 我們把空格和不合法字元換成底線 "_"
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    clean_reason = "".join(
        c if c in valid_chars or c.isalnum() else "_" for c in error_reason
    )
    print(f"clean_reason = {clean_reason}")
    clean_reason = clean_reason.replace(" ", "_")


    # 2. 決定輸出目錄
    target_dir = Path(output_dir) if output_dir else orig_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # 3. 組合新檔名：[原檔名].[原副檔名].ERROR_[錯誤原因].txt
    error_filename = f"{orig_path.name}.ERROR_{clean_reason}.txt"
    error_file_path = target_dir / error_filename

    # 4. 產生空檔案 (exist_ok=True 代表若檔案已存在也不會報錯)
    error_file_path.touch(exist_ok=True)
    print(f"⚠️ 已建立錯誤標記檔: {error_file_path.name}")
    return error_file_path


from pathlib import Path
if __name__ == "__main__":

    class RawConverter:
        # 宣告回傳型態為 Result[bytes]，代表成功時裡面裝的是 bytes (影像 Buffer)
        def convert_to_jpg(self, raw_filepath: str) -> Result[bytes]:
            try:
                # 模擬檢查格式
                if not raw_filepath.endswith(('.raw', '.cr2', '.dng')):
                    return Result.fail(
                        error_code="UNSUPPORTED_FORMAT",
                        error_message=f"不支援的格式：{raw_filepath}"
                    )

                # 模擬轉換邏輯
                # with open(raw_filepath, 'rb') as f: ...
                img_buffer = b"fake_jpg_buffer_data"

                return Result.success(img_buffer)

            except Exception as e:
                # 如果底層套件（如 OpenCV 或 LibRaw）大崩潰，把 exception 一併打包，但不對外 raise
                return Result.fail(
                    error_code="CONVERSION_FAILED",
                    error_message=f"轉換過程中發生未預期錯誤: {str(e)}",
                    exception=e
                )


    '''------ Test App ------'''
    converter = RawConverter()
    #result = converter.convert_to_jpg("photo.raw")
    result = converter.convert_to_jpg("photo.xyz")

    # 1. 最直覺的 if 判斷（因為我們寫了 __bool__，可以直接當布林值用）
    if result:
        jpg_data = result.value
        print(f"🎉 轉換成功！拿到 Buffer 長度: {len(jpg_data)}")
    else:
        # 2. 失敗時，你可以根據 error_code 決定要怎麼處理
        print(f"❌ 錯誤代碼: {result.error_code}")
        print(f"📝 錯誤原因: {result.error_message}")

        # 3. 只有在真正嚴重的系統錯誤時，才去撈 result.exception 寫進你的 logger
        if result.error_code == "CONVERSION_FAILED":
            # 這裡可以用之前提過的 exc_info=True 來記錄完整的 Exception 堆疊
            print(f"🚨 發現系統級崩潰，準備上報。原始錯誤：{result.exception}")

    # 4. 超方便的一行倒帶防禦寫法（如果失敗就用一張空圖片 Buffer 頂替）
    safe_buffer = result.unwrap_or(b"empty_fallback_image_data")

    '''
    original_file = f"image.xyz"
    error_reason = "Can Not find card"

    result = report_error_via_filename(original_file, error_reason, output_dir=None)

    path = Path(result)


    print(f"result = {result}")
    print(f"path = {path}")
    print(f"path.name = {path.name}")
    '''