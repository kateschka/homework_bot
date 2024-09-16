"""Bot for checking the status of homework on the Practicum platform."""
import sys
import time
import requests
import os
import logging

from telebot import TeleBot
from dotenv import load_dotenv

from exceptions import NoneTokenError

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

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log',
    filemode='a',
    encoding='utf-8'
)
handler = logging.StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)


def check_tokens():
    """Check if the tokens are set."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token_name, token in tokens.items():
        if not token:
            error_message = (
                'Отсутствует обязательная переменная окружения:'
                f'\'{token_name}\'')
            logger.critical(error_message)
            raise NoneTokenError(error_message)


def send_message(bot, message):
    """Send a message to the Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение: \'{message}\'')
    except Exception:
        error_message = (f'Ошибка отправки сообщения \'{message}\', '
                         f'Chat ID: {TELEGRAM_CHAT_ID}')
        logger.error(error_message)


def get_api_answer(timestamp):
    """Get the API response and parse it to python data types."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp})
    except requests.RequestException as error:
        logger.error(f'Ошибка запроса к {ENDPOINT}: {error}')

    if response.status_code != 200:
        error_message = (
            f'Ошибка запроса к {ENDPOINT}. Код ответа: {response.status_code}')
        logger.error(error_message)
        raise requests.RequestException(error_message)

    try:
        response = response.json()
    except Exception:
        error_message = 'Ошибка преобразования ответа API в JSON'
        logger.error(error_message)
        raise TypeError(error_message)

    return response


def check_response(response):
    """Check the API response."""
    # if response is not a dictionary
    if not isinstance(response, dict):
        error_message = 'Ответ API не является словарем'
        logger.error(error_message)
        raise TypeError(error_message)

    # if the response does not contain the key 'homeworks'
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        error_message = 'Ответ API не содержит списка работ'
        logger.error(error_message)
        raise TypeError(error_message)

    # if homeworks is empty
    if not homeworks:
        logger.debug('Новых работ не найдено')

    return homeworks


def parse_status(homework):
    """Parse the response and get verdict if homework status changed."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')

    homework_params = {
        'homework_name': homework_name,
        'status': status,
    }

    for key, value in homework_params.items():
        if value is None:
            error_message = f'Отсутствует ключ "{key}" в ответе API'
            logger.error(error_message)
            raise KeyError(error_message)

    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        error_message = f'Статус проверки работы "{homework_name}" неизвестен'
        logger.error(error_message)
        raise ValueError(error_message)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Main logic of the bot."""
    bot = TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())

    try:
        check_tokens()
    except NoneTokenError:
        logger.critical('Выполнение программы прервано')
        sys.exit(1)

    while True:
        try:
            homeworks = check_response(get_api_answer(timestamp))
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
