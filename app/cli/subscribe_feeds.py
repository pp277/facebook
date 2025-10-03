#!/usr/bin/env python3
"""
WebSub subscription manager for Superfeedr
Subscribes to RSS feeds for instant notifications
"""

import logging
import secrets as pysecrets
from typing import List

from app.config import load_config
from app.logging import setup_logging
from app.websub.superfeedr import SuperfeedrClient


def main():
    """Subscribe to configured feeds via Superfeedr WebSub"""
    config = load_config()
    setup_logging(config.log_dir)
    logger = logging.getLogger(__name__)
    
    if not config.superfeedr_user or not config.superfeedr_pass:
        logger.error("SUPERFEEDR_USER and SUPERFEEDR_PASS must be set")
        return 1
    
    if not config.callback_url:
        logger.error("CALLBACK_URL must be set (e.g., https://yourdomain.com/webhook)")
        return 1
    
    # Get feeds from environment or use defaults
    feeds_env = os.getenv("FEEDS", "").strip()
    if feeds_env:
        feeds = [f.strip() for f in feeds_env.split(",") if f.strip()]
    else:
        # Default tech feeds
        feeds = [
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.wired.com/feed/rss",
            "https://www.engadget.com/rss.xml"
        ]
    
    if not feeds:
        logger.error("No feeds configured")
        return 1
    
    logger.info("Subscribing to %d feeds", len(feeds))
    logger.info("Callback URL: %s", config.callback_url)
    
    # Create Superfeedr client
    client = SuperfeedrClient(
        user=config.superfeedr_user,
        password=config.superfeedr_pass,
        hub_url=config.superfeedr_hub_url
    )
    
    success_count = 0
    error_count = 0
    
    for feed_url in feeds:
        try:
            # Generate random secret for this feed
            secret = pysecrets.token_hex(16)
            
            logger.info("Subscribing to: %s", feed_url)
            success = client.subscribe_feed(
                feed_url=feed_url,
                callback_url=config.callback_url,
                secret=secret,
                lease_seconds=86400  # 24 hours
            )
            
            if success:
                success_count += 1
                logger.info("✅ Successfully subscribed to %s", feed_url)
            else:
                error_count += 1
                logger.error("❌ Failed to subscribe to %s", feed_url)
                
        except Exception as exc:
            error_count += 1
            logger.exception("❌ Error subscribing to %s: %s", feed_url, exc)
    
    logger.info("Subscription complete: %d success, %d errors", success_count, error_count)
    
    if error_count > 0:
        logger.warning("Some subscriptions failed. Check your credentials and callback URL.")
        return 1
    
    return 0


if __name__ == "__main__":
    import os
    import sys
    sys.exit(main())
