import logging
from typing import List, Dict

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from ninja import Router
from notifications.models import Notification
from serde import to_dict

from api.auth import require_submit_access
from common.ai_review.dto import AIReviewResult, SuggestionState, SubmitSummary
from common.ai_review.processor import AI_REVIEW_COMMENT_AUTHOR, AI_REVIEW_COMMENT_TYPE
from common.dto import (
    AssignedSubmit,
    ImageSource,
    VideoSource,
    TextSource,
    SubmitSources,
    CommentDTO,
    TaskSubmitDetails,
)
from common.models import Submit, Comment
from common.upload import mimedetector
from common.utils import is_teacher
from evaluator.results import EvaluationResult
from web.dto import SubmitData
from web.views.student import is_file_small, get_submit_data

router = Router()

SUPPORTED_IMAGES = [
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
]

SOURCE_PRIORITY = {
    "video": 0,
    "img": 1,
    "source": 2,
}


def fetch_submit_sources(submit: Submit) -> SubmitSources:
    result: SubmitSources = {}

    for source in submit.all_sources():
        mime_type: str | None = mimedetector.from_file(source.phys)

        if mime_type and mime_type.startswith("image/"):
            source_url: str = reverse("submit_source", args=[submit.id, source.virt])
            if mime_type not in SUPPORTED_IMAGES:
                source_url = f"{source_url}?convert=1"

            result[source.virt] = ImageSource(path=source.virt, src=source_url)

        elif mime_type and mime_type.startswith("video/"):
            base_name: str = ".".join(source.virt.split(".")[:-1])

            if base_name not in result:
                result[base_name] = VideoSource(path=base_name)

            video_source: VideoSource = result[base_name]
            video_source.sources.append(reverse("submit_source", args=[submit.id, source.virt]))

        else:
            content_text: str = ""
            content_url: str | None = None
            content_error: str | None = None

            try:
                if is_file_small(source.phys):
                    with open(source.phys) as file_stream:
                        content_text = file_stream.read()
                else:
                    content_url = reverse("submit_source", args=[submit.id, source.virt])
            except UnicodeDecodeError:
                content_error = "The file contains binary data or is not encoded in UTF-8"
            except FileNotFoundError:
                content_error = "Source code not found"

            result[source.virt] = TextSource(
                path=source.virt, content=content_text, content_url=content_url, error=content_error
            )

    # Sort sources by type priority and path
    result = dict(
        sorted(result.items(), key=lambda item: (SOURCE_PRIORITY.get(item[1].type, 99), item[0]))
    )

    return result


def fetch_submit_comments(
    requester: settings.AUTH_USER_MODEL, submit: Submit, sources: SubmitSources, notifications
) -> List[CommentDTO]:
    summary_comments: List[CommentDTO] = []

    for comment in Comment.objects.filter(submit_id=submit.id).order_by("id"):
        is_comment_author: bool = comment.author == requester
        notification = notifications.get(comment.id, None)

        notification_id = None
        unread = False

        if notification:
            notification_id = notification.id
            unread = notification.unread

        try:
            if not comment.source or comment.source not in sources:
                summary_comments.append(
                    comment.to_dto(
                        can_edit=is_comment_author,
                        type=comment.type(),
                        unread=unread,
                        notification_id=notification_id,
                    )
                )
            else:
                max_lines = sources[comment.source].content.count("\n")
                line = 0 if comment.line > max_lines else comment.line

                sources[comment.source].comments.setdefault(line - 1, []).append(
                    comment.to_dto(
                        can_edit=is_comment_author,
                        type=comment.type(),
                        unread=unread,
                        notification_id=notification_id,
                    )
                )
        except KeyError as e:
            logging.exception(e)

    return summary_comments


def process_submit_evaluation_result(result: EvaluationResult, sources: SubmitSources):
    def process_text_source(text_source: TextSource, comment):
        try:
            line = min(text_source.content.count("\n"), int(comment["line"])) - 1

            if not any(
                filter(
                    lambda c: c["text"] == comment["text"],
                    text_source.comments.setdefault(line, []),
                )
            ):
                text_source.comments.setdefault(line, []).append(
                    CommentDTO(
                        author="Kelvin",
                        text=comment["text"],
                        line=None,
                        source=None,
                        type="automated",
                        unread=False,
                        can_edit=False,
                        meta={"url": comment.get("url", None)},
                    )
                )
        except KeyError as e:
            logging.exception(e)

    for pipe in result:
        for source, comments in pipe.comments.items():
            for comment in comments:
                if source not in result:
                    continue

                if isinstance(sources[source], TextSource):
                    process_text_source(sources[source], comment)


def process_submit_review_result(
    requester: settings.AUTH_USER_MODEL,
    result: AIReviewResult,
    sources: SubmitSources,
    summary_comments: list[CommentDTO],
):
    summary: SubmitSummary = result.summary

    def can_view_suggestion(state: SuggestionState, user) -> bool:
        return (
            is_teacher(user)
            and user.has_perm("common.view_suggestedcomment")
            and state is SuggestionState.PENDING
        )

    if can_view_suggestion(summary.state, requester):
        if len(result.summary.text) > 0:
            summary_comments.append(
                CommentDTO(
                    author=AI_REVIEW_COMMENT_AUTHOR,
                    author_id=-1,
                    text=summary.text,
                    line=None,
                    source=None,
                    type=AI_REVIEW_COMMENT_TYPE,
                    unread=False,
                    can_edit=False,
                    meta={
                        AI_REVIEW_COMMENT_TYPE: {
                            "id": summary.id,
                            "state": summary.state.name,
                        }
                    },
                )
            )

    for suggestion in result.suggestions:
        if suggestion.source not in sources:
            continue

        if can_view_suggestion(suggestion.state, requester):
            print(suggestion.source, type(sources[suggestion.source]))

            sources[suggestion.source].comments.setdefault(suggestion.line - 1, []).append(
                CommentDTO(
                    author=AI_REVIEW_COMMENT_AUTHOR,
                    author_id=-1,
                    text=suggestion.text,
                    line=None,
                    source=None,
                    type=AI_REVIEW_COMMENT_TYPE,
                    unread=False,
                    can_edit=False,
                    meta={
                        AI_REVIEW_COMMENT_TYPE: {
                            "id": suggestion.id,
                            "state": suggestion.state.name,
                        }
                    },
                )
            )


@router.get(
    "/{assignment_id}/{login}/{submit_num}",
    url_name="get_submit_details",
    summary="TODO:",
    description="TODO:",
)
@require_submit_access
def api_get_submit_details(request, assignment_id: int, login: str, submit_num: int):
    # Submit instances is already attached to request by the decorator
    submit: Submit = request.submit_instance

    # Retrieve all submits for the student
    submits: list[AssignedSubmit] = [
        AssignedSubmit(
            num=s.submit_num,
            submitted=s.created_at,
            points=s.assigned_points,
            comments=s.comment_set.count(),
        )
        for s in Submit.objects.filter(
            assignment_id=assignment_id, student__username=login
        ).order_by("submit_num")
    ]

    # Retrieve all notifications for submit, used later to mark comments as read/unread
    notifications: Dict[int, Notification] = {
        c.action_object.id: c
        for c in Notification.objects.filter(
            target_object_id=submit.id,
            target_content_type=ContentType.objects.get_for_model(Submit),
        )
    }

    # Fetch submit details
    submit_sources: SubmitSources = fetch_submit_sources(submit)
    submit_data: SubmitData = get_submit_data(submit)  # TODO: Rename to SubmitEvaluationResult?

    # Process comments, returns those not attached to sources
    summary_comments = fetch_submit_comments(request.user, submit, submit_sources, notifications)

    # Process evaluation results and attach comments to sources
    process_submit_evaluation_result(submit_data.results, submit_sources)

    # Process AI review results and attach comments to sources
    if submit_data.ai_review:
        process_submit_review_result(
            request.user, submit_data.ai_review, submit_sources, summary_comments
        )

    details = TaskSubmitDetails(
        sources=submit_sources,
        summary_comments=summary_comments,
        submits=submits,
        current_submit=submit_num,
        deadline=submit.assignment.deadline,
    )

    return to_dict(details)
