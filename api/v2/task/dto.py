from ninja import Schema


class SubmitCommentCreate(Schema):
    source: str
    line: int | None
    content: str | None


class SubmitCommentUpdate(Schema):
    content: str | None
