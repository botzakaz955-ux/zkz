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
    Парсит HTML таблицу из тела письма и возвращает словарь:
    {номер_заказа: {'delivery_date': ..., 'delivery_time': ...}}
    """
    import re
    from html import unescape
    
    delivery_data = {}
    
    # Декодируем HTML сущности
    email_body = unescape(email_body)
    
    # Ищем все строки таблицы с данными заказов
    # Ищем паттерн: номер заказа (7+ цифр), затем дата и время
    order_pattern = r'(\d{7,})\s*</td>.*?(\d{1,2}\.\d{1,2}\.\d{4})\s*</td>.*?(\d{1,2}\s*[-–]\s*\d{1,2})'
    
    matches = re.findall(order_pattern, email_body, re.DOTALL)
    
    for match in matches:
        order_number = match[0].strip()
        delivery_date = match[1].strip()
        delivery_time = match[2].strip()
        
        if order_number and delivery_date:
            delivery_data[order_number] = {
                'delivery_date': delivery_date,
                'delivery_time': delivery_time
            }
            print(f"✅ Найдена доставка: {order_number} -> {delivery_date} {delivery_time}")
    
    # Если не нашли по паттерну, пробуем найти по классам таблицы
    if not delivery_data:
        # Ищем строки таблицы с классом R6 (строки с данными)
        row_pattern = r'<tr[^>]*class="R6"[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, email_body, re.DOTALL)
        
        for row in rows:
            # Извлекаем все ячейки из строки
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            
            if len(cells) >= 7:
                try:
                    # Ищем номер заказа (ячейка с 7+ цифрами)
                    order_number = None
                    delivery_date = None
                    delivery_time = None
                    
                    for i, cell in enumerate(cells):
                        # Очищаем ячейку от HTML тегов
                        cell_text = re.sub(r'<[^>]+>', '', cell).strip()
                        
                        # Проверяем на номер заказа
                        if re.match(r'^\d{7,}$', cell_text):
                            order_number = cell_text
                        
                        # Проверяем на дату (ДД.ММ.ГГГГ)
                        if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', cell_text):
                            delivery_date = cell_text
                        
                        # Проверяем на время (ЧЧ - ЧЧ)
                        if re.match(r'^\d{1,2}\s*[-–]\s*\d{1,2}$', cell_text):
                            delivery_time = cell_text
                    
                    if order_number and delivery_date:
                        delivery_data[order_number] = {
                            'delivery_date': delivery_date,
                            'delivery_time': delivery_time if delivery_time else "Не указано"
                        }
                        print(f"✅ Найдена доставка: {order_number} -> {delivery_date} {delivery_time if delivery_time else 'Не указано'}")
                
                except Exception as e:
                    print(f"❌ Ошибка парсинга строки: {e}")
                    continue
    
    return delivery_data

# Алиас для обратной совместимости с main.py
parse_delivery_info_from_email = parse_delivery_table_from_email
