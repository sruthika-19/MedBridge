import sqlite3
from datetime import datetime, timezone

DB_FILE = "mappings.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def initialize_cache():
    """
    Create mapping_cache table if it does not already exist.

    The source terminology fields are preserved:
        rec_id
        sys_id
        term_id
        parent_id
        term_iast
        w_trans
        w_def
        refn

    These are stored along with the NAMASTE and ICD-11 mapping data.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mapping_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            input_term TEXT,
            normalized_term TEXT,

            -- Original source terminology
            source_rec_id TEXT,
            source_sys_id TEXT,
            source_term_id TEXT,
            source_parent_id TEXT,
            term_iast TEXT,
            w_trans TEXT,
            w_def TEXT,
            refn TEXT,

            -- Traditional medicine information
            traditional_term TEXT,
            system TEXT,

            -- NAMASTE mapping
            namaste_code TEXT,
            namaste_term TEXT,

            -- ICD-11 mapping
            icd11_code TEXT,
            icd11_title TEXT,
            icd11_uri TEXT,

            -- Matching information
            match_score REAL,
            match_type TEXT,
            match_status TEXT,

            -- Validation information
            mapping_status TEXT,
            validation_status TEXT,

            -- Source information
            source TEXT,
            source_version TEXT,

            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def get_cached_mapping(term):
    """
    Return only validated cached mappings.

    Cache hit response:
        {
            "cache": {
                "hit": True,
                "source": "mapping_cache"
            }
        }
    """

    if not term:
        return None

    initialize_cache()

    normalized_term = term.strip().lower()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            input_term,
            normalized_term,

            source_rec_id,
            source_sys_id,
            source_term_id,
            source_parent_id,
            term_iast,
            w_trans,
            w_def,
            refn,

            traditional_term,
            system,

            namaste_code,
            namaste_term,

            icd11_code,
            icd11_title,
            icd11_uri,

            match_score,
            match_type,
            match_status,

            mapping_status,
            validation_status,

            source,
            source_version,

            created_at,
            updated_at

        FROM mapping_cache

        WHERE normalized_term = ?
        AND validation_status = 'validated'

        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (normalized_term,)
    )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "cache": {
            "hit": True,
            "source": "mapping_cache"
        },

        "id": row[0],

        "inputTerm": row[1],
        "normalizedTerm": row[2],

        "sourceRecord": {
            "recId": row[3],
            "sysId": row[4],
            "termId": row[5],
            "parentId": row[6],
            "termIast": row[7],
            "translation": row[8],
            "definition": row[9],
            "reference": row[10]
        },

        "traditionalTerm": {
            "term": row[11],
            "system": row[12]
        },

        "namaste": {
            "code": row[13],
            "term": row[14],
            "source": "NAMASTE",
            "sourceVersion": row[25]
        },

        "icd11": {
            "code": row[15],
            "title": row[16],
            "uri": row[17],
            "source": "WHO ICD-11"
        },

        "matchScore": row[18],
        "matchType": row[19],
        "matchStatus": row[20],

        "mappingStatus": row[21],
        "validationStatus": row[22],

        "source": row[23],
        "sourceVersion": row[24],

        "createdAt": row[25],
        "updatedAt": row[26]
    }


def save_mapping_cache(mapping):
    """
    Save mapping only when validationStatus is 'validated'.

    Unvalidated mappings are NOT stored in the cache.
    """

    if not mapping:
        return False

    # ---------------------------------------------------------
    # IMPORTANT:
    # Only validated mappings are allowed into the cache.
    # ---------------------------------------------------------
    if mapping.get("validationStatus") != "validated":
        return False

    initialize_cache()

    now = datetime.now(timezone.utc).isoformat()

    input_term = mapping.get("inputTerm")

    normalized_term = mapping.get("normalizedTerm")

    # ---------------------------------------------------------
    # Traditional medicine information
    # ---------------------------------------------------------
    traditional = mapping.get("traditionalTerm") or {}

    # ---------------------------------------------------------
    # NAMASTE information
    # ---------------------------------------------------------
    namaste = mapping.get("namaste") or {}

    # ---------------------------------------------------------
    # ICD-11 information
    # ---------------------------------------------------------
    icd11 = mapping.get("icd11") or {}

    # ---------------------------------------------------------
    # Original source information
    #
    # These correspond to the columns in your source file:
    #
    # rec_id
    # sys_id
    # term_id
    # parent_id
    # term_iast
    # w_trans
    # w_def
    # refn
    # ---------------------------------------------------------
    source_record = mapping.get("sourceRecord") or {}

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # -----------------------------------------------------
        # Check whether a validated mapping already exists.
        # -----------------------------------------------------
        cursor.execute(
            """
            SELECT id
            FROM mapping_cache
            WHERE normalized_term = ?
            AND validation_status = 'validated'
            LIMIT 1
            """,
            (normalized_term,)
        )

        existing = cursor.fetchone()

        if existing:

            # -------------------------------------------------
            # Update existing validated mapping
            # -------------------------------------------------
            cursor.execute(
                """
                UPDATE mapping_cache
                SET
                    input_term = ?,
                    normalized_term = ?,

                    source_rec_id = ?,
                    source_sys_id = ?,
                    source_term_id = ?,
                    source_parent_id = ?,
                    term_iast = ?,
                    w_trans = ?,
                    w_def = ?,
                    refn = ?,

                    traditional_term = ?,
                    system = ?,

                    namaste_code = ?,
                    namaste_term = ?,

                    icd11_code = ?,
                    icd11_title = ?,
                    icd11_uri = ?,

                    match_score = ?,
                    match_type = ?,
                    match_status = ?,

                    mapping_status = ?,
                    validation_status = ?,

                    source = ?,
                    source_version = ?,

                    updated_at = ?

                WHERE id = ?
                """,
                (
                    input_term,
                    normalized_term,

                    source_record.get("recId"),
                    source_record.get("sysId"),
                    source_record.get("termId"),
                    source_record.get("parentId"),
                    source_record.get("termIast"),
                    source_record.get("translation"),
                    source_record.get("definition"),
                    source_record.get("reference"),

                    traditional.get("term"),
                    traditional.get("system"),

                    namaste.get("code"),
                    namaste.get("term"),

                    # IMPORTANT:
                    # ICD-11 title comes from the ICD-11 result.
                    icd11.get("code"),
                    icd11.get("title"),
                    icd11.get("uri"),

                    mapping.get("matchScore"),
                    mapping.get("matchType"),
                    mapping.get("matchStatus"),

                    mapping.get("mappingStatus"),
                    mapping.get("validationStatus"),

                    mapping.get("source"),
                    mapping.get("sourceVersion"),

                    now,

                    existing[0]
                )
            )

        else:

            # -------------------------------------------------
            # Insert new validated mapping
            # -------------------------------------------------
            cursor.execute(
                """
                INSERT INTO mapping_cache (
                    input_term,
                    normalized_term,

                    source_rec_id,
                    source_sys_id,
                    source_term_id,
                    source_parent_id,
                    term_iast,
                    w_trans,
                    w_def,
                    refn,

                    traditional_term,
                    system,

                    namaste_code,
                    namaste_term,

                    icd11_code,
                    icd11_title,
                    icd11_uri,

                    match_score,
                    match_type,
                    match_status,

                    mapping_status,
                    validation_status,

                    source,
                    source_version,

                    created_at,
                    updated_at
                )

                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?
                )
                """,
                (
                    input_term,
                    normalized_term,

                    source_record.get("recId"),
                    source_record.get("sysId"),
                    source_record.get("termId"),
                    source_record.get("parentId"),
                    source_record.get("termIast"),
                    source_record.get("translation"),
                    source_record.get("definition"),
                    source_record.get("reference"),

                    traditional.get("term"),
                    traditional.get("system"),

                    namaste.get("code"),
                    namaste.get("term"),

                    icd11.get("code"),
                    icd11.get("title"),
                    icd11.get("uri"),

                    mapping.get("matchScore"),
                    mapping.get("matchType"),
                    mapping.get("matchStatus"),

                    mapping.get("mappingStatus"),
                    mapping.get("validationStatus"),

                    mapping.get("source"),
                    mapping.get("sourceVersion"),

                    now,
                    now
                )
            )

        conn.commit()

        return True

    except sqlite3.Error:
        conn.rollback()
        return False

    finally:
        conn.close()
        