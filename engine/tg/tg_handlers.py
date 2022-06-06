import engine.tg.tg_messages as msgs
import engine.sqlite.database as db

from engine import global_params
from telegram import Update, ChatMember
from telegram.ext import CallbackContext, Updater, CommandHandler, Filters, MessageHandler


def help(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if not db.group_exists(chat_id):
        response = msgs.TG_UNAUTHZ_GROUP.format(name=update.effective_chat.title, chat_id=update.effective_chat.id)
        context.bot.send_message(chat_id=global_params.MAINT_ID, text=response)

    context.bot.send_message(chat_id=update.effective_chat.id, text=msgs.TG_HELP)


def unknown_cmd(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(chat_id=update.effective_chat.id, text=msgs.TG_UNKNOWN)


def get_balance(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if not db.group_exists(chat_id):
        return

    balance = db.get_balance(chat_id)
    response = msgs.TG_GET_BALANCE.format(balance=balance)
    context.bot.send_message(chat_id=chat_id, text=response)


def add_balance(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if not db.group_exists(chat_id):
        return

    if len(context.args) != 1:
        response = msgs.TG_INVALID_ARG_NUM.format(num=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    try:
        deposit = int(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    balance = db.add_balance(update.effective_chat.id, deposit)
    response = msgs.TG_ADD_BALANCE.format(deposit=deposit, balance=balance)
    context.bot.send_message(chat_id=chat_id, text=response)


def use_balance(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if not db.group_exists(chat_id):
        return

    if len(context.args) != 2:
        response = msgs.TG_INVALID_ARG_NUM.format(num=2)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    try:
        time = float(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    try:
        rent = int(context.args[1])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=2)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    hour_fee = db.get_hour_fee(chat_id)
    spent = int(hour_fee * time) + rent
    balance = db.use_balance(chat_id, spent)
    response = msgs.TG_USE_BALANCE.format(spent=spent, balance=balance)
    context.bot.send_message(chat_id=chat_id, text=response)


def authz_group(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if chat_id != global_params.MAINT_ID:
        return

    if len(context.args) != 1:
        response = msgs.TG_INVALID_ARG_NUM.format(num=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    try:
        group_id = int(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    db.add_group(group_id)
    context.bot.send_message(chat_id=group_id, text=msgs.TG_AUTHZ_COMPLETE)


def set_hour_fee(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    status = context.bot.get_chat_member(chat_id=chat_id, user_id=update.effective_user.id).status

    if status not in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        context.bot.send_message(chat_id=chat_id, text=msgs.TG_NOT_ALLOWED)
        return

    if len(context.args) != 1:
        response = msgs.TG_INVALID_ARG_NUM.format(num=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    try:
        hour_fee = int(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    db.set_hour_fee(chat_id, hour_fee)
    response = msgs.TG_HOUR_FEE_SET.format(sum=hour_fee)
    context.bot.send_message(chat_id=chat_id, text=response)


def start_bot() -> None:
    updater = Updater(token=global_params.TOKEN, use_context=True)

    registered_methods = (help, get_balance, add_balance, use_balance, set_hour_fee)
    registered_names = [x.__name__ for x in registered_methods]
    msgs.TG_HELP = msgs.TG_HELP % tuple(registered_names)

    updater.dispatcher.add_handler(CommandHandler('start', help))
    updater.dispatcher.add_handler(CommandHandler(authz_group.__name__, authz_group))
    for m in registered_methods:
        updater.dispatcher.add_handler(CommandHandler(m.__name__, m))

    unknown_handler = MessageHandler(Filters.command, unknown_cmd)
    updater.dispatcher.add_handler(unknown_handler)

    updater.start_polling(poll_interval=global_params.POLL_INTERVAL)
    updater.idle()