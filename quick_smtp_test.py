import os, ssl, smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()

host = os.getenv("SMTP_HOST", "smtp.gmail.com")
port = int(os.getenv("SMTP_PORT", "465"))
user = os.getenv("SMTP_USER")
pwd  = os.getenv("SMTP_PASSWORD")

assert user and pwd, "Missing SMTP_USER or SMTP_PASSWORD"

msg = EmailMessage()
msg["From"] = user
msg["To"] = user
msg["Subject"] = "SMTP sanity test"
msg.set_content("If you received this, SMTP auth works.")

if port == 465:
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as s:
        s.login(user, pwd)
        s.send_message(msg)
else:
    with smtplib.SMTP(host, port) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(user, pwd)
        s.send_message(msg)

print("Sent!")
