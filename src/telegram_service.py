import requests
import os

def get_chat_id_by_city(city):
    """Возвращает ID чата в зависимости от города."""
    city = city.lower()
    
    # Проверяем наличие чатов для городов
    kem_chat = os.getenv("GROUP_KEMEROVO")
    kras_chat = os.getenv("GROUP_KRASNOYARSK")
    shere_chat = os.getenv("GROUP_SHEREGESH")
    
    if "кемерово" in city and kem_chat:
        return kem_chat
    elif "красноярск" in city and kras_chat:
        return kras_chat
    elif "шерегеш" in city and shere_chat:
        return shere_chat
    else:
        return None  # Возвращаем None, если чат для города не найден

def send_to_telegram(message_text, chat_id):
    """Отправляет сообщение в указанный чат."""
    token = os.getenv("BOT_TOKEN")
    
    if not chat_id:
        print(f"⚠️ Chat ID не указан, сообщение не отправлено")
        return False
    
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
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False

def format_order_message(order):
    """Создает красивое сообщение из словаря заказа."""
    text = (
        f"🛒 <b>НОВЫЙ ЗАКАЗ #{order['order_number']}</b>\n\n"
        f"👤 <b>Покупатель:</b> {order['customer']}\n"
        f"📞 <b>Телефон:</b> <a href='tel:{order['phone']}'>{order['phone']}</a>\n"
        f"📅 <b>Дата доставки:</b> {order['delivery_date']}\n"
        f"🕐 <b>Время доставки:</b> {order['delivery_time']}\n"
        f"🚚 <b>Доставка:</b> {order['delivery_method']}\n"
        f"📍 <b>Адрес:</b> {order['delivery_address']}\n"
        f"💳 <b>Оплата:</b> {order['payment_method']}\n"
        f"🏪 <b>Магазин:</b> {order['shop_address']}\n"
        f"📝 <b>Комментарий:</b> {order['comment']}\n"
        f"\n━━━━━━━━━━━━━━━━━━━━"
    )
    return text
