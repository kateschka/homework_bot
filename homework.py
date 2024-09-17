"""Bot for checking the status of homework on the Practicum platform."""
import sys
import time
import requests
import os
import logging

from telebot import TeleBot
from dotenv import load_dotenv

from exceptions import NoneTokenError, RequestError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Check if the tokens are set."""
    tokens = {
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    }
    missing_tokens = []

    for token_name, token in tokens:
        if not token:
            missing_tokens.append(token_name)

    error_message = (
        'Отсутствуют обязательные переменные окружения: ')

    if missing_tokens:
        error_message += ', '.join(missing_tokens)
        logging.critical(error_message)
        raise NoneTokenError(error_message)


def send_message(bot, message):
    """Send a message to the Telegram chat."""
    try:
        logging.info(f'Попытка отправки сообщения: \'{message}\'')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: \'{message}\'')

    except Exception:
        error_message = (f'Ошибка отправки сообщения \'{message}\', '
                         f'Chat ID: {TELEGRAM_CHAT_ID}')
        logging.error(error_message)


def get_api_answer(timestamp):
    """Get the API response and parse it to python data types."""
    logging.info(
        f'Попытка запроса данных с {ENDPOINT} '
        f'с параметром from_date = {timestamp}')
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp})

        if response.status_code != 200:
            error_message = (
                f'Ошибка запроса к {ENDPOINT}. '
                f'Код ответа: {response.status_code}')
            raise RequestError(error_message)

        try:
            response = response.json()
            logging.info('Ответ на запрос к API получен')
            return response

        except Exception:
            error_message = 'Ошибка преобразования ответа API в JSON'
            raise ValueError(error_message)

    except requests.RequestException as error:
        logging.error(f'Ошибка запроса к {ENDPOINT}: {error}')


def check_response(response):
    """Check the API response."""
    logging.info('Проверка ответа API')

    # if response is not a dictionary
    if not isinstance(response, dict):
        error_message = 'Ответ API не является словарем'
        raise TypeError(error_message)

    # if the response does not contain the key 'homeworks'
    if 'homeworks' not in response:
        error_message = 'Ответ API не содержит ключа \'homeworks\''
        raise KeyError(error_message)

    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        error_message = 'Ответ API не содержит списка работ'
        raise TypeError(error_message)

    # if homeworks is empty
    if not homeworks:
        logging.debug('Новых работ не найдено')

    return homeworks


def parse_status(homework):
    """Parse the response and get verdict if homework status changed."""
    logging.info('Есть изменения в статусе работы. Проверка статусов')

    homework_params = ('homework_name', 'status')
    missing_params = []

    for param in homework_params:
        if param not in homework:
            missing_params.append(param)

    if missing_params:
        error_message = (
            f'В ответе API отсутствуют следующие параметры: '
            f'{", ".join(missing_params)}'
        )
        raise KeyError(error_message)

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS:
        error_message = f'Статус проверки работы "{homework_name}" неизвестен'
        raise KeyError(error_message)

    verdict = HOMEWORK_VERDICTS.get(status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main logic of the bot."""
    bot = TeleBot(TELEGRAM_TOKEN)
    logging.info('Бот начал свою работу')
    timestamp = int(time.time())

    try:
        check_tokens()
    except NoneTokenError:
        logging.critical('Выполнение программы прервано')
        sys.exit(1)

    while True:
        try:
            # check the API response for new homeworks
            homeworks = check_response(get_api_answer(timestamp))
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)

            # update the timestamp if there were new homeworks
            if homeworks:
                timestamp = int(time.time())

        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        encoding='utf-8',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
