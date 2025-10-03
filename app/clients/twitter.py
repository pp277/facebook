import logging
from typing import Tuple

import requests
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type


logger = logging.getLogger(__name__)


class TwitterError(Exception):
    pass


class TwitterClient:
    def __init__(self, bearer_token: str) -> None:
        if not bearer_token:
            raise ValueError("bearer_token is required")
        self.bearer_token = bearer_token

    @retry(
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(TwitterError),
        reraise=True,
    )
    def post_tweet(self, text: str) -> str:
        if not text or not text.strip():
            raise ValueError("text is empty")
        url = "https://api.twitter.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        payload = {"text": text.strip()}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
        except requests.RequestException as exc:
            logger.warning("Twitter request error: %s", exc)
            raise TwitterError(str(exc))

        if resp.status_code >= 500:
            raise TwitterError(f"Server error: {resp.status_code}")
        if resp.status_code >= 400:
            logger.error("Twitter client error %s: %s", resp.status_code, resp.text[:500])
            raise TwitterError(f"Client error: {resp.status_code}")

        tweet_id = (resp.json().get("data") or {}).get("id")
        if not tweet_id:
            raise TwitterError("No tweet id returned")
        return tweet_id


