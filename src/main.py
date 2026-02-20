import os
import time
from email_service import connect_to_yandex, get_unseen_orders
from pdf_parser import extract_text_from_pdf, parse_orders
from telegram_service import send_to_telegram, format_order_message

def main():
    # Получаем переменные напрямую из окружения (без .env файла)
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    
    print(f"🔍 Проверка переменных...")
    print(f"EMAIL_USER: {'✅ Настроен' if EMAIL_USER else '❌ Пусто'}")
    print(f"EMAIL_PASS: {'✅ Настроен' if EMAIL_PASS else '❌ Пусто'}")
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Ошибка: Не настроены переменные окружения почты")
        return

    try:
        print(f"📬 Подключение к почте: {EMAIL_USER}")
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
                
                for i, order in enumerate(orders):
                    msg = format_order_message(order)
                    success = send_to_telegram(msg)
                    if success:
                        print(f"✅ Заказ #{order['order_number']} отправлен в Telegram")
                    else:
                        print(f"❌ Не удалось отправить заказ #{order['order_number']}")
                    
                    # ⏱ ЗАДЕРЖКА между сообщениями (15 секунд)
                    if i < len(orders) - 1:  # Не ждём после последнего сообщения
                        print(f"⏳ Пауза 15 секунд перед следующим сообщением...")
                        time.sleep(10)
                    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
