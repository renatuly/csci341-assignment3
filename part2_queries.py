"""CSCI 341 Assignment 3 -- Part 2: SQL operations through Python and SQLAlchemy.

Run:   python part2_queries.py            (prints everything)
       python part2_queries.py > part2_output.txt

Every statement is executed with sqlalchemy.text() and bound parameters.
Updates and deletions run inside a transaction that is rolled back afterwards,
so every task runs against the original seed dataset.
"""
import textwrap

from sqlalchemy import text

from db import engine, read_sql, run_script

# Query parameter values (documented in the README)
PARAMS = {
    "3.1": {"email": "arman.armanov@example.com", "phone": "+77773414141"},
    "3.2": {"city": "Astana", "astana_days": 7, "other_days": 3},
    "4.1": {"email": "amina.aminova@example.com"},
    "4.2": {"city": "Astana"},
    "5.2": {"pattern": "%machine learning%"},
    "5.3": {"paper_id": 1},
    "5.4": {"conference_id": 1, "area": "Databases", "min_years": 3},
}

TABLES = ["app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
          "conference", "conference_host", "conference_reviewer", "track",
          "conference_session", "paper", "paper_keyword", "paper_author",
          "paper_version", "review"]


# ------------------------------------------------------------------ printing helpers
def header(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def show_sql(sql: str, params: dict | None = None) -> None:
    print("SQL:")
    print(textwrap.indent(textwrap.dedent(sql).strip(), "    "))
    if params:
        print(f"Bound parameters: {params}")


def print_table(result) -> None:
    cols = list(result.keys())
    rows = [["NULL" if v is None else str(v) for v in r] for r in result]
    widths = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c)
              for i, c in enumerate(cols)]
    line = "+".join("-" * (w + 2) for w in widths)
    print(line)
    print("|".join(f" {c:<{w}} " for c, w in zip(cols, widths)))
    print(line)
    for r in rows:
        print("|".join(f" {v:<{w}} " for v, w in zip(r, widths)))
    print(line)
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")


def run_query(conn, sql: str, params: dict | None = None, label: str | None = None) -> None:
    if label:
        print(f"\n-- {label}")
    show_sql(sql, params)
    print_table(conn.execute(text(sql), params or {}))


def run_mutation(conn, sql: str, params: dict) -> None:
    show_sql(sql, params)
    result = conn.execute(text(sql), params)
    print(f"Rows affected: {result.rowcount}")


# ------------------------------------------------------------------ tasks 1 and 2
def task_1_create() -> None:
    header("TASK 1 -- Create statements (sql/schema.sql)")
    print(read_sql("schema.sql"))
    with engine.begin() as conn:
        run_script(conn, "schema.sql")
        run_query(conn, """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name""", label="Tables created")
        run_query(conn, """
            SELECT tc.table_name, tc.constraint_name, tc.constraint_type
            FROM information_schema.table_constraints tc
            WHERE tc.table_schema = 'public'
              AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK')
              AND tc.constraint_name NOT LIKE '%_not_null'
            ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name""",
                  label="Constraints created (NOT NULL constraints omitted from this list)")


def count_rows(conn, label: str) -> None:
    sql = "\nUNION ALL\n".join(
        f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in TABLES)
    run_query(conn, sql, label=label)


def task_2_insert() -> None:
    header("TASK 2 -- Insert statements (sql/seed.sql)")
    print(read_sql("seed.sql"))
    with engine.begin() as conn:
        run_script(conn, "seed.sql")
        count_rows(conn, "Row count of every table")
    print("\nTo restore this initial dataset at any time:  python init_db.py --reset")


# ------------------------------------------------------------------ task 3 updates
def task_3_1() -> None:
    header("TASK 3.1 -- Update the phone number of Arman Armanov")
    p = PARAMS["3.1"]
    check = """
        SELECT user_id, given_name, surname, email, phone_number
        FROM app_user WHERE email = :email"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, check, {"email": p["email"]}, "BEFORE")
        print("\n-- UPDATE")
        run_mutation(conn, """
            UPDATE app_user
            SET phone_number = :phone
            WHERE email = :email""", p)
        run_query(conn, check, {"email": p["email"]}, "AFTER")
        trans.rollback()
        print("Transaction rolled back -- seed data restored.")


def task_3_2() -> None:
    header("TASK 3.2 -- Extend review deadlines: +7 days in Astana, +3 days elsewhere")
    p = PARAMS["3.2"]
    check = """
        SELECT conference_id, acronym, city, review_deadline
        FROM conference ORDER BY conference_id"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, check, label="BEFORE")
        print("\n-- UPDATE (single conditional statement)")
        run_mutation(conn, """
            UPDATE conference
            SET review_deadline = review_deadline +
                CASE WHEN city = :city THEN :astana_days ELSE :other_days END
            """, p)
        run_query(conn, check, label="AFTER")
        trans.rollback()
        print("Transaction rolled back -- seed data restored.")


# ------------------------------------------------------------------ task 4 deletes
def task_4_1() -> None:
    header("TASK 4.1 -- Delete withdrawn papers whose corresponding author is Amina Aminova")
    p = PARAMS["4.1"]
    papers = """
        SELECT p.paper_id, p.title, p.status, u.email AS corresponding_email
        FROM paper p
        JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
        JOIN app_user u ON u.user_id = pa.author_id
        ORDER BY p.paper_id"""
    dependents = """
        SELECT (SELECT COUNT(*) FROM paper)         AS papers,
               (SELECT COUNT(*) FROM paper_author)  AS authorships,
               (SELECT COUNT(*) FROM paper_keyword) AS keywords,
               (SELECT COUNT(*) FROM paper_version) AS versions,
               (SELECT COUNT(*) FROM review)        AS reviews,
               (SELECT COUNT(*) FROM app_user)      AS users,
               (SELECT COUNT(*) FROM track)         AS tracks,
               (SELECT COUNT(*) FROM conference)    AS conferences"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, papers, label="BEFORE: papers with corresponding author")
        run_query(conn, dependents, label="BEFORE: row counts")
        print("\n-- DELETE (authorship, keyword, version and review rows are removed by ON DELETE CASCADE)")
        run_mutation(conn, """
            DELETE FROM paper p
            WHERE p.status = 'withdrawn'
              AND EXISTS (SELECT 1
                          FROM paper_author pa
                          JOIN app_user u ON u.user_id = pa.author_id
                          WHERE pa.paper_id = p.paper_id
                            AND pa.is_corresponding
                            AND u.email = :email)""", p)
        run_query(conn, papers, label="AFTER: papers with corresponding author")
        run_query(conn, dependents, label="AFTER: row counts")
        trans.rollback()
        print("Transaction rolled back -- seed data restored.")


def task_4_2() -> None:
    header("TASK 4.2 -- Delete empty sessions of conferences held in Astana")
    p = PARAMS["4.2"]
    check = """
        SELECT s.session_id, s.title, c.acronym, c.city,
               COUNT(p.paper_id) AS assigned_papers
        FROM conference_session s
        JOIN conference c ON c.conference_id = s.conference_id
        LEFT JOIN paper p ON p.session_id = s.session_id
        GROUP BY s.session_id, s.title, c.acronym, c.city
        ORDER BY s.session_id"""
    with engine.connect() as conn:
        trans = conn.begin()
        run_query(conn, check, label="BEFORE")
        print("\n-- DELETE")
        run_mutation(conn, """
            DELETE FROM conference_session s
            WHERE s.conference_id IN (SELECT conference_id FROM conference WHERE city = :city)
              AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)""", p)
        run_query(conn, check, label="AFTER")
        run_query(conn, "SELECT conference_id, acronym, city FROM conference ORDER BY conference_id",
                  label="AFTER: all conferences are kept")
        trans.rollback()
        print("Transaction rolled back -- seed data restored.")


# ------------------------------------------------------------------ task 5 simple queries
Q5_1 = """
    SELECT p.paper_id, p.title,
           u.given_name || ' ' || u.surname AS corresponding_author,
           u.email AS corresponding_email,
           t.name AS track_name,
           c.conference_id, c.acronym
    FROM paper p
    JOIN track t         ON t.track_id = p.track_id
    JOIN conference c    ON c.conference_id = t.conference_id
    JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
    JOIN app_user u      ON u.user_id = pa.author_id
    WHERE p.status = 'accepted'
    ORDER BY p.paper_id"""

Q5_2 = """
    SELECT paper_id, title
    FROM paper
    WHERE abstract ILIKE :pattern
    ORDER BY paper_id"""

Q5_3 = """
    SELECT version_no, file_location, uploaded_at
    FROM paper_version
    WHERE paper_id = :paper_id
    ORDER BY version_no DESC"""

Q5_4 = """
    SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name, u.email
    FROM conference_reviewer cr
    JOIN reviewer r ON r.reviewer_id = cr.reviewer_id
    JOIN app_user u ON u.user_id = r.reviewer_id
    WHERE cr.conference_id = :conference_id
      AND r.years_experience >= :min_years
      AND EXISTS (SELECT 1 FROM reviewer_expertise e
                  WHERE e.reviewer_id = r.reviewer_id AND e.area_label = :area)
    ORDER BY r.reviewer_id"""

# ------------------------------------------------------------------ task 6 complex queries
Q6_1 = """
    SELECT t.track_id, t.name AS track_name, t.conference_id,
           COUNT(DISTINCT p.paper_id)   AS paper_count,
           COUNT(DISTINCT pa.author_id) AS author_count
    FROM track t
    LEFT JOIN paper p         ON p.track_id = t.track_id
    LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
    GROUP BY t.track_id, t.name, t.conference_id
    ORDER BY t.track_id"""

Q6_2 = """
    SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
           COUNT(rv.review_id)               AS review_count,
           ROUND(AVG(rv.overall_score), 2)   AS avg_overall_score
    FROM reviewer r
    JOIN app_user u     ON u.user_id = r.reviewer_id
    LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.reviewer_id, u.given_name, u.surname
    ORDER BY r.reviewer_id"""

Q6_3 = """
    WITH paper_counts AS (
        SELECT t.conference_id,
               COUNT(*)                                     AS total_papers,
               COUNT(*) FILTER (WHERE p.status = 'accepted') AS accepted_papers
        FROM paper p JOIN track t ON t.track_id = p.track_id
        GROUP BY t.conference_id
    ),
    review_scores AS (
        SELECT t.conference_id, AVG(rv.overall_score) AS avg_score
        FROM review rv
        JOIN paper p ON p.paper_id = rv.paper_id
        JOIN track t ON t.track_id = p.track_id
        GROUP BY t.conference_id
    )
    SELECT c.conference_id, c.acronym,
           COALESCE(pc.total_papers, 0)    AS total_papers,
           COALESCE(pc.accepted_papers, 0) AS accepted_papers,
           ROUND(rs.avg_score, 2)          AS avg_overall_score
    FROM conference c
    LEFT JOIN paper_counts pc  ON pc.conference_id = c.conference_id
    LEFT JOIN review_scores rs ON rs.conference_id = c.conference_id
    ORDER BY c.conference_id"""

Q6_4 = """
    WITH reviewer_counts AS (
        SELECT r.reviewer_id, COUNT(rv.review_id) AS review_count
        FROM reviewer r
        LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
        GROUP BY r.reviewer_id
    ),
    overall AS (
        SELECT AVG(review_count) AS avg_reviews FROM reviewer_counts
    )
    SELECT rc.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
           rc.review_count, ROUND(o.avg_reviews, 2) AS avg_reviews_per_reviewer
    FROM reviewer_counts rc
    CROSS JOIN overall o
    JOIN app_user u ON u.user_id = rc.reviewer_id
    WHERE rc.review_count > o.avg_reviews
    ORDER BY rc.review_count DESC, rc.reviewer_id"""

# ------------------------------------------------------------------ task 7 derived attribute
Q7 = """
    SELECT c.conference_id, c.acronym,
           COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted') AS accepted_count,
           COUNT(p.paper_id) FILTER (WHERE p.status = 'rejected') AS rejected_count,
           ROUND(100.0 * COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted')
                 / NULLIF(COUNT(p.paper_id) FILTER (WHERE p.status IN ('accepted', 'rejected')), 0),
                 2) AS acceptance_rate_pct
    FROM conference c
    LEFT JOIN track t ON t.conference_id = c.conference_id
    LEFT JOIN paper p ON p.track_id = t.track_id
    GROUP BY c.conference_id, c.acronym
    ORDER BY c.conference_id"""

# ------------------------------------------------------------------ task 8 view
Q8 = """
    SELECT *
    FROM accepted_paper_schedule
    ORDER BY conference_id, session_date, start_time, session_id, paper_id"""


def simple_and_complex_queries() -> None:
    with engine.connect() as conn:
        header("TASK 5.1 -- Accepted papers with corresponding author, track and conference")
        run_query(conn, Q5_1)
        header("TASK 5.2 -- Papers whose abstract contains 'machine learning' (case-insensitive)")
        run_query(conn, Q5_2, PARAMS["5.2"])
        header("TASK 5.3 -- All versions of a selected paper, newest first")
        run_query(conn, Q5_3, PARAMS["5.3"])
        header("TASK 5.4 -- Pool reviewers with 'Databases' expertise and >= 3 years experience")
        run_query(conn, Q5_4, PARAMS["5.4"])

        header("TASK 6.1 -- Papers and distinct authors per track")
        run_query(conn, Q6_1)
        header("TASK 6.2 -- Review count and average overall score per reviewer")
        run_query(conn, Q6_2)
        header("TASK 6.3 -- Paper counts and average review score per conference")
        run_query(conn, Q6_3)
        header("TASK 6.4 -- Reviewers with more reviews than the average per reviewer")
        run_query(conn, Q6_4)

        header("TASK 7 -- Acceptance rate per conference (derived attribute)")
        run_query(conn, Q7)


def task_8_view() -> None:
    header("TASK 8 -- View accepted_paper_schedule")
    print(read_sql("view.sql"))
    with engine.begin() as conn:
        run_script(conn, "view.sql")
        run_query(conn, Q8, label="Query the view")


if __name__ == "__main__":
    task_1_create()
    task_2_insert()
    task_3_1()
    task_3_2()
    task_4_1()
    task_4_2()
    simple_and_complex_queries()
    task_8_view()
