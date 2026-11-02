import os
import smtplib
import datetime
import socket

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

class MailMessage:
    def __init__(self, to_address, subject, sender=''):
        self.mail = MIMEMultipart()  #建立MIMEMultipart物件
        self.mail["To"] = to_address
        self.mail["Subject"] = subject
        self.mail["From"] = sender

    def content(self, body):
        msg_content = MIMEText(body, 'plain', 'utf-8')
        self.mail.attach(msg_content)


    def attach(self, filepath:str)->bool:
        if not os.path.exists(filepath):
            print(f"警告: 找不到附件檔案 {filepath}，已跳過。")
            return False
        file_name = os.path.basename(filepath)

        try:
            # 以二進位讀取檔案
            with open(filepath, "rb") as attachment:
                # 建立附件物件
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            # 將檔案編碼為 Base64
            encoders.encode_base64(part)

            # 加入標頭資訊（解決中文檔名可能亂碼的問題）
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={file_name}",
            )
            self.mail.attach(part)
        except Exception as e:
            print(f"attach: Exception {e} ")

class MAIL_SERVER:
    def __init__(self, login, password, host = "smtp.gmail.com", port="587"):
        self.login = login
        self.password = password
        self.host = host
        self.port = port
        #self.server = smtplib.SMTP(host=self.host, port=self.port)

    def send(self, letter:MailMessage):
        status = True
        with smtplib.SMTP(host=self.host, port=self.port) as smtp:  # 設定SMTP伺服器
            try:
                smtp.ehlo()  # 驗證SMTP伺服器
                smtp.starttls()  # 建立加密傳輸
                smtp.login(self.login, self.password)  # 登入寄件者gmail
                if letter.mail["From"] == '':
                    letter.mail["From"] = self.login
                # 將收件人轉換為清單格式
                to_emails = [letter.mail["To"]]
                smtp.sendmail(self.login, to_emails, letter.mail.as_string())  # 寄送郵件
                print("Mail sent Complete!")
            except Exception as e:
                print("MAIL_SERVER: send(): Error message: ", e)
                status = False
        return status




if __name__ == "__main__":
    now = datetime.datetime.now()
    hostname = socket.gethostname().split(sep='.')[0]
    message = f'{hostname} Power-Up Alarm @ {now}'
    print(message)

    pwd = "vpwi qjqe cbjm hpzo"
    login = "shih.norman@gmail.com"
    GMail = MAIL_SERVER(login=login, password=pwd)

    mail = MailMessage("shih.norman@eshadetech.com", "Test Mail from norman")
    mail.content("This is a test mail from Norman to verify mail implementation")
    mail.attach("/Users/norman/PycharmProjects/eShade2ndGen/pyproject.toml")
    status = GMail.send(letter=mail)
    print(f'Mail sent {status}')


    '''
    content = MIMEMultipart()  #建立MIMEMultipart物件
    content["subject"] = "Learn Code With Mike"  #郵件標題
    content["from"] = "shih.norman@gmail.com"  #寄件者
    content["to"] = "shih.norman@gmail.com" #收件者
    content.attach(MIMEText("Demo python send email"))  #郵件內容
    
    # Gmail authenticatication
    pwd = "vpwi qjqe cbjm hpzo"
    
    # Google Cloud Service
    gcs_propject_number = "139806995033"
    gcs_id = "utopian-trilogy-411505"
    
    google_drive_api_tcc_key = "139806995033-ltat7972eft2pohuvhnvhjcrt9dnc8rf.apps.googleusercontent.com"
    
    
    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:  # 設定SMTP伺服器
        try:
            smtp.ehlo()  # 驗證SMTP伺服器
            smtp.starttls()  # 建立加密傳輸
            smtp.login("shih.norman@gmail.com", pwd)  # 登入寄件者gmail
            smtp.send_message(content)  # 寄送郵件
            print("Complete!")
        except Exception as e:
            print("Error message: ", e)
    '''