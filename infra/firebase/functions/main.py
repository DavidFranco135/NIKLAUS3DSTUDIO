"""Phase 0 spike: validate that (a) a plain Python Cloud Function deploys and
responds, and (b) the existing FastAPI app can run inside a Cloud Function via
a hand-rolled ASGI-to-WSGI bridge, since Firebase's Python Functions SDK
builds its `https_fn.Request`/`Response` on Flask (WSGI), not ASGI.

Once this is validated, apps/api's real FastAPI app gets wired in the same
way as part of Phase 3 (see the migration plan) instead of this toy app.
"""

from firebase_functions import https_fn, options
from fastapi import FastAPI

options.set_global_options(region="us-central1")


@https_fn.on_request(invoker="public")
def ping(req: https_fn.Request) -> https_fn.Response:
    return https_fn.Response("pong", status=200)


_fastapi_app = FastAPI()


@_fastapi_app.get("/hello")
def _hello() -> dict[str, str]:
    return {"message": "Hello from FastAPI running inside a Firebase Cloud Function"}


def _call_asgi_via_wsgi_environ(app: FastAPI, environ: dict) -> tuple[bytes, int, list[tuple[str, str]]]:
    """Runs an ASGI app synchronously against a WSGI environ (what Firebase's

    Flask-based Request gives us) by converting environ -> ASGI scope,
    driving the app with asyncio.run, and collecting the response. This is
    the piece being validated — if it works cleanly here, apps/api's real
    FastAPI app gets the same treatment in Phase 3.
    """
    import asyncio

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": environ["REQUEST_METHOD"],
        "path": environ.get("PATH_INFO", "/"),
        "raw_path": environ.get("PATH_INFO", "/").encode(),
        "query_string": environ.get("QUERY_STRING", "").encode(),
        "headers": [
            (k[5:].lower().replace("_", "-").encode(), v.encode())
            for k, v in environ.items()
            if k.startswith("HTTP_")
        ],
        "server": (environ.get("SERVER_NAME", ""), int(environ.get("SERVER_PORT", 0) or 0)),
        "client": (environ.get("REMOTE_ADDR", ""), 0),
    }
    body_stream = environ.get("wsgi.input")
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    request_body = body_stream.read(content_length) if body_stream and content_length > 0 else b""

    response_parts: dict = {"status": 500, "headers": [], "body": b""}

    async def receive():
        return {"type": "http.request", "body": request_body, "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            response_parts["status"] = message["status"]
            response_parts["headers"] = message["headers"]
        elif message["type"] == "http.response.body":
            response_parts["body"] += message.get("body", b"")

    asyncio.run(app(scope, receive, send))

    headers = [(k.decode(), v.decode()) for k, v in response_parts["headers"]]
    return response_parts["body"], response_parts["status"], headers


@https_fn.on_request(invoker="public")
def api(req: https_fn.Request) -> https_fn.Response:
    body, status_code, headers = _call_asgi_via_wsgi_environ(_fastapi_app, req.environ)
    return https_fn.Response(body, status=status_code, headers=dict(headers))
