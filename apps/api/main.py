"""Firebase Cloud Functions (2nd gen) entry point for the real FastAPI app.

Replaces the Phase 0 spike (infra/firebase/functions/main.py) now that the
ASGI-to-WSGI bridge it validated is ready to carry real traffic. Firebase's
Python Functions SDK builds `https_fn.Request`/`Response` on Flask (WSGI),
not ASGI, so every request is converted into an ASGI scope and driven
through `src.main:app` with `asyncio.run` - see `_call_asgi_via_wsgi_environ`.

This is a deploy-target change only: `DB_BACKEND` still defaults to
"postgres" (see src/config.py), so the app keeps talking to the same
Render Postgres database it always has. Firestore doesn't become the
backend until Phase 5's cutover.

Secrets (DATABASE_URL, JWT_SECRET, S3_*, API_CORS_ORIGINS) are read from
Secret Manager via the `secrets=` list below - set once per project with
`firebase functions:secrets:set <NAME> --project niklaus3d`, which prompts
for the value directly so it never passes through source control or chat.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from firebase_functions import https_fn, options

from src.main import app as fastapi_app

options.set_global_options(region="us-central1")

_SECRETS = [
    "DATABASE_URL",
    "JWT_SECRET",
    "API_ENV",
    "S3_ENDPOINT_URL",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
    "S3_BUCKET",
    "S3_REGION",
    "API_CORS_ORIGINS",
]


def _call_asgi_via_wsgi_environ(environ: dict) -> tuple[bytes, int, list[tuple[str, str]]]:
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
        ]
        + [
            (name.encode(), environ[key].encode())
            for key, name in (
                ("CONTENT_TYPE", "content-type"),
                ("CONTENT_LENGTH", "content-length"),
            )
            if environ.get(key)
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

    asyncio.run(fastapi_app(scope, receive, send))

    headers = [(k.decode(), v.decode()) for k, v in response_parts["headers"]]
    return response_parts["body"], response_parts["status"], headers


@https_fn.on_request(
    invoker="public",
    memory=options.MemoryOption.GB_1,
    timeout_sec=60,
    secrets=_SECRETS,
)
def api(req: https_fn.Request) -> https_fn.Response:
    body, status_code, headers = _call_asgi_via_wsgi_environ(req.environ)
    return https_fn.Response(body, status=status_code, headers=dict(headers))
