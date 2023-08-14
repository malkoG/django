# Levels
DEBUG = 10
INFO = 20
WARNING = 30
ERROR = 40
CRITICAL = 50


# [TODO] CheckMessage
class CheckMessage:
    # [TODO] CheckMessage > __init__
    def __init__(self, level, msg, hint=None, obj=None, id=None):
        if not isinstance(level, int):
            raise TypeError("The first argument should be level.")
        self.level = level
        self.msg = msg
        self.hint = hint
        self.obj = obj
        self.id = id

    # [TODO] CheckMessage > __eq__
    def __eq__(self, other):
        return isinstance(other, self.__class__) and all(
            getattr(self, attr) == getattr(other, attr)
            for attr in ["level", "msg", "hint", "obj", "id"]
        )

    # [TODO] CheckMessage > __str__
    def __str__(self):
        from django.db import models

        if self.obj is None:
            obj = "?"
        elif isinstance(self.obj, models.base.ModelBase):
            # We need to hardcode ModelBase and Field cases because its __str__
            # method doesn't return "applabel.modellabel" and cannot be changed.
            obj = self.obj._meta.label
        else:
            obj = str(self.obj)
        id = "(%s) " % self.id if self.id else ""
        hint = "\n\tHINT: %s" % self.hint if self.hint else ""
        return "%s: %s%s%s" % (obj, id, self.msg, hint)

    # [TODO] CheckMessage > __repr__
    def __repr__(self):
        return "<%s: level=%r, msg=%r, hint=%r, obj=%r, id=%r>" % (
            self.__class__.__name__,
            self.level,
            self.msg,
            self.hint,
            self.obj,
            self.id,
        )

    # [TODO] CheckMessage > is_serious
    def is_serious(self, level=ERROR):
        return self.level >= level

    # [TODO] CheckMessage > is_silenced
    def is_silenced(self):
        from django.conf import settings

        return self.id in settings.SILENCED_SYSTEM_CHECKS


# [TODO] Debug
class Debug(CheckMessage):
    # [TODO] Debug > __init__
    def __init__(self, *args, **kwargs):
        super().__init__(DEBUG, *args, **kwargs)


# [TODO] Info
class Info(CheckMessage):
    # [TODO] Info > __init__
    def __init__(self, *args, **kwargs):
        super().__init__(INFO, *args, **kwargs)


# [TODO] Warning
class Warning(CheckMessage):
    # [TODO] Warning > __init__
    def __init__(self, *args, **kwargs):
        super().__init__(WARNING, *args, **kwargs)


# [TODO] Error
class Error(CheckMessage):
    # [TODO] Error > __init__
    def __init__(self, *args, **kwargs):
        super().__init__(ERROR, *args, **kwargs)


# [TODO] Critical
class Critical(CheckMessage):
    # [TODO] Critical > __init__
    def __init__(self, *args, **kwargs):
        super().__init__(CRITICAL, *args, **kwargs)