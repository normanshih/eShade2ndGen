from abc import ABC, abstractmethod
from utils.mail import MAIL_SERVER, MailMessage

# ====== 實現層：底層的通訊管道 (Implementor) ======
class CommunicationChannel(ABC):
    @abstractmethod
    def output(self, message):
        pass

class SMSChannel(CommunicationChannel):
    def output(self, message):
        print(f"[SMS] 傳送簡訊: {message}")

class EmailChannel(CommunicationChannel):
    def __init__(self, mailServer:MAIL_SERVER):
        self.mailServer = mailServer


    def output(self, message: MailMessage):
        print(f"[Email] 傳送郵件: {message}")
        self.mailServer.send(message)


# ====== 抽象層：高層的發送介面 (Abstraction) ======
# 任務基底類別：在這裡持有 Bridge 管道
class MessageTask(ABC):
    def __init__(self, channel: CommunicationChannel):
        self._channel = channel  # 這就是橋樑接頭

    @abstractmethod
    def run(self, message: str) -> None:
        pass


# 任務 A：最普通、單純的發送任務
class SimpleSendTask(MessageTask):
    def run(self, message: str) -> None:
        # 直接交給底層管道輸出
        self._channel.output(message)


# 任務 B：進階任務，發送前與發送後要自動記錄 Log
class LoggedSendTask(MessageTask):
    def run(self, message: str) -> None:
        print(f"[Log] ── 準備發送，時間: {time.time():.2f}")

        # 呼叫相同的底層管道
        self._channel.output(message)

        print(f"[Log] ── 發送完成 ──")


if __name__ == "__main__":
    # 準備好底層管道（同一個 Bridge）
    sms = SMSChannel()
    email = EmailChannel()

    print("--- 情境一：一般任務使用 SMS ---")
    task1 = SimpleSendTask(channel=sms)
    task1.run("您好，這是您的認證碼。")

    print("\n--- 情境二：Log 任務使用同一個 SMS 管道 ---")
    task2 = LoggedSendTask(channel=sms)
    task2.run("您的帳號有新的登入活動。")

    print("\n--- 情境三：Log 任務切換到 Email 管道 ---")
    task3 = LoggedSendTask(channel=email)
    task3.run("當月電子帳單已產生。")
