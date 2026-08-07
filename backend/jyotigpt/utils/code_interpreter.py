"""Remote code execution against a Jupyter server.

Connects to a Jupyter kernel over its REST and WebSocket APIs, submits an
``execute_request`` message, and accumulates stdout, stderr, and results
(text/plain or base64 PNG) until the kernel reports idle or the timeout
elapses.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

import aiohttp
import websockets
from pydantic import BaseModel

from jyotigpt.env import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["MAIN"])


class ResultModel(BaseModel):
    """Captured output of one code execution."""

    stdout: Optional[str] = ""
    stderr: Optional[str] = ""
    result: Optional[str] = ""


class JupyterCodeExecuter:
    """Execute code in a Jupyter notebook kernel.

    Supports both token- and password-based authentication, creates a fresh
    kernel for each ``run()``, and always tears the kernel down on exit.
    """

    def __init__(
        self,
        base_url: str,
        code: str,
        token: str = "",
        password: str = "",
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.code = code
        self.token = token
        self.password = password
        self.timeout = timeout
        self.kernel_id = ""
        self.session = aiohttp.ClientSession(base_url=self.base_url)
        self.params = {}
        self.result = ResultModel()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.kernel_id:
            try:
                async with self.session.delete(
                    f"/api/kernels/{self.kernel_id}", params=self.params
                ) as response:
                    response.raise_for_status()
            except Exception as err:
                logger.exception("close kernel failed, %s", err)
        await self.session.close()

    async def run(self) -> ResultModel:
        """Run the full lifecycle: authenticate, create kernel, execute."""
        try:
            await self.sign_in()
            await self.init_kernel()
            await self.execute_code()
        except Exception as err:
            logger.exception("execute code failed, %s", err)
            self.result.stderr = f"Error: {err}"
        return self.result

    async def sign_in(self) -> None:
        """Authenticate with a password, or attach a token to all requests."""
        if self.password and not self.token:
            async with self.session.get("/login") as response:
                response.raise_for_status()
                xsrf_token = response.cookies["_xsrf"].value
                if not xsrf_token:
                    raise ValueError("_xsrf token not found")
                self.session.cookie_jar.update_cookies(response.cookies)
                self.session.headers.update({"X-XSRFToken": xsrf_token})
            async with self.session.post(
                "/login",
                data={"_xsrf": xsrf_token, "password": self.password},
                allow_redirects=False,
            ) as response:
                response.raise_for_status()
                self.session.cookie_jar.update_cookies(response.cookies)

        if self.token:
            self.params.update({"token": self.token})

    async def init_kernel(self) -> None:
        """Create a new kernel and store its id."""
        async with self.session.post(
            url="/api/kernels", params=self.params
        ) as response:
            response.raise_for_status()
            kernel_data = await response.json()
            self.kernel_id = kernel_data["id"]

    def init_ws(self):
        """Derive the kernel WebSocket URL (and auth headers) from session state."""
        ws_base = self.base_url.replace("http", "ws")
        query = "?" + "&".join(f"{key}={val}" for key, val in self.params.items())
        websocket_url = f"{ws_base}/api/kernels/{self.kernel_id}/channels{query}"
        ws_headers = {}
        if self.password and not self.token:
            ws_headers = {
                "Cookie": "; ".join(
                    f"{cookie.key}={cookie.value}"
                    for cookie in self.session.cookie_jar
                ),
                **self.session.headers,
            }
        return websocket_url, ws_headers

    async def execute_code(self) -> None:
        """Open the kernel channel socket and run the code."""
        websocket_url, ws_headers = self.init_ws()
        async with websockets.connect(
            websocket_url, additional_headers=ws_headers
        ) as ws:
            await self.execute_in_jupyter(ws)

    async def execute_in_jupyter(self, ws) -> None:
        """Send an ``execute_request`` and collect replies until idle/timeout."""
        msg_id = uuid.uuid4().hex
        await ws.send(
            json.dumps(
                {
                    "header": {
                        "msg_id": msg_id,
                        "msg_type": "execute_request",
                        "username": "user",
                        "session": uuid.uuid4().hex,
                        "date": "",
                        "version": "5.3",
                    },
                    "parent_header": {},
                    "metadata": {},
                    "content": {
                        "code": self.code,
                        "silent": False,
                        "store_history": True,
                        "user_expressions": {},
                        "allow_stdin": False,
                        "stop_on_error": True,
                    },
                    "channel": "shell",
                }
            )
        )

        stdout, stderr = "", ""
        result_parts = []
        while True:
            try:
                message = await asyncio.wait_for(ws.recv(), self.timeout)
                message_data = json.loads(message)

                if message_data.get("parent_header", {}).get("msg_id") != msg_id:
                    continue

                msg_type = message_data.get("msg_type")
                match msg_type:
                    case "stream":
                        stream_name = message_data["content"]["name"]
                        if stream_name == "stdout":
                            stdout += message_data["content"]["text"]
                        elif stream_name == "stderr":
                            stderr += message_data["content"]["text"]
                    case "execute_result" | "display_data":
                        data = message_data["content"]["data"]
                        if "image/png" in data:
                            result_parts.append(f"data:image/png;base64,{data['image/png']}")
                        elif "text/plain" in data:
                            result_parts.append(data["text/plain"])
                    case "error":
                        stderr += "\n".join(message_data["content"]["traceback"])
                    case "status":
                        if message_data["content"]["execution_state"] == "idle":
                            break
            except asyncio.TimeoutError:
                stderr += "\nExecution timed out."
                break

        self.result.stdout = stdout.strip()
        self.result.stderr = stderr.strip()
        self.result.result = "\n".join(result_parts).strip() if result_parts else ""


async def execute_code_jupyter(
    base_url: str, code: str, token: str = "", password: str = "", timeout: int = 60
) -> dict:
    """Execute ``code`` on a Jupyter server and return the serialized result."""
    async with JupyterCodeExecuter(
        base_url, code, token, password, timeout
    ) as executor:
        result = await executor.run()
        return result.model_dump()
