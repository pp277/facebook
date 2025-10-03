import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

from lxml import etree


logger = logging.getLogger(__name__)


class XMLParseError(Exception):
    pass


class FeedItem:
    def __init__(self, title: str = "", link: str = "", summary: str = "", 
                 published_at: str = "", source: str = ""):
        self.title = title.strip()
        self.link = link.strip()
        self.summary = summary.strip()
        self.published_at = published_at.strip()
        self.source = source.strip()
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'title': self.title,
            'link': self.link,
            'summary': self.summary,
            'published_at': self.published_at,
            'source': self.source,
        }
    
    def is_valid(self) -> bool:
        """Check if item has minimum required fields"""
        return bool(self.title and self.link)


class RobustXMLParser:
    """Handles any RSS/Atom format with fallback parsing strategies"""
    
    def __init__(self):
        self.parser = etree.XMLParser(recover=True, huge_tree=True)
    
    def parse_feed_content(self, xml_content: bytes, source_url: str = "") -> List[FeedItem]:
        """Parse XML content and return list of FeedItem objects"""
        try:
            root = etree.fromstring(xml_content, self.parser)
        except etree.XMLSyntaxError as exc:
            logger.error("XML syntax error: %s", exc)
            raise XMLParseError(f"Invalid XML: {exc}")
        except Exception as exc:
            logger.error("XML parsing error: %s", exc)
            raise XMLParseError(f"Parse error: {exc}")
        
        items = []
        
        # Try RSS 2.0 first (most common)
        rss_items = self._parse_rss2(root)
        if rss_items:
            items.extend(rss_items)
            logger.debug("Parsed %d RSS 2.0 items", len(rss_items))
        
        # Try Atom if RSS didn't work or returned empty
        if not items:
            atom_items = self._parse_atom(root)
            if atom_items:
                items.extend(atom_items)
                logger.debug("Parsed %d Atom items", len(atom_items))
        
        # Try RSS 1.0 (RDF) if still empty
        if not items:
            rdf_items = self._parse_rss1(root)
            if rdf_items:
                items.extend(rdf_items)
                logger.debug("Parsed %d RSS 1.0 items", len(rdf_items))
        
        # Set source for all items
        for item in items:
            item.source = source_url
        
        # Filter out invalid items
        valid_items = [item for item in items if item.is_valid()]
        logger.info("Parsed %d valid items from %s", len(valid_items), source_url)
        
        return valid_items
    
    def _parse_rss2(self, root) -> List[FeedItem]:
        """Parse RSS 2.0 format"""
        items = []
        
        # Look for channel/item structure
        for item_elem in root.xpath('//channel/item'):
            try:
                title = self._safe_text(item_elem, 'title')
                link = self._safe_text(item_elem, 'link')
                description = self._safe_text(item_elem, 'description')
                pub_date = self._safe_text(item_elem, 'pubDate')
                
                # Try alternative fields
                if not description:
                    description = self._safe_text(item_elem, 'summary')
                if not description:
                    description = self._safe_text(item_elem, 'content')
                
                if title and link:
                    items.append(FeedItem(
                        title=title,
                        link=link,
                        summary=description,
                        published_at=pub_date
                    ))
            except Exception as exc:
                logger.warning("Error parsing RSS item: %s", exc)
                continue
        
        return items
    
    def _parse_atom(self, root) -> List[FeedItem]:
        """Parse Atom format"""
        items = []
        
        # Look for feed/entry structure
        for entry_elem in root.xpath('//entry'):
            try:
                title = self._safe_text(entry_elem, '{*}title')
                
                # Handle Atom links (can be multiple)
                link = ""
                link_elem = entry_elem.find('{*}link')
                if link_elem is not None:
                    link = link_elem.get('href', '').strip()
                
                # Try alternative link fields
                if not link:
                    link = self._safe_text(entry_elem, '{*}id')
                
                # Handle content/summary
                content = self._safe_text(entry_elem, '{*}content')
                summary = self._safe_text(entry_elem, '{*}summary')
                description = content or summary
                
                # Handle dates
                published = self._safe_text(entry_elem, '{*}published')
                updated = self._safe_text(entry_elem, '{*}updated')
                pub_date = published or updated
                
                if title and link:
                    items.append(FeedItem(
                        title=title,
                        link=link,
                        summary=description,
                        published_at=pub_date
                    ))
            except Exception as exc:
                logger.warning("Error parsing Atom entry: %s", exc)
                continue
        
        return items
    
    def _parse_rss1(self, root) -> List[FeedItem]:
        """Parse RSS 1.0 (RDF) format"""
        items = []
        
        # Look for item elements in RDF namespace
        for item_elem in root.xpath('//item'):
            try:
                title = self._safe_text(item_elem, 'title')
                link = self._safe_text(item_elem, 'link')
                description = self._safe_text(item_elem, 'description')
                
                if title and link:
                    items.append(FeedItem(
                        title=title,
                        link=link,
                        summary=description,
                        published_at=""
                    ))
            except Exception as exc:
                logger.warning("Error parsing RSS 1.0 item: %s", exc)
                continue
        
        return items
    
    def _safe_text(self, elem, xpath: str) -> str:
        """Safely extract text from element using xpath"""
        try:
            if xpath.startswith('{*}'):
                # Handle namespace wildcard
                result = elem.findtext(xpath)
            else:
                result = elem.findtext(xpath)
            
            if result is None:
                return ""
            
            # Clean up text
            text = str(result).strip()
            # Remove HTML tags if present
            text = re.sub(r'<[^>]+>', '', text)
            # Decode HTML entities
            text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            text = text.replace('&quot;', '"').replace('&#39;', "'")
            
            return text
        except Exception:
            return ""
