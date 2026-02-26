import requests
import os

def send_to_telegram(message_text):
    token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("GROUP_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
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
        f"🚚 <b>Доставка:</b> {order['delivery_method']}\n"
        f"📅 <b>Дата доставки:</b> {order['delivery_date']}\n"
        f"⏰ <b>Время доставки:</b> {order['delivery_time']}\n"
        f"📍 <b>Адрес:</b> {order['delivery_address']}\n"
        f"💳 <b>Оплата:</b> {order['payment_method']}\n"
        f"🏪 <b>Магазин:</b> {order['shop_address']}\n"
        f"📝 <b>Комментарий:</b> {order['comment']}\n"
        f"\n━━━━━━━━━━━━━━━━━━━━"
    )
    return text
