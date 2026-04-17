import django_rq

RATE_LIMIT_REDIS_KEY = "ai_review:api_rate_limit"


class ApiRateLimiter:
    """
    Redis-backed rate limiter for the OpenAI API.

    Uses SET NX with a millisecond TTL so the check-and-acquire is atomic
    across all RQ workers sharing the same Redis instance.
    """

    def __init__(self, queue_name: str, interval_seconds: float):
        self._redis = django_rq.get_connection(queue_name)
        self._interval_ms = int(interval_seconds * 1000)

    def try_acquire(self) -> float:
        """
        Attempts to claim the next available rate-limit slot.

        Returns 0.0 when the slot is acquired and the caller may proceed.
        Returns a positive wait time in seconds when the slot is already
        taken; the caller should reschedule and retry after that interval.
        """
        acquired = self._redis.set(RATE_LIMIT_REDIS_KEY, 1, nx=True, px=self._interval_ms)
        if acquired:
            return 0.0
        ttl_ms = self._redis.pttl(RATE_LIMIT_REDIS_KEY)
        return max(ttl_ms / 1000.0, 0.05) if ttl_ms > 0 else 0.05
