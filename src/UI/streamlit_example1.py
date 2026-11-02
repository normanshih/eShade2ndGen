import threading
import time
import streamlit as st

st.title("單一 Process 系統主控台")


# 1. 這是你原本的系統核心程式 (現在變成一個 Function)
def my_original_system():
    print("🚀 核心系統在背景執行緒啟動了！")
    while True:
        # 直接讀取 Streamlit 秘密帳本裡的設定（超級即時！）
        is_running = st.session_state.get("sys_run", True)
        delay = st.session_state.get("sys_delay", 2)

        if is_running:
            print(f"[背景執行] 正在處理您的業務邏輯... 延遲：{delay}秒")
        else:
            print("[背景執行] 暫停中...")

        time.sleep(delay)


# 2. 核心魔法：用帳本保護，確保你的系統程式「只會被啟動一次」
# 絕對不能讓 Streamlit 的 Forever Loop 每重刷一次就幫你啟動一個新系統
if "system_thread_started" not in st.session_state:
    # 把你的系統丟進背景執行緒
    t = threading.Thread(target=my_original_system, daemon=True)
    t.start()
    st.session_state.system_thread_started = True

# 3. 網頁 UI 控制介面
st.subheader("⚙️ 控制面板")
# 注意：這裡的 key="sys_run" 會讓 Streamlit 自動把開關狀態存入 st.session_state["sys_run"]
st.toggle("啟用系統", key="sys_run", value=True)
st.slider("調整延遲", 1, 10, key="sys_delay", value=2)
