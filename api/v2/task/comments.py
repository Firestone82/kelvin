from ninja import Router

from api.auth import require_submit_access
from api.v2.task.dto import SubmitCommentCreate, SubmitCommentUpdate
from common.dto import CommentDTO
from common.models import Comment
from common.services.comments_service import (
    create_submit_comment,
    update_submit_comment,
    delete_submit_comment,
)

router = Router()


@router.post("", url_name="create_submit_comment", summary="TODO:", description="TODO:")
@require_submit_access
def api_create_submit_comment(
    request, assignment_id: int, login: str, submit_num: int, comment_data: SubmitCommentCreate
) -> CommentDTO:
    comment: Comment = create_submit_comment(
        submit=request.submit_instance,  # Passed from require_submit_access
        author=request.user,
        content=comment_data.content,
        source=comment_data.source,
        line=comment_data.line,
    )

    return comment.to_dto(can_edit=True, type=comment.type(), unread=False, notification_id=None)


@router.put("{comment_id}", url_name="modify_submit_comment", summary="TODO:", description="TODO:")
@require_submit_access
def api_modify_submit_comment(
    request,
    assignment_id: int,
    login: str,
    submit_num: int,
    comment_id: int,
    comment_data: SubmitCommentUpdate,
) -> CommentDTO:
    comment: Comment = update_submit_comment(
        submit=request.submit_instance,  # Passed from require_submit_access
        comment_id=comment_id,
        author=request.user,
        new_content=comment_data.content,
    )

    return comment.to_dto(can_edit=True, type=comment.type(), unread=False, notification_id=None)


@router.delete(
    "{comment_id}", url_name="delete_submit_comment", summary="TODO:", description="TODO:"
)
@require_submit_access
def api_delete_submit_comment(
    request, assignment_id: int, login: str, submit_num: int, comment_id: int
):
    delete_submit_comment(comment_id=comment_id, author=request.user)
