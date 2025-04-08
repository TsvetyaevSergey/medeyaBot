import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import xml.etree.ElementTree as ET
import requests
import time
import json
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация из .env
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMINS = [784810066, 842949819]  # ID администраторов
DEFAULT_URL = 'https://www.nmls.ru/data/feed/yandex/agency1003479.xml'
NAMESPACE = '{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}'

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Загрузка сохраненных данных
try:
    with open('data.json', 'r', encoding='utf-8') as f:
        properties = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    properties = []

try:
    with open('url.txt', 'r') as f:
        current_url = f.read().strip()
except FileNotFoundError:
    current_url = DEFAULT_URL

agents = list(set(prop['agent'] for prop in properties if 'agent' in prop))


# Клавиатуры
def main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("👤 По агенту"),
        KeyboardButton("🏠 По категории"),
        KeyboardButton("🔄 Обновить данные")
    ]
    if user_id in ADMINS:
        buttons.append(KeyboardButton("⚙️ Ссылка (Админ)"))
    markup.add(*buttons)
    return markup

def deal_type_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🏠 Аренда"), KeyboardButton("💰 Продажа"))
    return markup

def category_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    categories = [
        "🏘️ Все", "🏠 1-комнатная", "🏠 2-комнатная",
        "🏠 3-комнатная", "🏠 4-комнатная", "🌳 Участок",
        "🏡 Дом", "🚗 Гараж", "🚪 Комната", "🏪 Коммерческая"
    ]
    markup.add(*categories)
    return markup


def agent_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    formatted_agents = [f"👤 {agent}" for agent in agents]
    markup.add(*formatted_agents)
    return markup


def yes_no_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✅ Вывести", "❌ Отмена")
    return markup


# Парсинг XML
def safe_find(element, path, default=None):
    elem = element.find(path)
    return elem.text if elem is not None else default


def parse_xml(url):
    global properties, agents
    try:
        response = requests.get(url)
        root = ET.fromstring(response.content)
        new_properties = []
        new_agents = []

        for offer in root.findall(f'{NAMESPACE}offer'):
            prop = {
                'id': offer.get('internal-id', 'N/A'),
                'type': safe_find(offer, f'{NAMESPACE}type', 'Не указано'),
                'category': safe_find(offer, f'{NAMESPACE}category', 'Не указано'),
                'rooms': safe_find(offer, f'{NAMESPACE}rooms', '0'),
                'status': safe_find(offer, f'{NAMESPACE}status', '1'),
                'price': safe_find(offer, f'{NAMESPACE}price/{NAMESPACE}value', '0'),
                'agent': safe_find(offer, f'{NAMESPACE}sales-agent/{NAMESPACE}name', 'Нет агента'),
                'address': safe_find(offer, f'{NAMESPACE}location/{NAMESPACE}address') or 'Не задан',
                'area': safe_find(offer, f'{NAMESPACE}area/{NAMESPACE}value', '0')
            }

            new_properties.append(prop)
            if prop['agent'] not in new_agents:
                new_agents.append(prop['agent'])

        # Сохранение данных
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(new_properties, f, ensure_ascii=False, indent=2)

        properties = new_properties
        agents = new_agents
        return True

    except Exception as e:
        print(f"Ошибка парсинга: {str(e)}")
        return False


# Обработчики сообщений
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                    "🏡 Добро пожаловать в бот недвижимости!",
                    reply_markup=main_keyboard(message.from_user.id))



def ask_deal_type(message, next_step):
    bot.send_message(message.chat.id,
                    "📊 Выберите тип сделки:",
                    reply_markup=deal_type_keyboard())
    bot.register_next_step_handler(message, next_step)

@bot.message_handler(func=lambda m: m.text in ["👤 По агенту", "👤 Выбор по Агенту"])
def select_agent_flow(message):
    ask_deal_type(message, process_agent_selection)


def process_agent_selection(message):
    user_data = {'deal_type': message.text.replace("🏠 ", "").replace("💰 ", "")}
    bot.send_message(message.chat.id,
                    "👥 Выберите агента:",
                    reply_markup=agent_keyboard())
    bot.register_next_step_handler(message, process_agent_choice, user_data)

def process_agent_choice(message, user_data):
    user_data['agent'] = message.text.replace("👤 ", "")
    bot.send_message(message.chat.id,
                    "📦 Выберите категорию:",
                    reply_markup=category_keyboard())
    bot.register_next_step_handler(message, process_category_choice, user_data)

def process_search(message, user_data):
    user_data['market'] = message.text
    filtered = filter_properties(user_data)
    bot.send_message(message.chat.id, f"🔍 Найдено объектов: {len(filtered)}", reply_markup=yes_no_keyboard())
    bot.register_next_step_handler(message, show_results, filtered)


def show_results(message, filtered):
    if message.text == "✅ Вывести":
        for prop in filtered:
            send_property_info(message.chat.id, prop)
            time.sleep(0.5)
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda m: m.text in ["🏠 По категории", "🏠 Выбор по Категории"])
def select_category_flow(message):
    ask_deal_type(message, process_category_selection)

def process_category_selection(message):
    user_data = {'deal_type': message.text.replace("🏠 ", "").replace("💰 ", "")}
    bot.send_message(message.chat.id,
                    "📦 Выберите категорию:",
                    reply_markup=category_keyboard())
    bot.register_next_step_handler(message, process_category_choice, user_data)

def process_category_choice(message, user_data):
    user_data['category'] = message.text
    filtered = filter_properties(user_data)
    bot.send_message(message.chat.id,
                    f"🔍 Найдено объектов: {len(filtered)}",
                    reply_markup=yes_no_keyboard())
    bot.register_next_step_handler(message, show_results, filtered)

def filter_properties(data):
    result = []
    for prop in properties:
        match = True

        # Фильтр по типу сделки
        if 'deal_type' in data:
            match &= (prop['type'].lower() == data['deal_type'].lower())

        # Фильтр по агенту
        if 'agent' in data:
            match &= (prop['agent'] == data['agent'])

        # Фильтр по категории
        if 'category' in data and data['category'] != "🏘️ Все":
            category = data['category']
            if category.startswith("🏠"):
                room_count = category.split('-')[0][-1]
                match &= (
                        prop['category'] == "квартира"
                        and prop['rooms'] == room_count
                )
            else:
                category_map = {
                    "🌳 Участок": "участок",
                    "🏡 Дом": "дом",
                    "🚗 Гараж": "гараж",
                    "🚪 Комната": "комната",
                    "🏪 Коммерческая": "коммерческая"
                }
                match &= (prop['category'] == category_map.get(category, ""))

        if match:
            result.append(prop)
    return result


def send_property_info(chat_id, prop):
    emoji_map = {
        "квартира": "🏢", "участок": "🌳", "дом": "🏠",
        "гараж": "🚗", "комната": "🚪", "коммерческая": "🏪"
    }
    price = format(int(prop['price']), ',') if prop['price'].isdigit() else prop['price']
    if prop['status'] == "1": status = "🟢 Внешний 🟢"
    else:
        status = "🟣 Внутренний 🟣"

    text = (
        f"{emoji_map.get(prop['category'], '🏠')} {prop['category'].capitalize()} ({prop['type'].capitalize()})\n"
        f"📏 Площадь: {prop.get('area', 'N/A')} м²\n"
        f"🛏 Комнат: {prop['rooms']}\n"
        f"💰 Цена: {price} RUB\n"
        f"📍 Адрес: {prop['address']}\n\n"
        f"🤝 Рынок: {status}\n\n"
        f"👤 Агент: {prop['agent']}\n"
        f"🔗 Ссылка: http://nn.nmls.ru/realty/view/{prop['id']}"
    )
    bot.send_message(chat_id, text)


@bot.message_handler(func=lambda m: m.text == "🔄 Обновить данные")
def update_data(message):
    if parse_xml(current_url):
        bot.send_message(message.chat.id, "✅ Данные успешно обновлены!",
                         reply_markup=main_keyboard(message.from_user.id))
    else:
        bot.send_message(message.chat.id, "❌ Ошибка обновления! Проверьте ссылку.",
                         reply_markup=main_keyboard(message.from_user.id))


@bot.message_handler(func=lambda m: m.text == "⚙️ Изменить ссылку (Админ)" and m.from_user.id in ADMINS)
def change_url(message):
    bot.send_message(message.chat.id, "🔗 Введите новую ссылку на XML:")
    bot.register_next_step_handler(message, save_new_url)


def save_new_url(message):
    global current_url
    current_url = message.text
    with open('url.txt', 'w') as f:
        f.write(current_url)
    bot.send_message(message.chat.id, "✅ Ссылка успешно обновлена!", reply_markup=main_keyboard(message.from_user.id))


if __name__ == '__main__':
    print("Бот запущен!")
    bot.polling(none_stop=True)
