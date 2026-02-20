import os
from dotenv import load_dotenv
from email_service import connect_to_yandex, get_unseen_orders
from pdf_parser import extract_text_from_pdf, parse_orders
from telegram_service import send_to_telegram, format_order_message

load_dotenv()

def main():
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Ошибка: Не настроены переменные окружения почты")
        return

    try:
        mail = connect_to_yandex(EMAIL_USER, EMAIL_PASS)
        emails = get_unseen_orders(mail)
        mail.close()
        mail.logout()
        
        if not emails:
            print("✅ Новых заказов нет")
            return

        print(f"📬 Найдено писем с вложениями: {len(emails)}")

        for email_item in emails:
            for pdf_bytes in email_item["attachments"]:
                text = extract_text_from_pdf(pdf_bytes)
                orders = parse_orders(text)
                
                print(f"📄 В PDF найдено заказов: {len(orders)}")
                
                for order in orders:
                    msg = format_order_message(order)
                    send_to_telegram(msg)
                    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
