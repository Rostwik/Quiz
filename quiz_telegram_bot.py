import os

import logging
from functools import partial
from random import choice

import telegram
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters, RegexHandler
from dotenv import load_dotenv

from add_quiz_questions import add_quiz_questions
from logger_handler import TelegramLogsHandler

import redis

from enum import Enum

logger = logging.getLogger('quiz')


class Color(Enum):
    QUESTION = 1
    ANSWER = 2
    GIVE_UP = 3


state = Enum('state', ['QUESTION', 'ANSWER', 'GIVE_UP'])


def error_handler(bot, update):
    logger.error(f'Телеграм бот упал с ошибкой: {update.error}', exc_info=True)


def start(bot, update):
    user_id = update.message.chat_id
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    bot.send_message(
        chat_id=user_id,
        text="Привет! Я бот для викторин! Для начала викторины, пожалуйста, нажмите 'Новый вопрос'",
        reply_markup=reply_markup
    )

    return state.QUESTION


def handle_new_question_request(bot, update, bd_connection, quiz):
    user_input = update.effective_message.text
    user_id = update.message.chat_id

    if user_input == 'Новый вопрос':
        random_question = choice(list(quiz))
        update.message.reply_text(
            random_question,
        )
        bd_connection.set(user_id, random_question)

        return state.ANSWER

    else:
        update.message.reply_text(
            'Я не вижу ни одного выбранного Вами вопроса - нажмите, пожалуйста, «Новый вопрос»',
        )

        return state.QUESTION


def handle_solution_attempt(bot, update, bd_connection, quiz):
    user_input = update.effective_message.text
    user_id = update.message.chat_id
    current_issue = bd_connection.get(user_id).decode('utf-8')
    correct_answer = quiz[current_issue]
    smart_answer = ''

    if '(' in correct_answer:
        smart_answer, *_ = correct_answer.split('(')
    elif '.' in correct_answer:
        smart_answer, *_ = correct_answer.split('.')

    if user_input in smart_answer:
        update.message.reply_text(
            'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос».',
        )

        return state.QUESTION

    else:
        update.message.reply_text(
            'Неправильно… Попробуете ещё раз?',
        )

        return state.ANSWER


def handle_give_up(bot, update, bd_connection, quiz):
    user_id = update.message.chat_id
    current_issue = bd_connection.get(user_id).decode('utf-8')
    correct_answer = quiz[current_issue]

    bot.send_message(
        chat_id=user_id,
        text=f"Правильный ответ: '{correct_answer}'"
    )

    redis_connection = bd_connection
    random_question = choice(list(quiz))
    redis_connection.set(user_id, random_question)
    update.message.reply_text(
        f'Новый вопрос: {random_question}',
    )

    return state.ANSWER


def end(bot, update):
    update.message.reply_text(
        'Конец связи',
    )

    return ConversationHandler.END


def main():
    load_dotenv()
    telegram_api_token = os.getenv('TELEGRAM_API_TOKEN')
    telegram_monitor_api_token = os.getenv('TELEGRAM_MONITOR_API_TOKEN')
    telegram_admin_chat_id = os.getenv('TELEGRAM_CHAT_ID')
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

    updater = Updater(telegram_api_token)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            state.QUESTION: [RegexHandler(
                'Новый вопрос',
                partial(
                    handle_new_question_request,
                    bd_connection=bd_connection,
                    quiz=quiz
                )
            ),
            ],

            state.ANSWER: [RegexHandler(
                'Сдаться',
                partial(
                    handle_give_up,
                    bd_connection=bd_connection,
                    quiz=quiz
                )
            ),
                MessageHandler(
                    Filters.text,
                    partial(
                        handle_solution_attempt,
                        bd_connection=bd_connection,
                        quiz=quiz
                    )
                ),
            ],
        },
        fallbacks=[CommandHandler('end', end)]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(error_handler)

    logger.info('Телеграм бот запущен.')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
