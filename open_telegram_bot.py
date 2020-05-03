#!/usr/bin/env python

import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from settings import Settings
from integrations.google_df import GoogleIntegrationWithDialogFlow as df

settings = Settings()
project_id = settings.project_id
session_id = settings.session_id
language_code = settings.language_code
TRAINING_PHRASES, ANSWER, CREATE_INTENT = range(3)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def approved_intent(update, context):
    display_name = context.chat_data['new_intent']['training_phrases'][0]
    training_phrases_parts = context.chat_data['new_intent']['training_phrases']
    message_texts = [context.chat_data['new_intent']['answer']]
    df.create_intent(project_id, display_name, training_phrases_parts, message_texts)
    update.message.reply_text('Спасибо! Вы делаете меня лучше!. Теперь я знаю ответ на вопрос: \r\n'+
                              display_name)
    clean(context)
    return ConversationHandler.END

def teach_me(update, context):
    clean(context)
    update.message.reply_text('Чтобы я научился отвечать на новый вопрос, мне необходимо получить несколько примеров новго вопроса. '
                              'Отправляй примеры вопросов каждым сообщением отдельно. \r\nЧем больше, тем лучше. \r\n'
                              'Когда закончишь, нажми /put_answer\r\nДля отмены нажми /cancel')

    return TRAINING_PHRASES

def training_phrases(update, context):
    if len(update.message.text) >= 10:
        context.chat_data['new_intent']['training_phrases'].append(update.message.text)
    else:
        update.message.reply_text('Вариант вопроса слишком короткий. Так у меня все смешается в голове.. /cancel')

def check_before_put_answer(update, context):
    if 'training_phrases' in context.chat_data['new_intent'] and len(context.chat_data['new_intent']['training_phrases']) >= 3:
        update.message.reply_text('Отлично! Теперь скажи, что мне нужно отвечать на эти вопросы')
        return ANSWER
    else:
        update.message.reply_text('Введи хотя бы 3 варианта вопроса. Иначе мне будет тяжело научиться. /cancel')
        return TRAINING_PHRASES

def put_answer(update, context):

    context.chat_data['new_intent']['answer'] = update.message.text + " /edit"
    training_phrases_for_print = ''
    for phrase in context.chat_data['new_intent']['training_phrases']:
        training_phrases_for_print = training_phrases_for_print + '\r\n' + phrase
    update.message.reply_text('Осталось проверить и подтвердить!\r\nВарианты вопросов:' +
                              training_phrases_for_print + '\r\nОтвет:\r\n' + context.chat_data['new_intent']['answer'] +
                              '\r\n /cancel /approve')
    return CREATE_INTENT

def cancel(update, context):
    clean(context)
    update.message.reply_text('Ладно! Спроси тогда, что-нибудь еще :)')
    return ConversationHandler.END

def clean(context):
    context.chat_data['new_intent'] = {
        "training_phrases": [],
        "answer": None
    }

def error_conv(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    clean(context)
    update.message.reply_text('Ой, что-то пошло не так..')
    return ConversationHandler.END

def edit(update, context):
    update.message.reply_text('Эта фитча находится в разработке')

def text_request(update, context):
    response = df.detect_intent_texts(project_id, session_id, update.message.text, language_code, update)
    update.message.reply_text(response)

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    clean(context)
    update.message.reply_text('Ой, что-то пошло не так..')

def start(update, context):
    update.message.reply_text('Привет! Я первый бот, которого могут учить пользователи. '
                              'Спроси меня что-нибудь, а если я не знаю ответ - научи! /teach_me')

def main():

    updater = Updater(settings.telegram_token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("edit", edit))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('teach_me', teach_me)],

        states={
            TRAINING_PHRASES: [MessageHandler(Filters.text, training_phrases),
                               CommandHandler('put_answer', check_before_put_answer),
                               CommandHandler('cancel', cancel)],

            ANSWER: [MessageHandler(Filters.text, put_answer),
                               CommandHandler('cancel', cancel)],

            CREATE_INTENT: [CommandHandler('cancel', cancel),
                            CommandHandler('approve', approved_intent)],

        },

        fallbacks=[CommandHandler('fallback', error_conv)]
    )

    dp.add_handler(conv_handler)

    dp.add_handler(MessageHandler(Filters.text, text_request))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
