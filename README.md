# domainPingerBot

Telegram бот для проверки доступности сайтов.
Бот оповестит вас, если ваш сайт(ы) стали недоступны (error 4XX & 5XX), а
также сообщит код и время появления ошибки.

Рабочий бот: https://t.me/domainsPingerBot

# Развертывание:

1. Создайте файл .env рядом с файлом main.py, и вставьте в него следующий текст:

> botID = 'BOT_TOKEN'

(вместо BOT_TOKEN введите токен вашего бота, полученного от BotFather)

2. Установите актуальную версию docker

3. Создайте изображение приложения в docker:

> docker build -t domain_pinger .

4. Создайте и запустите docker контейнер из этого изображения:

> docker run -d --restart always -v domains_dir:/domains domain_pinger:latest