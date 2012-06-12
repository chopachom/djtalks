# -*- coding: utf-8 -*-
"""
:Authors:
    - qweqwe
"""

from django.contrib import admin
from django.db import transaction

from djtalks.djforum.models import Forum, Topic, Post

class ForumAdmin(admin.ModelAdmin):
    #TODO: comments
    @transaction.commit_on_success
    def save_model(self, request, obj, form, change):
        """
        :type obj: :class:`djtalks.djforum.models.Forum`
        """
        # if this forum has parent, then we should populate certain fields
        if obj.parent:
            parent = obj.parent
            obj.depth = parent.depth + 1
            obj.path  = (parent.path or '') + "{}.".format(parent.id)
            #TODO: change path of all descendants
            if change:
                previous_obj = Forum.objects.get(pk=obj.id)
                previous_parent = previous_obj.parent
                # if previous parent existed and we are moving the forum to a new parent
                if previous_parent and parent.id != previous_parent.id:
                    # we should check if previous parent has subforums, and if
                    # it is not then we should update its has_subforums
                    if not previous_parent.children.count():
                        previous_parent.has_subforums = False
                        previous_parent.save()
                #FIXME: dummy shim
                descendants = previous_obj.descendants()
                print previous_obj, descendants, len(descendants)
                for descendant in descendants:
                    descendant.depth  = obj.depth + 1
                    descendant.path   = (obj.path or '') + "{}.".format(obj.id)
                    descendant.save()
                    print descendant, descendant.depth, descendant.path

            if not parent.has_subforums:
                parent.has_subforums = True
                parent.save()
        obj.save()

admin.site.register(Forum, ForumAdmin)