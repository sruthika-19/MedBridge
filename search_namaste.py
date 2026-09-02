import sqlite3


DB_FILENAME = "mappings.db"


def search_namaste(term, system=None):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()

    if not term or not term.strip():
        conn.close()
        return []

    search_term = term.strip().lower()
    query = """
        SELECT
            rec_id,
            t_id,
            term_id,
            term_devanagari,
            term_iast,
            wordtree,
            parent_id,
            def_id,
            w_trans,
            w_def,
            refn,
            sys_id
        FROM namaste_terms
        WHERE
            LOWER(term_iast) LIKE ?
            OR LOWER(wordtree) LIKE ?
            OR LOWER(w_trans) LIKE ?
            OR LOWER(w_def) LIKE ?
            OR LOWER(term_devanagari) LIKE ?
    """

    search_pattern = f"%{search_term}%"
    params = [
        search_pattern,
        search_pattern,
        search_pattern,
        search_pattern,
        search_pattern,
    ]
    if system is not None:
        query += " AND CAST(sys_id AS TEXT) = ?"
        params.append(str(system).strip())

    query += " ORDER BY rec_id LIMIT 50"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [
        "rec_id",
        "t_id",
        "term_id",
        "term_devanagari",
        "term_iast",
        "wordtree",
        "parent_id",
        "def_id",
        "w_trans",
        "w_def",
        "refn",
        "sys_id",
    ]

    results = [dict(zip(columns, row)) for row in rows]

    conn.close()
    return results

if __name__ == "__main__":
    results = search_namaste("āyurveda", system="1")

    print(f"Found {len(results)} result(s).")

    for result in results[:3]:
        print(result)
