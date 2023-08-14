from django.core.exceptions import ImproperlyConfigured
from django.forms import Form
from django.forms import models as model_forms
from django.http import HttpResponseRedirect
from django.views.generic.base import ContextMixin, TemplateResponseMixin, View
from django.views.generic.detail import (
    BaseDetailView,
    SingleObjectMixin,
    SingleObjectTemplateResponseMixin,
)


# [TODO] FormMixin
class FormMixin(ContextMixin):
    """Provide a way to show and handle a form in a request."""

    initial = {}
    form_class = None
    success_url = None
    prefix = None

    # [TODO] FormMixin > get_initial
    def get_initial(self):
        """Return the initial data to use for forms on this view."""
        return self.initial.copy()

    # [TODO] FormMixin > get_prefix
    def get_prefix(self):
        """Return the prefix to use for forms."""
        return self.prefix

    # [TODO] FormMixin > get_form_class
    def get_form_class(self):
        """Return the form class to use."""
        return self.form_class

    # [TODO] FormMixin > get_form
    def get_form(self, form_class=None):
        """Return an instance of the form to be used in this view."""
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(**self.get_form_kwargs())

    # [TODO] FormMixin > get_form_kwargs
    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    # [TODO] FormMixin > get_success_url
    def get_success_url(self):
        """Return the URL to redirect to after processing a valid form."""
        if not self.success_url:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return str(self.success_url)  # success_url may be lazy

    # [TODO] FormMixin > form_valid
    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url())

    # [TODO] FormMixin > form_invalid
    def form_invalid(self, form):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response(self.get_context_data(form=form))

    # [TODO] FormMixin > get_context_data
    def get_context_data(self, **kwargs):
        """Insert the form into the context dict."""
        if "form" not in kwargs:
            kwargs["form"] = self.get_form()
        return super().get_context_data(**kwargs)


# [TODO] ModelFormMixin
class ModelFormMixin(FormMixin, SingleObjectMixin):
    """Provide a way to show and handle a ModelForm in a request."""

    fields = None

    # [TODO] ModelFormMixin > get_form_class
    def get_form_class(self):
        """Return the form class to use in this view."""
        if self.fields is not None and self.form_class:
            raise ImproperlyConfigured(
                "Specifying both 'fields' and 'form_class' is not permitted."
            )
        if self.form_class:
            return self.form_class
        else:
            if self.model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            elif getattr(self, "object", None) is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_queryset().model

            if self.fields is None:
                raise ImproperlyConfigured(
                    "Using ModelFormMixin (base class of %s) without "
                    "the 'fields' attribute is prohibited." % self.__class__.__name__
                )

            return model_forms.modelform_factory(model, fields=self.fields)

    # [TODO] ModelFormMixin > get_form_kwargs
    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs

    # [TODO] ModelFormMixin > get_success_url
    def get_success_url(self):
        """Return the URL to redirect to after processing a valid form."""
        if self.success_url:
            url = self.success_url.format(**self.object.__dict__)
        else:
            try:
                url = self.object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the Model."
                )
        return url

    # [TODO] ModelFormMixin > form_valid
    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save()
        return super().form_valid(form)


# [TODO] ProcessFormView
class ProcessFormView(View):
    """Render a form on GET and processes it on POST."""

    # [TODO] ProcessFormView > get
    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        return self.render_to_response(self.get_context_data())

    # [TODO] ProcessFormView > post
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    # [TODO] ProcessFormView > put
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


# [TODO] BaseFormView
class BaseFormView(FormMixin, ProcessFormView):
    """A base view for displaying a form."""


# [TODO] FormView
class FormView(TemplateResponseMixin, BaseFormView):
    """A view for displaying a form and rendering a template response."""


# [TODO] BaseCreateView
class BaseCreateView(ModelFormMixin, ProcessFormView):
    """
    Base view for creating a new object instance.

    Using this base class requires subclassing to provide a response mixin.
    """

    # [TODO] BaseCreateView > get
    def get(self, request, *args, **kwargs):
        self.object = None
        return super().get(request, *args, **kwargs)

    # [TODO] BaseCreateView > post
    def post(self, request, *args, **kwargs):
        self.object = None
        return super().post(request, *args, **kwargs)


# [TODO] CreateView
class CreateView(SingleObjectTemplateResponseMixin, BaseCreateView):
    """
    View for creating a new object, with a response rendered by a template.
    """

    template_name_suffix = "_form"


# [TODO] BaseUpdateView
class BaseUpdateView(ModelFormMixin, ProcessFormView):
    """
    Base view for updating an existing object.

    Using this base class requires subclassing to provide a response mixin.
    """

    # [TODO] BaseUpdateView > get
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    # [TODO] BaseUpdateView > post
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


# [TODO] UpdateView
class UpdateView(SingleObjectTemplateResponseMixin, BaseUpdateView):
    """View for updating an object, with a response rendered by a template."""

    template_name_suffix = "_form"


# [TODO] DeletionMixin
class DeletionMixin:
    """Provide the ability to delete objects."""

    success_url = None

    # [TODO] DeletionMixin > delete
    def delete(self, request, *args, **kwargs):
        """
        Call the delete() method on the fetched object and then redirect to the
        success URL.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)

    # Add support for browsers which only accept GET and POST for now.
    # [TODO] DeletionMixin > post
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    # [TODO] DeletionMixin > get_success_url
    def get_success_url(self):
        if self.success_url:
            return self.success_url.format(**self.object.__dict__)
        else:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")


# [TODO] BaseDeleteView
class BaseDeleteView(DeletionMixin, FormMixin, BaseDetailView):
    """
    Base view for deleting an object.

    Using this base class requires subclassing to provide a response mixin.
    """

    form_class = Form

    # [TODO] BaseDeleteView > post
    def post(self, request, *args, **kwargs):
        # Set self.object before the usual form processing flow.
        # Inlined because having DeletionMixin as the first base, for
        # get_success_url(), makes leveraging super() with ProcessFormView
        # overly complex.
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    # [TODO] BaseDeleteView > form_valid
    def form_valid(self, form):
        success_url = self.get_success_url()
        self.object.delete()
        return HttpResponseRedirect(success_url)


# [TODO] DeleteView
class DeleteView(SingleObjectTemplateResponseMixin, BaseDeleteView):
    """
    View for deleting an object retrieved with self.get_object(), with a
    response rendered by a template.
    """

    template_name_suffix = "_confirm_delete"