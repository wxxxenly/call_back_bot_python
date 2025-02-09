import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
import random

# Токен вашего Telegram-бота
TOKEN = '7006214794:AAFYzuBE62Dk1jyDWNhze3chtJfXmlPWrAI'

# ID оператора (или группа операторов)
OPERATOR_CHAT_ID = '998820941'

# Создание бота
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения данных пользователей
user_data = {}
captcha_data = {}

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

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    # Генерируем капчу
    captcha_question, correct_answer = generate_captcha()
    captcha_data[message.chat.id] = {'question': captcha_question, 'answer': correct_answer}

    # Отправляем вопрос и варианты ответа
    options = [correct_answer] + [random.randint(-5, 20) for _ in range(3)]
    random.shuffle(options)  # Перемешиваем варианты ответа
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for option in options:
        keyboard.add(KeyboardButton(str(option)))

    bot.send_message(message.chat.id, f"Для использования бота пройдите проверку:\n{captcha_question} = ?", reply_markup=keyboard)

# Обработчик ответов на капчу
@bot.message_handler(func=lambda message: message.chat.id in captcha_data)
def check_captcha(message):
    try:
        user_answer = int(message.text)
        correct_answer = captcha_data[message.chat.id]['answer']

        if user_answer == correct_answer:
            # Пользователь успешно прошёл проверку
            del captcha_data[message.chat.id]
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton("Позвать оператора"))
            bot.send_message(message.chat.id, "Вы успешно прошли проверку! Теперь можете использовать бота.", reply_markup=keyboard)
        else:
            # Генерируем новую капчу
            captcha_question, correct_answer = generate_captcha()
            captcha_data[message.chat.id] = {'question': captcha_question, 'answer': correct_answer}

            # Отправляем новый вопрос и варианты ответа
            options = [correct_answer] + [random.randint(-5, 20) for _ in range(3)]
            random.shuffle(options)  # Перемешиваем варианты ответа
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for option in options:
                keyboard.add(KeyboardButton(str(option)))

            bot.send_message(message.chat.id, f"Неверный ответ. Попробуйте снова:\n{captcha_question} = ?", reply_markup=keyboard)

    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, выберите один из предложенных вариантов.")

# Обработчик нажатия кнопки "Позвать оператора"
@bot.message_handler(func=lambda message: message.text == "Позвать оператора")
def request_phone(message):
    if message.chat.id not in captcha_data:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton("Отправить номер", request_contact=True))
        bot.send_message(message.chat.id, "Поделитесь своим номером телефона, пожалуйста.", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик получения контакта
@bot.message_handler(content_types=['contact'])
def request_location(message):
    if message.chat.id not in captcha_data:
        phone_number = message.contact.phone_number
        user_data[message.chat.id] = {'phone': phone_number}  # Сохраняем номер телефона
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(KeyboardButton("Отправить локацию", request_location=True))
        bot.send_message(message.chat.id, "Теперь поделитесь своей геолокацией, пожалуйста.", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик получения геолокации
@bot.message_handler(content_types=['location'])
def request_message(message):
    if message.chat.id not in captcha_data:
        try:
            location = message.location
            user_data[message.chat.id]['location'] = location  # Сохраняем геолокацию
            bot.send_message(message.chat.id, "Введите сообщение, которое вы хотите передать оператору.")
        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при обработке геолокации. Пожалуйста, попробуйте снова.")
            print(f"Error in request_message: {e}")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Обработчик получения текстового сообщения
@bot.message_handler(func=lambda message: 'phone' in user_data.get(message.chat.id, {}) and 'location' in user_data.get(message.chat.id, {}))
def send_to_operator(message):
    if message.chat.id not in captcha_data:
        try:
            # Получаем данные из user_data
            phone_number = user_data[message.chat.id]['phone']
            location = user_data[message.chat.id]['location']
            message_text = message.text

            if not phone_number or not location or not message_text:
                bot.send_message(message.chat.id, "Не все данные были получены. Пожалуйста, начните заново.")
                return

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

            # Отправка текстового сообщения оператору
            bot.send_message(OPERATOR_CHAT_ID, operator_message, reply_markup=inline_keyboard)

            # Отправка геолокации как отдельное сообщение
            bot.send_location(OPERATOR_CHAT_ID, latitude=location.latitude, longitude=location.longitude)

            # Уведомление пользователя о отправке запроса
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(KeyboardButton("Позвать оператора"))
            bot.send_message(message.chat.id, "Ваш запрос был успешно отправлен оператору.", reply_markup=keyboard)

            # Очищаем данные пользователя
            del user_data[message.chat.id]

        except Exception as e:
            bot.send_message(message.chat.id, "Произошла ошибка при отправке запроса оператору. Пожалуйста, попробуйте снова.")
            print(f"Error in send_to_operator: {e}")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

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
    if message.chat.id not in captcha_data:
        bot.send_message(message.chat.id, "Не понимаю, что вы хотите сделать. Пожалуйста, используйте кнопки или команды.")
    else:
        bot.send_message(message.chat.id, "Сначала пройдите проверку!")

# Запуск бота
if __name__ == '__main__':
    bot.polling(non_stop=True)
