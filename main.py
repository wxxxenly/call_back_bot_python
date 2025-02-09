import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
import random
import logging
import time
from threading import Thread

# Токен вашего Telegram-бота
TOKEN = '7006214794:AAFYzuBE62Dk1jyDWNhze3chtJfXmlPWrAI'

# ID оператора (или группа операторов)
OPERATOR_CHAT_ID = '998820941'

# ID администратора для административной панели
ADMIN_ID = '998820941'

# Создание бота
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения данных пользователей
user_data = {}
captcha_data = {}
spam_protection = {}
blocked_users = set()
user_history = {}

# Логирование действий пользователей
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Генерация математической капчи
def generate_captcha():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    operation = random.choice(['+', '-'])
    if operation == '+':
        correct_answer = num1 + num2
    else:
        correct_answer = num1 - num2
    return f"{num1} {operation} {num2}", correct_answer

# Проверка таймаута капчи
def check_captcha_timeout(chat_id):
    if captcha_data.get(chat_id, {}).get('timestamp', 0) + 60 < time.time():  # Таймаут 60 секунд
        del captcha_data[chat_id]
        bot.send_message(chat_id, "Время прохождения капчи истекло. Попробуйте снова командой /start.")

# Фоновая очистка данных
def cleanup_user_data():
    while True:
        time.sleep(3600)  # Каждый час
        current_time = time.time()
        for chat_id in list(user_data.keys()):
            if current_time - user_data[chat_id].get('timestamp', 0) > 3600:
                del user_data[chat_id]
        for chat_id in list(captcha_data.keys()):
            if current_time - captcha_data[chat_id].get('timestamp', 0) > 60:
                del captcha_data[chat_id]

Thread(target=cleanup_user_data, daemon=True).start()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id in blocked_users:
        bot.send_message(message.chat.id, "Вы заблокированы. Обратитесь к администратору.")
        return

    # Генерируем капчу
    captcha_question, correct_answer = generate_captcha()
    captcha_data[message.chat.id] = {
        'question': captcha_question,
        'answer': correct_answer,
        'attempts': 0,
        'timestamp': time.time()
    }

    # Отправляем вопрос и варианты ответа
    options = [correct_answer] + [random.randint(-5, 20) for _ in range(3)]
    random.shuffle(options)  # Перемешиваем варианты ответа
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for option in options:
        keyboard.add(KeyboardButton(str(option)))

    bot.send_message(message.chat.id, f"Для использования бота пройдите проверку:\n{captcha_question} = ?", reply_markup=keyboard)
    logger.info(f"User {message.chat.id} started the bot.")

# Обработчик ответов на капчу
@bot.message_handler(func=lambda message: message.chat.id in captcha_data)
def check_captcha(message):
    if message.chat.id in blocked_users:
        bot.send_message(message.chat.id, "Вы заблокированы. Обратитесь к администратору.")
        return

    try:
        user_answer = int(message.text)
        correct_answer = captcha_data[message.chat.id]['answer']
        attempts = captcha_data[message.chat.id]['attempts']

        if user_answer == correct_answer:
            # Пользователь успешно прошёл проверку
            del captcha_data[message.chat.id]
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton("Позвать оператора"), KeyboardButton("FAQ"))
            bot.send_message(message.chat.id, "Вы успешно прошли проверку! Теперь можете использовать бота.", reply_markup=keyboard)
            logger.info(f"User {message.chat.id} passed the captcha.")
        else:
            # Увеличиваем количество попыток
            captcha_data[message.chat.id]['attempts'] += 1
            if captcha_data[message.chat.id]['attempts'] >= 3:
                blocked_users.add(message.chat.id)
                bot.send_message(message.chat.id, "Вы исчерпали все попытки. Вы заблокированы.")
                del captcha_data[message.chat.id]
                logger.warning(f"User {message.chat.id} failed captcha 3 times and was blocked.")
                return

            # Генерируем новую капчу
            captcha_question, correct_answer = generate_captcha()
            captcha_data[message.chat.id]['question'] = captcha_question
            captcha_data[message.chat.id]['answer'] = correct_answer
            captcha_data[message.chat.id]['timestamp'] = time.time()

            # Отправляем новый вопрос и варианты ответа
            options = [correct_answer] + [random.randint(-5, 20) for _ in range(3)]
            random.shuffle(options)  # Перемешиваем варианты ответа
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for option in options:
                keyboard.add(KeyboardButton(str(option)))

            bot.send_message(message.chat.id, f"Неверный ответ. Попробуйте снова:\n{captcha_question} = ?", reply_markup=keyboard)

    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, выберите один из предложенных вариантов.")

# Проверка спама
def is_spam(chat_id):
    last_request = spam_protection.get(chat_id, 0)
    if time.time() - last_request < 0.5:  # Ограничение 1 запрос в минуту
        return True
    spam_protection[chat_id] = time.time()
    return False

# Обработчик нажатия кнопки "FAQ"
@bot.message_handler(func=lambda message: message.text == "FAQ")
def show_faq(message):
    if message.chat.id not in captcha_data:
        # Создаем клавиатуру с кнопками "Позвать оператора" и "FAQ"
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Позвать оператора"), KeyboardButton("FAQ"))
        bot.send_message(message.chat.id, faq_text, reply_markup=keyboard)

# Обработчик нажатия кнопки "Позвать оператора"
@bot.message_handler(func=lambda message: message.text == "Позвать оператора")
def request_phone(message):
    if message.chat.id in blocked_users or is_spam(message.chat.id):
        bot.send_message(message.chat.id, "Слишком много запросов. Пожалуйста, подождите.")
        return

    if message.chat.id not in captcha_data:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton("Отправить номер", request_contact=True))
        bot.send_message(message.chat.id, "Поделитесь своим номером телефона, пожалуйста.", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик получения контакта
@bot.message_handler(content_types=['contact'])
def request_location(message):
    if message.chat.id in blocked_users or is_spam(message.chat.id):
        bot.send_message(message.chat.id, "Слишком много запросов. Пожалуйста, подождите.")
        return

    if message.chat.id not in captcha_data:
        phone_number = message.contact.phone_number
        user_data[message.chat.id] = {'phone': phone_number, 'timestamp': time.time()}
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton("Отправить локацию", request_location=True))
        bot.send_message(message.chat.id, "Теперь поделитесь своей геолокацией, пожалуйста.", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик получения геолокации
@bot.message_handler(content_types=['location'])
def request_message(message):
    if message.chat.id in blocked_users or is_spam(message.chat.id):
        bot.send_message(message.chat.id, "Слишком много запросов. Пожалуйста, подождите.")
        return
    if message.chat.id not in captcha_data:
        try:
            location = message.location
            user_data[message.chat.id]['location'] = location
            user_data[message.chat.id]['timestamp'] = time.time()

            # Удаляем клавиатуру после получения геолокации
            bot.send_message(message.chat.id, "Геолокация успешно получена. Отправьте фотографию (необязательно) или текстовое сообщение.", reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при обработке геолокации. Пожалуйста, попробуйте снова.")
            print(f"Error in request_message: {e}")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик получения фото
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id not in captcha_data:
        file_info = bot.get_file(message.photo[-1].file_id)
        user_data[message.chat.id]['photo'] = file_info.file_id
        bot.send_message(message.chat.id, "Фото успешно загружено. Введите сообщение для оператора.")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик текстового сообщения
@bot.message_handler(func=lambda message: 'phone' in user_data.get(message.chat.id, {}) and 'location' in user_data.get(message.chat.id, {}))
def send_to_operator(message):
    if message.chat.id in blocked_users or is_spam(message.chat.id):
        bot.send_message(message.chat.id, "Слишком много запросов. Пожалуйста, подождите.")
        return

    if message.chat.id not in captcha_data:
        try:
            phone_number = user_data[message.chat.id]['phone']
            location = user_data[message.chat.id]['location']
            message_text = message.text
            photo_id = user_data[message.chat.id].get('photo')

            if not phone_number or not location or not message_text:
                bot.send_message(message.chat.id, "Не все данные были получены. Пожалуйста, начните заново.")
                return

            # Сохраняем историю запросов
            user_history.setdefault(message.chat.id, []).append({
                'phone': phone_number,
                'location': (location.latitude, location.longitude),
                'message': message_text,
                'timestamp': time.time()
            })

            # Формирование текстового сообщения для оператора
            operator_message = (
                f"Новый запрос от пользователя:\n"
                f"ID пользователя: {message.chat.id}\n"
                f"Никнейм: @{message.from_user.username}\n"
                f"Номер телефона: {phone_number}\n"
                f"Сообщение: {message_text}\n\n"
                f"Перейти в чат с пользователем в WhatsApp: "
            )

            # Создание ссылки для перехода в WhatsApp
            whatsapp_link = f"https://wa.me/{phone_number.lstrip('+')}"
            inline_keyboard = InlineKeyboardMarkup()
            inline_keyboard.add(InlineKeyboardButton("Перейти в WhatsApp", url=whatsapp_link))

            # Отправка данных оператору
            bot.send_message(OPERATOR_CHAT_ID, operator_message, reply_markup=inline_keyboard)
            bot.send_location(OPERATOR_CHAT_ID, latitude=location.latitude, longitude=location.longitude)
            if photo_id:
                bot.send_photo(OPERATOR_CHAT_ID, photo_id)

            # Уведомление пользователя
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton("Позвать оператора"),("FAQ"))
            bot.send_message(message.chat.id, "Ваш запрос был успешно отправлен оператору.", reply_markup=keyboard)

            # Очищаем данные пользователя
            del user_data[message.chat.id]

        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при отправке запроса оператору. Пожалуйста, попробуйте снова.")
            print(f"Error in send_to_operator: {e}")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# FAQ
faq_text = (
    "Часто задаваемые вопросы:\n"
    "1. Как работает бот?\nОтвет: Бот помогает связаться с оператором.\n"
    "2. Что делать, если бот не отвечает?\nОтвет: Попробуйте позже или обратитесь к администратору."
)


# Таймаут на использование функционала бота
def check_usage_timeout(chat_id):
    if user_data.get(chat_id, {}).get('timestamp', 0) + 300 < time.time():  # Таймаут 5 минут
        del user_data[chat_id]
        bot.send_message(chat_id, "Время использования бота истекло. Начните заново командой /start.")

# Обработчик отмены действия
@bot.message_handler(commands=['cancel'])
def cancel(message):
    if message.chat.id in captcha_data:
        del captcha_data[message.chat.id]
        bot.send_message(message.chat.id, "Проверка отменена. Начните заново командой /start.")
    else:
        bot.send_message(message.chat.id, "Действие отменено. Если нужно, начните заново.")

# Обработчик непредвиденных сообщений
@bot.message_handler(func=lambda message: True)
def fallback(message):
    if message.chat.id in blocked_users:
        bot.send_message(message.chat.id, "Вы заблокированы. Обратитесь к администратору.")
        return

    if message.chat.id not in captcha_data:
        bot.send_message(message.chat.id, "Не понимаю, что вы хотите сделать. Пожалуйста, используйте кнопки или команды.")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Запуск бота
if __name__ == '__main__':
    bot.polling(non_stop=True)
