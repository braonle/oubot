from peewee import SqliteDatabase, Model, IntegerField
from ..global_params import DB_NAME


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(DB_NAME)


class TgGroupBalance(BaseModel):
    chat_id = IntegerField(unique=True)
    balance = IntegerField()


class TgGroupParams(BaseModel):
    chat_id = IntegerField(unique=True)
    hour_fee = IntegerField()


def add_group(chat_id: int) -> None:
    """
    Raises:
        IntegrityError: group already exists
    """
    TgGroupParams.create(chat_id=chat_id)
    TgGroupBalance.create(chat_id=chat_id)


def group_exists(chat_id: int) -> bool:
    return TgGroupParams.select().where(TgGroupParams.chat_id == chat_id).exists()


def get_balance(chat_id: int) -> int:
    return TgGroupBalance.get(TgGroupBalance.chat_id == chat_id).balance


def add_balance(chat_id: int, deposit: int) -> int:
    entity = TgGroupBalance.get(TgGroupBalance.chat_id == chat_id)
    entity.balance = entity.balance + deposit
    entity.save()
    return entity.balance


def use_balance(chat_id: int, spent: int) -> int:
    entity = TgGroupBalance.get(TgGroupBalance.chat_id == chat_id)
    entity.balance = entity.balance - spent
    entity.save()
    return entity.balance


def get_hour_fee(chat_id: int) -> int:
    return TgGroupParams.get(TgGroupParams.chat_id == chat_id).hour_fee


def set_hour_fee(chat_id: int, hour_fee: int) -> None:
    entity = TgGroupParams.get(TgGroupParams.chat_id == chat_id)
    entity.hour_fee = hour_fee
    entity.save()
