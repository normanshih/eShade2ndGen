import os
import platform
import subprocess

def get_ram_size_gb():
    """
    不需安裝額外套件，支援 macOS 與 Windows 的 RAM 大小偵測程式（單位：GB）
    """
    os_type = platform.system()

    try:
        # ---- macOS 環境 ----
        if os_type == "Darwin":
            # 呼叫 sysctl 取得記憶體 bytes
            output = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
            total_bytes = int(output)
            return round(total_bytes / (1024 ** 3), 2)

        # ---- Windows 環境 ----
        elif os_type == "Windows":
            # 呼叫 PowerShell 取得記憶體總和 bytes
            cmd = "powershell -Command \"(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum\""
            output = subprocess.check_output(cmd, shell=True).decode().strip()
            total_bytes = int(output)
            return round(total_bytes / (1024 ** 3), 2)

        else:
            print(f"不支援的作業系統: {os_type}")
            return 8        # 大膽假設 8是最低限制

    except Exception as e:
        print(f"偵測記憶體時發生錯誤: {e}")
        return None

if __name__ == "__main__":
    ram_size = get_ram_size_gb()
    if ram_size is not None:
        # 印出四捨五入後的整數或浮點數
        print(f"目前電腦的 RAM 大小為: {ram_size} GB")
