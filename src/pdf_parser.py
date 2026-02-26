def parse_delivery_info_from_email(email_body):
    """
    Извлекает дату и время доставки из тела письма.
    Парсит табличные данные из письма.
    
    Формат таблицы:
    Магазин	Номер заказа	Сумма заказа	Способ оплаты	Способ доставки	Дата доставки	Время доставки
    ФР Кемерово, Ленина пр, 64					
    Заказ покупателя 00ЦБ-019770 от 26.02.2026 13:56:43	8090280	819,00	Оплата на сайте	Доставка курьером	26.02.2026	14 - 15
    """
    delivery_info = {
        "delivery_date": "Не указано",
        "delivery_time": "Не указано"
    }
    
    # Разбиваем тело письма на строки
    lines = email_body.split('\n')
    
    for line in lines:
        # Ищем строки с табуляцией (табличные данные)
        if '\t' in line:
            # Разбиваем по табуляции
            columns = line.split('\t')
            
            # Очищаем от лишних пробелов
            columns = [col.strip() for col in columns]
            
            # Ищем строку с датой в формате DD.MM.YYYY
            # Обычно дата доставки находится в 6-й колонке (индекс 5)
            # Время доставки в 7-й колонке (индекс 6)
            
            for i, col in enumerate(columns):
                # Проверяем на формат даты DD.MM.YYYY
                if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', col):
                    delivery_info["delivery_date"] = col
                    # Время обычно в следующей колонке
                    if i + 1 < len(columns) and columns[i + 1]:
                        # Проверяем формат времени (14 - 15 или 10:00-14:00)
                        time_col = columns[i + 1].strip()
                        if re.match(r'\d{1,2}\s*[-–]\s*\d{1,2}', time_col) or re.match(r'\d{1,2}:\d{2}', time_col):
                            delivery_info["delivery_time"] = time_col
                    break
                
                # Альтернативный поиск: если колонка содержит "Дата доставки" в заголовке
                if 'дата доставки' in col.lower():
                    # Следующая строка или колонка должна содержать дату
                    if i + 1 < len(columns) and columns[i + 1]:
                        delivery_info["delivery_date"] = columns[i + 1]
                    break
                    
                # Поиск времени
                if 'время доставки' in col.lower():
                    if i + 1 < len(columns) and columns[i + 1]:
                        delivery_info["delivery_time"] = columns[i + 1]
                    break
            
            # Дополнительная проверка: ищем паттерн времени в строке
            for col in columns:
                # Формат: "14 - 15" или "10:00-14:00"
                if re.match(r'\d{1,2}\s*[-–]\s*\d{1,2}', col) and delivery_info["delivery_time"] == "Не указано":
                    delivery_info["delivery_time"] = col
                # Формат: "10:00 - 14:00"
                elif re.match(r'\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}', col) and delivery_info["delivery_time"] == "Не указано":
                    delivery_info["delivery_time"] = col
    
    # Если не нашли в таблице, пробуем старые паттерны
    if delivery_info["delivery_date"] == "Не указано":
        date_pattern = r"Дата доставки:\s*(\d{1,2}\.\d{1,2}\.\d{4})"
        date_match = re.search(date_pattern, email_body)
        if date_match:
            delivery_info["delivery_date"] = date_match.group(1)
    
    if delivery_info["delivery_time"] == "Не указано":
        time_pattern = r"Время доставки:\s*(\d{1,2}:\d{2}[-–]\d{1,2}:\d{2})"
        time_match = re.search(time_pattern, email_body)
        if time_match:
            delivery_info["delivery_time"] = time_match.group(1)
        else:
            # Пробуем найти просто время в формате "14 - 15"
            time_pattern2 = r'(\d{1,2}\s*[-–]\s*\d{1,2})'
            time_match2 = re.search(time_pattern2, email_body)
            if time_match2:
                delivery_info["delivery_time"] = time_match2.group(1)
    
    return delivery_info
