import imaplib
import email
from email.header import decode_header

def connect_to_yandex(user, password):
    mail = imaplib.IMAP4_SSL("imap.yandex.ru")
    mail.login(user, password)
    mail.select("inbox")
    return mail

def get_unseen_orders(mail, sender_filter="ishop@volcov.ru"):
    """Находит непрочитанные письма от конкретного отправителя."""
    # Поиск непрочитанных писем
    status, messages = mail.search(None, '(UNSEEN)', 'FROM', f'"{sender_filter}"')
    
    email_ids = messages[0].split()
    processed_ids = []
    emails_data = []

    for e_id in email_ids:
        status, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Проверяем вложения
                attachments = []
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        if content_type == "application/pdf" and "attachment" in content_disposition:
                            try:
                                pdf_data = part.get_payload(decode=True)
                                attachments.append(pdf_data)
                            except Exception:
                                continue
                
                if attachments:
                    emails_data.append({"id": e_id, "attachments": attachments})
                    processed_ids.append(e_id)

    # Помечаем как прочитанные
    for e_id in processed_ids:
        mail.store(e_id, '+FLAGS', '\\Seen')
        
    return emails_data
