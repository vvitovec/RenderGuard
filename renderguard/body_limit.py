"""Bound request streams before multipart parsing can spool arbitrary data to disk."""

from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        maximum = 8 * 1024 * 1024 + 65536 if scope["path"] == "/api/documents/upload" else 65536
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        try:
            oversized = length is not None and int(length) > maximum
        except ValueError:
            return await JSONResponse(
                {"error": "body_length", "message": "Invalid request length"}, status_code=400
            )(scope, receive, send)
        if oversized:
            return await JSONResponse(
                {"error": "body_limit", "message": "Request exceeds the bounded upload / JSON size"},
                status_code=413,
            )(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > maximum:
                return await JSONResponse(
                    {"error": "body_limit", "message": "Stream exceeds the bounded upload / JSON size"},
                    status_code=413,
                )(scope, receive, send)
            if not message.get("more_body", False):
                break
        sent = False

        async def bounded_receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
