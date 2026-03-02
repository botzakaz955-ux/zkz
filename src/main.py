import os
import time
import json
from email_service import connect_to_yandex, get_unseen_orders
from pdf_parser import extract_text_from_pdf, parse_orders, parse_delivery_table_from_email

# ИСПРАВЛЕНИЕ: Импортируем именно функцию send_order (которая дублирует чаты), а не базовую send_to_telegram!
from telegram_service import send_order

SENT_ORDERS_FILE = "sent_orders.json"

def load_sent_orders():
    """Загружает номера отправленных заказов из файла."""
    if os.path.exists(SENT_ORDERS_FILE):
        try:
            with open(SENT_ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return[]

def save_sent_orders(sent_orders):
    """Сохраняет номера отправленных заказов в файл."""
    with open(SENT_ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sent_orders, f, ensure_ascii=False, indent=2)

def should_skip_order(order):
    """Проверяет, нужно ли пропустить заказ."""
    delivery = order.get('delivery_method', '').lower()
    if 'самовывоз' in delivery:
        print(f"⏭️ Пропущен заказ #{order['order_number']}: Самовывоз")
        return True
    
    comment = order.get('comment', '').lower()
    if 'см №' in comment or 'см#' in comment or 'см№' in comment:
        print(f"⏭️ Пропущен заказ #{order['order_number']}: СМ № в комментарии")
        return True
    
    return False

def extract_city_from_address(address):
    """Извлекает название города из адреса доставки."""
    city_keywords =['кемерово', 'красноярск', 'шерегеш', 'геш']
    address_lower = address.lower()
    
    for keyword in city_keywords:
        if keyword in address_lower:
            return keyword
    
    return 'other'

def main():
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Ошибка: Не настроены переменные окружения почты")
        return

    sent_orders = load_sent_orders()
    try:
        mail = connect_to_yandex(EMAIL_USER, EMAIL_PASS)
        emails = get_unseen_orders(mail)
        mail.close()
        mail.logout()
        
        if not emails:
            print("✅ Новых заказов нет")
            return

        total_orders = 0
        sent_orders_count = 0
        skipped_orders = 0
        duplicate_orders = 0

        for email_item in emails:
            html_body = email_item.get("html_body", "")
            delivery_table = parse_delivery_table_from_email(html_body)
            
            for pdf_bytes in email_item["attachments"]:
                text = extract_text_from_pdf(pdf_bytes)
                orders = parse_orders(text)
                
                for i, order in enumerate(orders):
                    total_orders += 1
                    
                    if order['order_number'] in sent_orders:
                        duplicate_orders += 1
                        continue
                    
                    if should_skip_order(order):
                        skipped_orders += 1
                        continue
                    
                    if order['order_number'] in delivery_table:
                        order['delivery_date'] = delivery_table[order['order_number']]['delivery_date']
                        order['delivery_time'] = delivery_table[order['order_number']]['delivery_time']
                    else:
                        order['delivery_date'] = "Не указано"
                        order['delivery_time'] = "Не указано"
                    
                    city = extract_city_from_address(order['delivery_address'])
                    order['city'] = city 
                    
                    print(f"📍 Определен город: {city}. Запуск маршрутизации (send_order)...")
                    
                    # ИСПРАВЛЕНИЕ: Вызов умной отправки (в главный + в локальный)
                    success = send_order(order)
                    
                    if success:
                        print(f"✅ Заказ #{order['order_number']} обработан.")
                        sent_orders.append(order['order_number'])
                        sent_orders_count += 1
                    else:
                        print(f"❌ Заказ #{order['order_number']} НЕ был отправлен.")
                    
                    if i < len(orders) - 1:
                        time.sleep(15)
        
        save_sent_orders(sent_orders)
        
        print(f"\n📊 === ИТОГИ ===")
        print(f"Всего заказов: {total_orders}")
        print(f"Отправлено: {sent_orders_count}")
        print(f"Дубликаты: {duplicate_orders}")
        print(f"Пропущено: {skipped_orders}")
                    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
