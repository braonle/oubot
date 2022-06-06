TG_HELP = \
"""
Учёт индивидуальных занятий

Команды:
/%s - показать начальное сообщение (то же, что и /start)
/%s - показать доступный баланс
/%s <RUB> - пополнить баланс
/%s <часы> <аренда> - потратить депозит
/%s <RUB> - стоимость занятия за час
"""

TG_UNKNOWN = "Команда не зарегистрирована"

TG_GET_BALANCE = "Доступно {balance} RUB"

TG_ADD_BALANCE = "Добавлено {deposit} RUB, доступно {balance} RUB"

TG_USE_BALANCE = "Использовано {spent} RUB, доступно {balance} RUB"

TG_INVALID_ARG_NUM = "Неверное число аргументов, должно быть {num}"

TG_INVALID_ARG_FMT = "Неверный тип аргумента №{position}"

TG_UNAUTHZ_GROUP = 'Неавторизованная группа "{name}", chat_id = {chat_id}'

TG_AUTHZ_COMPLETE = "Группа авторизована"

TG_NOT_ALLOWED = "Команда разрешена только администратору"

TG_HOUR_FEE_SET = "Оплата за час установлена как {sum} RUB"
