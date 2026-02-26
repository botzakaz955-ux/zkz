import fitz  # PyMuPDF
import re

def extract_text_from_pdf(pdf_bytes):
    """Извлекает весь текст из PDF байтов."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def parse_orders(raw_text):
    """
    Разбивает текст на заказы и парсит поля.
    """
    orders = []
    
    # Паттерн для поиска начала заказа
    order_split_pattern = r"Номер интернет-заказа:\s*\d+"
    
    # Находим все позиции начал заказов
    matches = list(re.finditer(order_split_pattern, raw_text))
    
    if not matches:
        return orders

    for i, match in enumerate(matches):
        start_index = match.start()
        end_index = matches[i+1].start() if i+1 < len(matches) else len(raw_text)
        
        order_block = raw_text[start_index:end_index]
        order_data = parse_single_order(order_block)
        
        if order_data.get("order_number"):
            orders.append(order_data)
            
    return orders

def parse_single_order(text_block):
    """Парсит конкретные поля внутри блока заказа."""
    data = {
        "customer": "Не указано",
        "phone": "Не указано",
        "order_number": "Не указано",
        "delivery_method": "Не указано",
        "delivery_address": "Не указано",
        "payment_method": "Не указано",
        "shop_address": "Не указано",
        "comment": "Нет",
        "delivery_date": "Не указано",
        "delivery_time": "Не указано"
    }
    
    def find_value(key, fallback="Не указано"):
        pattern = rf"{key}:\s*(.+?)(?:\n|$)"
        match = re.search(pattern, text_block)
        if match:
            return match.group(1).strip()
        return fallback

    data["order_number"] = find_value("Номер интернет-заказа")
    data["customer"] = find_value("Покупатель")
    data["phone"] = find_value("Телефон")
    data["delivery_method"] = find_value("Способ доставки")
    data["delivery_address"] = find_value("Адрес доставки")
    data["payment_method"] = find_value("Способ оплаты")
    data["shop_address"] = find_value("Адрес магазина")
    
    comment_val = find_value("Комментарий", "")
    data["comment"] = comment_val if comment_val else "Нет"

    return data

def parse_delivery_table_from_email(email_body):
    """
    Парсит таблицу из тела письма и возвращает словарь:
    {номер_заказа: {'delivery_date': ..., 'delivery_time': ...}}
    
    Формат таблицы из письма:
    Магазин	Номер заказа	Сумма заказа	Способ оплаты	Способ доставки	Дата доставки	Время доставки
    ФР Кемерово, Ленина пр, 64					
    Заказ покупателя 00ЦБ-002857 от 26.02.2026 14:09:03	8090287	2 163,00	Оплата на сайте	Доставка курьером	26.02.2026	15 - 16
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
                
                # Пропускаем строки заголовков секций (просто "Заказ")
                if data_line == 'Заказ':
                    continue
                
                # Пропускаем строки с названиями магазинов (в них нет 7-значного номера заказа)
                if not re.search(r'\d{7,}', data_line):
                    continue
                
                # Разбиваем по табуляции
                columns = [col.strip() for col in data_line.split('\t')]
                columns = [col for col in columns if col]  # Убираем пустые
                
                # Если мало колонок, пробуем по двойным пробелам
                if len(columns) < 6:
                    columns = [col.strip() for col in re.split(r'\s{2,}', data_line)]
                    columns = [col for col in columns if col]
                
                # Ожидаем минимум 7 колонок:
                # 0: Описание заказа
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
                            if re.match(r'^\d{7,}$', col.replace(' ', '').replace(',', '')):
                                order_number = col.replace(' ', '').replace(',', '')
                                break
                        
                        if not order_number:
                            continue
                        
                        # Ищем дату в формате ДД.ММ.ГГГГ
                        delivery_date = "Не указано"
                        delivery_time = "Не указано"
                        
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
                            print(f"✅ Найдена доставка: {order_number} -> {delivery_date} {delivery_time}")
                            
                    except Exception as e:
                        print(f"❌ Ошибка парсинга строки: {e}")
                        continue
    
    return delivery_data

# Алиас для обратной совместимости с main.py
parse_delivery_info_from_email = parse_delivery_table_from_email
