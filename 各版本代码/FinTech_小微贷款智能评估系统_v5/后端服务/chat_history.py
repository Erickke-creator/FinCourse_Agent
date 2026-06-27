"""
v5 对话记忆 SQLite 持久化
重启/崩溃后恢复历史对话上下文
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        history TEXT DEFAULT '[]',
        enterprise_profile TEXT DEFAULT '{}',
        updated_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        score REAL,
        risk_level TEXT,
        enterprise_name TEXT,
        result_json TEXT,
        created_at TEXT
    )""")
    c.commit()
    return c


def save_session(session_id: str, history: list, profile: dict):
    c = _conn()
    c.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?)",
        (session_id, json.dumps(history, ensure_ascii=False),
         json.dumps(profile, ensure_ascii=False), datetime.now().isoformat())
    )
    c.commit()
    c.close()


def load_session(session_id: str) -> dict:
    c = _conn()
    row = c.execute("SELECT history, enterprise_profile FROM sessions WHERE session_id = ?",
                    (session_id,)).fetchone()
    c.close()
    if row:
        return {"history": json.loads(row[0]), "profile": json.loads(row[1])}
    return {"history": [], "profile": {}}


def save_evaluation(session_id: str, score: float, risk: str, name: str, result_json: dict):
    c = _conn()
    c.execute(
        "INSERT INTO evaluations (session_id, score, risk_level, enterprise_name, result_json, created_at) VALUES (?,?,?,?,?,?)",
        (session_id, score, risk, name, json.dumps(result_json, ensure_ascii=False, default=str),
         datetime.now().isoformat())
    )
    c.commit()
    c.close()


def get_recent_evaluations(session_id: str = "", limit: int = 5) -> list[dict]:
    """获取最近 N 次评估（用于历史对比）"""
    c = _conn()
    if session_id:
        rows = c.execute(
            "SELECT score, risk_level, enterprise_name, created_at, result_json FROM evaluations WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit)).fetchall()
    else:
        rows = c.execute(
            "SELECT score, risk_level, enterprise_name, created_at, result_json FROM evaluations ORDER BY created_at DESC LIMIT ?",
            (limit,)).fetchall()
    c.close()
    return [{"score": r[0], "risk_level": r[1], "enterprise_name": r[2],
             "created_at": r[3], "result": json.loads(r[4])} for r in rows]
