"""Structured audit logging middleware.

Captures request and response bodies (up to a size limit), HTTP metadata,
and authenticated user information for write-class requests. Logs are
emitted through Loguru's ``auditable`` binding and written to the file
handler configured in ``utils/logger.py``.
"""

import re
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    MutableMapping,
    Optional,
    cast,
)

from asgiref.typing import (
    ASGI3Application,
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
    Scope as ASGIScope,
)
from loguru import logger
from starlette.requests import Request

from jyotigpt.env import AUDIT_LOG_LEVEL, MAX_BODY_LOG_SIZE
from jyotigpt.models.users import UserModel
from jyotigpt.utils.auth import get_current_user, get_http_authorization_cred

if TYPE_CHECKING:
    from loguru import Logger


@dataclass(frozen=True)
class AuditLogEntry:
    """Immutable record of one audited HTTP request.

    Fields are grouped by audit level: ``METADATA`` includes id through
    source_ip; ``REQUEST`` adds request_object; ``REQUEST_RESPONSE`` adds
    response_object and response_status_code.
    """

    id: str
    user: dict[str, Any]
    audit_level: str
    verb: str
    request_uri: str
    user_agent: Optional[str] = None
    source_ip: Optional[str] = None
    request_object: Any = None
    response_object: Any = None
    response_status_code: Optional[int] = None


class AuditLevel(str, Enum):
    """Controls how much data is captured in audit logs."""

    NONE = "NONE"
    METADATA = "METADATA"
    REQUEST = "REQUEST"
    REQUEST_RESPONSE = "REQUEST_RESPONSE"


class AuditLogger:
    """Writes structured audit entries through Loguru's auditable channel."""

    def __init__(self, logger: "Logger"):
        self.logger = logger.bind(auditable=True)

    def write(
        self,
        audit_entry: AuditLogEntry,
        *,
        log_level: str = "INFO",
        extra: Optional[dict] = None,
    ):
        """Emit ``audit_entry`` with optional extra metadata."""
        entry = asdict(audit_entry)
        if extra:
            entry["extra"] = extra
        self.logger.log(log_level, "", **entry)


class AuditContext:
    """Accumulator for request/response bodies during one request lifecycle.

    Captures up to ``max_body_size`` bytes of each stream to prevent
    excessive memory usage. Additional metadata (response status) is stored
    in the ``metadata`` dict.
    """

    def __init__(self, max_body_size: int = MAX_BODY_LOG_SIZE):
        self.request_body = bytearray()
        self.response_body = bytearray()
        self.max_body_size = max_body_size
        self.metadata: Dict[str, Any] = {}

    def add_request_chunk(self, chunk: bytes):
        if len(self.request_body) < self.max_body_size:
            remaining = self.max_body_size - len(self.request_body)
            self.request_body.extend(chunk[:remaining])

    def add_response_chunk(self, chunk: bytes):
        if len(self.response_body) < self.max_body_size:
            remaining = self.max_body_size - len(self.response_body)
            self.response_body.extend(chunk[:remaining])


class AuditLoggingMiddleware:
    """ASGI middleware that logs structured audit entries for write operations.

    Only audits PUT/PATCH/DELETE/POST requests with an Authorization header,
    skipping paths matching the excluded-path patterns and respecting the
    configured audit level.
    """

    AUDITED_METHODS = {"PUT", "PATCH", "DELETE", "POST"}

    def __init__(
        self,
        app: ASGI3Application,
        *,
        excluded_paths: Optional[list[str]] = None,
        max_body_size: int = MAX_BODY_LOG_SIZE,
        audit_level: AuditLevel = AuditLevel.NONE,
    ) -> None:
        self.app = app
        self.audit_logger = AuditLogger(logger)
        self.excluded_paths = excluded_paths or []
        self.max_body_size = max_body_size
        self.audit_level = audit_level

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceiveCallable,
        send: ASGISendCallable,
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope=cast(MutableMapping, scope))

        if self._should_skip_auditing(request):
            return await self.app(scope, receive, send)

        async with self._audit_context(request) as context:

            async def send_wrapper(message: ASGISendEvent) -> None:
                if self.audit_level == AuditLevel.REQUEST_RESPONSE:
                    await self._capture_response(message, context)
                await send(message)

            async def receive_wrapper() -> ASGIReceiveEvent:
                message = await receive()
                if self.audit_level in (
                    AuditLevel.REQUEST,
                    AuditLevel.REQUEST_RESPONSE,
                ):
                    await self._capture_request(message, context)
                return message

            await self.app(scope, receive_wrapper, send_wrapper)

    @asynccontextmanager
    async def _audit_context(
        self, request: Request
    ) -> AsyncGenerator[AuditContext, None]:
        """Context manager that logs the audit entry on exit."""
        context = AuditContext()
        try:
            yield context
        finally:
            await self._log_audit_entry(request, context)

    async def _get_authenticated_user(self, request: Request) -> UserModel:
        """Resolve the user from the Authorization header."""
        auth_header = request.headers.get("Authorization")
        assert auth_header
        return get_current_user(
            request, None, get_http_authorization_cred(auth_header)
        )

    def _should_skip_auditing(self, request: Request) -> bool:
        """Return ``True`` if this request should not be audited."""
        if (
            request.method not in self.AUDITED_METHODS
            or AUDIT_LOG_LEVEL == "NONE"
            or not request.headers.get("authorization")
        ):
            return True

        pattern = re.compile(
            r"^/api(?:/v1)?/(" + "|".join(self.excluded_paths) + r")\b"
        )
        return bool(pattern.match(request.url.path))

    async def _capture_request(
        self, message: ASGIReceiveEvent, context: AuditContext
    ):
        """Append the request body chunk to the audit context."""
        if message["type"] == "http.request":
            body = message.get("body", b"")
            context.add_request_chunk(body)

    async def _capture_response(
        self, message: ASGISendEvent, context: AuditContext
    ):
        """Append the response body/status to the audit context."""
        if message["type"] == "http.response.start":
            context.metadata["response_status_code"] = message["status"]
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            context.add_response_chunk(body)

    async def _log_audit_entry(self, request: Request, context: AuditContext):
        """Construct and write the final audit log entry."""
        try:
            user = await self._get_authenticated_user(request)

            entry = AuditLogEntry(
                id=str(uuid.uuid4()),
                user=user.model_dump(include={"id", "name", "email", "role"}),
                audit_level=self.audit_level.value,
                verb=request.method,
                request_uri=str(request.url),
                response_status_code=context.metadata.get("response_status_code", None),
                source_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_object=context.request_body.decode("utf-8", errors="replace"),
                response_object=context.response_body.decode("utf-8", errors="replace"),
            )

            self.audit_logger.write(entry)
        except Exception as e:
            logger.error(f"Failed to log audit entry: {str(e)}")
