from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from notifications.models import Notification
from notifications.signals import notify

from common.dto import CommentDTO
from common.exceptions.http_exceptions import HttpException403
from common.models import Submit, Comment


def get_submit_comment(submit: Submit, comment_id: int, notifications: dict = None) -> CommentDTO:
    comment: Comment = get_object_or_404(Comment, id=comment_id)

    if not notifications:
        notifications = {
            c.action_object.id: c
            for c in Notification.objects.filter(
                target_object_id=submit.id,
                target_content_type=ContentType.objects.get_for_model(Submit),
            )
        }

    notification = notifications.get(comment.id, None)
    unread = False
    notification_id = None

    if notification:
        unread = notification.unread
        notification_id = notification.id

    return comment.to_dto(
        can_edit=True, type=comment.type(), unread=unread, notification_id=notification_id
    )


def create_submit_comment(
    submit: Submit,
    author: settings.AUTH_USER_MODEL,
    content: str,
    source: str | None,
    line: int | None,
) -> Comment:
    comment: Comment = Comment(submit=submit, author=author, text=content, source=source, line=line)
    comment.save()

    notify.send(
        sender=author,
        recipient=fetch_comment_recipients(submit=submit, current_author=author),
        verb="added new",
        action_object=comment,
        target=submit,
        public=False,
        important=True,
    )

    return comment


def update_submit_comment(
    submit: Submit, comment_id: int, author: settings.AUTH_USER_MODEL, new_content: str
):
    # If content is empty. Delete the comment instead.
    if not new_content:
        delete_submit_comment(comment_id, author)
        return None

    comment = get_object_or_404(Comment, id=comment_id)

    if comment.author != author:
        raise HttpException403("Only the author can update the comment")

    Notification.objects.filter(
        action_object_object_id=comment.id,
        action_object_content_type=ContentType.objects.get_for_model(Comment),
    ).delete()

    if comment.text != new_content:
        comment.text = new_content
        comment.save()

        notify.send(
            sender=author,
            recipient=fetch_comment_recipients(submit, author),
            verb="updated",
            action_object=comment,
            target=submit,
            public=False,
            important=True,
        )

    return comment


def delete_submit_comment(comment_id: int, author: settings.AUTH_USER_MODEL):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.author != author:
        raise HttpException403("Only the author can delete the comment")

    Notification.objects.filter(
        action_object_object_id=comment.id,
        action_object_content_type=ContentType.objects.get_for_model(Comment),
    ).delete()

    comment.delete()


def fetch_comment_recipients(submit: Submit, current_author: settings.AUTH_USER_MODEL):
    recipients = [submit.assignment.clazz.teacher, submit.student]

    # Add all participants
    for comment in Comment.objects.filter(submit_id=submit.id):
        if comment.author not in recipients:
            recipients.append(comment.author)

    recipients.remove(current_author)
    return recipients
