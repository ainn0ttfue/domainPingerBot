from telebot import types

# Buttons
SHOW_DOMAINS_BTN = 'Показать мои домены'
ADD_DOMAIN_BTN = 'Добавить домен'
REMOVE_DOMAIN_BTN = 'Удалить домен'
CANCEL_ADD_BTN = 'Отменить добавление'
CANCEL_RM_BTN = 'Отменить удаление'
SHOW_SSL_BTN = 'Показать статус SSL'
SHOW_REGISTRATION_BTN = 'Показать статус регистрации доменов'

DEFAULT_ANSWER = 'OK'

# Emoji
OK_EMOJI = '\u2705'
ERROR_EMOJI = '\u274C'
WARNING_EMOJI = '\u26A0'

# Messages

SSL_MSG_CAPTION = '*SSL сертификаты ваших доменов истекают через*:'
SSL_MSG_EXPIRE_WARNING = f"{WARNING_EMOJI} *ВНИМАНИЕ!* {WARNING_EMOJI} \n " \
                         f"SSL следующих доменов истекают менее чем через"

REGISTRATION_MSG_CAPTION = '*Регистрация ваших доменов истекает через:*'
REGISTRATION_MSG_EXPIRE_WARNING = f"{WARNING_EMOJI} *ВНИМАНИЕ!* {WARNING_EMOJI} \n " \
                                  f"Регистрация следующих доменов истекает менее чем через"

# Control dates
SSL_WARNING_EXPIRE_DAYS = 10
SSL_ALERT_EXPIRE_DAYS = 5

DOMAIN_WARNING_REGISTRATION_DAYS = 30
DOMAIN_ALERT_REGISTRATION_DAYS = 10

# markup
default_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
add_domain = types.KeyboardButton(ADD_DOMAIN_BTN)
rm_domain = types.KeyboardButton(REMOVE_DOMAIN_BTN)
my_domains = types.KeyboardButton(SHOW_DOMAINS_BTN)
ssl_status = types.KeyboardButton(SHOW_SSL_BTN)
registration_status = types.KeyboardButton(SHOW_REGISTRATION_BTN)
default_markup.add(add_domain, rm_domain, my_domains, ssl_status, registration_status)

cancel_add_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
cancel_add_btn = types.KeyboardButton(CANCEL_ADD_BTN)
cancel_add_markup.add(cancel_add_btn)
