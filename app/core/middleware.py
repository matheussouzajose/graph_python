import json
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from .logger import logger
from .observability.masking import SENSITIVE_KEYS, mask_sensitive_data

__all__ = ["LoggingMiddleware", "mask_sensitive_data", "SENSITIVE_KEYS"]


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()

        # Streaming endpoints (SSE, by convention paths ending in "/stream")
        # never get their request body replayed here. `StreamingResponse`
        # keeps a background task alive for the whole response listening for
        # client disconnect via `receive()` — the synthetic `receive`
        # closure below always returns the same buffered `http.request`
        # message instead of eventually yielding `http.disconnect`, which
        # breaks that listener (`RuntimeError: Unexpected message received`)
        # and kills the stream before any bytes reach the client. Regular
        # JSON endpoints never hit that listener, so this only needs to be
        # skipped here, not fixed at the ASGI level.
        is_streaming_request = request.url.path.endswith("/stream")

        # 1. Process Request
        request_body = b""
        if not is_streaming_request and request.method in ["POST", "PUT", "PATCH"]:
            request_body = await request.body()

            # Restore the body for the route handler
            async def receive():
                return {"type": "http.request", "body": request_body}

            request._receive = receive

        # Log Request (Masked)
        if is_streaming_request:
            logger.info(
                "REQUEST [%s %s] (streaming, body not captured)",
                request.method,
                request.url.path,
            )
        else:
            try:
                req_json = json.loads(request_body) if request_body else {}
                masked_req = mask_sensitive_data(req_json)
                logger.info(
                    "REQUEST [%s %s] Body: %s",
                    request.method,
                    request.url.path,
                    json.dumps(masked_req),
                )
            except Exception:
                logger.info(
                    "REQUEST [%s %s] (Non-JSON or empty body)",
                    request.method,
                    request.url.path,
                )

        # 2. Call the next handler
        try:
            response = await call_next(request)
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error("EXCEPTION after %.2fms: %s", process_time, str(e), exc_info=True)
            return Response(
                content=json.dumps(
                    {"detail": "Erro interno do servidor. A equipe técnica foi notificada."}
                ),
                status_code=500,
                media_type="application/json",
            )

        # 3. Process Response
        process_time = (time.time() - start_time) * 1000

        if is_streaming_request:
            # Consuming `body_iterator` here (like the JSON branch below
            # does) would buffer the entire SSE stream before sending
            # anything — defeating the point of streaming. Just log that it
            # started; there's no full body to log anyway.
            logger.info(
                "RESPONSE [%s %s] (%s) streaming started after %.2fms",
                request.method,
                request.url.path,
                response.status_code,
                process_time,
            )
            return response

        # For logging response body, we need to consume the iterator
        # WARNING: This can be memory intensive for large files.
        # We only log JSON responses.
        if "application/json" in response.headers.get("content-type", ""):
            response_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))

            try:
                full_body = b"".join(response_body)
                res_json = json.loads(full_body)
                masked_res = mask_sensitive_data(res_json)
                logger.info(
                    "RESPONSE [%s %s] (%s) in %.2fms | Body: %s",
                    request.method,
                    request.url.path,
                    response.status_code,
                    process_time,
                    json.dumps(masked_res),
                )
            except Exception:
                logger.info(
                    "RESPONSE [%s %s] (%s) in %.2fms (Empty/Non-JSON)",
                    request.method,
                    request.url.path,
                    response.status_code,
                    process_time,
                )
        else:
            logger.info(
                "RESPONSE [%s %s] (%s) in %.2fms",
                request.method,
                request.url.path,
                response.status_code,
                process_time,
            )

        return response
