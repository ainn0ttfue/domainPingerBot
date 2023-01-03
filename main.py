import time
from datetime import datetime
from ssl_info import ssl_expiry_datetime
import requests
import _thread as thread
import telebot
import sqlite3
from whois import whois
from decouple import config
from src.vars import *


def requests_demon():
    """Демон, который опрашивает домены на доступность"""
    while True:
        items = execute_sql('SELECT * from domains').fetchall()

        for item in items:
            domain = item[1]
            user_id = item[2]
            was_alive = item[3]
            last_change = datetime.utcfromtimestamp(item[4]).strftime('%H:%M %d.%m.%Y')

            domain_status = get_domain_status(domain)
            is_alive = domain_status.get('status')

            if not is_alive and was_alive:
                execute_sql(f'UPDATE domains SET (is_alive, last_change) = (0, {int(time.time())}) '
                            f'WHERE user_id = {user_id} AND domain = "{domain}"')
            elif not is_alive and not was_alive:
                bot.send_message(user_id,
                                 f'{ERROR_EMOJI} ВНИМАНИЕ! Сайт {domain} недоступен (с {last_change}). {domain_status.get("desc")}')
            elif is_alive and not was_alive:
                bot.send_message(user_id, f'{OK_EMOJI} Сайт {domain} стал доступен.')
                execute_sql(f'UPDATE domains SET (is_alive, last_change) = (1, {int(time.time())}) '
                            f'WHERE user_id = {user_id} AND domain = "{domain}"')

        time.sleep(60 * 15)  # every 15 minutes


def send_domains_info(user_id=False, info_type=False):
    """
    Get SSL or registration info of domains and inform users
    @type user_id : int
    @type info_type : str - ['SSL' or 'REGISTRATION']
    """
    if not info_type or info_type not in ['SSL', 'REGISTRATION']:
        raise Exception("Didn't set info_type parameter")

    if user_id:
        items = execute_sql(f'SELECT * FROM domains WHERE user_id = {user_id}').fetchall()
    else:
        items = execute_sql('SELECT * from domains').fetchall()

    if info_type == 'SSL':
        msg_caption_text = SSL_MSG_CAPTION
        msg_expire_warning = SSL_MSG_EXPIRE_WARNING
        expire_warning_limit = SSL_WARNING_EXPIRE_DAYS
        expire_alert_limit = SSL_ALERT_EXPIRE_DAYS
    else:
        msg_caption_text = REGISTRATION_MSG_CAPTION
        msg_expire_warning = REGISTRATION_MSG_EXPIRE_WARNING
        expire_warning_limit = DOMAIN_WARNING_REGISTRATION_DAYS
        expire_alert_limit = DOMAIN_ALERT_REGISTRATION_DAYS

    almost_expire = {}
    users_dict = {}

    for item in items:
        domain = item[1]
        user_id = item[2]
        temp_emoji = OK_EMOJI

        try:
            if info_type == 'SSL':
                expire = ssl_expiry_datetime(domain)
            else:
                expire = whois(domain).expiration_date

            diff = expire - datetime.now()

            if not str(user_id) in users_dict:
                users_dict[str(user_id)] = msg_caption_text + " \n"

            if diff.days <= expire_warning_limit:
                if not str(user_id) in almost_expire:
                    almost_expire[str(user_id)] = [domain]
                else:
                    almost_expire[str(user_id)].append(domain)

            if diff.days <= expire_warning_limit:
                temp_emoji = WARNING_EMOJI
                if diff.days <= expire_alert_limit:
                    temp_emoji = ERROR_EMOJI

            users_dict[str(user_id)] += \
                f"{temp_emoji} {diff.days} дня - {domain} ({expire.strftime('%d.%m.%Y')}) \n"

        except Exception as e:
            users_dict[str(user_id)] += f"{ERROR_EMOJI} НЕТ ДАННЫХ - {domain}\n"

    for usr_id, msg in users_dict.items():
        bot.send_message(int(usr_id), msg, parse_mode='Markdown')

    # Inform users about expires domains
    if len(almost_expire):
        for usr_id, domains in almost_expire.items():
            bot.send_message(int(usr_id), msg_expire_warning + f' {expire_warning_limit} дней: \n{"- ".join(domains)}',
                             parse_mode='Markdown')


def ssl_requests_demon():
    """Демон, который опрашивает ssl"""
    while True:
        send_domains_info(info_type='SSL')
        time.sleep(60 * 60 * 24)  # every day


def domains_registration_demon():
    """Демон, который опрашивает ssl"""
    while True:
        send_domains_info(info_type='REGISTRATION')
        time.sleep(60 * 60 * 24)  # every day


def execute_sql(command):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    res = c.execute(command)
    conn.commit()
    return res


def get_domain_status(domain):
    url = 'http://' + str(domain)

    try:
        response_code = requests.get(url).status_code
        if response_code >= 400:
            return {'status': False, 'desc': f'Error: {response_code}'}
    except Exception:
        return {'status': False, 'desc': 'Error: Unknown'}

    return {'status': True}


if __name__ == "__main__":
    BOT_ID = config('botID', default='')

    if not BOT_ID:
        print('Не указан ID бота! Завершение программы...')
        exit()

    bot = telebot.TeleBot(BOT_ID)

    DB_NAME = '/domains/db.sqlite'
    # DB_NAME = 'db.sqlite'

    execute_sql('CREATE TABLE IF NOT EXISTS domains (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT, '
                'user_id INTEGER, is_alive BOOLEAN, last_change INTERGER);')

    PINGER_THREAD_ID = thread.start_new_thread(requests_demon, ())
    SSL_TEST_THREAD_ID = thread.start_new_thread(ssl_requests_demon, ())
    DOMAIN_EXPIRE_THREAD_ID = thread.start_new_thread(domains_registration_demon, ())


    @bot.message_handler(commands=['start'])
    def start(message):
        bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}', reply_markup=default_markup)


    @bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_SSL_BTN)
    def sh_ssl(message):
        bot.send_message(message.chat.id, 'Собираю данные о SSL сертификатах...')
        send_domains_info(user_id=message.from_user.id, info_type='SSL')


    @bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_REGISTRATION_BTN)
    def sh_registration(message):
        bot.send_message(message.chat.id, 'Собираю данные о регистрации доменов...')
        send_domains_info(user_id=message.from_user.id, info_type='REGISTRATION')


    @bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_DOMAINS_BTN)
    def sh_all(message):
        """Вывод всех доменов ПОЛЬЗОВАТЕЛЯ"""
        domains = execute_sql(f'SELECT * from domains WHERE user_id = {message.from_user.id}').fetchall()

        if not domains:
            bot.send_message(message.chat.id, 'Вы еще не добавили ни одного домена')
            return

        msg = '*Ваши домены:*\n'

        for item in domains:
            domain = item[1]
            status = OK_EMOJI if item[3] else ERROR_EMOJI

            msg += f'{status} {domain}\n'

        bot.send_message(message.chat.id, msg, parse_mode='Markdown')


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


    def get_rm_d(message):
        """Ввод домена на УДАЛЕНИЕ"""
        if message.text == CANCEL_RM_BTN:
            bot.send_message(message.chat.id, DEFAULT_ANSWER, reply_markup=default_markup)
            return

        if not message.text:
            bot.send_message(message.chat.id, 'Введите домен !')
            return

        execute_sql(f'DELETE FROM domains WHERE user_id = {message.from_user.id} AND domain = "{message.text}"')

        bot.send_message(message.chat.id, f'*** Домен {message.text} был успешно удален ***',
                         reply_markup=default_markup)


    @bot.message_handler(chat_types=["private"], content_types=['text'])
    def unknown(message):
        bot.send_message(message.chat.id, 'Неизвестная команда')


    bot.polling(none_stop=True)
