from typing import Union, List, Tuple

import engine.tg.tg_messages as msgs
import engine.sqlite.database as db

from engine import global_params
from telegram import Update, ChatMember, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, Updater, CommandHandler, Filters, MessageHandler, ConversationHandler, \
    CallbackQueryHandler, Dispatcher
from telegram.error import BadRequest
from telegram.utils.helpers import get_signal_name

"""Consts for state selection within ConversationHandler"""
(
    STATE_SELECTION,
    STATE_ADD_BALANCE,
    STATE_USE_BALANCE_HOURS,
    STATE_USE_BALANCE_RENT,
    STATE_SET_HOUR_FEE,
    STATE_FINISH
) = map(chr, range(0, 6))
STATE_END = ConversationHandler.END

"""Consts for session cache access"""
INITIAL_MSG_KEY = "initial_msg"
INLINE_MSG_KEY = "inline_msg"
HOURS_SPENT_KEY = "hours"


def inform_all_chats(updater: Dispatcher, msg: str) -> None:
    # Get all chats available
    chat_ids = db.get_groups()
    for chat_id in chat_ids:
        try:
            # Inform users of bot activity without notification
            updater.bot.send_message(chat_id=chat_id, text=msg, disable_notification=True)
        except BadRequest as e:
            # Chat might have been changed due to admin rights assignment, ignore such chats
            print(f'{chat_id} is not valid, reason: {e.message}')


class CustomUpdater(Updater):
    def _signal_handler(self, signum, frame) -> None:
        inform_all_chats(self.dispatcher, msgs.BOT_STOP)
        super()._signal_handler(signum, frame)


def replay_message(chat_id: int, context: CallbackContext, log_msg: str, prompt: str, keyboard: InlineKeyboardMarkup):
    # Message in chat for user prompts and inline keyboard
    inline_msg_id = context.user_data.pop(INLINE_MSG_KEY)
    # Message in chat that invoked conversation
    initial_msg_id = context.user_data[INITIAL_MSG_KEY]
    # Cleanup keyboard (otherwise it is should as reply for deleted message)
    context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=inline_msg_id, reply_markup=None)
    context.bot.delete_message(chat_id, inline_msg_id)
    msg = context.bot.send_message(chat_id=chat_id, text=log_msg)
    context.bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)

    # Command requested directly, new conversation
    msg = context.bot.send_message(chat_id=chat_id, text=prompt, reply_to_message_id=initial_msg_id,
                                   reply_markup=keyboard, disable_notification=True)
    # Message in chat for user prompts and inline keyboard
    context.user_data[INLINE_MSG_KEY] = msg.message_id


def default_keyboard() -> InlineKeyboardMarkup:
    """ Keyboard with 2 buttons: main menu and exit

    :return: InlineKeyboardMarkup object
    """
    buttons = [[InlineKeyboardButton(text=msgs.BUTTON_START, callback_data=start.__name__)],
               [InlineKeyboardButton(msgs.BUTTON_FINISH, callback_data=finish_conversation.__name__)]
               ]
    return InlineKeyboardMarkup(buttons)


def start(update: Update, context: CallbackContext) -> str:
    """ Provides user with inline keyboard and changes state to action selection

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to action selection
    """
    chat_id = update.effective_chat.id

    # If chat is not authorized (does not exist in DB) - delete message (only help is allowed)
    if not db.group_exists(chat_id):
        context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
        return STATE_SELECTION

    # Main menu keyboard buttons
    keyboard = [
        [
            InlineKeyboardButton(msgs.BUTTON_BALANCE, callback_data=get_balance_inline.__name__),
            InlineKeyboardButton(msgs.BUTTON_DEPOSIT, callback_data=add_balance_inline.__name__),
        ],
        [
            InlineKeyboardButton(msgs.BUTTON_SPEND, callback_data=use_balance_inline.__name__)
        ],
        [
            InlineKeyboardButton(msgs.BUTTON_FINISH, callback_data=finish_conversation.__name__)
        ]

    ]

    # If calling user is an admin or an owner, add button for hour fee change
    status = context.bot.get_chat_member(chat_id=chat_id, user_id=update.effective_user.id).status
    if status in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        keyboard[1].append(InlineKeyboardButton(msgs.BUTTON_HOUR_FEE, callback_data=set_hour_fee_inline.__name__))

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message is not None:
        # Command requested directly, new conversation
        msg = update.message.reply_text(text=msgs.PROMPT_INITIAL_MENU, reply_markup=reply_markup, disable_notification=True)
        # Message in chat that invoked conversation
        context.user_data[INITIAL_MSG_KEY] = update.message.message_id
        # Message in chat for user prompts and inline keyboard
        context.user_data[INLINE_MSG_KEY] = msg.message_id
    else:
        # Command requested via button thus via callback
        update.callback_query.answer()
        # If message is not actually changed and stays the same, BadRequest is thrown
        try:
            update.callback_query.edit_message_text(text=msgs.PROMPT_INITIAL_MENU, reply_markup=reply_markup)
        except BadRequest:
            pass

    return STATE_SELECTION


def help(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    # Notify maintenance about a new chat to be authorized (chat_id added to DB for further processing)
    if not db.group_exists(chat_id):
        response = msgs.TG_UNAUTHZ_GROUP.format(name=update.effective_chat.title, chat_id=update.effective_chat.id)
        context.bot.send_message(chat_id=global_params.MAINT_ID, text=response)
        context.bot.send_message(chat_id=global_params.MAINT_ID, text=update.effective_chat.id)

    context.bot.send_message(chat_id=update.effective_chat.id, text=msgs.TG_HELP)


def unknown_cmd(update: Update, context: CallbackContext) -> None:
    """ Notify user that command is not known or supported

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: null
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=msgs.TG_UNKNOWN)


def __get_balance(chat_id: int) -> str:
    """ Retrieve balance from DB based on chat_id

    Internal function to be used by command and conversation processors to interact with DB.

    :param chat_id: unique key in DB
    :return: string with amount available
    """
    balance = db.get_balance(chat_id)
    return msgs.TG_GET_BALANCE.format(balance=balance)


def get_balance(update: Update, context: CallbackContext) -> None:
    """ Get available balance from DB via direct command

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: null
    """
    chat_id = update.effective_chat.id

    # If group is not authorized (DB entry does not exists), remove message without comment (only /help is allowed)
    if not db.group_exists(chat_id):
        context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
        return

    context.bot.send_message(chat_id=chat_id, text=__get_balance(chat_id))


def get_balance_inline(update: Update, context: CallbackContext) -> str:
    """ Get available balance from DB via inline keyboard

    Since no additional input is required, conversation is reset back to initial state.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to action selection
    """
    chat_id = update.effective_chat.id
    update.callback_query.edit_message_text(text=__get_balance(chat_id), reply_markup=default_keyboard())
    return STATE_SELECTION


def __add_balance(chat_id: int, deposit: int) -> str:
    """ Increase balance and store it in DB based on chat_id

    Internal function to be used by command and conversation processors to interact with DB.

    :param chat_id: unique key in DB
    :param deposit: amount of credit debited
    :return: string with amount debited and available as a result
    """
    balance = db.add_balance(chat_id, deposit)
    return msgs.TG_ADD_BALANCE.format(deposit=deposit, balance=balance)


def add_balance(update: Update, context: CallbackContext) -> None:
    """ Increase available balance and store it in DB via direct command

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: null
    """
    chat_id = update.effective_chat.id

    # If group is not authorized (DB entry does not exists), remove message without comment (only /help is allowed)
    if not db.group_exists(chat_id):
        context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
        return

    # Check if the number of arguments is correct
    if len(context.args) != 1:
        response = msgs.TG_INVALID_ARG_NUM.format(num=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    # Check if parameter is integer; otherwise, notify user
    try:
        deposit = int(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    context.bot.send_message(chat_id=chat_id, text=__add_balance(chat_id, deposit))


def add_balance_inline(update: Update, context: CallbackContext) -> str:
    """ Increase available balance and store it in DB via inline keyboard

    The debit amount is requested from user. State of the conversation is adjusted to invoke correct handler
    to process input value as debit.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to debiting an amount
    """
    update.callback_query.edit_message_text(text=msgs.PROMPT_DEPOSIT, reply_markup=default_keyboard())
    return STATE_ADD_BALANCE


def add_balance_inline_deposit(update: Update, context: CallbackContext) -> str:
    """ Process debit amount from user input after corresponding inline keyboard button is pressed

    User input is tested to be integer. If valid, the amount is added to DB.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to debiting an amount (if error) or action selection (if success)
    """

    chat_id = update.effective_chat.id
    message_id = context.user_data[INLINE_MSG_KEY]

    # Test if the value is integer; if not, notify user inline and delete invalid message
    try:
        deposit = int(update.message.text)
    except ValueError:
        context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
        # If message is not actually changed and stays the same, BadRequest is thrown
        try:
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msgs.PROMPT_NAN,
                                          reply_markup=default_keyboard())
        except BadRequest:
            pass

        return STATE_ADD_BALANCE

    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    prompt = __add_balance(chat_id, deposit)
    replay_message(chat_id, context, prompt, prompt, default_keyboard())

    return STATE_SELECTION


def __use_balance(chat_id: int, time: float, rent: int) -> str:
    """ Decrease balance in DB based on chat_id, rent fee and time spent

    Internal function to be used by command and conversation processors to interact with DB.

    :param chat_id: unique key in DB
    :param deposit: amount of credit debited
    :return: string with amount spent and available as a result
    """
    hour_fee = db.get_hour_fee(chat_id)
    spent = int(hour_fee * time) + rent
    balance = db.use_balance(chat_id, spent)
    return msgs.TG_USE_BALANCE.format(spent=spent, balance=balance)


def use_balance(update: Update, context: CallbackContext) -> None:
    """ Decrease balance in DB based on chat_id, rent fee and time spent via direct command

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: null
    """
    chat_id = update.effective_chat.id

    # If group is not authorized (DB entry does not exists), remove message without comment (only /help is allowed)
    if not db.group_exists(chat_id):
        context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
        return

    # Check if the number of arguments is correct
    if len(context.args) != 2:
        response = msgs.TG_INVALID_ARG_NUM.format(num=2)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    # Check if parameters have correct type; otherwise, notify user
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

    context.bot.send_message(chat_id=chat_id, text=__use_balance(chat_id, time, rent))


def use_balance_inline(update: Update, context: CallbackContext) -> str:
    """ Decrease balance in DB based on chat_id, rent fee and time spent via inline keyboard

    The time spent and rent fee are to be provided by user. State of the conversation is adjusted to invoke
    correct handler to process next input value as time spent.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to time spent input
    """
    update.callback_query.edit_message_text(text=msgs.PROMPT_HOURS_SPENT, reply_markup=default_keyboard())
    return STATE_USE_BALANCE_HOURS


def use_balance_inline_hours(update: Update, context: CallbackContext) -> str:
    """ Decrease balance in DB based on chat_id, rent fee and time spent via inline keyboard

    Process user input value as time spent. State of the conversation is adjusted to invoke correct handler
    to process next input value as rent fee.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to time spent input (if error) or rent fee input (if success)
    """
    chat_id = update.effective_chat.id
    # Message in chat for user prompts and inline keyboard
    message_id = context.user_data[INLINE_MSG_KEY]

    # Test if the value is float; if not, notify user inline and delete invalid message
    try:
        hours = float(update.message.text)
    except ValueError:
        context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
        # If message is not actually changed and stays the same, BadRequest is thrown
        try:
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msgs.PROMPT_NAN,
                                          reply_markup=default_keyboard())
        except BadRequest:
            pass

        return STATE_USE_BALANCE_HOURS

    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    # Save hours spent in cache
    context.user_data[HOURS_SPENT_KEY] = hours
    context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msgs.PROMPT_RENT_SPENT,
                                  reply_markup=default_keyboard())
    return STATE_USE_BALANCE_RENT


def use_balance_inline_rent(update: Update, context: CallbackContext) -> str:
    """ Decrease balance in DB based on chat_id, rent fee and time spent via inline keyboard

    Process user input value as rent fee. Since no additional input is required, conversation is reset back to
    initial state.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to rent fee input (if error) or action selection (if success)
    """
    chat_id = update.effective_chat.id
    # Message in chat for user prompts and inline keyboard
    message_id = context.user_data[INLINE_MSG_KEY]

    # Test if the value is integer; if not, notify user inline and delete invalid message
    try:
        rent = int(update.message.text)
    except ValueError:
        context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
        # If message is not actually changed and stays the same, BadRequest is thrown
        try:
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msgs.PROMPT_NAN,
                                          reply_markup=default_keyboard())
        except BadRequest:
            pass

        return STATE_USE_BALANCE_RENT

    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    # Get hours spent from cache
    hours = context.user_data.pop(HOURS_SPENT_KEY)
    prompt = __use_balance(chat_id, hours, rent)
    replay_message(chat_id, context, prompt, prompt, default_keyboard())

    return STATE_USE_BALANCE_RENT


def authz_group(update: Update, context: CallbackContext) -> None:
    """ Authorize new group for bot processing via maintenance chat

    Authorization is required in order to conserve resources. By default, only static help is available, other
    commands should not return any reply in group is not authorized. Authorization is based on availability of
    corresponding chat_id in DB. All unauthorized chats are reported to maintenance group that is responsible
    for admitting new group chats by chat_id.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: null
    """
    chat_id = update.effective_chat.id

    # If command is invoked manually from any chat except maintenance, delete violating message without notification
    if chat_id != global_params.MAINT_ID:
        context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
        return

    # Check if the number of arguments is correct
    if len(context.args) != 1:
        response = msgs.TG_INVALID_ARG_NUM.format(num=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    # Check if parameter is integer; otherwise, notify user
    try:
        group_id = int(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    db.add_group(group_id)
    context.bot.send_message(chat_id=group_id, text=msgs.TG_AUTHZ_COMPLETE)


def __set_hour_fee(chat_id: int, hour_fee: int) -> str:
    """ Set hour fee in DB based on chat_id

    Internal function to be used by command and conversation processors to interact with DB.

    :param chat_id: unique key in DB
    :param hour_fee: hour fee
    :return: string with new fee set as a result
    """
    db.set_hour_fee(chat_id, hour_fee)
    return msgs.TG_HOUR_FEE_SET.format(sum=hour_fee)


def set_hour_fee(update: Update, context: CallbackContext) -> None:
    """ Set hour fee in DB based on chat_id via direct command

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: null
    """
    chat_id = update.effective_chat.id

    # Hour fee setting is available for admins only
    status = context.bot.get_chat_member(chat_id=chat_id, user_id=update.effective_user.id).status
    if status not in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        context.bot.send_message(chat_id=chat_id, text=msgs.TG_NOT_ALLOWED)
        return

    # If group is not authorized (DB entry does not exists), remove message without comment (only /help is allowed)
    if not db.group_exists(chat_id):
        context.bot.delete_message(chat_id=chat_id, message_id=update.effective_message.message_id)
        return

    # Check if the number of arguments is correct
    if len(context.args) != 1:
        response = msgs.TG_INVALID_ARG_NUM.format(num=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    # Check if parameter is integer; otherwise, notify user
    try:
        hour_fee = int(context.args[0])
    except ValueError:
        response = msgs.TG_INVALID_ARG_FMT.format(position=1)
        context.bot.send_message(chat_id=chat_id, text=response)
        return

    context.bot.send_message(chat_id=chat_id, text=__set_hour_fee(chat_id, hour_fee))


def set_hour_fee_inline(update: Update, context: CallbackContext) -> str:
    """ Set hour fee in DB based on chat_id via inline keyboard

    Hour fee is requested from user. State of the conversation is adjusted to invoke correct handler
    to process input value as hour fee.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to action selection (non-admins) or hour fee input (admins)
    """
    chat_id = update.effective_chat.id
    status = context.bot.get_chat_member(chat_id=chat_id, user_id=update.effective_user.id).status

    # Hour fee setting is available for admins only
    if status in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        fee = db.get_hour_fee(chat_id)
        update.callback_query.edit_message_text(text=msgs.PROMPT_HOUR_FEE.format(value=fee),
                                                reply_markup=default_keyboard())
        return STATE_SET_HOUR_FEE
    else:
        update.callback_query.edit_message_text(text=msgs.PROMPT_NOT_ALLOWED, reply_markup=default_keyboard())
        return STATE_SELECTION


def set_hour_fee_inline_value(update: Update, context: CallbackContext) -> str:
    """ Decrease balance in DB based on chat_id, rent fee and time spent via inline keyboard

    Process user input value as rent fee. Since no additional input is required, conversation is reset back to
    initial state.

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to hour fee input (if error) or action selection (if success)
    """
    chat_id = update.effective_chat.id
    # Message in chat for user prompts and inline keyboard
    message_id = context.user_data[INLINE_MSG_KEY]

    # Test if the value is integer; if not, notify user inline and delete invalid message
    try:
        hour_fee = int(update.message.text)
    except ValueError:
        context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
        # If message is not actually changed and stays the same, BadRequest is thrown
        try:
            context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=msgs.PROMPT_NAN,
                                          reply_markup=default_keyboard())
        except BadRequest:
            pass
        return STATE_SET_HOUR_FEE

    context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id)
    context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=__set_hour_fee(chat_id, hour_fee),
                                  reply_markup=default_keyboard())
    return STATE_SELECTION


def finish_conversation(update: Update, context: CallbackContext) -> str:
    """ Cleanup cache, keyboard and messages in chat

    :param update: message info (prototype required by telegram-bot)
    :param context: session info (prototype required by telegram-bot)
    :return: ConversationHandler state equal to end
    """
    chat_id = update.effective_chat.id
    # Message in chat for user prompts and inline keyboard
    inline_msg_id = context.user_data.pop(INLINE_MSG_KEY)
    # Message in chat that invoked conversation
    initial_msg_id = context.user_data.pop(INITIAL_MSG_KEY)
    # Cleanup keyboard (otherwise it is should as reply for deleted message)
    context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=inline_msg_id, reply_markup=None)
    context.bot.delete_message(update.effective_chat.id, inline_msg_id)
    context.bot.delete_message(chat_id=chat_id, message_id=initial_msg_id)
    return STATE_END


def start_bot() -> None:
    """ Authenticate, authorize to Telegram; initialize handlers; start polling

    :return: null
    """
    updater = CustomUpdater(token=global_params.TOKEN, use_context=True)

    # Main menu handlers
    selection_handlers = [
        CallbackQueryHandler(finish_conversation, pattern=f"^{finish_conversation.__name__}$"),
        CallbackQueryHandler(get_balance_inline, pattern=f"^{get_balance_inline.__name__}$"),
        CallbackQueryHandler(add_balance_inline, pattern=f"^{add_balance_inline.__name__}$"),
        CallbackQueryHandler(set_hour_fee_inline, pattern=f"^{set_hour_fee_inline.__name__}$"),
        CallbackQueryHandler(use_balance_inline, pattern=f"^{use_balance_inline.__name__}$"),
        CallbackQueryHandler(start, pattern=f"^{start.__name__}$")
    ]

    # Handlers during state of balance topping (debit input)
    add_balance_handlers = {
        CallbackQueryHandler(finish_conversation, pattern=f"^{finish_conversation.__name__}$"),
        MessageHandler(Filters.text & ~Filters.command, add_balance_inline_deposit),
        CallbackQueryHandler(start, pattern=f"^{start.__name__}$")
    }

    # Handlers during state of setting hour fee (value input)
    set_hour_fee_handlers = {
        CallbackQueryHandler(finish_conversation, pattern=f"^{finish_conversation.__name__}$"),
        MessageHandler(Filters.text & ~Filters.command, set_hour_fee_inline_value),
        CallbackQueryHandler(start, pattern=f"^{start.__name__}$")
    }

    # Handlers during state of submitting hours spent (hours input)
    use_balance_hours_handlers = {
        CallbackQueryHandler(finish_conversation, pattern=f"^{finish_conversation.__name__}$"),
        MessageHandler(Filters.text & ~Filters.command, use_balance_inline_hours),
        CallbackQueryHandler(start, pattern=f"^{start.__name__}$")
    }

    # Handlers during state of submitting rent fee after hours spent (rent fee input)
    use_balance_rent_handlers = {
        CallbackQueryHandler(finish_conversation, pattern=f"^{finish_conversation.__name__}$"),
        MessageHandler(Filters.text & ~Filters.command, use_balance_inline_rent),
        CallbackQueryHandler(start, pattern=f"^{start.__name__}$")
    }

    # Button menu handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(start.__name__, start)],
        states={
            STATE_SELECTION: selection_handlers,
            STATE_ADD_BALANCE: add_balance_handlers,
            STATE_USE_BALANCE_HOURS: use_balance_hours_handlers,
            STATE_USE_BALANCE_RENT: use_balance_rent_handlers,
            STATE_SET_HOUR_FEE: set_hour_fee_handlers
        },
        fallbacks=[CommandHandler(start.__name__, start)]
    )
    updater.dispatcher.add_handler(conv_handler)

    # Maintenance direct command handlers (not visible in help)
    updater.dispatcher.add_handler(CommandHandler(authz_group.__name__, authz_group))

    # Generate help prompt and handlers from bot methods available for regular authorized groups
    registered_methods = (help, get_balance, add_balance, use_balance, set_hour_fee)
    registered_names = [x.__name__ for x in registered_methods]
    msgs.TG_HELP = msgs.TG_HELP % tuple(registered_names)

    for m in registered_methods:
        updater.dispatcher.add_handler(CommandHandler(m.__name__, m))

    # Unknown direct command handlers
    unknown_handler = MessageHandler(Filters.command, unknown_cmd)
    updater.dispatcher.add_handler(unknown_handler)

    # updater.start_polling(poll_interval=global_params.POLL_INTERVAL)
    updater.start_webhook(listen=global_params.LISTEN_IP, port=global_params.PORT, url_path=global_params.TOKEN,
                          key=global_params.PRIVATE_KEY, cert=global_params.CERTIFICATE,
                          webhook_url=f'https://{global_params.PUBLIC_IP}:{global_params.PORT}/{global_params.TOKEN}')

    inform_all_chats(updater.dispatcher, msgs.BOT_START)

    updater.idle()
