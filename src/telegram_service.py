import requests
import os

def escape_tg_html(text):
    """Экранирует только те символы, которые ломают разметку Telegram (<, >, &)."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def get_chat_id_by_city(city):
    """Возвращает ID чата в зависимости от города."""
    city = city.lower()
    kem_chat = os.getenv("GROUP_KEMEROVO")
    kras_chat = os.getenv("GROUP_KRASNOYARSK")
    shere_chat = os.getenv("GROUP_SHEREGESH")
    
    if "кемерово" in city and kem_chat: return kem_chat.strip()
    elif "красноярск" in city and kras_chat: return kras_chat.strip()
    elif "шерегеш" in city and shere_chat: return shere_chat.strip()
    else: return None

def send_to_telegram(message_text, chat_id):
    """Отправляет сообщение в указанный чат."""
    token = os.getenv("BOT_TOKEN")
    if not chat_id: return False
    
    # Очищаем ID от случайных пробелов и невидимых символов
    chat_id = str(chat_id).strip()
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Telegram API Error (чат {chat_id}): {e}")
        # ВОТ ЭТО ВЫВЕДЕТ ИСТИННУЮ ПРИЧИНУ ОШИБКИ ОТ TELEGRAM:
        if e.response is not None:
            print(f"👉 Подробности от Telegram: {e.response.text}")
        return False

def format_order_message(order):
    """Создает красивое сообщение из словаря заказа."""
    
    # Безопасно подготавливаем данные
    safe_order = {}
    for key, value in order.items():
        safe_order[key] = escape_tg_html(value)

    text = (
        f"🛒 <b>НОВЫЙ ЗАКАЗ #{safe_order.get('order_number', '')}</b>\n\n"
        f"👤 <b>Покупатель:</b> {safe_order.get('customer', '')}\n"
        f"📞 <b>Телефон:</b> {safe_order.get('phone', '')}\n"
        f"📅 <b>Дата доставки:</b> {safe_order.get('delivery_date', '')}\n"
        f"🕐 <b>Время доставки:</b> {safe_order.get('delivery_time', '')}\n"
        f"🚚 <b>Доставка:</b> {safe_order.get('delivery_method', '')}\n"
        f"📍 <b>Адрес:</b> {safe_order.get('delivery_address', '')}\n"
        f"💳 <b>Оплата:</b> {safe_order.get('payment_method', '')}\n"
        f"🏪 <b>Магазин:</b> {safe_order.get('shop_address', '')}\n"
        f"📝 <b>Комментарий:</b> {safe_order.get('comment', '')}\n"
        f"\n━━━━━━━━━━━━━━━━━━━━"
    )
    return text

def send_order(order):
    """Отправляет заказ в Главный чат и дублирует в чат Города."""
    message_text = format_order_message(order)
    main_chat_id = os.getenv("GROUP_MAIN")
    
    success_main = False
    success_city = False

    # Отправка в ГЛАВНЫЙ чат
    if main_chat_id:
        main_chat_id = main_chat_id.strip()
        success_main = send_to_telegram(message_text, main_chat_id)
        if success_main:
            print(f"➡️ Заказ отправлен в ГЛАВНЫЙ чат ({main_chat_id})")
        else:
            print(f"❌ Ошибка отправки в ГЛАВНЫЙ чат {main_chat_id}")
    else:
        print("⚠️ ВНИМАНИЕ: Переменная GROUP_MAIN не найдена в окружении! Главный чат пропущен.")
    
    # Отправка в чат ГОРОДА
    city_chat_id = get_chat_id_by_city(order.get('city', ''))
    if city_chat_id and city_chat_id != main_chat_id:
        success_city = send_to_telegram(message_text, city_chat_id)
        if success_city:
            print(f"➡️ Заказ продублирован в чат города {order.get('city')} ({city_chat_id})")
        else:
            print(f"❌ Ошибка отправки в чат ГОРОДА {city_chat_id}")
            
    return success_main or success_city
