TG_HELP = \
"""
Учёт индивидуальных занятий

Команды:
/%s - показать начальное сообщение
/%s - показать доступный баланс
/%s <RUB> - пополнить баланс
/%s <часы> <аренда> - потратить депозит
/%s <RUB> - стоимость занятия за час
"""

BOT_START = "Бот oubot запущен"
BOT_STOP = "Бот oubot остановлен"

TG_UNKNOWN = "Команда не зарегистрирована"
TG_GET_BALANCE = "Доступно {balance} RUB"
TG_ADD_BALANCE = "Добавлено {deposit} RUB, доступно {balance} RUB"
TG_USE_BALANCE = "Использовано {spent} RUB, доступно {balance} RUB"
TG_INVALID_ARG_NUM = "Неверное число аргументов, должно быть {num}"
TG_INVALID_ARG_FMT = "Неверный тип аргумента №{position}"
TG_UNAUTHZ_GROUP = 'Неавторизованная группа "{name}"'
TG_AUTHZ_COMPLETE = "Группа авторизована"
TG_NOT_ALLOWED = "Команда разрешена только администратору"
TG_HOUR_FEE_SET = "Оплата за час установлена как {sum} RUB"

BUTTON_START = "В начало"
BUTTON_BALANCE = "Остаток"
BUTTON_DEPOSIT = "Пополнить"
BUTTON_SPEND = "Потратить"
BUTTON_HOUR_FEE = "Цена за час"
BUTTON_FINISH = "Завершить"
BUTTON_AUTHZ = "Авторизовать"

PROMPT_INITIAL_MENU = "Меню"
PROMPT_DEPOSIT = "Введите депозит"
PROMPT_HOUR_FEE = "Введите стоимость за час (сейчас {value})"
PROMPT_NAN = "Нужно ввести число в качестве параметра"
PROMPT_HOURS_SPENT = "Сколько часов занимались?"
PROMPT_RENT_SPENT = "Стоимость аренды зала?"
PROMPT_NOT_ALLOWED = "Команда разрешена только администратору"
PROMPT_AUTHZ_GR_OK = "Группа {group_name} авторизована"
