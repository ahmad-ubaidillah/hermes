"""Aizen Bridge Client - Python client for remote Aizen Agent access.

Connects to a Aizen Bridge Server via WebSocket or REST API.

Usage:
    from bridge.client import BridgeClient

    # WebSocket client (recommended for streaming)
    client = BridgeClient("ws://localhost:8765", token="jwt...")
    response = client.chat("Hello Aizen!")

    # REST client
    client = BridgeClient("http://localhost:8765", api_key="key...")
    response = client.chat("Hello Aizen!")

    # Streaming
    for chunk in client.stream_chat("Tell me a story"):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import requests

logger = logging.getLogger("bridge.client")


class BridgeClient:
    """Client for connecting to a Aizen Bridge Server.

    Supports both REST API and WebSocket connections.
    WebSocket is preferred for streaming and real-time interaction.

    Args:
        base_url: Bridge server URL (ws:// or http://)
        token: JWT authentication token
        api_key: Simple API key (alternative to JWT)
        session_id: Session ID to use (auto-generated if None)
        reconnect: Enable auto-reconnection for WebSocket
        reconnect_delay: Delay between reconnection attempts (seconds)
        max_reconnect_attempts: Maximum reconnection attempts

    Example:
        >>> client = BridgeClient("ws://localhost:8765")
        >>> response = client.chat("What is Python?")
        >>> print(response)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8765",
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        reconnect: bool = True,
        reconnect_delay: float = 2.0,
        max_reconnect_attempts: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.api_key = api_key
        self.session_id = session_id or f"client_{int(time.time())}"
        self.model = model
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        self._ws = None
        self._connected = False
        self._reconnect_attempt = 0
        self._headers = {}

        if api_key:
            self._headers["X-API-Key"] = api_key
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            import websockets
            import asyncio

            ws_url = self.base_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )
            ws_url = f"{ws_url}/ws/{self.session_id}"

            self._ws = asyncio.get_event_loop().run_until_complete(
                websockets.connect(
                    ws_url,
                    additional_headers=self._headers,
                )
            )
            self._connected = True
            self._reconnect_attempt = 0

            # Authenticate
            if self.token:
                asyncio.get_event_loop().run_until_complete(
                    self._ws.send(json.dumps({"type": "auth", "token": self.token}))
                )

            logger.info("Connected to bridge at %s", self.base_url)
            return True
        except ImportError:
            logger.warning(
                "websockets not installed. Install with: pip install websockets"
            )
            return False
        except Exception as e:
            logger.error("Failed to connect: %s", e)
            self._connected = False
            return False

    def disconnect(self):
        """Close WebSocket connection."""
        if self._ws:
            try:
                import asyncio

                asyncio.get_event_loop().run_until_complete(self._ws.close())
            except Exception:
                pass
            self._ws = None
        self._connected = False

    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        return self._connected and self._ws is not None

    # ------------------------------------------------------------------
    # Chat methods
    # ------------------------------------------------------------------
    def chat(self, message: str, session_id: str = None, model: str = None) -> str:
        """Send a message and get a response.

        Uses REST API by default. Falls back to WebSocket if connected.

        Args:
            message: User message
            session_id: Optional session override
            model: Optional model override

        Returns:
            Agent response string
        """
        # Try WebSocket first if connected
        if self.is_connected():
            return self._chat_ws(message, session_id, model)

        # Fall back to REST
        return self._chat_rest(message, session_id, model)

    def _chat_rest(
        self, message: str, session_id: str = None, model: str = None
    ) -> str:
        """Send chat via REST API."""
        url = f"{self.base_url}/chat"
        payload = {
            "message": message,
            "session_id": session_id or self.session_id,
            "model": model or self.model,
        }
        try:
            response = requests.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.exceptions.RequestException as e:
            logger.error("REST chat failed: %s", e)
            raise

    def _chat_ws(self, message: str, session_id: str = None, model: str = None) -> str:
        """Send chat via WebSocket."""
        import asyncio

        async def _send():
            await self._ws.send(
                json.dumps(
                    {
                        "type": "chat",
                        "message": message,
                        "session_id": session_id or self.session_id,
                        "model": model or self.model,
                    }
                )
            )

            chunks = []
            while True:
                msg = await self._ws.recv()
                data = json.loads(msg)
                msg_type = data.get("type", "")

                if msg_type == "chunk":
                    chunk = data.get("chunk", "")
                    chunks.append(chunk)
                elif msg_type == "done":
                    return "".join(chunks)
                elif msg_type == "error":
                    raise RuntimeError(data.get("message", "Unknown error"))

        try:
            return asyncio.get_event_loop().run_until_complete(_send())
        except Exception as e:
            logger.error("WebSocket chat failed: %s", e)
            # Try reconnect
            if self.reconnect and self._reconnect_attempt < self.max_reconnect_attempts:
                self._reconnect_attempt += 1
                time.sleep(self.reconnect_delay)
                if self.connect():
                    return self._chat_ws(message, session_id, model)
            raise

    def stream_chat(
        self, message: str, session_id: str = None, model: str = None
    ) -> Iterator[str]:
        """Stream response chunks.

        Requires WebSocket connection.

        Args:
            message: User message
            session_id: Optional session override
            model: Optional model override

        Yields:
            Response text chunks
        """
        if not self.is_connected():
            raise RuntimeError("WebSocket not connected. Call connect() first.")

        import asyncio

        async def _stream():
            await self._ws.send(
                json.dumps(
                    {
                        "type": "chat_stream",
                        "message": message,
                        "session_id": session_id or self.session_id,
                        "model": model or self.model,
                    }
                )
            )

            while True:
                msg = await self._ws.recv()
                data = json.loads(msg)
                msg_type = data.get("type", "")

                if msg_type == "chunk":
                    yield data.get("chunk", "")
                elif msg_type == "done":
                    break
                elif msg_type == "error":
                    raise RuntimeError(data.get("message", "Unknown error"))

        yield from asyncio.get_event_loop().run_until_complete(
            self._collect_stream(_stream())
        )

    async def _collect_stream(self, async_gen):
        """Collect async generator into list for sync iteration."""
        results = []
        async for item in async_gen:
            results.append(item)
        return results

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def get_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        url = f"{self.base_url}/sessions"
        response = requests.get(url, headers=self._headers)
        response.raise_for_status()
        return response.json()

    def get_session(self, session_id: str = None) -> Dict[str, Any]:
        """Get session details."""
        sid = session_id or self.session_id
        url = f"{self.base_url}/sessions/{sid}"
        response = requests.get(url, headers=self._headers)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Tools and models
    # ------------------------------------------------------------------
    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        url = f"{self.base_url}/tools"
        response = requests.get(url, headers=self._headers)
        response.raise_for_status()
        data = response.json()
        return data.get("tools", [])

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        url = f"{self.base_url}/models"
        response = requests.get(url, headers=self._headers)
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def upload_file(self, file_path: str, remote_path: str = None) -> Dict[str, Any]:
        """Upload a file to the bridge server workspace.

        Args:
            file_path: Local file path
            remote_path: Remote path (defaults to filename)

        Returns:
            Upload result
        """
        url = f"{self.base_url}/files/upload"
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "rb") as f:
            files = {"file": (remote_path or path.name, f)}
            data = {"path": remote_path or path.name}
            response = requests.post(url, files=files, data=data, headers=self._headers)

        response.raise_for_status()
        return response.json()

    def download_file(self, remote_path: str, local_path: str = None) -> Path:
        """Download a file from the bridge server workspace.

        Args:
            remote_path: Remote file path
            local_path: Local save path (defaults to filename)

        Returns:
            Path to downloaded file
        """
        url = f"{self.base_url}/files/download"
        response = requests.get(
            url,
            params={"path": remote_path},
            headers=self._headers,
            stream=True,
        )
        response.raise_for_status()

        save_path = Path(local_path or Path(remote_path).name)
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return save_path

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """Check bridge server health."""
        url = f"{self.base_url}/health"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def __del__(self):
        self.disconnect()
