from django.db.models import DateTimeField, Func, UUIDField


# [TODO] RandomUUID
class RandomUUID(Func):
    template = "GEN_RANDOM_UUID()"
    output_field = UUIDField()


# [TODO] TransactionNow
class TransactionNow(Func):
    template = "CURRENT_TIMESTAMP"
    output_field = DateTimeField()