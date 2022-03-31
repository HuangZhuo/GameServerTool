import unittest

import smtplib
from email.mime.text import MIMEText
from email.header import Header


class TestMail(unittest.TestCase):
    def test_send(self):
        # 第三方 SMTP 服务
        mail_host = "smtp.163.com"  #设置服务器
        mail_user = "idorable@163.com"  #用户名
        mail_pass = ""  #口令

        sender = 'idorable@163.com'  # 这里必须使用邮箱地址
        receivers = ['idorable@163.com']  # 接收邮件地址

        message = MIMEText('测试邮件正文', 'plain', 'utf-8')
        # message['From'] = Header("test_from", 'utf-8')
        # message['To'] = Header("test_to", 'utf-8')

        subject = '测试邮件标题'
        message['Subject'] = Header(subject, 'utf-8')

        try:
            smtpObj = smtplib.SMTP()
            smtpObj.connect(mail_host, 25)  # 25 为 SMTP 端口号
            smtpObj.login(mail_user, mail_pass)
            smtpObj.sendmail(sender, receivers, message.as_string())
            print("邮件发送成功")
        except smtplib.SMTPException as e:
            print("Error: 无法发送邮件", repr(e))