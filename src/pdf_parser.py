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

def parse_delivery_table_from_email(html_body):
    """
    Парсит HTML таблицу из тела письма и возвращает словарь:
    {номер_заказа: {'delivery_date': ..., 'delivery_time': ...}}
    """
    delivery_data = {}
    
    if not html_body:
        print("⚠️ HTML тело письма пустое")
        return delivery_data
    
    # Декодируем HTML сущности
    html_body = unescape(html_body)
    
    # Ищем все строки таблицы с классом R6 (строки с данными заказов)
    # В HTML это выглядит как <tr class="R6">...</tr>
    row_pattern = r'<tr[^>]*class="R6"[^>]*>(.*?)</tr>'
    rows = re.findall(row_pattern, html_body, re.DOTALL | re.IGNORECASE)
    
    print(f"📋 Найдено строк таблицы R6: {len(rows)}")
    
    for row in rows:
        # Извлекаем все ячейки из строки
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        
        # Очищаем ячейки от HTML тегов
        cleaned_cells = []
        for cell in cells:
            # Удаляем HTML теги
            cell_text = re.sub(r'<[^>]+>', '', cell)
            cell_text = cell_text.strip()
            if cell_text:
                cleaned_cells.append(cell_text)
        
        print(f"📋 Ячейки строки: {cleaned_cells}")
        
        # Ожидаем минимум 7 колонок:
        # 0: Описание заказа
        # 1: Номер заказа (8090287)
        # 2: Сумма
        # 3: Способ оплаты
        # 4: Способ доставки
        # 5: Дата доставки (26.02.2026)
        # 6: Время доставки (15 - 16)
        
        if len(cleaned_cells) >= 7:
            try:
                # Ищем номер заказа (должен быть только цифры, 7+ знаков)
                order_number = None
                for cell in cleaned_cells:
                    if re.match(r'^\d{7,}$', cell.replace(' ', '').replace(',', '')):
                        order_number = cell.replace(' ', '').replace(',', '')
                        break
                
                if not order_number:
                    print(f"⚠️ Не найден номер заказа в строке")
                    continue
                
                # Ищем дату в формате ДД.ММ.ГГГГ
                delivery_date = "Не указано"
                delivery_time = "Не указано"
                
                for idx, cell in enumerate(cleaned_cells):
                    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', cell):
                        delivery_date = cell
                        # Время - следующая ячейка
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
                    print(f"✅ Найдена доставка: {order_number} -> {delivery_date} {delivery_time}")
                    
            except Exception as e:
                print(f"❌ Ошибка парсинга строки: {e}")
                continue
    
    return delivery_data
