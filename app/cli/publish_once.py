import logging
import time
from typing import Optional

from app.config import load_config
from app.logging import setup_logging
from app.rss.fetch import fetch_feeds
from app.storage.db import init_db, add_items, get_items, delete_older_than
from app.clients.groq_llm import GroqRephraser
from app.clients.facebook import FacebookClient
from app.clients.twitter import TwitterClient


def main(tone_hint: Optional[str] = None) -> None:
    cfg = load_config()
    setup_logging(cfg.log_dir)
    logging.getLogger(__name__).info("Starting single-run publish pipeline")

    init_db()

    # Cleanup old items first
    removed = delete_older_than(cfg.storage_ttl_seconds)
    if removed:
        logging.getLogger(__name__).info("Cleaned up %s expired items", removed)

    # Fetch feeds
    items = fetch_feeds(cfg.feeds)
    add_items(items)
    logging.getLogger(__name__).info("Fetched and stored %s items", len(items))

    # Prepare clients
    llm = GroqRephraser(base_url=cfg.tiri_base_url, api_keys=cfg.tiri_api_keys)

    fb_clients = []
    if 'facebook' in cfg.platforms and cfg.facebook_page_ids and cfg.facebook_page_tokens:
        if len(cfg.facebook_page_ids) != len(cfg.facebook_page_tokens):
            logging.getLogger(__name__).warning("FACEBOOK_PAGE_IDS and FACEBOOK_PAGE_TOKENS length mismatch; skipping Facebook")
        else:
            for pid, token in zip(cfg.facebook_page_ids, cfg.facebook_page_tokens):
                fb_clients.append(FacebookClient(page_id=pid, access_token=token))

    tw_clients = []
    if 'twitter' in cfg.platforms and cfg.twitter_bearer_tokens:
        for tok in cfg.twitter_bearer_tokens:
            tw_clients.append(TwitterClient(bearer_token=tok))

    # Process and post with delays
    for it in get_items(limit=50):
        original_text = f"{it['title']}\n\n{it['summary']}\n\nRead more: {it['link']}"
        try:
            rewritten = llm.rephrase(original_text, tone_hint=tone_hint)

            # Facebook: requires image for /photos; skip if none.
            if fb_clients:
                image_url = it['link'] if it['link'].lower().endswith((".jpg", ".jpeg", ".png", ".gif")) else None
                if image_url:
                    for fb in fb_clients:
                        try:
                            post_id = fb.post_photo_with_caption(image_url=image_url, caption=rewritten)
                            logging.getLogger(__name__).info("Posted to Facebook page %s: %s", fb.page_id, post_id)
                        except Exception:
                            logging.getLogger(__name__).exception("Facebook post failed for page %s", fb.page_id)
                else:
                    logging.getLogger(__name__).warning("No image URL for item; skipping Facebook photo post: %s", it['link'])

            # Twitter/X: text-only allowed; append link if present
            if tw_clients:
                tweet_text = rewritten
                if it['link']:
                    tweet_text = f"{tweet_text}\n\n{it['link']}"
                for tw in tw_clients:
                    try:
                        tweet_id = tw.post_tweet(tweet_text)
                        logging.getLogger(__name__).info("Tweeted via token ****%s: %s", tw.bearer_token[-4:], tweet_id)
                    except Exception:
                        logging.getLogger(__name__).exception("Tweet failed for token ****%s", tw.bearer_token[-4:])
        except Exception as exc:
            logging.getLogger(__name__).exception("Failed processing item from %s: %s", it['source'], exc)

        time.sleep(max(0, int(cfg.process_delay_seconds)))


if __name__ == "__main__":
    main()


