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
    Предполагается, что каждый заказ начинается с 'Номер интернет-заказа'.
    """
    orders = []
    
    # Разделяем текст по номеру заказа. 
    # Regex ищет "Номер интернет-заказа: 12345" и делает сплит, сохраняя разделитель в логике
    # Но проще найти все вхождения блоков.
    
    # Паттерн для поиска начала заказа
    order_split_pattern = r"Номер интернет-заказа:\s*\d+"
    
    # Находим все позиции начал заказов
    matches = list(re.finditer(order_split_pattern, raw_text))
    
    if not matches:
        return orders

    for i, match in enumerate(matches):
        start_index = match.start()
        # Конец блока - начало следующего заказа или конец текста
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
        "delivery_date": "Не указано",      # ✅ НОВОЕ ПОЛЕ
        "delivery_time": "Не указано",      # ✅ НОВОЕ ПОЛЕ
        "payment_method": "Не указано",
        "shop_address": "Не указано",
        "comment": "Нет"
    }
    
    # Helper для поиска значения после ключа
    def find_value(key, fallback="Не указано"):
        # Ищем ключ, затем двоеточие, затем значение до конца строки
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
    data["delivery_date"] = find_value("Дата доставки")      # ✅ НОВОЕ
    data["delivery_time"] = find_value("Время доставки")      # ✅ НОВОЕ
    data["payment_method"] = find_value("Способ оплаты")
    data["shop_address"] = find_value("Адрес магазина")
    
    # Комментарий часто бывает в конце, может быть пустым
    comment_val = find_value("Комментарий", "")
    data["comment"] = comment_val if comment_val else "Нет"

    return data
