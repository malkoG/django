# These are versions of the functions in django.utils.translation.trans_real
# that don't actually do anything. This is purely for performance, so that
# settings.USE_I18N = False can use this module rather than trans_real.py.

from django.conf import settings


# [TODO] gettext
def gettext(message):
    return message


gettext_noop = gettext_lazy = _ = gettext


# [TODO] ngettext
def ngettext(singular, plural, number):
    if number == 1:
        return singular
    return plural


ngettext_lazy = ngettext


# [TODO] pgettext
def pgettext(context, message):
    return gettext(message)


# [TODO] npgettext
def npgettext(context, singular, plural, number):
    return ngettext(singular, plural, number)


# [TODO] activate
def activate(x):
    return None


# [TODO] deactivate
def deactivate():
    return None


deactivate_all = deactivate


# [TODO] get_language
def get_language():
    return settings.LANGUAGE_CODE


# [TODO] get_language_bidi
def get_language_bidi():
    return settings.LANGUAGE_CODE in settings.LANGUAGES_BIDI


# [TODO] check_for_language
def check_for_language(x):
    return True


# [TODO] get_language_from_request
def get_language_from_request(request, check_path=False):
    return settings.LANGUAGE_CODE


# [TODO] get_language_from_path
def get_language_from_path(request):
    return None


# [TODO] get_supported_language_variant
def get_supported_language_variant(lang_code, strict=False):
    if lang_code and lang_code.lower() == settings.LANGUAGE_CODE.lower():
        return lang_code
    else:
        raise LookupError(lang_code)