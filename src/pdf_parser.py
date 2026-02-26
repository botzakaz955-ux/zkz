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

def parse_delivery_info_from_email(email_body):
    """
    Извлекает дату и время доставки из тела письма.
    Ищет паттерны: "Дата доставки: 25.12.2024", "Время доставки: 10:00-14:00"
    """
    delivery_info = {
        "delivery_date": "Не указано",
        "delivery_time": "Не указано"
    }
    
    # Поиск даты доставки
    date_pattern = r"Дата доставки:\s*(\d{1,2}\.\d{1,2}\.\d{4})"
    date_match = re.search(date_pattern, email_body)
    if date_match:
        delivery_info["delivery_date"] = date_match.group(1)
    
    # Поиск времени доставки
    time_pattern = r"Время доставки:\s*(\d{1,2}:\d{2}[-–]\d{1,2}:\d{2})"
    time_match = re.search(time_pattern, email_body)
    if time_match:
        delivery_info["delivery_time"] = time_match.group(1)
    
    return delivery_info
