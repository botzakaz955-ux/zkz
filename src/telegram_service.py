import requests
import os

def get_chat_id_by_city(city):
    """Возвращает ID чата в зависимости от города."""
    city = city.lower()
    
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
        return None

def send_to_telegram(message_text, chat_id):
    """Отправляет сообщение в указанный чат."""
    token = os.getenv("BOT_TOKEN")
    
    if not chat_id:
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

def send_order(order):
    """
    Отправляет заказ в Telegram:
    1. Всегда в основной чат (GROUP_MAIN)
    2. Дополнительно в чат города, если он настроен и отличается от основного
    """
    message_text = format_order_message(order)
    main_chat_id = os.getenv("GROUP_MAIN")
    
    success_main = False
    success_city = False

    # 1. Отправка в ГЛАВНЫЙ чат (обязательно для всех городов)
    if main_chat_id:
        success_main = send_to_telegram(message_text, main_chat_id)
        if success_main:
            print("➡️ Успешно отправлено в ГЛАВНЫЙ чат.")
    else:
        print("⚠️ GROUP_MAIN не настроен, основной чат пропущен")
    
    # 2. Дублирование в чат ГОРОДА
    city_chat_id = get_chat_id_by_city(order.get('city', ''))
    
    if city_chat_id and city_chat_id != main_chat_id:
        success_city = send_to_telegram(message_text, city_chat_id)
        if success_city:
            print(f"➡️ Успешно продублировано в чат города ({order.get('city')}).")
            
    # Заказ считается успешно отправленным, если он ушел хотя бы в один чат
    return success_main or success_city
