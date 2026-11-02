### NOT run by python, but streamlit run webIF.py

import json
import os
import pandas as pd
import streamlit as st

# 定義共享檔案的路徑（確保兩個 Process 讀寫同一個檔案）
CONFIG_FILE = "config.json"
STATS_FILE = "business_stats.json"  # 模擬核心程式輸出的統計數據
LOG_FILE = "system.log"  # 模擬核心程式輸出的日誌

st.set_page_config(page_title="系統獨立主控台", layout="wide")     # 必須是除了 import 之外，整份檔案的第一行 Streamlit 程式碼，否則程式會報錯。
st.title("🖥️ 系統獨立主控台 (Process B)")


# =====================================================================
# 功能一：控制端 - 讀寫設定檔 (Config)
# =====================================================================
st.header("⚙️ 系統參數設定")

# 1. 初始化或讀取現有的設定檔
if not os.path.exists(CONFIG_FILE):
    # 預設值
    current_config = {"is_running": True, "scan_interval": 5, "max_retry": 3}
    with open(CONFIG_FILE, "w") as f:
        json.dump(current_config, f, indent=4)
else:
    with open(CONFIG_FILE, "r") as f:
        current_config = json.load(f)

# 2. 在網頁上渲染 UI 元件（並帶入現有設定值）
col1, col2, col3 = st.columns(3)
with col1:
    ui_run = st.toggle("啟動核心業務", value=current_config.get("is_running", True))
with col2:
    ui_interval = st.slider(
        "掃描間隔 (秒)", 1, 60, value=current_config.get("scan_interval", 5)
    )
with col3:
    ui_retry = st.number_input(
        "最大重試次數", 1, 10, value=current_config.get("max_retry", 3)
    )

# 3. 按鈕觸發：寫入覆蓋設定檔
if st.button("💾 儲存並即時套用新設定", type="primary"):
    new_config = {
        "is_running": ui_run,
        "scan_interval": ui_interval,
        "max_retry": ui_retry,
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(new_config, f, indent=4)
    st.success("設定檔已成功更新！核心程式將在下次輪詢時讀取新參數。")


st.divider()

# =====================================================================
# 功能二：監控端 - 讀取業務統計與 LOG
# =====================================================================
st.header("📊 核心程式運行狀態監控")

# 透過 Streamlit 的兩欄式佈局，左邊放統計數據，右邊放最新日誌
mon_col1, mon_col2 = st.columns([1, 1])

with mon_col1:
    st.subheader("📈 業務統計數據")
    # 模擬讀取核心程式定時輸出的統計 JSON
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            stats_data = json.load(f)
        # 用 Streamlit 內建的精美卡片顯示
        st.metric(label="今日處理總量", value=stats_data.get("total_processed", 0))
        st.metric(
            label="成功率",
            value=f"{stats_data.get('success_rate', 0)}%",
            delta=f"{stats_data.get('hourly_growth', 0)}% (每小時)",
        )
    else:
        st.warning("尚未偵測到統計數據檔案，等待核心程式寫入...")

with mon_col2:
    st.subheader("📋 最新系統日誌 (Last 10 lines)")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 只抓最後 10 行日誌
            last_logs = "".join(lines[-10:])
        # 用程式碼區塊或純文字框漂亮地呈現日誌
        st.code(last_logs, language="text")
    else:
        st.info("暫無日誌記錄。")

# 加一個手動重刷頁面的按鈕，用來觀看最新狀態
if st.button("🔄 重新整理監控數據"):
    st.rerun()
