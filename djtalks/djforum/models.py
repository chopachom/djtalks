
import os
from datetime import datetime
from hashlib import sha256

from django.db import models
from django.db.models import signals
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, Group

import registration.signals

from djtalks.djforum.fields import AutoOneToOneField
from djtalks import settings



class ForumManager(models.Manager):
    class DescendantsMixin(object):
        def descendants(self, forum, depth=None):
            """
            Finds all descendants of the forum
            """
            query = dict(path__startswith=forum.path+str(forum.id))
            if depth: query.update(dict(depth__lte=depth+forum.depth))
            return self.filter(**query)

    class DescendantsQuerySet(QuerySet, DescendantsMixin): pass

    def get_query_set(self):
        return ForumManager.DescendantsQuerySet(self.model, using=self._db)

class Forum(models.Model):
    name        = models.CharField(_('Name'), max_length=80)
    description = models.TextField(_('Description'), blank=True, default='')
    updated     = models.DateTimeField(_('Updated'), auto_now=True)
    post_count  = models.IntegerField(_('Post count'), blank=True, default=0)
    topic_count = models.IntegerField(_('Topic count'), blank=True, default=0)
    last_post   = models.ForeignKey('Post', related_name='last_forum_post', blank=True, null=True)

    parent      = models.ForeignKey('self', related_name='forums', verbose_name=_('Parent Board'), blank=True, null=True)
    path        = models.CharField(_('Path'), max_length=4096, blank=True, null=True, db_index=True)
    depth       = models.SmallIntegerField(_('Depth'), default=0)
    is_category = models.BooleanField(_('Is category'), default=False)
    has_subforums = models.BooleanField(_('Has subforums'), default=False)

    objects = ForumManager()

    @property
    def has_parent(self):
        return self.depth

    @property
    def posts(self):
        return Post.objects.filter(topic__forum__id=self.id).select_related()

    @property
    def children(self):
        return Forum.objects.filter(parent=self)

    @staticmethod
    def post_save(instance, **kwargs):
        """
        :type instance: :class:`~Forum`
        """
        forum = instance
        parent = forum.parent
        if parent:
            parent.updated = forum.updated
            #todo all posts count
            parent.post_count = parent.posts.count()
            parent.last_post_id = forum.last_post_id
            parent.save(force_update=True)


    def __unicode__(self):
        return u'{}'.format(self.name)


class Topic(models.Model):
    forum   = models.ForeignKey(Forum, related_name='topics', verbose_name=_('Forum'))
    subject = models.CharField(_('Subject'), max_length=255)
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), null=True)
    author  = models.ForeignKey(User, verbose_name=_('User'))
    views   = models.IntegerField(_('Views count'), blank=True, default=0)
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)
    last_post  = models.ForeignKey('Post', related_name='last_topic_post', blank=True, null=True)



    @staticmethod
    def post_save(instance, **kwargs):
        topic = instance
        forum = topic.forum
        forum.topic_count = forum.topics.count()
        forum.updated = topic.updated
        forum.post_count = forum.posts.count()
        forum.last_post_id = topic.last_post_id
        forum.save(force_update=True)

class Post(models.Model):
    topic   = models.ForeignKey(Topic, related_name='posts', verbose_name=_('Topic'))
    author  = models.ForeignKey(User, related_name='posts', verbose_name=_('User'))
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), blank=True, null=True)
    updated_by = models.ForeignKey(User, verbose_name=_('Updated by'), blank=True, null=True)
    message    = models.TextField(_('Message'))
    body_html  = models.TextField(_('HTML version'))
    user_ip    = models.IPAddressField(_('User IP'), blank=True, null=True)


    @staticmethod
    def post_save(instance, **kwargs):
        created = kwargs.get('created')
        post    = instance
        topic   = post.topic

        if created:
            topic.last_post = post
            topic.post_count = topic.posts.count()
            topic.updated = datetime.now()
            profile = post.author.forum_profile
            profile.post_count = post.author.posts.count()
            profile.save(force_update=True)
        topic.save(force_update=True)

class Profile(models.Model):
    user = AutoOneToOneField(User, related_name='forum_profile', verbose_name=_('User'))
    post_count = models.IntegerField(_('Post count'), blank=True, default=0)

    @staticmethod
    def user_registered(sender, **kwargs):
        user = kwargs['user']
        user.groups.add(Group.objects.get(name=settings.REGISTRATION_DEFAULT_GROUP_NAME))
        user.save()


random64bit = lambda: int(sha256(os.urandom(512)).hexdigest(), 16) % 2**64

class PrivateMessage(models.Model):
    sender  = models.ForeignKey(User, related_name='outgoing_pms', verbose_name=_('Recipient'))
    recipients = models.ManyToManyField(User, through='Inbox', related_name='pms')
    conversation_id = models.BigIntegerField(_('Conversation id'), default=random64bit)
    parent  = models.ForeignKey('self', related_name='children', verbose_name=_('Recipient'), blank=True, null=True)
    depth   = models.SmallIntegerField(_('Depth'), default=0)
    subject = models.TextField(_('Subject'))
    message = models.TextField(_('Message'))

    def __unicode__(self):
        return ",".join([self.subject, self.message[:20]])


class Inbox(models.Model):
    message   = models.ForeignKey(PrivateMessage, related_name='outgoing_pms', verbose_name=_('Message'))
    recipient = models.ForeignKey(User, related_name='incoming_pms', verbose_name=_('Recipient'))
    is_read   = models.BooleanField(_('Is read'), default=False)

    def __unicode__(self):
        return ",".join([self.message.subject, self.message.sender.username,
                         self.recipient.username])



signals.post_save.connect(
    Post.post_save, sender=Post, dispatch_uid='djforum_post_save')

signals.post_save.connect(
    Topic.post_save, sender=Topic, dispatch_uid='djforum_topic_save')

signals.post_save.connect(
    Forum.post_save, sender=Forum, dispatch_uid='djforum_forum_save')

registration.signals.user_registered.connect(Profile.user_registered)

from object_permissions import register
register(['view', 'edit', 'destroy'], Forum)
register(['view', 'edit', 'destroy'], Topic)