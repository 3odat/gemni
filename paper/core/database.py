import sqlite3
import json
import numpy as np
from typing import List, Dict, Any, Optional
from core.logger import log

DB_PATH = "mission_memory.db"


class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_tables()

    def _init_tables(self):
        # 1. Episodic Memory (The "Black Box" Log)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                drone_id INTEGER,
                mission_id TEXT,
                action_type TEXT,
                state_json TEXT,      -- {lat, lon, battery}
                outcome_text TEXT,
                embedding BLOB,       -- Numpy bytes of the vector
                integrity_hash TEXT,  -- For Phase 6 Defense
                is_poisoned INTEGER DEFAULT 0  -- 0=Real, 1=Fake
            )
        """)

        # 2. Semantic Memory (The "Rules")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_text TEXT,
                rule_type TEXT,       -- 'HAZARD', 'ENERGY'
                location_json TEXT,   -- {lat, lon, radius}
                confidence REAL,
                embedding BLOB,
                is_poisoned INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()
        log.success("Memory Database Initialized (SQLite)")

    def insert_episode(self, drone_id: int, action: str, state: Dict, outcome: str, embedding: List[float], is_poisoned: int = 0):
        """Standard insertion of a flight event."""
        # Convert list of floats to bytes for storage
        emb_blob = np.array(embedding, dtype=np.float32).tobytes()

        self.cursor.execute("""
            INSERT INTO episodic_memory 
            (timestamp, drone_id, action_type, state_json, outcome_text, embedding, is_poisoned)
            VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)
        """, (drone_id, action, json.dumps(state), outcome, emb_blob, is_poisoned))
        self.conn.commit()

    def find_similar_episodes(self, query_embedding: List[float], limit: int = 3) -> List[str]:
        """
        Naive Vector Search: Loads all embeddings and calculates Cosine Similarity.
        (Sufficient for <10k rows in a PhD prototype).
        """
        query_vec = np.array(query_embedding, dtype=np.float32)

        self.cursor.execute("SELECT outcome_text, embedding FROM episodic_memory")
        rows = self.cursor.fetchall()

        results = []
        for text, blob in rows:
            if not blob:
                continue
            db_vec = np.frombuffer(blob, dtype=np.float32)

            # Cosine Similarity
            similarity = np.dot(query_vec, db_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(db_vec))
            results.append((similarity, text))

        # Sort by similarity desc
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def find_similar_episodes_with_flags(self, query_embedding: List[float], limit: int = 3) -> List[Dict[str, Any]]:
        """Return episodes with poison flag for visibility."""
        query_vec = np.array(query_embedding, dtype=np.float32)
        self.cursor.execute("SELECT outcome_text, embedding, is_poisoned FROM episodic_memory")
        rows = self.cursor.fetchall()
        results = []
        for text, blob, poisoned in rows:
            if not blob:
                continue
            db_vec = np.frombuffer(blob, dtype=np.float32)
            similarity = np.dot(query_vec, db_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(db_vec))
            results.append((similarity, {"text": text, "poisoned": bool(poisoned)}))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def insert_rule(self, rule_text: str, rule_type: str, location: Dict, confidence: float, embedding: List[float], is_poisoned: int = 0):
        emb_blob = np.array(embedding, dtype=np.float32).tobytes()
        self.cursor.execute("""
            INSERT INTO semantic_rules
            (rule_text, rule_type, location_json, confidence, embedding, is_poisoned)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rule_text, rule_type, json.dumps(location), confidence, emb_blob, is_poisoned))
        self.conn.commit()

    def find_similar_rules(self, query_embedding: List[float], limit: int = 3) -> List[str]:
        query_vec = np.array(query_embedding, dtype=np.float32)
        self.cursor.execute("SELECT rule_text, embedding FROM semantic_rules")
        rows = self.cursor.fetchall()
        results = []
        for text, blob in rows:
            if not blob:
                continue
            db_vec = np.frombuffer(blob, dtype=np.float32)
            similarity = np.dot(query_vec, db_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(db_vec))
            results.append((similarity, text))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def find_similar_rules_with_flags(self, query_embedding: List[float], limit: int = 3) -> List[Dict[str, Any]]:
        query_vec = np.array(query_embedding, dtype=np.float32)
        self.cursor.execute("SELECT rule_text, rule_type, location_json, embedding, is_poisoned FROM semantic_rules")
        rows = self.cursor.fetchall()
        results = []
        for text, rule_type, loc_json, blob, poisoned in rows:
            if not blob:
                continue
            db_vec = np.frombuffer(blob, dtype=np.float32)
            similarity = np.dot(query_vec, db_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(db_vec))
            results.append(
                (
                    similarity,
                    {
                        "text": text,
                        "rule_type": rule_type,
                        "location": loc_json,
                        "poisoned": bool(poisoned),
                    },
                )
            )
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def count_episodes(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM episodic_memory")
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def count_poisoned(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM episodic_memory WHERE is_poisoned=1")
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def count_rules(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM semantic_rules")
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def count_poisoned_rules(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM semantic_rules WHERE is_poisoned=1")
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def recent_episodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        self.cursor.execute("""
            SELECT id, timestamp, drone_id, action_type, outcome_text, is_poisoned
            FROM episodic_memory
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = self.cursor.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "drone_id": r[2],
                "action_type": r[3],
                "outcome": r[4],
                "poisoned": bool(r[5]),
            }
            for r in rows
        ]

    def recent_rules(self, limit: int = 5) -> List[Dict[str, Any]]:
        self.cursor.execute("""
            SELECT id, rule_type, rule_text, location_json, confidence, is_poisoned
            FROM semantic_rules
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = self.cursor.fetchall()
        return [
            {
                "id": r[0],
                "rule_type": r[1],
                "rule_text": r[2],
                "location": r[3],
                "confidence": r[4],
                "poisoned": bool(r[5]),
            }
            for r in rows
        ]
