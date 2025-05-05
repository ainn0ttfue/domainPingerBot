import telebot
import os
import random
from datetime import datetime
from ssl_info import ssl_expiry_datetime
import requests
from whois import whois
from decouple import config
from src.vars import *

def get_domains():
    usr_id = int(os.environ.get('ADMIN_USER_ID'))

    return [
        [None, "example.com", usr_id],
        [None, "ya.ru", usr_id],
        [None, "grim-irk.ru", usr_id],
        [None, "continent-export.ru", usr_id],
        [None, "loft-mebel38.ru", usr_id],
        [None, "alliance-decor.ru", usr_id],
        [None, "zerkalo-irk.ru", usr_id],
        [None, "aurora-irk.ru", usr_id],
        [None, "мебель-стайл.рф", usr_id],
        [None, "alita-mebel.ru", usr_id],
        [None, "360-irkutsk.ru", usr_id],
        [None, "new-era.dev", usr_id],
        [None, "mineral-irnitu.ru", usr_id],
        [None, "альянс-декор.рф", usr_id],
        [None, "айронвуд.рф", usr_id],
        [None, "delo-mebel.com", usr_id],
        [None, "specprompostavka.ru", usr_id],
        [None, "spp-store.ru", usr_id],
        [None, "ainn0ttfue-vpn.ru", usr_id],
    ]


def send_domains_info(user_id=False, info_type=False):
    """
    Get SSL or registration info of domains and inform users
    @type user_id : int
    @type info_type : str - ['SSL' or 'REGISTRATION']
    """
    if not info_type or info_type not in ['SSL', 'REGISTRATION']:
        raise Exception("Didn't set info_type parameter")

    items = get_domains()

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
                if type(expire) is list:
                    expire = expire[0]

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


def get_domain_status(domain):
    url = 'http://' + str(domain)

    try:
        response_code = requests.get(url).status_code
        if response_code >= 400:
            return {'status': False, 'desc': f'Error: {response_code}'}
    except Exception:
        return {'status': False, 'desc': 'Error: Unknown'}

    return {'status': True}

bot = telebot.TeleBot(os.environ.get('BOT_TOKEN'))

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}', reply_markup=default_markup)


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_SSL_BTN)
def sh_ssl(message):
    if message.chat.id != int(os.environ.get('ADMIN_USER_ID')):
        bot.send_message(message.chat.id, 'Access Denied')
        return
    bot.send_message(message.chat.id, 'Собираю данные о SSL сертификатах...')
    send_domains_info(user_id=message.from_user.id, info_type='SSL')


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_REGISTRATION_BTN)
def sh_registration(message):
    if message.chat.id != int(os.environ.get('ADMIN_USER_ID')):
        bot.send_message(message.chat.id, 'Access Denied')
        return
    bot.send_message(message.chat.id, 'Собираю данные о регистрации доменов...')
    send_domains_info(user_id=message.from_user.id, info_type='REGISTRATION')


@bot.message_handler(chat_types=["private"], func=lambda msg: msg.text == SHOW_DOMAINS_BTN)
def sh_all(message):
    """Вывод всех доменов ПОЛЬЗОВАТЕЛЯ"""
    if message.chat.id != int(os.environ.get('ADMIN_USER_ID')):
        bot.send_message(message.chat.id, 'Access Denied')
        return
    domains = get_domains()

    if not domains:
        bot.send_message(message.chat.id, 'Вы еще не добавили ни одного домена')
        return

    msg = '*Ваши домены:*\n'

    for item in domains:
        domain = item[1]
        msg += f'{domain}\n'

    bot.send_message(message.chat.id, msg, parse_mode='Markdown')


@bot.message_handler(chat_types=["private"], content_types=['text'])
def unknown(message):
    bot.send_message(message.chat.id, 'Неизвестная команда')


def handler(event, context):
    message = telebot.types.Update.de_json(event['body'])
    bot.process_new_updates([message])
    return {
        'statusCode': 200,
        'body': '!',
    }
