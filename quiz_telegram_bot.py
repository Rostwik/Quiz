import os

import logging
from random import choice

import telegram
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

from add_quiz_questions import add_quiz_questions
from logger_handler import TelegramLogsHandler

import redis

logger = logging.getLogger('speech_recognizer')


def error_handler(update, context):
    logger.error(f'Телеграм бот упал с ошибкой: {context.error}', exc_info=True)


def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = update.message.chat_id
    custom_keyboard = [['Новый вопрос', 'Сдаться'],
                       ['Мой счет']]
    reply_markup = telegram.ReplyKeyboardMarkup(custom_keyboard)
    context.bot.send_message(
        chat_id=user_id,
        text="Привет! Я бот для викторин!",
        reply_markup=reply_markup
    )


def echo(update: Update, context: CallbackContext):
    user_input = update.effective_message.text
    user_id = update.message.chat_id
    redis_connection = context.bot_data['redis']
    quiz = context.bot_data['quiz']
    current_issue = redis_connection.get(user_id).decode('utf-8')

    if user_input == 'Новый вопрос':
        random_question = choice(list(quiz))
        update.message.reply_text(
            random_question,
        )
        redis_connection.set(user_id, random_question)
    elif current_issue:
        correct_answer = quiz[current_issue]
        if '(' in correct_answer:
            smart_answer, _ = correct_answer.split('(')
        elif '.' in correct_answer:
            smart_answer, _ = correct_answer.split('.')

        if user_input in smart_answer:
            update.message.reply_text(
                'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос».',
            )
        else:
            update.message.reply_text(
                'Неправильно… Попробуете ещё раз?',
            )

    else:
        update.message.reply_text(
            'Я не вижу ни одного выбранного Вами вопроса - нажмите, пожалуйста, «Новый вопрос»',
        )


def main():
    load_dotenv()
    telegram_api_token = os.getenv('TELEGRAM_API_TOKEN')
    telegram_monitor_api_token = os.getenv('TELEGRAM_MONITOR_API_TOKEN')
    telegram_admin_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    redis_bd_credentials = os.getenv('REDIS_BD_CREDENTIALS')

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

    quiz = add_quiz_questions()

    dispatcher.bot_data['redis'] = bd_connection
    dispatcher.bot_data['quiz'] = quiz

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dispatcher.add_error_handler(error_handler)

    logger.info('Телеграм бот запущен.')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
