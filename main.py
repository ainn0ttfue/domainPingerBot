import time
from datetime import datetime
from ssl_info import ssl_expiry_datetime
import requests
import _thread as thread
import telebot
from telebot import types
import sqlite3
from whois import whois
from decouple import config

BOT_ID = config('botID', default='')

if not BOT_ID:
    print('Не указан ID бота! Завершение программы...')
    exit()

bot = telebot.TeleBot(BOT_ID)

DB_NAME = '/domains/db.sqlite'
# DB_NAME = 'db.sqlite'

REQUEST_FREQUENCY = 60  # in seconds
SSL_WARNING_EXPIRE_DAYS = 10
SSL_ALERT_EXPIRE_DAYS = 5
HTTP = 'http://'
HTTPS = 'http://'

OK_EMOJI = '\u2705'
ERROR_EMOJI = '\u274C'
WARNING_EMOJI = '\u26A0'

SHOW_DOMAINS_BTN = 'Показать мои домены'
ADD_DOMAIN_BTN = 'Добавить домен'
REMOVE_DOMAIN_BTN = 'Удалить домен'
CANCEL_ADD_BTN = 'Отменить добавление'
CANCEL_RM_BTN = 'Отменить удаление'
SHOW_SSL_BTN = 'Показать статус SSL'

DEFAULT_ANSWER = 'OK'

default_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
add_domain = types.KeyboardButton(ADD_DOMAIN_BTN)
rm_domain = types.KeyboardButton(REMOVE_DOMAIN_BTN)
my_domains = types.KeyboardButton(SHOW_DOMAINS_BTN)
ssl_status = types.KeyboardButton(SHOW_SSL_BTN)
default_markup.add(add_domain, rm_domain, my_domains, ssl_status)

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
            was_alive = item[3]
            last_change = datetime.utcfromtimestamp(item[4]).strftime('%H:%M %Y-%m-%d')

            domain_status = get_domain_status(domain)
            is_alive = domain_status.get('status')

            if not is_alive and was_alive:
                bot.send_message(user_id,
                                 f'{ERROR_EMOJI} ВНИМАНИЕ! Сайт {domain} недоступен. {domain_status.get("desc")}')
                execute_sql(f'UPDATE domains SET (is_alive, last_change) = (0, {int(time.time())}) '
                            f'WHERE user_id = {user_id} AND domain = "{domain}"')
            elif not is_alive and not was_alive:
                bot.send_message(user_id,
                                 f'{ERROR_EMOJI}Сайт {domain} не доступен (с {last_change}). {domain_status.get("desc")}')
            elif is_alive and not was_alive:
                bot.send_message(user_id, f'{OK_EMOJI} Сайт {domain} стал доступен.')
                execute_sql(f'UPDATE domains SET (is_alive, last_change) = (1, {int(time.time())}) '
                            f'WHERE user_id = {user_id} AND domain = "{domain}"')

        time.sleep(REQUEST_FREQUENCY * 15)


def ssl_requests_demon():
    """Демон, который опрашивает ssl"""
    while True:
        items = execute_sql('SELECT * from domains').fetchall()
        almost_expire = {}
        users_info_dict = {}
        ssl_info_str = "SSL сертификаты ваших доменов истекают через: \n"

        for item in items:
            domain = item[1]
            user_id = item[2]
            now = datetime.now()
            temp_emoji_str = OK_EMOJI

            try:
                expire = ssl_expiry_datetime(domain)
                diff = expire - now

                if not str(user_id) in users_info_dict:
                    users_info_dict[str(user_id)] = ssl_info_str

                if diff.days <= SSL_WARNING_EXPIRE_DAYS:
                    if not str(user_id) in almost_expire:
                        almost_expire[str(user_id)] = [domain]
                    else:
                        almost_expire[str(user_id)].append(domain)

                if diff.days <= SSL_WARNING_EXPIRE_DAYS:
                    temp_emoji_str = WARNING_EMOJI

                    if diff.days <= SSL_ALERT_EXPIRE_DAYS:
                        temp_emoji_str = ERROR_EMOJI

                users_info_dict[str(user_id)] += \
                    f"{temp_emoji_str} {diff.days} дня - {domain} ({expire.strftime('%Y-%m-%d')}) \n"

            except Exception as e:
                users_info_dict[str(user_id)] += f"{ERROR_EMOJI} *** НЕТ ДАННЫХ *** - {domain}\n"
                print(e)

        for usr_id, msg in users_info_dict.items():
            bot.send_message(int(usr_id), msg)

        if len(almost_expire):
            for usr_id, domains in almost_expire.items():
                bot.send_message(int(usr_id), f'ВНИМАНИЕ! SSL следующих доменов истекают менее чем через'
                                              f'{SSL_WARNING_EXPIRE_DAYS} дней: \n{"- ".join(domains)}')

        time.sleep(REQUEST_FREQUENCY * 60 * 24 * 10)  # every 10 day


def execute_sql(command):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    res = c.execute(command)
    conn.commit()
    return res


def get_domain_status(domain):
    url = HTTP + str(domain)

    try:
        response_code = requests.get(url).status_code
        if response_code >= 400:
            return {'status': False, 'desc': f'Error: {response_code}'}
    except Exception:
        return {'status': False, 'desc': 'Error: Unknown'}

    return {'status': True}


execute_sql('CREATE TABLE IF NOT EXISTS domains (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT, '
            'user_id INTEGER, is_alive BOOLEAN, last_change INTERGER);')
PINGER_THREAD_ID = thread.start_new_thread(requests_demon, ())
SSL_TEST_THREAD_ID = thread.start_new_thread(ssl_requests_demon, ())


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}', reply_markup=default_markup)


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_DOMAINS_BTN)
def sh_all(message):
    """Вывод всех доменов ПОЛЬЗОВАТЕЛЯ"""
    domains = execute_sql(f'SELECT * from domains WHERE user_id = {message.from_user.id}').fetchall()

    if not domains:
        bot.send_message(message.chat.id, 'Вы еще не добавили ни одного домена')
        return

    msg = 'Ваши домены:\n'

    for item in domains:
        domain = item[1]
        status = OK_EMOJI if item[3] else ERROR_EMOJI

        msg += f'{status} {domain}\n'

    bot.send_message(message.chat.id, msg)


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

    domain = message.text

    try:
        domain_obj = whois(domain)

        if not domain_obj.get('domain_name'):
            raise Exception

        domain_status = 1
        if not get_domain_status(domain).get('status'):
            domain_status = 0

        execute_sql(f'INSERT INTO domains (domain, user_id, is_alive, last_change) VALUES '
                    f'("{domain}", {message.from_user.id}, {domain_status}, {int(time.time())})')

        bot.send_message(message.chat.id, f'*** Домен {domain} был успешно добавлен ***',
                         reply_markup=default_markup)
    except Exception as e:
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


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_SSL_BTN)
def rm_d(message):
    """Показать статус SSL доменов"""
    domains = execute_sql(f'SELECT (domain) from domains WHERE user_id = {message.from_user.id}').fetchall()
    temp_str = 'SSL сертификаты ваших доменов истекают через: \n'

    for domain in domains:
        now = datetime.now()
        domain = str(domain[0])
        temp_emoji_str = OK_EMOJI

        try:
            expire = ssl_expiry_datetime(domain)
            diff = expire - now

            if diff.days <= SSL_WARNING_EXPIRE_DAYS:
                temp_emoji_str = WARNING_EMOJI

                if diff.days <= SSL_ALERT_EXPIRE_DAYS:
                    temp_emoji_str = ERROR_EMOJI

            temp_str += f"{temp_emoji_str} {diff.days} дня - {domain} ({expire.strftime('%Y-%m-%d')}) \n"

        except Exception as e:
            temp_str += f"{ERROR_EMOJI} *** НЕТ ДАННЫХ *** - {domain}\n"
            print(e)

    bot.send_message(message.chat.id, temp_str)


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
