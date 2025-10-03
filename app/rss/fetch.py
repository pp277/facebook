import logging
from typing import Iterable, List, Dict

import requests
from lxml import etree


logger = logging.getLogger(__name__)


def _parse_xml_items(xml_bytes: bytes) -> List[Dict[str, str]]:
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_bytes, parser=parser)

    items: List[Dict[str, str]] = []

    # Try RSS 2.0 structure: channel/item
    for item in root.xpath('//channel/item'):
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        description = (item.findtext('description') or '').strip()
        pub_date = (item.findtext('pubDate') or '').strip()
        items.append({
            'title': title,
            'link': link,
            'summary': description,
            'published_at': pub_date,
        })

    if items:
        return items

    # Try Atom structure: feed/entry
    for entry in root.xpath('//entry'):
        title = (entry.findtext('{*}title') or '').strip()
        link_el = entry.find('{*}link')
        link = link_el.get('href').strip() if link_el is not None and link_el.get('href') else ''
        summary = (entry.findtext('{*}summary') or entry.findtext('{*}content') or '').strip()
        published = (entry.findtext('{*}published') or entry.findtext('{*}updated') or '').strip()
        items.append({
            'title': title,
            'link': link,
            'summary': summary,
            'published_at': published,
        })

    return items


def fetch_feeds(feed_urls: Iterable[str], timeout_sec: int = 20) -> List[Dict[str, str]]:
    all_items: List[Dict[str, str]] = []
    for url in feed_urls:
        try:
            resp = requests.get(url, timeout=timeout_sec)
            if resp.status_code != 200:
                logger.warning("Feed %s returned status %s", url, resp.status_code)
                continue
            items = _parse_xml_items(resp.content)
            for it in items:
                it['source'] = url
            all_items.extend(items)
        except requests.RequestException as exc:
            logger.warning("Error fetching feed %s: %s", url, exc)
    return all_items


