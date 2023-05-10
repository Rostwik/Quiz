import os

import logging
import time
from random import choice

import requests

import vk_api as vk
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
import telegram
from dotenv import load_dotenv
from vk_api.utils import get_random_id
import redis
from add_quiz_questions import add_quiz_questions

from logger_handler import TelegramLogsHandler

logger = logging.getLogger('vk_quiz_bot')


def handle_new_question_request(vk_api, event, bd_connection, keyboard, quiz):
    random_question = choice(list(quiz))

    vk_api.messages.send(
        user_id=event.user_id,
        message=random_question,
        keyboard=keyboard.get_keyboard(),
        random_id=get_random_id()
    )

    bd_connection.set(event.user_id, random_question)


def handle_solution_attempt(vk_api, event, bd_connection, keyboard, quiz):
    current_issue = bd_connection.get(event.user_id).decode('utf-8')
    correct_answer = quiz[current_issue]
    smart_answer = ''

    if '(' in correct_answer:
        smart_answer, *_ = correct_answer.split('(')
    elif '.' in correct_answer:
        smart_answer, *_ = correct_answer.split('.')

    if event.text in smart_answer:
        vk_api.messages.send(
            user_id=event.user_id,
            message='Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос».',
            keyboard=keyboard.get_keyboard(),
            random_id=get_random_id()
        )
    else:
        vk_api.messages.send(
            user_id=event.user_id,
            message='Неправильно… Попробуешь ещё раз?',
            keyboard=keyboard.get_keyboard(),
            random_id=get_random_id()
        )


def main():
    load_dotenv()
    vk_api_token = os.getenv('VK_API_TOKEN')
    telegram_admin_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    telegram_monitor_api_token = os.getenv('TELEGRAM_MONITOR_API_TOKEN')
    redis_bd_credentials = os.getenv('REDIS_BD_CREDENTIALS')

    quiz = add_quiz_questions()

    bd_connection = redis.from_url(redis_bd_credentials)
    bd_connection.ping()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )
    logger_bot = telegram.Bot(token=telegram_monitor_api_token)
    logger.setLevel(logging.WARNING)
    logger.addHandler(TelegramLogsHandler(logger_bot, telegram_admin_chat_id))

    vk_session = vk.VkApi(token=vk_api_token)
    vk_api = vk_session.get_api()

    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Мой счет', color=VkKeyboardColor.PRIMARY)

    longpoll = VkLongPoll(vk_session)

    while True:
        try:
            logger.info('VK Бот запущен.')
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == '/start':
                        vk_api.messages.send(
                            user_id=event.user_id,
                            message='Привет! Я бот для викторин!',
                            keyboard=keyboard.get_keyboard(),
                            random_id=get_random_id()
                        )

                    elif event.text == "Новый вопрос":
                        handle_new_question_request(vk_api, event, bd_connection, keyboard, quiz)

                    elif event.text == "Сдаться":
                        current_issue = bd_connection.get(event.user_id).decode('utf-8')
                        correct_answer = quiz[current_issue]

                        vk_api.messages.send(
                            user_id=event.user_id,
                            message=f'Правильный ответ: "{correct_answer}"',
                            random_id=get_random_id()
                        )

                        handle_new_question_request(vk_api, event, bd_connection, keyboard, quiz)

                    else:
                        handle_solution_attempt(vk_api, event, bd_connection, keyboard, quiz)

        except requests.exceptions.ConnectionError:
            logger.error('Интернет исчез')
            time.sleep(5)
        except Exception as err:
            logger.error(f'VK Бот упал с ошибкой: {err}', exc_info=True)


if __name__ == '__main__':
    main()
