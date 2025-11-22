from ninja import Router

from .submit import router as submit_router

router = Router(tags=["Task"])
router.add_router("", submit_router)
# router.add_router("/{assignment_id}/{login}/{submit_num}/comment", comments_router)
