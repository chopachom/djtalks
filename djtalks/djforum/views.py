# Create your views here.
from collections import defaultdict
from django.core.urlresolvers import reverse
from django.shortcuts import  render, get_object_or_404, redirect
from django.http import Http404
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from djtalks.djforum.models import *
from djtalks.djforum import forms


def make_forum_tree(parent, forums):
    children = {}
    # take a copy of a list and iterate over it
    for forum in forums[:]:
        if not forum.parent_id or parent and forum.parent_id == parent.id:
            forums.remove(forum)
            children[forum] = {}
    for forum in children:
        children[forum] = make_forum_tree(forum, forums)
    return children

def index(request):
    # if user is not authenticated then request.user will be instance of the
    # AnonymousUser, not the User. Therefore it will not have `get_objects_any_perms`
    # method, so we check if user is authenticated and if he isn't we manually query
    # for the special anonymous user model
    user = request.user if request.user.is_authenticated() \
                        else User.objects.get(pk=settings.ANONYMOUS_USER_ID)
#    # select all the top level forums that current user has access to
#    _forums = user.get_objects_any_perms(Forum).filter(depth=0)
#    top_forums = [forum for forum in _forums]
#    top_forums_ids = [forum.id for forum in top_forums]
#    # create query to select all forums that user has access to
#    q = reduce(lambda acc, f: acc|Q(path__startswith=f.id),
#               top_forums, Q(id__in=top_forums_ids))
#    _forums = Forum.objects.filter(q).select_related('last_post__topic',
#                                                     'last_post__author')

    # selecting all forums that current user has access to
    _forums = user.get_objects_any_perms(Forum, perms=['view'])\
                  .filter(depth__lte=3)\
                  .select_related('last_post__topic', 'last_post__author')
    # make forum tree
    forums = make_forum_tree(None, list(_forums))
    context = dict(forums=forums)
    return render(request, 'djforum/index.html', context)

@transaction.commit_on_success
def forum(request, forum_id):

    user = request.user if \
        request.user.is_authenticated()\
    else \
        User.objects.get(pk=settings.ANONYMOUS_USER_ID)

    forum = get_object_or_404(Forum, pk=forum_id)
    if not user.has_perm('view', forum):
        raise Http404

    form  = forms.AddTopicForm(request.POST or None)
    if form.is_valid_on_submit(request):
        topic = Topic(forum=forum, subject=form.cleaned_data['subject'],
                      author=request.user)
        topic.save()
        post = Post(topic=topic, author=request.user,
                    message=form.cleaned_data['message'],
                    user_ip=request.META.get('REMOTE_ADDR', None))
        post.save()

    topics = forum.topics.order_by('-updated')\
                         .select_related('author','last_post','last_post__author')
    subforums = user.get_objects_any_perms(Forum, perms=['view'])\
                    .descendants(forum, depth=3)\
                    .select_related('last_post__topic', 'last_post__author')

    context = dict(forum=forum, topics=topics, form=form,
                   subforums=make_forum_tree(forum, list(subforums)))

    return render(request, 'djforum/forum.html', context)

@transaction.commit_on_success
def topic(request, topic_id):
    form  = forms.AddPostForm(request.POST or None)
    topic = get_object_or_404(Topic, pk=topic_id)
    user = request.user if\
        request.user.is_authenticated()\
    else\
        User.objects.get(pk=settings.ANONYMOUS_USER_ID)
    if not user.has_perm('view', topic.forum):
        raise Http404
    posts = topic.posts.prefetch_related('author')
    if form.is_valid_on_submit(request):
        post = Post(topic=topic, author=request.user,
                    message=form.cleaned_data['message'],
                    user_ip=request.META.get('REMOTE_ADDR', None))
        post.save()
    payload = dict(topic=topic, posts=posts, form=form)
    return render(request, 'djforum/topic.html', payload)


@login_required
def inbox(request):
    incoming = request.user.incoming_pms.select_related()
    outgoing = request.user.outgoing_pms.select_related().prefetch_related('recipients')
    payload = dict(incoming=incoming, outgoing=outgoing)
    return render(request, 'djforum/inbox.html', payload)


@transaction.commit_on_success
@login_required
def new_pm(request):
    """
    Check:
        - That user can reply to the parent message
          We need to ensure that use can reply to the message, probably comparing
          given user to the list of the recipients of the first message.
    """
    #TODO: make sure that user cannot include himself in recipients
    #TODO: restrict depth to 0 when only two users are participating in the conversation
    form = forms.NewMessageForm(request.POST or None, user=request.user)
    if form.is_valid_on_submit(request):
        parent = form.cleaned_data['parent']
        pm = PrivateMessage(sender=request.user,
                            subject=form.cleaned_data['subject'],
                            message=form.cleaned_data['message'])
        if parent:
            sender = parent.sender
            user   = request.user
            pm.parent  = parent
            pm.conversation_id = parent.conversation_id
            if not form.cleaned_data['subject']:
                pm.subject = parent.subject
            recipients = (set(parent.recipients.all()) - {user}) | {sender}
            if len(recipients) > 1:
                pm.depth = parent.depth + 1
        else:
            recipients = form.cleaned_data['recipients']
        pm.save()
        # deliver message to users
        Inbox.objects.bulk_create([
            Inbox(message=pm, recipient=recipient) for recipient in recipients
        ])
        return redirect(reverse(conversation, args=[pm.conversation_id]))
    payload = dict(form=form)
    return render(request, 'djforum/new_pm.html', payload)

@login_required
def conversation(request, conversation_id):
    def make_message_tree(outgoing, incoming):
        def make_tree(parent, messages):
            children = defaultdict(list)
            for message in messages:
                if message.parent_id == parent.id:
                    children[parent].apend(message)
        messages = list(outgoing)
        messages.extend([message.message for message in incoming])


#        for message in outgoing:
#            print message, message.parent_id, message.depth
#        for message in incoming:
#            print message, message.message.message, message.message.parent_id, message.message.depth
    outgoing = request.user.outgoing_pms.filter(conversation_id=conversation_id).prefetch_related('recipients')
    incoming = request.user.incoming_pms.filter(message__conversation_id=conversation_id).select_related()
    print outgoing, incoming
    make_message_tree(outgoing, incoming)

