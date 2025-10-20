import smtplib, ssl, mimetypes, httpx
from email.message import EmailMessage
from html import escape as html_escape

def to_html_paras(user_text: str) -> str:
    """
    Convertit un texte brut en HTML simple en conservant les sauts de ligne.
    Double saut = nouveau paragraphe, simple saut = <br>.
    """
    if not user_text:
        return ""
    # Normaliser fins de ligne
    t = user_text.replace("\r\n", "\n").replace("\r", "\n")
    paras = [p.strip() for p in t.split("\n\n") if p.strip()]
    safe_paras = []
    for p in paras:
        safe = html_escape(p).replace("\n", "<br>")
        safe_paras.append(f"<p style=\"margin:0 0 12px 0;\">{safe}</p>")
    return "".join(safe_paras) or "<p></p>"

def build_html(title: str, main_html: str, preheader: str = "") -> str:
    """
    Gabarit HTML email-friendly (tables + styles inline).
    """
    pre = html_escape(preheader or "")
    return f"""\
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html_escape(title or "")}</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f9fc;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{pre}</div>
    <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background:#f6f9fc;">
      <tr>
        <td align="center" style="padding:24px;">
          <table role="presentation" width="600" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;border:1px solid #eceff3;" cellspacing="0" cellpadding="0">
            <tr>
              <td style="padding:28px 24px 8px 24px;">
                <h1 style="margin:0 0 12px 0;font-size:22px;line-height:28px;font-weight:700;color:#111827;">
                  {html_escape(title or "")}
                </h1>
              </td>
            </tr>
            <tr>
              <td style="padding:0 24px 24px 24px;color:#111827;font-size:15px;line-height:22px;">
                {main_html}
              </td>
            </tr>
          </table>
          <div style="padding:16px;color:#9ca3af;font-size:12px;">
            Envoyé par Mail Groups Sender
          </div>
        </td>
      </tr>
    </table>
  </body>
</html>"""

def _add_attachments(msg: EmailMessage, attachments):
    for filename, filebytes in attachments or []:
        ctype, _ = mimetypes.guess_type(filename)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(filebytes, maintype=maintype, subtype=subtype, filename=filename)

def send_via_smtp(sender, recipients, subject, text_body, html_body, attachments, host, port, user, password):
    """
    Envoi SMTP en multipart/alternative (texte + HTML).
    """
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = sender
    msg["Bcc"] = ", ".join(recipients)
    msg["Subject"] = subject

    # Fallback texte (normaliser CRLF pour certains serveurs)
    text_norm = (text_body or "").replace("\r\n", "\n").replace("\r", "\n")
    text_norm = text_norm.replace("\n", "\r\n")
    msg.set_content(text_norm, subtype="plain", charset="utf-8")

    # Version HTML
    msg.add_alternative(html_body or to_html_paras(text_body or ""), subtype="html")

    # Pièces jointes
    _add_attachments(msg, attachments)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(user, password)
        server.send_message(msg)

def send_via_resend(api_key, from_addr, recipients, subject, text_body, html_body, attachments):
    """
    Envoi via l'API Resend (multipart si pièces jointes).
    """
    files_payload = []
    for filename, filebytes in attachments or []:
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        files_payload.append(("attachments", (filename, filebytes, mime)))

    data = {
        "from": from_addr,
        "to": recipients,
        "subject": subject,
        "text": text_body or "",
        "html": html_body or to_html_paras(text_body or ""),
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files=files_payload if files_payload else None,
        )
        resp.raise_for_status()
