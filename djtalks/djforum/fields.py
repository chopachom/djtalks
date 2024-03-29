# -*- coding: utf-8 -*-
"""
:Authors:
    - qweqwe
"""

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.db.models import OneToOneField
from django.db.models.fields.related import SingleRelatedObjectDescriptor



class AutoSingleRelatedObjectDescriptor(SingleRelatedObjectDescriptor):
    def __get__(self, instance, instance_type=None):
        try:
            return super(AutoSingleRelatedObjectDescriptor, self).__get__(instance, instance_type)
        except self.related.model.DoesNotExist:
            obj = self.related.model(**{self.related.field.name: instance})
            obj.save()
            return obj


class AutoOneToOneField(OneToOneField):
    """
    OneToOneField creates dependent object on first request from parent object
    if dependent object has not created yet.

    Details about AutoOneToOneField (in russian):
        http://softwaremaniacs.org/blog/2007/03/07/auto-one-to-one-field/
    """

    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(), AutoSingleRelatedObjectDescriptor(related))
        #if not cls._meta.one_to_one_field:
        #    cls._meta.one_to_one_field = self