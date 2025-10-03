import logging
import base64
import hashlib
import hmac
from typing import List, Dict, Optional
import requests
from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type


logger = logging.getLogger(__name__)


class SuperfeedrError(Exception):
    pass


class SuperfeedrClient:
    """WebSub subscription manager for Superfeedr"""
    
    def __init__(self, user: str, password: str, hub_url: str = "https://push.superfeedr.com"):
        if not user or not password:
            raise ValueError("user and password are required")
        self.user = user
        self.password = password
        self.hub_url = hub_url.rstrip("/")
        self.auth_header = f"Basic {base64.b64encode(f'{user}:{password}'.encode()).decode()}"
    
    @retry(
        wait=wait_exponential_jitter(initial=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(SuperfeedrError),
        reraise=True,
    )
    def subscribe_feed(self, feed_url: str, callback_url: str, 
                      secret: str = None, lease_seconds: int = 86400) -> bool:
        """Subscribe to a feed via WebSub"""
        if not feed_url or not callback_url:
            raise ValueError("feed_url and callback_url are required")
        
        params = {
            'hub.mode': 'subscribe',
            'hub.topic': feed_url,
            'hub.callback': callback_url,
            'hub.verify': 'async',
            'hub.lease_seconds': str(lease_seconds),
        }
        
        if secret:
            params['hub.secret'] = secret
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        try:
            resp = requests.post(
                self.hub_url,
                data=params,
                headers=headers,
                timeout=30
            )
        except requests.RequestException as exc:
            logger.warning("Superfeedr request error: %s", exc)
            raise SuperfeedrError(f"Request failed: {exc}")
        
        if resp.status_code == 204:
            logger.info("Successfully subscribed to %s", feed_url)
            return True
        elif resp.status_code == 202:
            logger.info("Subscription request accepted for %s (verification pending)", feed_url)
            return True
        elif resp.status_code == 400:
            logger.error("Bad request for %s: %s", feed_url, resp.text[:500])
            raise SuperfeedrError(f"Bad request: {resp.text[:500]}")
        elif resp.status_code == 401:
            logger.error("Unauthorized for %s", feed_url)
            raise SuperfeedrError("Invalid credentials")
        else:
            logger.error("Subscription failed for %s: %s %s", feed_url, resp.status_code, resp.text[:500])
            raise SuperfeedrError(f"Subscription failed: {resp.status_code}")
    
    @retry(
        wait=wait_exponential_jitter(initial=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(SuperfeedrError),
        reraise=True,
    )
    def unsubscribe_feed(self, feed_url: str, callback_url: str) -> bool:
        """Unsubscribe from a feed"""
        params = {
            'hub.mode': 'unsubscribe',
            'hub.topic': feed_url,
            'hub.callback': callback_url,
        }
        
        headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        try:
            resp = requests.post(
                self.hub_url,
                data=params,
                headers=headers,
                timeout=30
            )
        except requests.RequestException as exc:
            logger.warning("Superfeedr unsubscribe error: %s", exc)
            raise SuperfeedrError(f"Unsubscribe failed: {exc}")
        
        if resp.status_code in [204, 202]:
            logger.info("Successfully unsubscribed from %s", feed_url)
            return True
        else:
            logger.error("Unsubscribe failed for %s: %s %s", feed_url, resp.status_code, resp.text[:500])
            raise SuperfeedrError(f"Unsubscribe failed: {resp.status_code}")
    
    def verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify WebSub signature"""
        if not signature or not secret:
            return False
        
        try:
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            # Create HMAC
            expected = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
        except Exception as exc:
            logger.warning("Signature verification error: %s", exc)
            return False
