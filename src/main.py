import os
import time
import json
from email_service import connect_to_yandex, get_unseen_orders
from pdf_parser import extract_text_from_pdf, parse_orders, parse_delivery_table_from_email
from telegram_service import send_to_telegram, format_order_message, get_chat_id_by_city

# Файл для хранения отправленных заказов
SENT_ORDERS_FILE = "sent_orders.json"

def load_sent_orders():
    """Загружает номера отправленных заказов из файла."""
    if os.path.exists(SENT_ORDERS_FILE):
        try:
            with open(SENT_ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_sent_orders(sent_orders):
    """Сохраняет номера отправленных заказов в файл."""
    with open(SENT_ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sent_orders, f, ensure_ascii=False, indent=2)

def should_skip_order(order):
    """Проверяет, нужно ли пропустить заказ."""
    # 🚫 Фильтр 1: Самовывоз
    delivery = order.get('delivery_method', '').lower()
    if 'самовывоз' in delivery:
        print(f"⏭️ Пропущен заказ #{order['order_number']}: Самовывоз")
        return True
    
    # 🚫 Фильтр 2: Комментарий содержит "СМ №"
    comment = order.get('comment', '').lower()
    if 'см №' in comment or 'см#' in comment or 'см№' in comment:
        print(f"⏭️ Пропущен заказ #{order['order_number']}: СМ № в комментарии")
        return True
    
    return False

def extract_city_from_address(address):
    """Извлекает название города из адреса доставки."""
    city_keywords = ['кемерово', 'красноярск', 'шерегеш', 'геш']
    address_lower = address.lower()
    
    for keyword in city_keywords:
        if keyword in address_lower:
            return keyword
    
    return 'other'

def main():
    # Получаем переменные из окружения
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    
    print(f"🔍 Проверка переменных...")
    print(f"EMAIL_USER: {'✅ Настроен' if EMAIL_USER else '❌ Пусто'}")
    print(f"EMAIL_PASS: {'✅ Настроен' if EMAIL_PASS else '❌ Пусто'}")
    
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ Ошибка: Не настроены переменные окружения почты")
        return

    # Загружаем номера отправленных заказов
    sent_orders = load_sent_orders()
    print(f"📋 Загружено отправленных заказов: {len(sent_orders)}")

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

        # Счётчики для статистики
        total_orders = 0
        sent_orders_count = 0
        skipped_orders = 0
        duplicate_orders = 0

        for email_item in emails:
            # 📅 Парсим таблицу из HTML части письма
            html_body = email_item.get("html_body", "")
            print(f"📄 Длина HTML тела: {len(html_body)} символов")
            
            delivery_table = parse_delivery_table_from_email(html_body)
            print(f"📅 Найдено записей о доставке в таблице: {len(delivery_table)}")
            print(f"📅 Данные: {delivery_table}")
            
            for pdf_bytes in email_item["attachments"]:
                text = extract_text_from_pdf(pdf_bytes)
                orders = parse_orders(text)
                
                print(f"📄 В PDF найдено заказов: {len(orders)}")
                
                for i, order in enumerate(orders):
                    total_orders += 1
                    
                    # 🔒 Проверка на дубликат
                    if order['order_number'] in sent_orders:
                        print(f"⏭️ Пропущен заказ #{order['order_number']}: Уже отправлен")
                        duplicate_orders += 1
                        continue
                    
                    # 🚫 Проверка фильтров
                    if should_skip_order(order):
                        skipped_orders += 1
                        continue
                    
                    # 📅 Добавляем дату и время из таблицы по номеру заказа
                    if order['order_number'] in delivery_table:
                        order['delivery_date'] = delivery_table[order['order_number']]['delivery_date']
                        order['delivery_time'] = delivery_table[order['order_number']]['delivery_time']
                        print(f"✅ Найдена доставка для заказа #{order['order_number']}: {order['delivery_date']} {order['delivery_time']}")
                    else:
                        order['delivery_date'] = "Не указано"
                        order['delivery_time'] = "Не указано"
                        print(f"⚠️ Не найдена доставка для заказа #{order['order_number']}")
                    
                    # 📍 Определение города и выбор группы
                    city = extract_city_from_address(order['delivery_address'])
                    chat_id = get_chat_id_by_city(city)
                    
                    print(f"📍 Город: {city} → Чат: {chat_id}")
                    
                    # Форматируем и отправляем
                    msg = format_order_message(order)
                    success = send_to_telegram(msg, chat_id)
                    
                    if success:
                        print(f"✅ Заказ #{order['order_number']} отправлен в Telegram")
                        sent_orders.append(order['order_number'])
                        sent_orders_count += 1
                    else:
                        print(f"❌ Не удалось отправить заказ #{order['order_number']}")
                    
                    # ⏱ ЗАДЕРЖКА между сообщениями (15 секунд)
                    if i < len(orders) - 1:
                        print(f"⏳ Пауза 15 секунд перед следующим сообщением...")
                        time.sleep(15)
        
        # 💾 Сохраняем номера отправленных заказов
        save_sent_orders(sent_orders)
        print(f"💾 Сохранено отправленных заказов: {len(sent_orders)}")
        
        # 📊 Итоговая статистика
        print(f"\n📊 === ИТОГИ ===")
        print(f"Всего заказов: {total_orders}")
        print(f"Отправлено: {sent_orders_count}")
        print(f"Дубликаты: {duplicate_orders}")
        print(f"Пропущено (фильтры): {skipped_orders}")
                    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
