from collections import defaultdict
import datetime
import json
from pathlib import Path


class CustomerCaseStats:
    """單一客戶的案件狀態結構"""

    def __init__(self):
        self.ok_count = 0
        self.ng_count = 0
        self.ng_reasons = defaultdict(int)
        self.active_days_count = 0
        self.last_active_date = None
        self.avg_daily_cases = 0.0

    def record_active_day(self, current_date: datetime.date):
        date_str = (
            current_date.isoformat()
            if isinstance(current_date, datetime.date)
            else current_date
        )
        if self.last_active_date != date_str:
            self.active_days_count += 1
            self.last_active_date = date_str

    def to_dict(self):
        return {
            "ok_count": self.ok_count,
            "ng_count": self.ng_count,
            "ng_reasons": dict(self.ng_reasons),
            "active_days_count": self.active_days_count,
            "last_active_date": self.last_active_date,
            "avg_daily_cases": round(self.avg_daily_cases, 2),
        }

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls()
        obj.ok_count = data.get("ok_count", 0)
        obj.ng_count = data.get("ng_count", 0)
        obj.ng_reasons = defaultdict(int, data.get("ng_reasons", {}))
        obj.active_days_count = data.get("active_days_count", 0)
        obj.last_active_date = data.get("last_active_date")
        obj.avg_daily_cases = data.get("avg_daily_cases", 0.0)
        return obj


class CRMAccountTracker:
    """CRM 客戶案件動態統計器（功能完全體）"""

    def __init__(self):
        self.customers = defaultdict(CustomerCaseStats)

    def _get_today(self) -> datetime.date:
        return datetime.date.today()

    def log_success(self, customer_id: str):
        stats = self.customers[customer_id]
        stats.record_active_day(self._get_today())
        stats.ok_count += 1
        total_cases = stats.ok_count + stats.ng_count
        stats.avg_daily_cases += (
            total_cases - stats.avg_daily_cases
        ) / stats.active_days_count

    def log_failure(self, customer_id: str, reason: str = "未知錯誤"):
        stats = self.customers[customer_id]
        stats.record_active_day(self._get_today())
        stats.ng_count += 1
        stats.ng_reasons[reason] += 1
        total_cases = stats.ok_count + stats.ng_count
        stats.avg_daily_cases += (
            total_cases - stats.avg_daily_cases
        ) / stats.active_days_count

    # ==================== 📊 完美回歸：單一客戶綜合報告 ====================

    def get_customer_report(self, customer_id: str) -> dict:
        """獲取特定顧客的完整案件分析報告 (適合配合 pprint 使用)"""
        if customer_id not in self.customers:
            return {"error": f"找不到客戶 [{customer_id}] 的統計紀錄"}

        stats = self.customers[customer_id]
        total_cases = stats.ok_count + stats.ng_count
        success_rate = (
            (stats.ok_count / total_cases * 100) if total_cases > 0 else 0.0
        )

        return {
            "customer_id": customer_id,
            "總上傳案件數": total_cases,
            "成功件數_OK": stats.ok_count,
            "失敗件數_NG": stats.ng_count,
            "成功率": f"{round(success_rate, 2)}%",
            "每日平均用量_件": round(stats.avg_daily_cases, 2),
            "累計使用天數": stats.active_days_count,
            "NG原因分佈": dict(stats.ng_reasons),
        }

    # ==================== 💾 檔案儲存與讀取 ====================

    def save_to_json(self, file_path: str = "crm_stats.json"):
        output_data = {
            cid: stats.to_dict() for cid, stats in self.customers.items()
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            print(f"💾 統計資料已成功儲存至: {file_path}")
        except Exception as e:
            print(f"❌ 儲存檔案失敗: {e}")

    def load_from_json(self, file_path: str = "crm_stats.json"):
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️ 找不到 {file_path}，將以全新資料開始。")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                input_data = json.load(f)
            self.customers.clear()
            for cid, data in input_data.items():
                self.customers[cid] = CustomerCaseStats.from_dict(data)
            print(f"📂 已成功從 {file_path} 載入歷史數據！")
        except Exception as e:
            print(f"❌ 讀取檔案失敗: {e}")

    # ==================== 🧹 歷史數據清理 ====================

    def clear_stats(self, customer_id: str = None):
        if customer_id:
            if customer_id in self.customers:
                del self.customers[customer_id]
                print(f"🧹 已成功清理客戶 [{customer_id}] 的所有統計數據。")
            else:
                print(f"⚠️ 找不到客戶 [{customer_id}]，無需清理。")
        else:
            self.customers.clear()
            print("🧹 已成功清空【全系統】所有客戶的統計數據。")

class CRM_Statistics_Agent:
    def __init__(self):
        self.crmStatistics = CRMAccountTracker()
        self.startDate = None


if __name__ == "__main__":
    import pprint

    # 1. 初始化並模擬一些客戶數據
    tracker = CRMAccountTracker()
    tracker.log_success("cust_A")
    tracker.log_failure("cust_A", reason="格式不支援")
    tracker.log_success("cust_B")

    # ---- 查詢客戶報表 ----
    print("===== 📊 CRM 客戶綜合案件分析報告 =====")
    pprint.pprint(tracker.get_customer_report("cust_A"))

    # 2. 儲存成檔案
    tracker.save_to_json("my_crm_report.json")

    # 3. 清理測試：只刪除 cust_A
    tracker.clear_stats(customer_id="cust_A")
    print("目前記憶體中的客戶:", list(tracker.customers.keys()))  # 應該只剩 B

    # 4. 全系統徹底清空
    tracker.clear_stats()
    print("目前記憶體中的客戶:", list(tracker.customers.keys()))  # 變空空如也

    # 5. 重新從檔案載入，復活所有數據
    tracker.load_from_json("my_crm_report.json")
    print("復活後的客戶:", list(tracker.customers.keys()))  # A 和 B 都回來了
