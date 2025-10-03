import logging
import random
from typing import List, Optional

import requests
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type


logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


class GroqRephraser:
    def __init__(self, base_url: str, api_keys: List[str], model: str = "llama-3.3-70b-versatile") -> None:
        if not api_keys:
            raise ValueError("At least one API key is required")
        self.base_url = base_url.rstrip("/")
        self.api_keys = list(api_keys)
        self.model = model

    def _pick_key(self) -> str:
        # Randomize to distribute load; failed keys get rotated out on exceptions
        return random.choice(self.api_keys)

    @retry(
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(LLMError),
        reraise=True,
    )
    def rephrase(self, article_text: str, tone_hint: Optional[str] = None) -> str:
        if not article_text or not article_text.strip():
            raise ValueError("article_text is empty")

        api_key = self._pick_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        prompt = (
            "Rewrite the following news article into a concise, engaging social media post. "
            "Include emojis only if appropriate. Keep URLs intact.\n\n"
            f"{article_text.strip()}"
        )
        if tone_hint:
            prompt = f"Tone hint: {tone_hint}\n\n" + prompt

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 220,
        }

        url = f"{self.base_url}/openai/v1/chat/completions"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
        except requests.RequestException as exc:
            logger.warning("Groq request error: %s", exc)
            raise LLMError(str(exc))

        if resp.status_code == 401:
            # Remove the bad key and retry
            try:
                self.api_keys.remove(api_key)
            except ValueError:
                pass
            if not self.api_keys:
                raise LLMError("All API keys exhausted (unauthorized)")
            raise LLMError("Unauthorized key; retrying with another key")

        if resp.status_code >= 500:
            raise LLMError(f"Server error: {resp.status_code}")

        if resp.status_code >= 400:
            logger.error("Groq client error %s: %s", resp.status_code, resp.text[:500])
            raise LLMError(f"Client error: {resp.status_code}")

        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            raise LLMError("Empty response from LLM")
        return content


