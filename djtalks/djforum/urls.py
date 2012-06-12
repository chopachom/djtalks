# -*- coding: utf-8 -*-
"""
:Authors:
    - qweqwe
"""

from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    (r'^$', 'djtalks.djforum.views.index'),
    url(r'^forum/(\d+)/$', 'djtalks.djforum.views.forum'),
    url(r'^topic/(\d+)/$', 'djtalks.djforum.views.topic'),
    url(r'^inbox/?$', 'djtalks.djforum.views.inbox'),
    url(r'^inbox/new/?$', 'djtalks.djforum.views.new_pm'),
    url(r'^inbox/conversation/(\d+)/$', 'djtalks.djforum.views.conversation'),
)