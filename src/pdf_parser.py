import fitz  # PyMuPDF
import re
from html import unescape

def extract_text_from_pdf(pdf_bytes):
    """Извлекает весь текст из PDF байтов."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def parse_orders(raw_text):
    """Разбивает текст на заказы и парсит поля."""
    orders =[]
    
    # ИСПРАВЛЕНИЕ: Начинаем захват с самой верхней строчки документа, 
    # чтобы не потерять Покупателя и Телефон, которые идут ДО Номера интернет-заказа.
    order_split_pattern = r"Заказ покупателя №"
    matches = list(re.finditer(order_split_pattern, raw_text))
    
    if not matches:
        # Если фразы "Заказ покупателя №" нет, парсим весь файл как один большой заказ
        order_data = parse_single_order(raw_text)
        if order_data.get("order_number") and order_data.get("order_number") != "Не указано":
            orders.append(order_data)
        return orders

    for i, match in enumerate(matches):
        start_index = match.start()
        end_index = matches[i+1].start() if i+1 < len(matches) else len(raw_text)
        
        order_block = raw_text[start_index:end_index]
        order_data = parse_single_order(order_block)
        
        if order_data.get("order_number") and order_data.get("order_number") != "Не указано":
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
        # Ищем классический вариант "Ключ: Значение"
        pattern = rf"{key}:\s*([^\n]+)"
        match = re.search(pattern, text_block)
        if match:
            val = match.group(1).strip()
            if val:
                return val
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

def parse_delivery_table_from_email(html_body):
    """Парсит HTML таблицу из тела письма."""
    delivery_data = {}
    if not html_body:
        return delivery_data
    
    html_body = unescape(html_body)
    row_pattern = r'<tr[^>]*class="R6"[^>]*>(.*?)</tr>'
    rows = re.findall(row_pattern, html_body, re.DOTALL | re.IGNORECASE)
    
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        cleaned_cells = []
        for cell in cells:
            cell_text = re.sub(r'<[^>]+>', '', cell).strip()
            if cell_text:
                cleaned_cells.append(cell_text)
        
        if len(cleaned_cells) >= 7:
            try:
                order_number = None
                for cell in cleaned_cells:
                    if re.match(r'^\d{7,}$', cell.replace(' ', '').replace(',', '')):
                        order_number = cell.replace(' ', '').replace(',', '')
                        break
                
                if not order_number:
                    continue
                
                delivery_date = "Не указано"
                delivery_time = "Не указано"
                
                for idx, cell in enumerate(cleaned_cells):
                    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', cell):
                        delivery_date = cell
                        if idx + 1 < len(cleaned_cells):
                            time_match = re.search(r'(\d{1,2}\s*[-–]\s*\d{1,2})', cleaned_cells[idx + 1])
                            if time_match:
                                delivery_time = time_match.group(1).replace('–', '-')
                        break
                
                if order_number and delivery_date != "Не указано":
                    delivery_data[order_number] = {
                        'delivery_date': delivery_date,
                        'delivery_time': delivery_time
                    }
                    
            except Exception:
                continue
    return delivery_data
