import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterable, Dict, List


logger = logging.getLogger(__name__)


DB_FILE = os.path.join(os.getcwd(), 'news_storage.sqlite3')


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                link TEXT,
                summary TEXT,
                source TEXT,
                created_at INTEGER
            )
            """
        )


@contextmanager
def _conn():
    con = sqlite3.connect(DB_FILE)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def add_items(items: Iterable[Dict[str, str]]) -> None:
    now = int(time.time())
    with _conn() as c:
        c.executemany(
            "INSERT INTO news_items (title, link, summary, source, created_at) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    (it.get('title') or '').strip(),
                    (it.get('link') or '').strip(),
                    (it.get('summary') or '').strip(),
                    (it.get('source') or '').strip(),
                    now,
                )
                for it in items
            ],
        )


def get_items(limit: int = 50) -> List[Dict[str, str]]:
    with _conn() as c:
        cur = c.execute("SELECT title, link, summary, source, created_at FROM news_items ORDER BY id ASC LIMIT ?", (limit,))
        rows = cur.fetchall()
    return [
        {
            'title': r[0],
            'link': r[1],
            'summary': r[2],
            'source': r[3],
            'created_at': r[4],
        }
        for r in rows
    ]


def delete_older_than(ttl_seconds: int) -> int:
    cutoff = int(time.time()) - int(ttl_seconds)
    with _conn() as c:
        cur = c.execute("DELETE FROM news_items WHERE created_at < ?", (cutoff,))
        return cur.rowcount


