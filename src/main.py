import os
import time
import json
import re
from email_service import connect_to_yandex, get_unseen_orders
from pdf_parser import extract_text_from_pdf, parse_orders, parse_delivery_info_from_email
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
    """
    Проверяет, нужно ли пропустить заказ.
    Возвращает True, если заказ нужно игнорировать.
    """
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

def parse_delivery_table_from_email(email_body):
    """
    Парсит таблицу из тела письма и возвращает словарь:
    {номер_заказа: {'delivery_date': ..., 'delivery_time': ...}}
    """
    delivery_data = {}
    
    # Разбиваем тело письма на строки
    lines = email_body.strip().split('\n')
    
    # Ищем заголовок таблицы
    header_found = False
    for i, line in enumerate(lines):
        if 'Магазин' in line and 'Дата доставки' in line:
            header_found = True
            print(f"📅 Заголовок таблицы найден на строке {i}")
            
            # Проходим по всем строкам после заголовка
            for j in range(i+1, len(lines)):
                data_line = lines[j].strip()
                
                # Пропускаем пустые строки
                if not data_line:
                    continue
                
                # Пропускаем строки, которые содержат только название магазина
                # (в них нет номера заказа - только цифры в формате 8090287)
                if not re.search(r'\d{7,}', data_line):
                    print(f"⏭️ Пропущена строка (нет номера заказа): {data_line[:50]}")
                    continue
                
                # Разбиваем по табуляции
                columns = [col.strip() for col in data_line.split('\t')]
                columns = [col for col in columns if col]  # Убираем пустые
                
                print(f"📋 Строка таблицы: {columns}")
                
                # Если мало колонок, пробуем по двойным пробелам
                if len(columns) < 6:
                    # Пробуем разбить по множественным пробелам (2 и более)
                    columns = [col.strip() for col in re.split(r'\s{2,}', data_line)]
                    columns = [col for col in columns if col]
                    print(f" После split по пробелам: {columns}")
                
                # Ожидаем минимум 7 колонок:
                # 0: Заказ покупателя... / Название магазина
                # 1: Номер заказа (8090287)
                # 2: Сумма (2 163,00)
                # 3: Способ оплаты
                # 4: Способ доставки
                # 5: Дата доставки (26.02.2026)
                # 6: Время доставки (15 - 16)
                
                if len(columns) >= 7:
                    try:
                        # Ищем номер заказа (должен быть только цифры, 7+ знаков)
                        order_number = None
                        for col in columns:
                            if re.match(r'^\d{7,}$', col.replace(' ', '')):
                                order_number = col.replace(' ', '')
                                break
                        
                        if not order_number:
                            print(f"⚠️ Не найден номер заказа в строке: {data_line[:50]}")
                            continue
                        
                        # Дата доставки - предпоследняя колонка с датой
                        delivery_date = "Не указано"
                        delivery_time = "Не указано"
                        
                        # Ищем дату в формате ДД.ММ.ГГГГ
                        for idx, col in enumerate(columns):
                            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', col):
                                delivery_date = col
                                # Время - следующая колонка
                                if idx + 1 < len(columns):
                                    time_match = re.search(r'(\d{1,2}\s*[-–]\s*\d{1,2})', columns[idx + 1])
                                    if time_match:
                                        delivery_time = time_match.group(1).replace('–', '-')
                                break
                        
                        if order_number and delivery_date != "Не указано":
                            delivery_data[order_number] = {
                                'delivery_date': delivery_date,
                                'delivery_time': delivery_time
                            }
                            print(f"✅ Добавлено: {order_number} -> {delivery_date} {delivery_time}")
                            
                    except Exception as e:
                        print(f"❌ Ошибка парсинга строки: {e}")
                        continue
    
    return delivery_data

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
            # 📅 Парсим таблицу из тела письма
            delivery_table = parse_delivery_table_from_email(email_item.get("body", ""))
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
