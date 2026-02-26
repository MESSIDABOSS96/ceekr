"""SQLite persistence layer for workspaces."""

import json
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'creating',
    intent_json TEXT,
    summary TEXT DEFAULT '',
    quality TEXT DEFAULT 'moderate',
    refinement_questions_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS journals (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT 'topic',
    color TEXT DEFAULT '#6366f1',
    canvas_x REAL DEFAULT 0,
    canvas_y REAL DEFAULT 0,
    enrichment_status TEXT DEFAULT 'pending',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    ranked_account_json TEXT NOT NULL,
    UNIQUE(workspace_id, user_id)
);

CREATE TABLE IF NOT EXISTS journal_people (
    journal_id TEXT NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    person_id INTEGER NOT NULL REFERENCES workspace_people(id) ON DELETE CASCADE,
    journal_note TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (journal_id, person_id)
);

CREATE TABLE IF NOT EXISTS workspace_axes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    axis_key TEXT NOT NULL,
    axis_label TEXT NOT NULL,
    example_groups_json TEXT DEFAULT '[]',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    action_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_journals_workspace ON journals(workspace_id);
CREATE INDEX IF NOT EXISTS idx_workspace_people_ws ON workspace_people(workspace_id);
CREATE INDEX IF NOT EXISTS idx_journal_people_journal ON journal_people(journal_id);
CREATE INDEX IF NOT EXISTS idx_workspace_axes_ws ON workspace_axes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chat_workspace ON chat_messages(workspace_id);
"""


MIGRATION_STATEMENTS = [
    "ALTER TABLE workspaces ADD COLUMN active_axis_id TEXT",
    "ALTER TABLE workspaces ADD COLUMN recommendation_reason TEXT DEFAULT ''",
    "ALTER TABLE journals ADD COLUMN axis_id TEXT",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkspaceDB:
    """Async SQLite wrapper for workspace persistence."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Open connection and create tables."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        # Run schema migrations for existing DBs
        for stmt in MIGRATION_STATEMENTS:
            try:
                await self._db.execute(stmt)
                await self._db.commit()
            except Exception:
                pass  # Column already exists

    async def close(self):
        if self._db:
            await self._db.close()

    # ── Workspace CRUD ─────────────────────────────────────

    async def create_workspace(self, workspace_id: str, query: str) -> dict:
        now = _now_iso()
        await self._db.execute(
            "INSERT INTO workspaces (id, query, status, created_at, updated_at) VALUES (?, ?, 'creating', ?, ?)",
            (workspace_id, query, now, now),
        )
        await self._db.commit()
        return {"id": workspace_id, "query": query, "status": "creating", "created_at": now}

    async def update_workspace(self, workspace_id: str, **kwargs):
        """Update workspace fields."""
        ALLOWED = {"status", "intent_json", "summary", "quality", "refinement_questions_json", "active_axis_id", "recommendation_reason"}
        sets = []
        vals = []
        for key, val in kwargs.items():
            if key in ALLOWED:
                sets.append(f"{key} = ?")
                vals.append(val)
        if not sets:
            return
        sets.append("updated_at = ?")
        vals.append(_now_iso())
        vals.append(workspace_id)
        await self._db.execute(
            f"UPDATE workspaces SET {', '.join(sets)} WHERE id = ?",
            vals,
        )
        await self._db.commit()

    async def get_workspace(self, workspace_id: str) -> Optional[dict]:
        cursor = await self._db.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return dict(row)

    async def list_workspaces(self, limit: int = 50) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT id, query, status, summary, quality, created_at, updated_at FROM workspaces ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def delete_workspace(self, workspace_id: str) -> bool:
        cursor = await self._db.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
        await self._db.commit()
        return cursor.rowcount > 0

    # ── Journal CRUD ───────────────────────────────────────

    async def create_journal(
        self,
        journal_id: str,
        workspace_id: str,
        label: str,
        description: str = "",
        theme: str = "topic",
        color: str = "#6366f1",
        canvas_x: float = 0,
        canvas_y: float = 0,
        sort_order: int = 0,
    ):
        now = _now_iso()
        await self._db.execute(
            """INSERT INTO journals (id, workspace_id, label, description, theme, color, canvas_x, canvas_y, sort_order, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (journal_id, workspace_id, label, description, theme, color, canvas_x, canvas_y, sort_order, now, now),
        )
        await self._db.commit()

    async def get_journals(self, workspace_id: str) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM journals WHERE workspace_id = ? ORDER BY sort_order",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_journal_people(self, journal_id: str) -> list[dict]:
        """Get full ranked_account JSON for all people in a journal."""
        cursor = await self._db.execute(
            """SELECT wp.user_id, wp.ranked_account_json, jp.journal_note, jp.sort_order
               FROM journal_people jp
               JOIN workspace_people wp ON jp.person_id = wp.id
               WHERE jp.journal_id = ?
               ORDER BY jp.sort_order""",
            (journal_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            account_data = json.loads(row["ranked_account_json"])
            account_data["journal_note"] = row["journal_note"]
            results.append(account_data)
        return results

    async def update_journal_layout(self, journal_id: str, canvas_x: float, canvas_y: float):
        await self._db.execute(
            "UPDATE journals SET canvas_x = ?, canvas_y = ?, updated_at = ? WHERE id = ?",
            (canvas_x, canvas_y, _now_iso(), journal_id),
        )
        await self._db.commit()

    # ── People CRUD ────────────────────────────────────────

    async def store_people_batch(self, workspace_id: str, people: list[dict]) -> dict[str, int]:
        """Store ranked accounts. Returns mapping of user_id → workspace_people.id."""
        user_id_to_pk = {}
        for person in people:
            user_id = person["user_id"]
            cursor = await self._db.execute(
                """INSERT INTO workspace_people (workspace_id, user_id, ranked_account_json)
                   VALUES (?, ?, ?)
                   ON CONFLICT(workspace_id, user_id) DO UPDATE SET ranked_account_json = excluded.ranked_account_json""",
                (workspace_id, user_id, json.dumps(person)),
            )
            user_id_to_pk[user_id] = cursor.lastrowid
        await self._db.commit()

        # Re-fetch IDs for any that were updates (lastrowid is 0 on conflict)
        cursor = await self._db.execute(
            "SELECT id, user_id FROM workspace_people WHERE workspace_id = ?",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        for row in rows:
            user_id_to_pk[row["user_id"]] = row["id"]

        return user_id_to_pk

    async def add_people_to_journal(
        self, journal_id: str, assignments: list[dict], user_id_to_pk: dict[str, int]
    ):
        """Add people to a journal. assignments = [{"user_id": ..., "journal_note": ...}, ...]"""
        for i, a in enumerate(assignments):
            person_pk = user_id_to_pk.get(a["user_id"])
            if person_pk is None:
                continue
            await self._db.execute(
                """INSERT OR IGNORE INTO journal_people (journal_id, person_id, journal_note, sort_order)
                   VALUES (?, ?, ?, ?)""",
                (journal_id, person_pk, a.get("journal_note", ""), i),
            )
        await self._db.commit()

    async def get_workspace_people_count(self, workspace_id: str) -> int:
        cursor = await self._db.execute(
            "SELECT COUNT(*) as cnt FROM workspace_people WHERE workspace_id = ?",
            (workspace_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"]

    async def get_journal_people_count(self, journal_id: str) -> int:
        cursor = await self._db.execute(
            "SELECT COUNT(*) as cnt FROM journal_people WHERE journal_id = ?",
            (journal_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"]

    # ── Axes CRUD ─────────────────────────────────────────

    async def create_axes_batch(self, workspace_id: str, axes: list[dict]):
        """Store grouping axes for a workspace."""
        for i, ax in enumerate(axes):
            await self._db.execute(
                """INSERT INTO workspace_axes (id, workspace_id, axis_key, axis_label, example_groups_json, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ax["id"], workspace_id, ax["axis_key"], ax["axis_label"],
                 json.dumps(ax.get("example_groups", [])), i),
            )
        await self._db.commit()

    async def get_axes(self, workspace_id: str) -> list[dict]:
        """Load all axes for a workspace."""
        cursor = await self._db.execute(
            "SELECT * FROM workspace_axes WHERE workspace_id = ? ORDER BY sort_order",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["example_groups"] = json.loads(d.pop("example_groups_json", "[]"))
            results.append(d)
        return results

    async def delete_journals_for_workspace(self, workspace_id: str):
        """Delete all journals and journal_people for a workspace (for re-grouping)."""
        # journal_people cascade-deleted via FK when journals are deleted
        await self._db.execute(
            "DELETE FROM journals WHERE workspace_id = ?", (workspace_id,)
        )
        await self._db.commit()

    async def get_all_workspace_people(self, workspace_id: str) -> list[dict]:
        """Load all ranked_account_json rows for a workspace."""
        cursor = await self._db.execute(
            "SELECT user_id, ranked_account_json FROM workspace_people WHERE workspace_id = ?",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        return [json.loads(row["ranked_account_json"]) for row in rows]

    # ── Chat CRUD ──────────────────────────────────────────

    async def add_chat_message(
        self, message_id: str, workspace_id: str, role: str, content: str, action: Optional[dict] = None
    ):
        await self._db.execute(
            "INSERT INTO chat_messages (id, workspace_id, role, content, action_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, workspace_id, role, content, json.dumps(action) if action else None, _now_iso()),
        )
        await self._db.commit()

    async def get_chat_history(self, workspace_id: str) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM chat_messages WHERE workspace_id = ? ORDER BY created_at",
            (workspace_id,),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get("action_json"):
                d["action"] = json.loads(d["action_json"])
            else:
                d["action"] = None
            del d["action_json"]
            result.append(d)
        return result
