"""统一记忆系统 - 融合 Hermes MemoryProvider + JiuwenSwarm MemoryIndexManager

Hermes基因: MemoryProvider ABC, SessionDB(FTS5三表), MEMORY.md
JiuwenSwarm基因: MemoryIndexManager, 向量索引, Coding Memory

FTS5三表架构（Hermes基因 hermes_state_search.py）:
- memory_fts: unicode61分词器, BM25排序, 适合英文/拉丁文
- memory_fts_trigram: trigram分词器, 子串匹配, 适合代码/标识符
- memory_fts_cjk: CJK二元组, 适合中文/日文/韩文

搜索路由策略:
- 纯拉丁文 → memory_fts (BM25)
- 包含CJK → memory_fts_cjk
- 子串查询 → memory_fts_trigram
- 短CJK查询 → LIKE回退
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


_CJK_RANGE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]")
_LATIN_ONLY = re.compile(r"^[a-zA-Z0-9\s\-_.,!?;:'\"()]+$")
_FTS5_SPECIAL_CHARS = '+{}():"^@/#&|~[]<>,;!?$=\\\''
_FTS5_SPECIAL_RE = re.compile(f"[{re.escape(_FTS5_SPECIAL_CHARS)}]")


def _is_cjk(text: str) -> bool:
    return bool(_CJK_RANGE.search(text))


def _is_latin_only(text: str) -> bool:
    return bool(_LATIN_ONLY.match(text))


def _sanitize_fts5_query(query: str) -> str:
    """清理FTS5特殊字符（Hermes基因: hermes_state_search.py）"""
    cleaned = _FTS5_SPECIAL_RE.sub(" ", query).strip()
    if not cleaned:
        return ""
    tokens = [t for t in cleaned.split() if len(t) >= 1]
    return " ".join(tokens)


def _build_trigram_query(text: str) -> str:
    """构建trigram查询（子串匹配）"""
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) < 3:
        return clean
    return clean


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    type: str = "long"
    source: str = "fusion"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    score: float = 0.0


class UnifiedMemory:
    """统一记忆系统

    融合:
    - Hermes: FTS5三表全文搜索, MEMORY.md, 跨会话回溯, WAL模式
    - JiuwenSwarm: 向量索引, Coding Memory, Task Memory

    三表架构:
    - memory_fts (unicode61): 英文BM25排序
    - memory_fts_trigram (trigram): 子串/代码匹配
    - memory_fts_cjk (CJK二元组): 中文搜索
    """

    def __init__(self, db_path: str = "~/.hermesswarm/memory.db"):
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self._trigram_available = self._check_trigram_support()
        self._init_db()

    def _check_trigram_support(self) -> bool:
        """检测SQLite是否支持trigram分词器（Hermes基因）"""
        try:
            tmp = sqlite3.connect(":memory:")
            tmp.execute("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram')")
            tmp.close()
            return True
        except sqlite3.OperationalError:
            return False

    def _init_db(self) -> None:
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    content, type, source,
                    tokenize='unicode61'
                )
            """)
            if self._trigram_available:
                cur.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts_trigram USING fts5(
                        content,
                        tokenize='trigram'
                    )
                """)
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts_cjk USING fts5(
                    content,
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    input TEXT,
                    output TEXT,
                    timestamp TEXT
                )
            """)
            self.conn.commit()

    def store(self, entry: MemoryEntry) -> None:
        """存储记忆（写入三张FTS5表）"""
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO memory (id, content, type, source, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (entry.id, entry.content, entry.type, entry.source, entry.timestamp, json.dumps(entry.metadata, ensure_ascii=False)),
            )
            rowid = cur.execute("SELECT rowid FROM memory WHERE id=?", (entry.id,)).fetchone()[0]

            cur.execute("DELETE FROM memory_fts WHERE rowid=?", (rowid,))
            cur.execute("INSERT INTO memory_fts (rowid, content, type, source) VALUES (?, ?, ?, ?)",
                        (rowid, entry.content, entry.type, entry.source))

            if self._trigram_available:
                cur.execute("DELETE FROM memory_fts_trigram WHERE rowid=?", (rowid,))
                cur.execute("INSERT INTO memory_fts_trigram (rowid, content) VALUES (?, ?)",
                            (rowid, entry.content))

            cur.execute("DELETE FROM memory_fts_cjk WHERE rowid=?", (rowid,))
            cur.execute("INSERT INTO memory_fts_cjk (rowid, content) VALUES (?, ?)",
                        (rowid, entry.content))
            self.conn.commit()

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """搜索记忆（Hermes基因: 三表智能路由）

        路由策略:
        1. 纯拉丁文 → memory_fts (BM25)
        2. 包含CJK → memory_fts_cjk
        3. 子串/代码 → memory_fts_trigram
        4. 短CJK查询 → LIKE回退
        """
        if not query.strip():
            return []

        with self._lock:
            results = self._route_search(query, limit)
            return results

    def _route_search(self, query: str, limit: int) -> list[MemoryEntry]:
        """智能路由搜索（Hermes基因: hermes_state_search.py）"""
        cur = self.conn.cursor()

        if _is_latin_only(query):
            sanitized = _sanitize_fts5_query(query)
            if sanitized:
                try:
                    rows = cur.execute(
                        """SELECT m.id, m.content, m.type, m.source, m.timestamp, m.metadata, f.rank
                           FROM memory_fts f JOIN memory m ON m.rowid = f.rowid
                           WHERE memory_fts MATCH ? ORDER BY f.rank LIMIT ?""",
                        (sanitized, limit),
                    ).fetchall()
                    if rows:
                        return [self._row_to_entry(r) for r in rows]
                except sqlite3.OperationalError:
                    pass

        if _is_cjk(query):
            cjk_results = self._search_cjk(cur, query, limit)
            if cjk_results:
                return cjk_results
            if len(query) <= 4:
                like_results = self._search_like(cur, query, limit)
                if like_results:
                    return like_results

        if self._trigram_available:
            tri_results = self._search_trigram(cur, query, limit)
            if tri_results:
                return tri_results

        return self._search_like(cur, query, limit)

    def _search_cjk(self, cur, query: str, limit: int) -> list[MemoryEntry]:
        """CJK搜索（中文/日文/韩文）"""
        sanitized = _sanitize_fts5_query(query)
        if not sanitized:
            return []
        try:
            rows = cur.execute(
                """SELECT m.id, m.content, m.type, m.source, m.timestamp, m.metadata, f.rank
                   FROM memory_fts_cjk f JOIN memory m ON m.rowid = f.rowid
                   WHERE memory_fts_cjk MATCH ? ORDER BY f.rank LIMIT ?""",
                (sanitized, limit),
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        except sqlite3.OperationalError:
            return []

    def _search_trigram(self, cur, query: str, limit: int) -> list[MemoryEntry]:
        """trigram子串搜索（代码/标识符匹配）"""
        tri_query = _build_trigram_query(query)
        if not tri_query:
            return []
        try:
            rows = cur.execute(
                """SELECT m.id, m.content, m.type, m.source, m.timestamp, m.metadata, f.rank
                   FROM memory_fts_trigram f JOIN memory m ON m.rowid = f.rowid
                   WHERE memory_fts_trigram MATCH ? ORDER BY f.rank LIMIT ?""",
                (tri_query, limit),
            ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        except sqlite3.OperationalError:
            return []

    def _search_like(self, cur, query: str, limit: int) -> list[MemoryEntry]:
        """LIKE回退搜索（短查询/FTS5失败时）"""
        escaped = query.replace("%", "\\%").replace("_", "\\_")
        rows = cur.execute(
            """SELECT id, content, type, source, timestamp, metadata, 0.0 as rank
               FROM memory WHERE content LIKE ? ESCAPE '\\' LIMIT ?""",
            (f"%{escaped}%", limit),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def store_interaction(self, agent_id: str, input: str, output: str) -> None:
        """存储交互记录"""
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                "INSERT INTO interactions (agent_id, input, output, timestamp) VALUES (?, ?, ?, ?)",
                (agent_id, input, output, datetime.now().isoformat()),
            )
            self.conn.commit()

    def get_history(self, agent_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """获取历史"""
        with self._lock:
            cur = self.conn.cursor()
            if agent_id:
                cur.execute(
                    "SELECT agent_id, input, output, timestamp FROM interactions WHERE agent_id=? ORDER BY id DESC LIMIT ?",
                    (agent_id, limit),
                )
            else:
                cur.execute("SELECT agent_id, input, output, timestamp FROM interactions ORDER BY id DESC LIMIT ?", (limit,))
            return [{"agent_id": r[0], "input": r[1], "output": r[2], "timestamp": r[3]} for r in cur.fetchall()]

    def save_memory_md(self, path: str | Path, agent_id: str = "default") -> None:
        """导出为MEMORY.md（Hermes基因: 按§分割的记忆块）"""
        path = Path(path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            cur = self.conn.cursor()
            rows = cur.execute(
                "SELECT id, content, type, timestamp FROM memory ORDER BY timestamp DESC"
            ).fetchall()
        lines = [f"# Memory for {agent_id}", ""]
        for r in rows:
            lines.append(f"## {r[0]} ({r[2]}) - {r[3]}")
            lines.append(r[1])
            lines.append("§")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row[0], content=row[1], type=row[2], source=row[3],
            timestamp=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            score=-row[6] if len(row) > 6 and row[6] else 0.0,
        )

    def close(self) -> None:
        with self._lock:
            self.conn.close()
