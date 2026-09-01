import sqlite3
from datetime import datetime

DB_FILE = "mappings.db"


def initialize_cache():
    """
    Creates the mapping_cache table if it does not already exist.
    Also adds the system column if an older cache table exists.
    """

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mapping_cache (
            term TEXT PRIMARY KEY,
            system TEXT,
            namaste_code TEXT,
            namaste_term TEXT,
            icd11_code TEXT,
            icd11_term TEXT,
            confidence REAL,
            validation_status TEXT,
            reason TEXT,
            created_at TEXT
        )
    """)

    # Support older versions of the cache table
    cursor.execute("PRAGMA table_info(mapping_cache)")
    columns = [column[1] for column in cursor.fetchall()]

    if "system" not in columns:
        cursor.execute(
            "ALTER TABLE mapping_cache ADD COLUMN system TEXT"
        )

    conn.commit()
    conn.close()


def get_cached_mapping(term):
    """
    Retrieves a cached mapping.

    Returns:
        Dictionary containing cached mapping,
        or None if the mapping is not found.
    """

    if not term or not term.strip():
        return None

    term = term.strip().lower()

    initialize_cache()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            term,
            system,
            namaste_code,
            namaste_term,
            icd11_code,
            icd11_term,
            confidence,
            validation_status,
            reason,
            created_at
        FROM mapping_cache
        WHERE term = ?
    """, (term,))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "term": row[0],
        "system": row[1],
        "namaste_code": row[2],
        "namaste_term": row[3],
        "icd11_code": row[4],
        "icd11_term": row[5],
        "confidence": row[6],
        "validation_status": row[7],
        "reason": row[8],
        "created_at": row[9]
    }


def save_mapping_cache(mapping):
    """
    Saves only validated mappings to the cache.

    Returns:
        True  -> mapping saved
        False -> mapping rejected
    """

    if not mapping:
        return False

    if mapping.get("validation_status") != "validated":
        return False

    term = mapping.get("term")

    if not term or not term.strip():
        return False

    initialize_cache()

    term = term.strip().lower()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO mapping_cache (
            term,
            system,
            namaste_code,
            namaste_term,
            icd11_code,
            icd11_term,
            confidence,
            validation_status,
            reason,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        term,
        mapping.get("system"),
        mapping.get("namaste_code"),
        mapping.get("namaste_term"),
        mapping.get("icd11_code"),
        mapping.get("icd11_term"),
        mapping.get("confidence"),
        mapping.get("validation_status"),
        mapping.get("reason", ""),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return True