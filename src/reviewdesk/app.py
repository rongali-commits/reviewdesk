from __future__ import annotations

import asyncio
import csv
import hmac
import io
import re
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Literal

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import Settings
from .mailer import Mailer
from .storage import Storage

STATIC_DIR = Path(__file__).parent / "static"
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class SlidingWindowLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.limit = requests_per_minute
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        current = time.monotonic()
        bucket = self.events[key]
        while bucket and bucket[0] < current - 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(current)
        return True


class ContactCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=200)
    phone: str = Field(default="", max_length=40)
    service: str = Field(default="", max_length=120)
    service_date: str = Field(default="", max_length=20)
    source: str = Field(default="manual", max_length=80)
    reminders_enabled: bool = True
    website: str = Field(default="", max_length=200, exclude=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value.lower()

    @model_validator(mode="after")
    def reject_bot(self) -> ContactCreate:
        if self.website:
            raise ValueError("Request could not be accepted")
        return self


class BulkContacts(BaseModel):
    contacts: list[ContactCreate] = Field(min_length=1, max_length=500)


class ContactWebhook(BaseModel):
    event: Literal["customer.completed", "job.completed", "invoice.paid"]
    customer: ContactCreate


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=2000)
    display_name: str = Field(min_length=2, max_length=100)
    testimonial_consent: bool = False
    website: str = Field(default="", max_length=200, exclude=True)

    @model_validator(mode="after")
    def reject_bot(self) -> FeedbackCreate:
        if self.website:
            raise ValueError("Feedback could not be accepted")
        return self


class FeatureUpdate(BaseModel):
    featured: bool


class BusinessUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    short_name: str = Field(min_length=1, max_length=40)
    logo_text: str = Field(min_length=1, max_length=3)
    tagline: str = Field(min_length=2, max_length=180)
    primary_color: str
    accent_color: str
    contact_email: str = Field(max_length=200)
    sender_name: str = Field(min_length=2, max_length=100)
    reply_to: str = Field(max_length=200)
    public_review_label: str = Field(min_length=2, max_length=80)
    public_review_url: str = Field(default="", max_length=500)
    privacy_url: str = Field(default="", max_length=500)
    thank_you_message: str = Field(min_length=10, max_length=500)
    review_prompt: str = Field(min_length=2, max_length=180)
    testimonial_heading: str = Field(min_length=2, max_length=120)

    @field_validator("primary_color", "accent_color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not HEX_RE.match(value):
            raise ValueError("Use a six-digit hex color such as #173f3a")
        return value

    @field_validator("contact_email", "reply_to")
    @classmethod
    def validate_business_email(cls, value: str) -> str:
        if value and not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value.lower()

    @field_validator("public_review_url", "privacy_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("URL must begin with https:// or http://")
        return value


class SequenceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    step: int = Field(ge=1, le=10)
    delay_hours: int = Field(ge=0, le=8760)
    name: str = Field(min_length=2, max_length=100)
    subject: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=10, max_length=5000)
    enabled: bool = True


class SequenceUpdate(BaseModel):
    items: list[SequenceItem] = Field(min_length=1, max_length=10)


def csv_safe(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in "=+-@":
        return "'" + value
    return value


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_settings.validate()
    storage = Storage(active_settings.database_path)
    storage.initialize(
        active_settings.load_business(),
        active_settings.load_sequence(),
        seed_demo_data=active_settings.seed_demo_data,
    )
    mailer = Mailer(active_settings)
    feedback_limiter = SlidingWindowLimiter(active_settings.request_rate_limit_per_minute)
    processing_lock = Lock()

    def process_requests() -> dict[str, int]:
        if not processing_lock.acquire(blocking=False):
            return {"processed": 0, "failed": 0}
        processed = 0
        failed = 0
        try:
            business = storage.get_settings()
            for message in storage.due_messages():
                try:
                    provider = mailer.send(message, business)
                    storage.mark_message_sent(message["id"], provider)
                    processed += 1
                except Exception as exc:
                    storage.mark_message_failed(message["id"], str(exc))
                    failed += 1
            return {"processed": processed, "failed": failed}
        finally:
            processing_lock.release()

    async def worker() -> None:
        while True:
            await asyncio.to_thread(process_requests)
            await asyncio.sleep(active_settings.request_poll_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = None
        if active_settings.request_worker_enabled:
            task = asyncio.create_task(worker())
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="ReviewDesk",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.storage = storage
    app.state.process_requests = process_requests
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    if active_settings.app_env == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["Content-Type", "X-Admin-Token", "X-Webhook-Token"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; img-src 'self' data:; frame-ancestors *; "
            "connect-src 'self'; form-action 'self'"
        )
        if request.url.path.startswith(("/admin", "/api/admin")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def require_admin(
        request: Request,
        x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    ) -> None:
        if x_admin_token and hmac.compare_digest(x_admin_token, active_settings.admin_token):
            return
        if (
            active_settings.seed_demo_data
            and request.method == "GET"
            and x_admin_token == "reviewdesk-demo-view"
        ):
            return
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    def require_webhook(
        x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
    ) -> None:
        if not x_webhook_token or not hmac.compare_digest(
            x_webhook_token, active_settings.webhook_token
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/", include_in_schema=False)
    async def demo() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/r/{token}", include_in_schema=False)
    async def review_request(token: str) -> FileResponse:
        if storage.get_contact_by_token(token) is None:
            raise HTTPException(status_code=404, detail="Review request not found")
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/admin", include_in_schema=False)
    async def admin() -> FileResponse:
        return FileResponse(STATIC_DIR / "admin.html")

    @app.get("/wall", include_in_schema=False)
    async def wall() -> FileResponse:
        return FileResponse(STATIC_DIR / "wall.html")

    @app.get("/widget", include_in_schema=False)
    async def widget() -> FileResponse:
        return FileResponse(STATIC_DIR / "wall.html")

    @app.get("/widget.js", include_in_schema=False)
    async def widget_script() -> FileResponse:
        return FileResponse(STATIC_DIR / "widget.js", media_type="application/javascript")

    @app.get("/demo/public", include_in_schema=False)
    async def demo_public_review() -> HTMLResponse:
        return HTMLResponse(
            """
            <!doctype html><html lang="en"><head><meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>ReviewDesk demo handoff</title>
            <style>body{margin:0;background:#f4f1e8;color:#173f3a;font-family:Arial,sans-serif;
            display:grid;place-items:center;min-height:100vh}.card{max-width:580px;background:white;
            border:1px solid #d9ded9;border-radius:24px;padding:42px;
            box-shadow:0 24px 70px #173f3a1a}
            b{color:#c8652d}h1{font-size:36px;margin:0 0 16px}p{font-size:18px;line-height:1.6}
            a{display:inline-block;margin-top:12px;color:#173f3a;font-weight:700}</style></head>
            <body><main class="card"><b>DEMO HANDOFF</b><h1>The honest-review step</h1>
            <p>In a client deployment, this button opens the business's official Google,
            Trustpilot, Facebook, or industry review page.</p>
            <p>ReviewDesk presents the same option to every genuine customer, regardless of
            the rating they submitted. This avoids review gating.</p>
            <a href="/">Return to demo</a></main></body></html>
            """
        )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        if not storage.ping():
            raise HTTPException(status_code=503, detail="Storage is unavailable")
        return {
            "status": "ok",
            "product": "ReviewDesk",
            "version": "1.0.0",
            "storage": "ok",
            "email_provider": active_settings.email_provider,
            "environment": active_settings.app_env,
        }

    @app.get("/api/public/config")
    async def public_config() -> dict[str, Any]:
        business = storage.get_settings()
        return {
            "name": business["name"],
            "short_name": business["short_name"],
            "logo_text": business["logo_text"],
            "tagline": business["tagline"],
            "primary_color": business["primary_color"],
            "accent_color": business["accent_color"],
            "review_prompt": business["review_prompt"],
            "thank_you_message": business["thank_you_message"],
            "public_review_label": business["public_review_label"],
            "privacy_url": business.get("privacy_url", ""),
            "demo": True,
        }

    @app.get("/api/review/{token}")
    async def review_context(token: str) -> dict[str, Any]:
        contact = storage.mark_opened(token)
        if contact is None:
            raise HTTPException(status_code=404, detail="Review request not found")
        business = storage.get_settings()
        return {
            "name": contact["name"],
            "service": contact["service"],
            "service_date": contact["service_date"],
            "responded": contact["status"] == "responded",
            "business": {
                "name": business["name"],
                "short_name": business["short_name"],
                "logo_text": business["logo_text"],
                "tagline": business["tagline"],
                "primary_color": business["primary_color"],
                "accent_color": business["accent_color"],
                "review_prompt": business["review_prompt"],
                "thank_you_message": business["thank_you_message"],
                "public_review_label": business["public_review_label"],
                "privacy_url": business.get("privacy_url", ""),
            },
        }

    @app.post("/api/review/{token}/feedback", status_code=201)
    async def submit_feedback(
        token: str, payload: FeedbackCreate, request: Request
    ) -> dict[str, Any]:
        client_host = request.client.host if request.client else "unknown"
        if not feedback_limiter.allow(client_host):
            raise HTTPException(status_code=429, detail="Please wait before submitting again")
        result = storage.submit_feedback(token, payload.model_dump())
        if result is None:
            raise HTTPException(status_code=404, detail="Review request not found")
        if result.get("duplicate"):
            raise HTTPException(status_code=409, detail="Feedback was already submitted")
        business = storage.get_settings()
        return {
            "message": business["thank_you_message"],
            "public_review_url": (
                f"/r/{token}/public" if business.get("public_review_url") else "/demo/public"
            ),
            "public_review_label": business["public_review_label"],
        }

    @app.post("/api/demo-feedback", status_code=201)
    async def submit_demo_feedback(payload: FeedbackCreate, request: Request) -> dict[str, Any]:
        client_host = request.client.host if request.client else "unknown"
        if not feedback_limiter.allow("demo:" + client_host):
            raise HTTPException(status_code=429, detail="Please wait before submitting again")
        business = storage.get_settings()
        return {
            "message": business["thank_you_message"],
            "public_review_url": "/demo/public",
            "public_review_label": business["public_review_label"],
            "demo": True,
        }

    @app.get("/r/{token}/public", include_in_schema=False)
    async def public_review_handoff(token: str) -> RedirectResponse:
        contact = storage.get_contact_by_token(token)
        if contact is None:
            raise HTTPException(status_code=404, detail="Review request not found")
        business = storage.get_settings()
        target = business.get("public_review_url", "")
        if not target:
            return RedirectResponse("/demo/public", status_code=303)
        storage.record_public_click(token)
        return RedirectResponse(target, status_code=303)

    @app.get("/api/testimonials")
    async def testimonials() -> dict[str, Any]:
        business = storage.get_settings()
        return {
            "business": business["name"],
            "heading": business["testimonial_heading"],
            "primary_color": business["primary_color"],
            "accent_color": business["accent_color"],
            "items": storage.public_testimonials(),
        }

    @app.get("/api/admin/overview", dependencies=[Depends(require_admin)])
    async def admin_overview() -> dict[str, Any]:
        return {
            "metrics": storage.overview(),
            "contacts": storage.list_contacts(12),
            "feedback": storage.list_feedback(8),
            "events": storage.events(12),
            "email_provider": active_settings.email_provider,
        }

    @app.get("/api/admin/contacts", dependencies=[Depends(require_admin)])
    async def contacts() -> dict[str, Any]:
        return {"items": storage.list_contacts()}

    @app.post("/api/admin/contacts", status_code=201, dependencies=[Depends(require_admin)])
    async def create_contact(payload: ContactCreate) -> dict[str, Any]:
        contact = storage.create_contact(payload.model_dump())
        process_requests()
        return {
            "contact": contact,
            "review_url": f"{active_settings.public_base_url}/r/{contact['token']}",
        }

    @app.post(
        "/api/admin/contacts/import",
        status_code=201,
        dependencies=[Depends(require_admin)],
    )
    async def import_contacts(payload: BulkContacts) -> dict[str, Any]:
        contacts = storage.create_contacts([item.model_dump() for item in payload.contacts])
        process_requests()
        return {"created": len(contacts)}

    @app.post(
        "/api/webhooks/customers",
        status_code=201,
        dependencies=[Depends(require_webhook)],
    )
    async def webhook_contact(payload: ContactWebhook) -> dict[str, Any]:
        data = payload.customer.model_dump()
        data["source"] = payload.event
        contact = storage.create_contact(data)
        process_requests()
        return {"id": contact["id"], "status": contact["status"]}

    @app.get("/api/admin/feedback", dependencies=[Depends(require_admin)])
    async def feedback() -> dict[str, Any]:
        return {"items": storage.list_feedback()}

    @app.put(
        "/api/admin/feedback/{feedback_id}",
        dependencies=[Depends(require_admin)],
    )
    async def feature_feedback(feedback_id: int, payload: FeatureUpdate) -> dict[str, Any]:
        result = storage.feature_feedback(feedback_id, payload.featured)
        if result is None:
            raise HTTPException(status_code=404, detail="Feedback not found")
        return {"feedback": result}

    @app.get("/api/admin/settings", dependencies=[Depends(require_admin)])
    async def admin_settings() -> dict[str, Any]:
        return storage.get_settings()

    @app.put("/api/admin/settings", dependencies=[Depends(require_admin)])
    async def update_settings(payload: BusinessUpdate) -> dict[str, Any]:
        return storage.update_settings(payload.model_dump())

    @app.get("/api/admin/sequence", dependencies=[Depends(require_admin)])
    async def sequence() -> dict[str, Any]:
        return {"items": storage.get_sequence()}

    @app.put("/api/admin/sequence", dependencies=[Depends(require_admin)])
    async def update_sequence(payload: SequenceUpdate) -> dict[str, Any]:
        steps = [item.step for item in payload.items]
        if len(steps) != len(set(steps)):
            raise HTTPException(status_code=422, detail="Sequence steps must be unique")
        return {"items": storage.update_sequence([item.model_dump() for item in payload.items])}

    @app.post("/api/admin/process", dependencies=[Depends(require_admin)])
    async def process() -> dict[str, int]:
        return process_requests()

    @app.get("/api/admin/export.csv", dependencies=[Depends(require_admin)])
    async def export_csv() -> StreamingResponse:
        output = io.StringIO()
        fields = [
            "name",
            "email",
            "phone",
            "service",
            "service_date",
            "status",
            "rating",
            "comment",
            "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for contact in storage.list_contacts(5000):
            writer.writerow({key: csv_safe(contact.get(key, "")) for key in fields})
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=reviewdesk-export.csv"},
        )

    return app


app = create_app()


def run() -> None:
    uvicorn.run("reviewdesk.app:app", host="0.0.0.0", port=8000, reload=False)
