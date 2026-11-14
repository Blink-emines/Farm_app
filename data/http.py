"""Tiny HTTP helper: urllib only, with a timeout, a retry and clear errors."""
import json
import time
import urllib.error
import urllib.request

from .errors import UpstreamUnavailable

USER_AGENT = "crop-rotation-mvp/0.1 (research prototype)"


def fetch_json(url, timeout=60, retries=1):
    """GET a URL and return parsed JSON. Any failure becomes UpstreamUnavailable."""
    last = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(2)
    raise UpstreamUnavailable(f"Request to {url.split('?')[0]} failed: {last}")
