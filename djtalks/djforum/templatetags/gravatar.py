# -*- coding: utf-8 -*-
"""
:Authors:
    - qweqwe
"""
import urllib
import hashlib

from django import template

register = template.Library()

@register.filter
def gravatar_url(email):
    gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({'d':'mm', 's':str(48)})
    return  gravatar_url