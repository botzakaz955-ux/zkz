import imaplib
import email
from email.header import decode_header

def connect_to_yandex(user, password):
    """Подключается к Яндекс.Почте по IMAP."""
    mail = imaplib.IMAP4_SSL("imap.yandex.ru")
    mail.login(user, password)
    mail.select("inbox")
    return mail

def get_unseen_orders(mail, sender_filter="ishop@volcov.ru"):
    """Находит непрочитанные письма от конкретного отправителя."""
    # Поиск всех непрочитанных писем
    status, messages = mail.search(None, 'UNSEEN')
    
    email_ids = messages[0].split()
    processed_ids = []
    emails_data = []

    for e_id in email_ids:
        status, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:  # ✅ Исправлено: msg_data + двоеточие
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Проверяем отправителя вручную
                sender = msg.get('From', '')
                if sender_filter not in sender:
                    continue  # Пропускаем, если не тот отправитель
                
                # Извлекаем тему письма
                subject, encoding = decode_header(msg.get('Subject', ''))[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                
                # Извлекаем тело письма (текст)
                email_body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        
                        # Текстовая часть письма
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            try:
                                body = part.get_payload(decode=True)
                                if body:
                                    email_body += body.decode('utf-8', errors='ignore')
                            except Exception:
                                continue
                
                # Проверяем вложения PDF
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
                    emails_data.append({
                        "id": e_id,
                        "attachments": attachments,
                        "body": email_body,
                        "subject": subject
                    })
                    processed_ids.append(e_id)

    # Помечаем как прочитанные
    for e_id in processed_ids:
        mail.store(e_id, '+FLAGS', '\\Seen')
        
    return emails_data
