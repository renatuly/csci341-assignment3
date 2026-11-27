# CSCI 341 Assignment 3: Research Conference and Paper Review Management System

PostgreSQL database, a Python/SQLAlchemy program for the numbered Part 2 tasks, and a Flask web
application with CRUD for users, papers, reviews and sessions.

## Contents

| Path | Purpose |
|---|---|
| `sql/schema.sql` | Part 1: tables, keys and constraints (drops and recreates everything) |
| `sql/seed.sql` | Part 1: fictional sample data |
| `sql/view.sql` | Task 8: view `accepted_paper_schedule` |
| `dump.sql` | Plain `pg_dump` export of schema, seed data and view |
| `db.py` | SQLAlchemy engine (reads `DATABASE_URL`) and helpers that run the SQL scripts |
| `init_db.py` | Creates and seeds the database (`--reset` restores the original dataset) |
| `part2_queries.py` | Part 2: tasks 1–8, printing every SQL statement, its bound parameters and its result |
| `part2_output.txt` | Saved output of `part2_queries.py` |
| `app.py`, `templates/` | Part 3: Flask web application |
| `requirements.txt`, `Procfile`, `render.yaml` | Dependencies and deployment configuration |

## Software versions

- Python 3.12 or newer (tested with 3.14.7)
- PostgreSQL 16 locally (Docker); the deployed app uses a free Neon PostgreSQL database
- SQLAlchemy 2.1.9, psycopg2-binary 2.9.13, Flask 3.1.3, gunicorn 27.0.1

## Setup and database restoration

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# A local PostgreSQL (any instance works; this one matches the default URL in db.py):
docker run -d --name csci341-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=conference -p 5433:5432 postgres:16
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/conference
```

You can restore the original seed dataset in any of three ways:

1. `python init_db.py --reset`: runs `schema.sql`, `seed.sql` and `view.sql` through SQLAlchemy.
2. `python part2_queries.py`: tasks 1 and 2 recreate and reseed the database.
3. `psql "$DATABASE_URL" -f dump.sql`: loads the plain pg_dump export into an empty database.

## Running Part 2

```bash
python part2_queries.py                    # prints to the terminal
python part2_queries.py > part2_output.txt
```

The program first runs tasks 1 and 2 (create and seed). Every later statement uses
`sqlalchemy.text()` with bound parameters. Each update and delete runs inside a transaction: the
program prints the rows before the change, the statement and the number of rows it affected, and the
rows after the change, then rolls the transaction back. So every mutation, query and view task runs
against the original seed dataset.

### Query parameter values

| Task | Parameters |
|---|---|
| 3.1 | `email = 'arman.armanov@example.com'`, `phone = '+77773414141'` |
| 3.2 | `city = 'Astana'`, `astana_days = 7`, `other_days = 3` |
| 4.1 | `email = 'amina.aminova@example.com'` (deletes papers 7 and 11; paper 13 is withdrawn but its corresponding author is someone else, so it stays) |
| 4.2 | `city = 'Astana'` (deletes session 3; empty session 5 is in Almaty and stays) |
| 5.2 | `pattern = '%machine learning%'` with `ILIKE` (matches "Machine Learning" in paper 2 and "machine learning" in paper 10) |
| 5.3 | `paper_id = 1` (versions 3, 2, 1) |
| 5.4 | `conference_id = 1`, `area = 'Databases'`, `min_years = 3` (Saule Omarova is excluded with 2 years) |

## Running the web application

```bash
python init_db.py           # first time only
python app.py               # http://127.0.0.1:5000
# or, as in production:
gunicorn app:app
```

Pages: **Home** (read-only conferences and tracks, plus the `accepted_paper_schedule` view),
**Users** (CRUD, including the author profile with ORCID and research areas, and the reviewer
profile with experience, expertise and reviewer pools), **Papers** (CRUD, including authorship with
positions and the corresponding author, keywords, and version add/edit/delete on the paper page),
**Reviews** (CRUD) and **Sessions** (CRUD). Each save runs in a single transaction. When the
application or the database rejects a change, the page shows a red message naming the violated rule
or constraint, and the database is left unchanged.

### Deployment (Render)

`render.yaml` defines a free Render web service; the PostgreSQL database is a free Neon database whose connection string is set as `DATABASE_URL`. In Render, choose
**New → Blueprint** and select this repository. With `AUTO_INIT_DB=1`, the app creates and seeds
the schema on its first start if the database is empty. To restore the seed data on the server,
open the web service's Shell and run `python init_db.py --reset`.

## Schema, keys and references

Primary keys are in bold. FK = foreign key.

| Table | Columns | Keys and references |
|---|---|---|
| app_user | **user_id**, given_name, surname, email, affiliation, country, phone_number | UNIQUE(email) |
| author | **author_id**, orcid (optional) | author_id FK → app_user (ON DELETE CASCADE); UNIQUE(orcid), CHECK ORCID format |
| author_research_area | **author_id, area_label** | author_id FK → author (CASCADE) |
| reviewer | **reviewer_id**, years_experience | reviewer_id FK → app_user (CASCADE); CHECK years_experience ≥ 0 |
| reviewer_expertise | **reviewer_id, area_label** | reviewer_id FK → reviewer (CASCADE) |
| conference | **conference_id**, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline | CHECK end_date ≥ start_date |
| conference_host | **conference_id, host_name** | FK → conference (CASCADE) |
| conference_reviewer | **conference_id, reviewer_id** | FK → conference (CASCADE), FK → reviewer (CASCADE) |
| track | **track_id**, conference_id, name, description, research_area, coordinator_id | FK → conference (CASCADE); coordinator_id FK → reviewer; (conference_id, coordinator_id) FK → conference_reviewer; UNIQUE(conference_id, name) |
| conference_session | **session_id**, conference_id, title, session_date, start_time, end_time, room_label, chair_id | FK → conference (CASCADE); chair_id FK → reviewer; (conference_id, chair_id) FK → conference_reviewer; CHECK end_time > start_time |
| paper | **paper_id**, track_id, title, abstract, submission_date, status, session_id (optional) | track_id FK → track (RESTRICT); session_id FK → conference_session (ON DELETE SET NULL); CHECK status ∈ {submitted, under review, accepted, rejected, withdrawn}; CHECK session_id IS NULL OR status = 'accepted' |
| paper_keyword | **paper_id, keyword** | FK → paper (CASCADE) |
| paper_author | **paper_id, author_id**, author_position, is_corresponding | FK → paper (CASCADE), FK → author (RESTRICT); UNIQUE(paper_id, author_position); CHECK author_position > 0; partial UNIQUE index: at most one corresponding author per paper |
| paper_version | **paper_id, version_no**, file_location, uploaded_at, change_note (optional) | FK → paper (CASCADE); CHECK version_no > 0 |
| review | **review_id**, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments (optional), review_submission_date | FK → paper (CASCADE), FK → reviewer (RESTRICT); UNIQUE(paper_id, reviewer_id); CHECK overall_score BETWEEN 1 AND 5; CHECK recommendation ∈ {accept, reject} |

Every column is NOT NULL except the three marked optional (orcid, session_id, change_note) and
`confidential_comments`. Because only completed reviews are stored, every other review attribute is
mandatory. Multivalued attributes (research areas, expertise areas, host institutions, keywords) and
the author list are stored in separate relations, never as comma-separated text.

### Deletion actions

- Deleting a **paper** cascades to its versions (required), keywords, authorship rows and reviews.
- Deleting a **session** sets `paper.session_id` to NULL, which unassigns its papers.
- Deleting a **conference** cascades to its hosts, pool memberships, tracks and sessions. It is
  rejected while any of its tracks still has papers (`paper.track_id` is RESTRICT). It never deletes
  users or reviewers.
- Deleting a **user** cascades to the author and reviewer profiles, their labels and pool
  memberships. It is rejected while the user authors a paper, has written a review, or coordinates a
  track or chairs a session. To delete such a user, first remove those references.
- Foreign keys are never disabled.

## Required application checks (Part 1)

Both checks are in `app.py`. They run inside the same transaction as the change they guard.

1. **No self-reviews.** `check_self_review` runs when a review is created or edited and rejects it
   if the reviewer is an author of the paper. `check_authors_have_not_reviewed` runs when a paper's
   authors are changed and rejects the change if a newly listed author has already reviewed that
   paper.
2. **Valid session assignments.** `check_session_assignment` runs on every paper create or update,
   including changes to the session, the status or the track. It requires that a paper with a session
   is `accepted` and that the paper's track and the session belong to the same conference. Otherwise
   the change is rejected. `check_session_conference_change` rejects moving a session to another
   conference while it holds papers from the original conference. In addition, the database CHECK
   `ck_paper_session_accepted` guarantees that only accepted papers can have a session.

## Other Assignment 1 business rules

All of these rules hold in the seed data.

| Rule | Enforced automatically? |
|---|---|
| Every user is an author, a reviewer, or both | Yes, by the application (user form) |
| An author has at least one research area; a reviewer has at least one expertise area | Yes, by the application |
| A paper has at least one author | Yes, by the application |
| Exactly one corresponding author per paper | At most one: database (partial unique index). At least one: application |
| A paper has at least one keyword | Yes, by the application |
| A paper has at least one version | Yes, by the application (a new paper needs a first version; the last version cannot be deleted) |
| A track coordinator and a session chair belong to the conference's reviewer pool | Yes, by the database (composite foreign keys to `conference_reviewer`) |
| Track names are unique within a conference | Yes, by the database (assumption, not in the specification) |
| A conference has at least one host, track and pool reviewer | No. Conferences are read-only seed data, and the seed satisfies the rule |
| Reviews and submissions respect the conference deadlines | No. Not enforced, but the seed satisfies it |

## Design assumptions

- The design follows the reference schema in Appendix A, used instead of an individual
  Assignment 1 design, so there are no further material changes to explain.
- A user is a superclass with overlapping, total specialization into author and reviewer. Each
  subclass shares the primary key of `app_user`.
- `paper_version` is a weak entity identified by (paper_id, version_no). Gaps are allowed, and the
  highest number is the current version. New versions get an upload timestamp of `now()` unless the
  user enters one. File locations are stored as text paths; no files are uploaded.
- Names in query results are shown as `given_name || ' ' || surname`.
- City matching for tasks 3.2 and 4.2 uses the exact value `'Astana'`.
- Task 6.3 counts papers and averages reviews in two separate subqueries. Papers with several reviews
  therefore do not inflate the paper counts, and each review is counted once in the average.
- Task 6.4 computes the average over all reviewers, including those with zero reviews (18 reviews / 8
  reviewers = 2.25).

## Sample data summary

The seed has 13 users: author-only users (Amina, Timur, Maria, Li, Ahmed), reviewer-only users
(Dana, Yerlan, Saule, John, Elena), and users with both roles (Arman, Aigerim, Daniyar). It also has
3 conferences (Astana, Almaty, Tashkent), 6 tracks, 5 sessions, 13 papers covering all five
statuses, 18 versions and 18 reviews.

Special cases included in the data:

- an empty track (track 3), and a conference with no papers (SRNET, conference 3)
- a reviewer with no reviews (Saule Omarova)
- review counts that vary from 0 to 5
- an empty session in Astana (session 3) and an empty session elsewhere (session 5)
- accepted papers with a session (1, 2, 3, 8) and without one (4, 12)
- two withdrawn papers with Amina Aminova as corresponding author (7, 11), and one withdrawn paper
  where she is only a co-author (13)
