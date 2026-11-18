"""Cross-file surname search over a folder of PDFs.

The index is a single SQLite file with an FTS5 table holding, for every
PDF page, the accent-folded text and its phonetic key. Indexing is
incremental: only files whose size or modification time changed are
read again.

Search order for a query such as "Villacrés":
1. exact folded match (villacres)
2. phonetic match (bilakres), which also finds Billacres, Villacrez
3. near-miss phonetic match (one or two edits), for OCR mistakes
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium

from .phonetic import edit_distance, fold, keys, phon, words

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
    path TEXT PRIMARY KEY, size INTEGER, mtime REAL, pages INTEGER, needs_ocr INTEGER);
CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
    path UNINDEXED, page UNINDEXED, raw UNINDEXED, folded, phonetic,
    tokenize = 'unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS vocab(word TEXT PRIMARY KEY, phon TEXT);
"""


@dataclass
class Hit:
    path: str
    page: int  # 1-based
    match: str  # how it matched: exacto, suena igual, parecido
    snippet: str


_SOFT_HYPHEN = re.compile(r"[\ufffe\u00ad]\s*")
_LINE_HYPHEN = re.compile(r"(?<=[a-záéíóúñü])-[ \t]*\r?\n\s*(?=[a-záéíóúñü])")


def join_hyphens(text: str) -> str:
    """Rejoin words split at the end of a line ("Coro-" + "nel").

    Typeset books (InDesign and similar) mark these breaks with a soft
    hyphen, which PDFium returns as U+FFFE. Plain hyphens are only joined
    when both sides are lowercase, so "Febres-Cordero" stays as written.
    """
    return _LINE_HYPHEN.sub("", _SOFT_HYPHEN.sub("", text))


def extract_pages(path: Path) -> list[str]:
    doc = pdfium.PdfDocument(str(path))
    try:
        return [join_hyphens(doc[i].get_textpage().get_text_range()) for i in range(len(doc))]
    finally:
        doc.close()


class Index:
    def __init__(self, db_path: Path | str):
        self.db = sqlite3.connect(str(db_path))
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # indexing
    def update(self, folder: Path | str) -> dict:
        folder = Path(folder)
        seen, added, skipped, needs_ocr = set(), 0, 0, []
        for pdf in sorted(folder.rglob("*")):
            if pdf.suffix.lower() != ".pdf" or not pdf.is_file():
                continue
            key = str(pdf.resolve())
            seen.add(key)
            st = pdf.stat()
            row = self.db.execute("SELECT size, mtime FROM files WHERE path=?", (key,)).fetchone()
            if row and row[0] == st.st_size and abs(row[1] - st.st_mtime) < 1e-6:
                skipped += 1
                continue
            try:
                texts = extract_pages(pdf)
            except Exception:
                continue
            self._remove(key)
            empty = all(not t.strip() for t in texts)
            for i, t in enumerate(texts, 1):
                f, p = keys(t)
                self.db.execute("INSERT INTO pages VALUES (?,?,?,?,?)", (key, i, t, f, p))
                for w in set(words(t)):
                    fw = fold(w)
                    if len(fw) > 2:
                        self.db.execute("INSERT OR IGNORE INTO vocab VALUES (?,?)", (fw, phon(w)))
            self.db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?)",
                            (key, st.st_size, st.st_mtime, len(texts), int(empty)))
            if empty:
                needs_ocr.append(key)
            added += 1
        for (gone,) in self.db.execute("SELECT path FROM files").fetchall():
            if gone.startswith(str(folder.resolve())) and gone not in seen:
                self._remove(gone)
        self.db.commit()
        return {"indexed": added, "unchanged": skipped, "needs_ocr": needs_ocr}

    def _remove(self, key: str) -> None:
        self.db.execute("DELETE FROM pages WHERE path=?", (key,))
        self.db.execute("DELETE FROM files WHERE path=?", (key,))

    # search
    def search(self, query: str, limit: int = 200) -> list[Hit]:
        terms = [w for w in words(query) if len(w) > 1]
        if not terms:
            return []
        hits: dict[tuple[str, int], Hit] = {}

        def run(column: str, values: list[str], label: str) -> None:
            expr = " AND ".join(f'{column}:"{v}"' for v in values)
            sql = ("SELECT path, page, raw FROM pages WHERE pages MATCH ? "
                   "ORDER BY rank LIMIT ?")
            for path, page, raw in self.db.execute(sql, (expr, limit)):
                hits.setdefault((path, page), Hit(path, page, label, _snippet(raw, values)))

        run("folded", [fold(t) for t in terms], "exacto")
        run("phonetic", [phon(t) for t in terms], "suena igual")
        # near misses: expand each term to vocabulary words with a close phonetic key
        expanded = []
        for t in terms:
            pt = phon(t)
            close = [w for w, p in self.db.execute("SELECT word, phon FROM vocab")
                     if p != pt and edit_distance(p, pt, 1) <= 1 and len(pt) >= 4]
            expanded.append(close)
        if all(expanded):
            for combo in _product(expanded):
                run("folded", list(combo), "parecido")
        return list(hits.values())[:limit]


def _product(lists: list[list[str]], cap: int = 20) -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = [()]
    for options in lists:
        out = [o + (x,) for o in out for x in options[:5]][:cap]
    return out


def _snippet(raw: str, terms: list[str], width: int = 60) -> str:
    flat = " ".join(raw.split())
    low = fold(flat)
    for t in terms:
        i = low.find(fold(t))
        if i >= 0:
            a, b = max(0, i - width), min(len(flat), i + len(t) + width)
            return ("..." if a else "") + flat[a:b] + ("..." if b < len(flat) else "")
    # phonetic match: show the start of the page
    return flat[: width * 2] + ("..." if len(flat) > width * 2 else "")


def default_db() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / "Chono" / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "indice.sqlite"
