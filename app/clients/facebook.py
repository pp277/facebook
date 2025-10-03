import logging
from typing import Optional

import requests
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type


logger = logging.getLogger(__name__)


class FacebookError(Exception):
    pass


class FacebookClient:
    def __init__(self, page_id: str, access_token: str) -> None:
        if not page_id or not access_token:
            raise ValueError("page_id and access_token are required")
        self.page_id = page_id
        self.access_token = access_token

    @retry(
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(FacebookError),
        reraise=True,
    )
    def post_photo_with_caption(self, image_url: str, caption: str) -> str:
        if not image_url:
            raise ValueError("image_url is required")
        url = f"https://graph.facebook.com/{self.page_id}/photos"
        payload = {
            "url": image_url,
            "caption": caption,
            "access_token": self.access_token,
        }
        try:
            resp = requests.post(url, data=payload, timeout=25)
        except requests.RequestException as exc:
            logger.warning("Facebook request error: %s", exc)
            raise FacebookError(str(exc))

        if resp.status_code >= 500:
            raise FacebookError(f"Server error: {resp.status_code}")
        if resp.status_code >= 400:
            logger.error("Facebook client error %s: %s", resp.status_code, resp.text[:500])
            raise FacebookError(f"Client error: {resp.status_code}")

        post_id = resp.json().get("id")
        if not post_id:
            raise FacebookError("No post id returned")
        return post_id


