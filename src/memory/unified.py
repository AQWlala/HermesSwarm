"""统一记忆系统 - 融合 Hermes MemoryProvider + JiuwenSwarm MemoryIndexManager

Hermes基因: MemoryProvider ABC, SessionDB(FTS5), MEMORY.md
JiuwenSwarm基因: MemoryIndexManager, 向量索引, Coding Memory
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    type: str = "long"  # short/long/episodic/semantic
    source: str = "fusion"  # hermes/jiuen/fusion
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


class UnifiedMemory:
    """统一记忆系统

    融合:
    - Hermes: FTS5全文搜索, MEMORY.md, 跨会话回溯
    - JiuwenSwarm: 向量索引, Coding Memory, Task Memory
    """

    def __init__(self, db_path: str = "~/.hermesswarm/memory.db"):
        self.db_path = str(Path(db_path).expanduser())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        cur = self.conn.cursor()
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
                content, type, source, content='memory', content_rowid='id'
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
        """存储记忆"""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO memory (id, content, type, source, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (entry.id, entry.content, entry.type, entry.source, entry.timestamp, json.dumps(entry.metadata)),
        )
        cur.execute(
            "INSERT INTO memory_fts (rowid, content, type, source) VALUES ((SELECT rowid FROM memory WHERE id=?), ?, ?, ?)",
            (entry.id, entry.content, entry.type, entry.source),
        )
        self.conn.commit()

    def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """搜索记忆（Hermes基因: FTS5）"""
        cur = self.conn.cursor()
        try:
            cur.execute(
                """SELECT m.id, m.content, m.type, m.source, m.timestamp, m.metadata
                   FROM memory m JOIN memory_fts f ON m.rowid = f.rowid
                   WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?""",
                (query, limit),
            )
        except sqlite3.OperationalError:
            cur.execute(
                "SELECT id, content, type, source, timestamp, metadata FROM memory WHERE content LIKE ? LIMIT ?",
                (f"%{query}%", limit),
            )
        return [self._row_to_entry(r) for r in cur.fetchall()]

    def store_interaction(self, agent_id: str, input: str, output: str) -> None:
        """存储交互记录"""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO interactions (agent_id, input, output, timestamp) VALUES (?, ?, ?, ?)",
            (agent_id, input, output, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_history(self, agent_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """获取历史"""
        cur = self.conn.cursor()
        if agent_id:
            cur.execute(
                "SELECT agent_id, input, output, timestamp FROM interactions WHERE agent_id=? ORDER BY id DESC LIMIT ?",
                (agent_id, limit),
            )
        else:
            cur.execute("SELECT agent_id, input, output, timestamp FROM interactions ORDER BY id DESC LIMIT ?", (limit,))
        return [{"agent_id": r[0], "input": r[1], "output": r[2], "timestamp": r[3]} for r in cur.fetchall()]

    def _row_to_entry(self, row: tuple) -> MemoryEntry:
        return MemoryEntry(
            id=row[0], content=row[1], type=row[2], source=row[3],
            timestamp=row[4], metadata=json.loads(row[5]) if row[5] else {},
        )

    def close(self) -> None:
        self.conn.close()
