import logging

import httpx

logger = logging.getLogger(__name__)


class SonnenClient:
    def __init__(self, base_url: str, auth_token: str | None = None, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        headers = {"Auth-Token": auth_token} if auth_token else {}
        self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def status(self) -> dict | None:
        try:
            r = self._client.get("/api/v1/status")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            logger.exception("sonnen /api/v1/status request failed")
            return None
