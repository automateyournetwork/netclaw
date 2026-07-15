"""Async HTTP client for Ollama API."""

import time
from typing import Optional, Dict, Any, List

import httpx


class OllamaClient:
    """Async client for communicating with an Ollama instance."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def is_reachable(self) -> bool:
        """Check if the Ollama instance is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> List[str]:
        """List all available models on the Ollama instance."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except (httpx.HTTPError, KeyError):
            return []

    async def model_exists(self, model: str) -> bool:
        """Check if a specific model is available."""
        models = await self.list_models()
        # Ollama model names can be "name:tag" — match with or without tag
        for m in models:
            if m == model or m.startswith(f"{model}:"):
                return True
        return False

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call Ollama's generate endpoint (single-turn).

        Returns dict with keys: response, total_duration, eval_count, etc.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        client = await self._get_client()
        start = time.monotonic()
        resp = await client.post("/api/generate", json=payload)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        resp.raise_for_status()
        result = resp.json()
        result["_elapsed_ms"] = elapsed_ms
        return result

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call Ollama's chat endpoint (multi-turn).

        Returns dict with keys: message, total_duration, eval_count, etc.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options

        client = await self._get_client()
        start = time.monotonic()
        resp = await client.post("/api/chat", json=payload)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        resp.raise_for_status()
        result = resp.json()
        result["_elapsed_ms"] = elapsed_ms
        return result

    async def show_model(self, model: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a model."""
        try:
            client = await self._get_client()
            resp = await client.post("/api/show", json={"name": model})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return None
