"""Dependency-free JSON-over-HTTP client with retries and client-side throttling.

Uses urllib so the whole toolkit runs on a bare Python 3.9+ install with no
`pip install` step -- important because this is meant to be run on a machine
where blockchain egress actually works.
"""

from __future__ import annotations

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    def __init__(self, status: int, url: str, body: str = ""):
        super().__init__(f"HTTP {status} for {url}: {body[:200]}")
        self.status = status
        self.url = url
        self.body = body


class JsonClient:
    """Throttled JSON client. One instance per host keeps rate limits honest."""

    def __init__(self, timeout=30.0, max_retries=5, min_interval=0.2, api_key=None,
                 user_agent="hoodtrack/1.0"):
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_interval = min_interval
        self.api_key = api_key
        self.user_agent = user_agent
        self._last_call = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()

    def get(self, url, params=None):
        params = dict(params or {})
        if self.api_key:
            params.setdefault("apikey", self.api_key)
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return self._request("GET", url, None)

    def post(self, url, payload):
        return self._request("POST", url, json.dumps(payload).encode())

    def _request(self, method, url, body):
        last_exc = None
        for attempt in range(self.max_retries):
            self._throttle()
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", self.user_agent)
            if body is not None:
                req.add_header("Content-Type", "application/json")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode() or "null")
            except urllib.error.HTTPError as exc:
                text = exc.read().decode(errors="replace")
                if exc.code not in RETRYABLE_STATUS:
                    raise HttpError(exc.code, url, text) from exc
                last_exc = HttpError(exc.code, url, text)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_exc = exc
            backoff = min(2.0 ** attempt, 30.0) + random.uniform(0, 0.4)
            log.warning("retry %d/%d for %s after %s (sleep %.1fs)",
                        attempt + 1, self.max_retries, url, last_exc, backoff)
            time.sleep(backoff)
        raise last_exc if last_exc else RuntimeError(f"request failed: {url}")
