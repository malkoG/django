from django import template

register = template.Library()


# [TODO] AdminLogNode
class AdminLogNode(template.Node):
    # [TODO] AdminLogNode > __init__
    def __init__(self, limit, varname, user):
        self.limit = limit
        self.varname = varname
        self.user = user

    # [TODO] AdminLogNode > __repr__
    def __repr__(self):
        return "<GetAdminLog Node>"

    # [TODO] AdminLogNode > render
    def render(self, context):
        entries = context["log_entries"]
        if self.user is not None:
            user_id = self.user
            if not user_id.isdigit():
                user_id = context[self.user].pk
            entries = entries.filter(user__pk=user_id)
        context[self.varname] = entries[: int(self.limit)]
        return ""


# [TODO] get_admin_log
@register.tag
def get_admin_log(parser, token):
    """
    Populate a template variable with the admin log for the given criteria.

    Usage::

        {% get_admin_log [limit] as [varname] for_user [context_var_with_user_obj] %}

    Examples::

        {% get_admin_log 10 as admin_log for_user 23 %}
        {% get_admin_log 10 as admin_log for_user user %}
        {% get_admin_log 10 as admin_log %}

    Note that ``context_var_containing_user_obj`` can be a hard-coded integer
    (user ID) or the name of a template context variable containing the user
    object whose ID you want.
    """
    tokens = token.contents.split()
    if len(tokens) < 4:
        raise template.TemplateSyntaxError(
            "'get_admin_log' statements require two arguments"
        )
    if not tokens[1].isdigit():
        raise template.TemplateSyntaxError(
            "First argument to 'get_admin_log' must be an integer"
        )
    if tokens[2] != "as":
        raise template.TemplateSyntaxError(
            "Second argument to 'get_admin_log' must be 'as'"
        )
    if len(tokens) > 4:
        if tokens[4] != "for_user":
            raise template.TemplateSyntaxError(
                "Fourth argument to 'get_admin_log' must be 'for_user'"
            )
    return AdminLogNode(
        limit=tokens[1],
        varname=tokens[3],
        user=(tokens[5] if len(tokens) > 5 else None),
    )