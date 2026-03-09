import logging
import time

from fastapi import Request


logger = logging.getLogger("app.request")


async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration = time.perf_counter() - start
    logger.info(
        "%s %s -> %s (%.3fs)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )

    return response