import asyncio
import logging
import time
from typing import Dict, List
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import PlainTextResponse

from app.config import load_config, AppConfig
from app.logging import setup_logging
from app.xml.parser import RobustXMLParser, FeedItem
from app.websub.superfeedr import SuperfeedrClient
from app.clients.groq_llm import GroqRephraser
from app.clients.facebook import FacebookClient
from app.clients.twitter import TwitterClient
from app.storage.db import init_db, add_items, delete_older_than


app = FastAPI()
config: AppConfig = None
xml_parser = RobustXMLParser()
secrets: Dict[str, str] = {}  # feed_url -> secret mapping


@app.on_event("startup")
async def on_startup() -> None:
    global config
    config = load_config()
    setup_logging(config.log_dir)
    init_db()
    
    logger = logging.getLogger(__name__)
    logger.info("WebSub server starting up")
    logger.info("Callback URL: %s", config.callback_url)
    
    # Clean up old items
    removed = delete_older_than(config.storage_ttl_seconds)
    if removed:
        logger.info("Cleaned up %d expired items", removed)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "timestamp": int(time.time())}


@app.get("/webhook")
async def webhook_verification(
    request: Request,
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_topic: str = Query(None, alias="hub.topic"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_lease_seconds: str = Query(None, alias="hub.lease_seconds"),
    hub_secret: str = Query(None, alias="hub.secret")
) -> PlainTextResponse:
    """WebSub verification endpoint"""
    logger = logging.getLogger(__name__)
    
    if hub_mode == "subscribe" and hub_challenge:
        logger.info("WebSub verification: topic=%s, lease=%s", hub_topic, hub_lease_seconds)
        if hub_secret:
            secrets[hub_topic] = hub_secret
            logger.info("Stored secret for topic: %s", hub_topic)
        return PlainTextResponse(content=hub_challenge)
    
    return PlainTextResponse(content="OK")


@app.post("/webhook")
async def webhook_notification(request: Request) -> PlainTextResponse:
    """WebSub notification handler - processes new feed content"""
    logger = logging.getLogger(__name__)
    
    try:
        body = await request.body()
        content_type = request.headers.get("content-type", "")
        signature = request.headers.get("x-hub-signature", "")
        
        logger.info("WebSub notification: %d bytes, type=%s", len(body), content_type)
        
        # Verify signature if available
        if signature and secrets:
            # Try to find matching secret
            verified = False
            superfeedr_client = SuperfeedrClient(
                user=config.superfeedr_user,
                password=config.superfeedr_pass,
                hub_url=config.superfeedr_hub_url
            )
            for topic, secret in secrets.items():
                if superfeedr_client.verify_signature(body, signature, secret):
                    verified = True
                    break
            
            if not verified:
                logger.warning("Signature verification failed")
                return PlainTextResponse(content="Signature verification failed", status_code=400)
        
        # Parse XML content
        try:
            items = xml_parser.parse_feed_content(body)
        except Exception as exc:
            logger.error("XML parsing failed: %s", exc)
            return PlainTextResponse(content="XML parsing failed", status_code=400)
        
        if not items:
            logger.info("No items found in notification")
            return PlainTextResponse(content="No items")
        
        # Store items
        add_items([item.to_dict() for item in items])
        logger.info("Stored %d new items", len(items))
        
        # Process items with delay
        await process_items(items)
        
        return PlainTextResponse(content="OK")
        
    except Exception as exc:
        logger.exception("Webhook processing error: %s", exc)
        return PlainTextResponse(content="Processing error", status_code=500)


async def process_items(items: List[FeedItem]) -> None:
    """Process feed items: rephrase and post to social media"""
    logger = logging.getLogger(__name__)
    
    if not config.platforms:
        logger.warning("No platforms configured")
        return
    
    # Prepare clients
    llm = GroqRephraser(base_url=config.tiri_base_url, api_keys=config.tiri_api_keys)
    
    fb_clients = []
    if 'facebook' in config.platforms and config.facebook_page_ids and config.facebook_page_tokens:
        if len(config.facebook_page_ids) == len(config.facebook_page_tokens):
            for pid, token in zip(config.facebook_page_ids, config.facebook_page_tokens):
                fb_clients.append(FacebookClient(page_id=pid, access_token=token))
        else:
            logger.warning("Facebook IDs and tokens length mismatch")
    
    tw_clients = []
    if 'twitter' in config.platforms and config.twitter_bearer_tokens:
        for token in config.twitter_bearer_tokens:
            tw_clients.append(TwitterClient(bearer_token=token))
    
    # Process each item
    for item in items:
        try:
            # Create original text
            original_text = f"{item.title}\n\n{item.summary}\n\nRead more: {item.link}"
            
            # Rephrase with AI
            rewritten = llm.rephrase(original_text)
            logger.info("Rephrased: %s", item.title[:50])
            
            # Post to Facebook (requires image)
            if fb_clients:
                image_url = item.link if item.link.lower().endswith((".jpg", ".jpeg", ".png", ".gif")) else None
                if image_url:
                    for fb in fb_clients:
                        try:
                            post_id = fb.post_photo_with_caption(image_url=image_url, caption=rewritten)
                            logger.info("Posted to Facebook page %s: %s", fb.page_id, post_id)
                        except Exception as exc:
                            logger.exception("Facebook post failed for page %s: %s", fb.page_id, exc)
                else:
                    logger.warning("No image URL for Facebook post: %s", item.link)
            
            # Post to Twitter
            if tw_clients:
                tweet_text = rewritten
                if item.link:
                    tweet_text = f"{tweet_text}\n\n{item.link}"
                
                for tw in tw_clients:
                    try:
                        tweet_id = tw.post_tweet(tweet_text)
                        logger.info("Tweeted via token ****%s: %s", tw.bearer_token[-4:], tweet_id)
                    except Exception as exc:
                        logger.exception("Tweet failed for token ****%s: %s", tw.bearer_token[-4:], exc)
            
            # Delay between items
            if config.process_delay_seconds > 0:
                await asyncio.sleep(config.process_delay_seconds)
                
        except Exception as exc:
            logger.exception("Failed processing item %s: %s", item.title, exc)


