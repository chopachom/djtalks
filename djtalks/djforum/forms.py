# -*- coding: utf-8 -*-
"""
:Authors:
    - qweqwe
"""

from django import forms
from django.forms.util import ValidationError
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from djtalks.djforum.models import PrivateMessage

class ModelMultipleCommaField(forms.ModelMultipleChoiceField):
    widget = forms.TextInput

    def __init__(self, queryset, db_lookup_field='pk', *args, **kwargs):
        super(ModelMultipleCommaField, self).__init__(queryset, *args, **kwargs)
        self.db_lookup_field = db_lookup_field


    def clean(self,value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []

        values=[x.strip() for x in value.split(',')]

        if not isinstance(values, (list, tuple)):
            raise ValidationError(self.error_messages['list'])

        for value in values:
            try:
                self.queryset.filter(**{self.db_lookup_field:values})
            except ValueError:
                raise ValidationError(self.error_messages['invalid_choice'] % value)

        qs = self.queryset.filter(**{self.db_lookup_field+'__in':values})
        existing_values = set([
            force_unicode(getattr(o, self.db_lookup_field)) for o in qs
        ])
        for val in values:
            if force_unicode(val) not in existing_values:
                raise ValidationError(self.error_messages['invalid_choice'] % val)
        return qs

class FilteredModelChoiceField(forms.ModelChoiceField):
    def __init__(self, queryset, filter, *args, **kwargs):
        super(FilteredModelChoiceField, self).__init__(queryset, *args, **kwargs)


class Form(forms.Form):
    def is_valid_on_submit(self, request, authentication=True):
        authenticated = request.user.is_authenticated() or not authentication
        return request.method == 'POST' and self.is_valid() and authenticated


class AddTopicForm(Form):
    subject = forms.CharField(label=_('Subject'), max_length=255,
                              widget=forms.TextInput(attrs={'size':'115'}))
    message = forms.CharField(label=_('Message'), widget=forms.Textarea())

class AddPostForm(Form):
    message = forms.CharField(label=_('Message'), widget=forms.Textarea())


class NewMessageForm(Form):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(NewMessageForm, self).__init__(*args, **kwargs)
        self.fields['parent'].queryset = PrivateMessage.objects.filter(
            Q(sender=user) | Q(recipients__id=user.id)
        )

    recipients = ModelMultipleCommaField(User.objects, label=_('Recipients'),
                                         widget=forms.TextInput(),
                                         db_lookup_field='username', required=False)
    parent  = forms.ModelChoiceField(PrivateMessage.objects, label=_('Parent'),
                                     widget=forms.TextInput(), required=False)
    subject = forms.CharField(label=_('Subject'), max_length=255,
                              widget=forms.TextInput(attrs={'size':'115'}),
                              required=False)
    message = forms.CharField(label=_('Message'), widget=forms.Textarea())


    def clean(self):
        if not self.fields['recipients'] or not self.fields['parent']:
            raise ValidationError('You should specify recipients')
        if self.fields['parent']:
            self.fields['subject'].required=False
        return super(NewMessageForm, self).clean()

