import time
import requests
import _thread as thread
import telebot
from telebot import types
import sqlite3
from whois import whois
from decouple import config

BOT_ID = config('botID', default='')

if not BOT_ID:
    print('Не указан ID бота! Завершение программы')
    exit()

bot = telebot.TeleBot(BOT_ID)

DB_NAME = 'db.sqlite'

REQUEST_FREQUENCY = 1  # in minutes
HTTP = 'http://'
HTTPS = 'http://'

SHOW_DOMAINS_BTN = 'Показать мои домены'
ADD_DOMAIN_BTN = 'Добавить домен'
REMOVE_DOMAIN_BTN = 'Удалить домен'
CANCEL_ADD_BTN = 'Отменить добавление'
CANCEL_RM_BTN = 'Отменить удаление'

DEFAULT_ANSWER = 'Отменить удаление'

default_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
add_domain = types.KeyboardButton(ADD_DOMAIN_BTN)
rm_domain = types.KeyboardButton(REMOVE_DOMAIN_BTN)
my_domains = types.KeyboardButton(SHOW_DOMAINS_BTN)
default_markup.add(add_domain, rm_domain, my_domains)

cancel_add_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
cancel_add_btn = types.KeyboardButton(CANCEL_ADD_BTN)
cancel_add_markup.add(cancel_add_btn)


def requests_demon():
    """Демон, который опрашивает домены на доступность"""
    while True:
        items = execute_sql('SELECT * from domains').fetchall()

        for item in items:
            domain = item[1]
            user_id = item[2]
            url = HTTP + str(domain)

            try:
                response_code = requests.get(url).status_code
                if response_code >= 400:
                    raise Exception

            except Exception as e:
                bot.send_message(user_id, f'Сайт {url} не доступен.')

        time.sleep(REQUEST_FREQUENCY * 60)


def execute_sql(command):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    res = c.execute(command)
    conn.commit()
    return res


execute_sql('CREATE TABLE IF NOT EXISTS domains (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT, '
            'user_id INTEGER UNIQUE, is_alive BOOLEAN, last_change INTERGER);')
PINGER_THREAD_ID = thread.start_new_thread(requests_demon, ())


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}', reply_markup=default_markup)


# todo: you don't have domains yet
@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_DOMAINS_BTN)
def sh_all(message):
    """Вывод всех доменов ПОЛЬЗОВАТЕЛЯ"""
    domain_str = 'Ваши домены:\n'

    domains = execute_sql(f'SELECT (domain) from domains WHERE user_id = {message.from_user.id}').fetchall()

    for domain in domains:
        domain_str += f'- {domain[0]} \n'

    bot.send_message(message.chat.id, domain_str)


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == ADD_DOMAIN_BTN)
def add_d(message):
    """Инициализация ДОБАВЛЕНИЯ домена"""
    bot.send_message(message.chat.id, 'Введите домен (example.com): ', reply_markup=cancel_add_markup)
    bot.register_next_step_handler(message, get_add_d)


def get_add_d(message):
    """Ввод домена на ДОБАВЛЕНИЕ"""
    if message.text == CANCEL_ADD_BTN:
        bot.send_message(message.chat.id, DEFAULT_ANSWER, reply_markup=default_markup)
        return

    try:
        domain_obj = whois(message.text)

        if not domain_obj.get('domain_name'):
            raise Exception

        execute_sql(f'INSERT INTO domains (domain, user_id) VALUES ("{message.text}", {message.from_user.id})')
        bot.send_message(message.chat.id, f'*** Домен {message.text} был успешно добавлен ***',
                         reply_markup=default_markup)
    except Exception:
        bot.send_message(message.chat.id, f'Ошибка! Указан несуществующий домен', reply_markup=default_markup)


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == REMOVE_DOMAIN_BTN)
def rm_d(message):
    """Инициализация УДАЛЕНИЯ домена"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    domains = execute_sql(f'SELECT (domain) from domains WHERE user_id = {message.from_user.id}').fetchall()

    for domain in domains:
        markup.add(types.KeyboardButton(domain[0]))

    markup.add(types.KeyboardButton(CANCEL_RM_BTN))

    bot.send_message(message.chat.id, 'Выберите домен для удаления:', reply_markup=markup)
    bot.register_next_step_handler(message, get_rm_d)


def get_rm_d(message):
    """Ввод домена на УДАЛЕНИЕ"""
    if message.text == CANCEL_RM_BTN:
        bot.send_message(message.chat.id, DEFAULT_ANSWER, reply_markup=default_markup)
        return

    if not message.text:
        bot.send_message(message.chat.id, 'Введите домен !')
        return

    execute_sql(f'DELETE FROM domains WHERE user_id = {message.from_user.id} AND domain = "{message.text}"')

    bot.send_message(message.chat.id, f'*** Домен {message.text} был успешно удален ***', reply_markup=default_markup)


@bot.message_handler(chat_types=["private"], content_types=['text'])
def unknown(message):
    bot.send_message(message.chat.id, 'Неизвестная команда')


bot.polling(none_stop=True)
