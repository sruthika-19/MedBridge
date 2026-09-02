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
            id,
            system,
            term_id,
            parent_id,
            term,
            code,
            short_definition,
            long_definition,
            reference,
            source,
            source_version
        FROM namaste_terms
        WHERE LOWER(term) LIKE ?
    """

    params = [f"%{search_term}%"]
    if system is not None:
        query += " AND LOWER(system) = ?"
        params.append(system.strip().lower())

    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [
        "id",
        "system",
        "term_id",
        "parent_id",
        "term",
        "code",
        "short_definition",
        "long_definition",
        "reference",
        "source",
        "source_version"
    ]

    results = [dict(zip(columns, row)) for row in rows]

    conn.close()
    return results

if __name__ == "__main__":
    results = search_namaste("āyurveda", system="1")

    print(f"Found {len(results)} result(s).")

    for result in results[:3]:
        print(result)
