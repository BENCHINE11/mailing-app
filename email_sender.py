import smtplib, ssl, os, mimetypes, base64, httpx
from email.message import EmailMessage

def send_via_smtp(sender, recipients, subject, html_body, attachments, host, port, user, password):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("Votre client mail ne supporte pas HTML.")
    msg.add_alternative(html_body, subtype="html")

    for filename, filebytes in attachments:
        ctype, _ = mimetypes.guess_type(filename)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(filebytes, maintype=maintype, subtype=subtype, filename=filename)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(user, password)
        server.send_message(msg)

def send_via_resend(api_key, from_addr, recipients, subject, html_body, attachments):
    # https://resend.com (envoi par API HTTP)
    files_payload = []
    for filename, filebytes in attachments:
        files_payload.append(("attachments", (filename, filebytes, mimetypes.guess_type(filename)[0] or "application/octet-stream")))
    data = {
        "from": from_addr,
        "to": recipients,
        "subject": subject,
        "html": html_body
    }
    # multipart pour gérer pièces jointes
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files=files_payload if files_payload else None,
        )
        resp.raise_for_status()
