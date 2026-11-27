"""CSCI 341 Assignment 3 -- Part 3: web application (Flask + SQLAlchemy Core).

CRUD for users (with author/reviewer profiles), papers (with authorship, keywords
and versions), reviews and sessions. Every change that touches several tables runs
in one transaction (engine.begin()); any failure rolls the whole change back.
"""
import os

from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from db import engine, is_initialised, reset_database

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
AUTHOR_SLOTS = 6


class ValidationError(Exception):
    """A business-rule violation detected by the application."""


def db_error_message(exc: DBAPIError) -> str:
    diag = getattr(exc.orig, "diag", None)
    if diag is not None and diag.message_primary:
        msg = diag.message_primary
        if diag.constraint_name:
            msg += f" [constraint: {diag.constraint_name}]"
        if diag.message_detail:
            msg += f" -- {diag.message_detail}"
        return msg
    return str(exc.orig)


def q(conn, sql, **params):
    return conn.execute(text(sql), params)


def rows(sql, **params):
    with engine.connect() as conn:
        return q(conn, sql, **params).mappings().all()


def one(sql, **params):
    with engine.connect() as conn:
        return q(conn, sql, **params).mappings().first()


def lines(value: str) -> list[str]:
    """Split a textarea into distinct non-empty lines (one label per line)."""
    seen = []
    for part in (value or "").replace(",", "\n").splitlines():
        part = part.strip()
        if part and part not in seen:
            seen.append(part)
    return seen


def int_or_none(value):
    value = (value or "").strip()
    return int(value) if value else None


def save(action, success_message):
    """Run action(conn) in one transaction; report validation or database errors."""
    try:
        with engine.begin() as conn:
            result = action(conn)
        flash(success_message, "ok")
        return True, result
    except ValidationError as exc:
        flash(f"Rejected: {exc}", "error")
    except DBAPIError as exc:
        flash(f"Database rejected the change: {db_error_message(exc)}", "error")
    except ValueError as exc:
        flash(f"Invalid input: {exc}", "error")
    return False, None


# ===================================================================== application checks
def check_self_review(conn, paper_id, reviewer_id):
    """Application check 1 (saving a review): a reviewer may not review their own paper."""
    if q(conn, "SELECT 1 FROM paper_author WHERE paper_id = :p AND author_id = :r",
         p=paper_id, r=reviewer_id).first():
        raise ValidationError(
            f"user {reviewer_id} is an author of paper {paper_id} and cannot review it (self-review).")


def check_authors_have_not_reviewed(conn, paper_id, author_ids):
    """Application check 1 (changing authors): a new author must not already review the paper."""
    clash = q(conn, """SELECT reviewer_id FROM review
                       WHERE paper_id = :p AND reviewer_id = ANY(:ids)""",
              p=paper_id, ids=list(author_ids)).scalars().all()
    if clash:
        raise ValidationError(
            f"user(s) {clash} already reviewed paper {paper_id}; they cannot become its authors (self-review).")


def check_session_assignment(conn, track_id, status, session_id):
    """Application check 2: a scheduled paper must be accepted and its track and
    session must belong to the same conference."""
    if session_id is None:
        return
    if status != "accepted":
        raise ValidationError(
            f"only accepted papers can be assigned to a session (status is '{status}'). "
            "Unassign the session first or keep the status 'accepted'.")
    row = q(conn, """SELECT t.conference_id AS track_conf, s.conference_id AS session_conf
                     FROM track t, conference_session s
                     WHERE t.track_id = :t AND s.session_id = :s""",
            t=track_id, s=session_id).mappings().first()
    if row is None:
        raise ValidationError("unknown track or session.")
    if row["track_conf"] != row["session_conf"]:
        raise ValidationError(
            f"session {session_id} belongs to conference {row['session_conf']} but the paper's "
            f"track belongs to conference {row['track_conf']}.")


def check_session_conference_change(conn, session_id, new_conference_id):
    """Application check 2 (changing a session's conference)."""
    bad = q(conn, """SELECT p.paper_id FROM paper p JOIN track t ON t.track_id = p.track_id
                     WHERE p.session_id = :s AND t.conference_id <> :c""",
            s=session_id, c=new_conference_id).scalars().all()
    if bad:
        raise ValidationError(
            f"papers {bad} are assigned to this session and belong to another conference; "
            "unassign them before moving the session.")


# ===================================================================== lookups
def conferences():
    return rows("SELECT conference_id, acronym, city FROM conference ORDER BY conference_id")


def reviewers():
    return rows("""SELECT r.reviewer_id AS id, u.given_name || ' ' || u.surname AS name
                   FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id ORDER BY name""")


def authors():
    return rows("""SELECT a.author_id AS id, u.given_name || ' ' || u.surname AS name
                   FROM author a JOIN app_user u ON u.user_id = a.author_id ORDER BY name""")


def tracks():
    return rows("""SELECT t.track_id, t.name, c.acronym, t.conference_id
                   FROM track t JOIN conference c ON c.conference_id = t.conference_id
                   ORDER BY t.track_id""")


def sessions_lookup():
    return rows("""SELECT s.session_id, s.title, c.acronym, s.conference_id
                   FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
                   ORDER BY s.session_id""")


def papers_lookup():
    return rows("SELECT paper_id, title FROM paper ORDER BY paper_id")


# ===================================================================== home
@app.route("/")
def home():
    counts = one("""SELECT (SELECT COUNT(*) FROM app_user) AS users,
                           (SELECT COUNT(*) FROM paper) AS papers,
                           (SELECT COUNT(*) FROM review) AS reviews,
                           (SELECT COUNT(*) FROM conference_session) AS sessions,
                           (SELECT COUNT(*) FROM conference) AS conferences""")
    schedule = rows("""SELECT * FROM accepted_paper_schedule
                       ORDER BY conference_id, session_date, start_time, session_id, paper_id""")
    confs = rows("""SELECT c.*, (SELECT string_agg(host_name, '; ' ORDER BY host_name)
                                 FROM conference_host h WHERE h.conference_id = c.conference_id) AS hosts
                    FROM conference c ORDER BY conference_id""")
    return render_template("home.html", counts=counts, schedule=schedule, confs=confs,
                           tracks=rows("""SELECT t.*, u.given_name || ' ' || u.surname AS coordinator
                                          FROM track t JOIN app_user u ON u.user_id = t.coordinator_id
                                          ORDER BY track_id"""))


# ===================================================================== users
def user_form_data(form):
    return {
        "given_name": form.get("given_name", "").strip(),
        "surname": form.get("surname", "").strip(),
        "email": form.get("email", "").strip(),
        "affiliation": form.get("affiliation", "").strip(),
        "country": form.get("country", "").strip(),
        "phone_number": form.get("phone_number", "").strip(),
        "is_author": form.get("is_author") == "on",
        "orcid": form.get("orcid", "").strip() or None,
        "research_areas": "\n".join(lines(form.get("research_areas"))),
        "is_reviewer": form.get("is_reviewer") == "on",
        "years_experience": form.get("years_experience", "").strip(),
        "expertise": "\n".join(lines(form.get("expertise"))),
        "pools": [int(x) for x in form.getlist("pools")],
    }


def load_user(user_id):
    u = one("SELECT * FROM app_user WHERE user_id = :id", id=user_id)
    if u is None:
        return None
    d = dict(u)
    a = one("SELECT orcid FROM author WHERE author_id = :id", id=user_id)
    r = one("SELECT years_experience FROM reviewer WHERE reviewer_id = :id", id=user_id)
    d["is_author"] = a is not None
    d["orcid"] = a["orcid"] if a else None
    d["research_areas"] = "\n".join(x["area_label"] for x in rows(
        "SELECT area_label FROM author_research_area WHERE author_id = :id ORDER BY 1", id=user_id))
    d["is_reviewer"] = r is not None
    d["years_experience"] = r["years_experience"] if r else ""
    d["expertise"] = "\n".join(x["area_label"] for x in rows(
        "SELECT area_label FROM reviewer_expertise WHERE reviewer_id = :id ORDER BY 1", id=user_id))
    d["pools"] = [x["conference_id"] for x in rows(
        "SELECT conference_id FROM conference_reviewer WHERE reviewer_id = :id", id=user_id)]
    return d


def save_user(conn, d, user_id=None):
    if not (d["is_author"] or d["is_reviewer"]):
        raise ValidationError("every user must be an author, a reviewer, or both.")
    for f in ("given_name", "surname", "email", "affiliation", "country", "phone_number"):
        if not d[f]:
            raise ValidationError(f"{f.replace('_', ' ')} is required.")
    base = {k: d[k] for k in ("given_name", "surname", "email", "affiliation", "country", "phone_number")}
    if user_id is None:
        user_id = q(conn, """INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
                             VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
                             RETURNING user_id""", **base).scalar()
    else:
        q(conn, """UPDATE app_user SET given_name = :given_name, surname = :surname, email = :email,
                   affiliation = :affiliation, country = :country, phone_number = :phone_number
                   WHERE user_id = :id""", id=user_id, **base)

    # author profile
    if d["is_author"]:
        areas = lines(d["research_areas"])
        if not areas:
            raise ValidationError("an author needs at least one research-area label.")
        q(conn, """INSERT INTO author (author_id, orcid) VALUES (:id, :orcid)
                   ON CONFLICT (author_id) DO UPDATE SET orcid = EXCLUDED.orcid""",
          id=user_id, orcid=d["orcid"])
        q(conn, "DELETE FROM author_research_area WHERE author_id = :id", id=user_id)
        for a in areas:
            q(conn, "INSERT INTO author_research_area VALUES (:id, :a)", id=user_id, a=a)
    else:
        q(conn, "DELETE FROM author WHERE author_id = :id", id=user_id)  # fails if they author papers

    # reviewer profile
    if d["is_reviewer"]:
        exp = lines(d["expertise"])
        if not exp:
            raise ValidationError("a reviewer needs at least one expertise-area label.")
        years = int(d["years_experience"]) if str(d["years_experience"]).strip() else None
        if years is None:
            raise ValidationError("years of reviewing experience is required for a reviewer.")
        q(conn, """INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :y)
                   ON CONFLICT (reviewer_id) DO UPDATE SET years_experience = EXCLUDED.years_experience""",
          id=user_id, y=years)
        q(conn, "DELETE FROM reviewer_expertise WHERE reviewer_id = :id", id=user_id)
        for a in exp:
            q(conn, "INSERT INTO reviewer_expertise VALUES (:id, :a)", id=user_id, a=a)
        q(conn, """DELETE FROM conference_reviewer
                   WHERE reviewer_id = :id AND NOT (conference_id = ANY(:pools))""",
          id=user_id, pools=d["pools"])
        for c in d["pools"]:
            q(conn, """INSERT INTO conference_reviewer VALUES (:c, :id)
                       ON CONFLICT DO NOTHING""", c=c, id=user_id)
    else:
        q(conn, "DELETE FROM reviewer WHERE reviewer_id = :id", id=user_id)  # fails if referenced
    return user_id


@app.route("/users")
def users_list():
    data = rows("""SELECT u.*, a.author_id IS NOT NULL AS is_author, r.reviewer_id IS NOT NULL AS is_reviewer,
                          r.years_experience
                   FROM app_user u
                   LEFT JOIN author a ON a.author_id = u.user_id
                   LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
                   ORDER BY u.user_id""")
    return render_template("users.html", users=data)


@app.route("/users/new", methods=["GET", "POST"])
def user_new():
    if request.method == "POST":
        d = user_form_data(request.form)
        ok, uid = save(lambda c: save_user(c, d), "User created.")
        if ok:
            return redirect(url_for("user_detail", user_id=uid))
    else:
        d = {"is_author": True, "is_reviewer": False, "pools": []}
    return render_template("user_form.html", u=d, confs=conferences(), user_id=None)


@app.route("/users/<int:user_id>")
def user_detail(user_id):
    u = load_user(user_id)
    if u is None:
        flash("User not found.", "error")
        return redirect(url_for("users_list"))
    papers = rows("""SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
                     FROM paper_author pa JOIN paper p ON p.paper_id = pa.paper_id
                     WHERE pa.author_id = :id ORDER BY p.paper_id""", id=user_id)
    reviews = rows("""SELECT rv.review_id, rv.paper_id, p.title, rv.overall_score, rv.recommendation
                      FROM review rv JOIN paper p ON p.paper_id = rv.paper_id
                      WHERE rv.reviewer_id = :id ORDER BY rv.review_id""", id=user_id)
    pool_names = [c["acronym"] for c in conferences() if c["conference_id"] in u["pools"]]
    return render_template("user_detail.html", u=u, user_id=user_id, papers=papers,
                           reviews=reviews, pool_names=pool_names)


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    if request.method == "POST":
        d = user_form_data(request.form)
        ok, _ = save(lambda c: save_user(c, d, user_id), "User updated.")
        if ok:
            return redirect(url_for("user_detail", user_id=user_id))
    else:
        d = load_user(user_id)
        if d is None:
            flash("User not found.", "error")
            return redirect(url_for("users_list"))
    return render_template("user_form.html", u=d, confs=conferences(), user_id=user_id)


@app.post("/users/<int:user_id>/delete")
def user_delete(user_id):
    ok, _ = save(lambda c: q(c, "DELETE FROM app_user WHERE user_id = :id", id=user_id),
                 f"User {user_id} deleted.")
    return redirect(url_for("users_list") if ok else url_for("user_detail", user_id=user_id))


# ===================================================================== papers
def paper_form_data(form):
    authors_ = []
    for i in range(AUTHOR_SLOTS):
        aid = int_or_none(form.get(f"author_{i}"))
        pos = int_or_none(form.get(f"position_{i}"))
        authors_.append({"author_id": aid, "position": pos})
    corr = int_or_none(form.get("corresponding"))
    return {
        "track_id": int_or_none(form.get("track_id")),
        "title": form.get("title", "").strip(),
        "abstract": form.get("abstract", "").strip(),
        "submission_date": form.get("submission_date", "").strip(),
        "status": form.get("status", "submitted"),
        "session_id": int_or_none(form.get("session_id")),
        "keywords": "\n".join(lines(form.get("keywords"))),
        "authors": authors_,
        "corresponding": corr,
        "file_location": form.get("file_location", "").strip(),
        "change_note": form.get("change_note", "").strip() or None,
    }


def load_paper(paper_id):
    p = one("SELECT * FROM paper WHERE paper_id = :id", id=paper_id)
    if p is None:
        return None
    d = dict(p)
    d["submission_date"] = p["submission_date"].isoformat()
    d["keywords"] = "\n".join(r["keyword"] for r in rows(
        "SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword", id=paper_id))
    pa = rows("""SELECT author_id, author_position, is_corresponding FROM paper_author
                 WHERE paper_id = :id ORDER BY author_position""", id=paper_id)
    d["authors"] = [{"author_id": r["author_id"], "position": r["author_position"]} for r in pa]
    d["authors"] += [{"author_id": None, "position": None}] * (AUTHOR_SLOTS - len(d["authors"]))
    d["corresponding"] = next((i for i, r in enumerate(pa) if r["is_corresponding"]), None)
    return d


def save_paper(conn, d, paper_id=None):
    for f in ("title", "abstract", "submission_date"):
        if not d[f]:
            raise ValidationError(f"{f.replace('_', ' ')} is required.")
    if d["track_id"] is None:
        raise ValidationError("a paper must be submitted to a track.")
    if d["status"] not in STATUSES:
        raise ValidationError("invalid status.")
    chosen = [(i, a) for i, a in enumerate(d["authors"]) if a["author_id"] is not None]
    if not chosen:
        raise ValidationError("a paper needs at least one author.")
    if any(a["position"] is None for _, a in chosen):
        raise ValidationError("every selected author needs a position.")
    if d["corresponding"] not in [i for i, _ in chosen]:
        raise ValidationError("exactly one of the selected authors must be the corresponding author.")
    ids = [a["author_id"] for _, a in chosen]
    if len(set(ids)) != len(ids):
        raise ValidationError("the same author is listed twice.")
    keywords = lines(d["keywords"])
    if not keywords:
        raise ValidationError("a paper needs at least one keyword.")

    check_session_assignment(conn, d["track_id"], d["status"], d["session_id"])

    cols = {k: d[k] for k in ("track_id", "title", "abstract", "submission_date", "status", "session_id")}
    if paper_id is None:
        if not d["file_location"]:
            raise ValidationError("a new paper needs its first version (file location).")
        paper_id = q(conn, """INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
                              VALUES (:track_id, :title, :abstract, :submission_date, :status, :session_id)
                              RETURNING paper_id""", **cols).scalar()
        q(conn, """INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                   VALUES (:p, 1, :f, now(), :n)""", p=paper_id, f=d["file_location"], n=d["change_note"])
    else:
        check_authors_have_not_reviewed(conn, paper_id, ids)
        q(conn, """UPDATE paper SET track_id = :track_id, title = :title, abstract = :abstract,
                   submission_date = :submission_date, status = :status, session_id = :session_id
                   WHERE paper_id = :id""", id=paper_id, **cols)

    q(conn, "DELETE FROM paper_author WHERE paper_id = :p", p=paper_id)
    for i, a in chosen:
        q(conn, """INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
                   VALUES (:p, :a, :pos, :c)""",
          p=paper_id, a=a["author_id"], pos=a["position"], c=(i == d["corresponding"]))
    q(conn, "DELETE FROM paper_keyword WHERE paper_id = :p", p=paper_id)
    for k in keywords:
        q(conn, "INSERT INTO paper_keyword VALUES (:p, :k)", p=paper_id, k=k)
    return paper_id


def paper_form(d, paper_id):
    return render_template("paper_form.html", p=d, paper_id=paper_id, tracks=tracks(),
                           sessions=sessions_lookup(), authors=authors(), statuses=STATUSES,
                           slots=AUTHOR_SLOTS)


@app.route("/papers")
def papers_list():
    data = rows("""SELECT p.paper_id, p.title, p.status, t.name AS track, c.acronym, p.session_id,
                          (SELECT MAX(version_no) FROM paper_version v WHERE v.paper_id = p.paper_id) AS current_version,
                          (SELECT COUNT(*) FROM review r WHERE r.paper_id = p.paper_id) AS reviews
                   FROM paper p JOIN track t ON t.track_id = p.track_id
                   JOIN conference c ON c.conference_id = t.conference_id
                   ORDER BY p.paper_id""")
    return render_template("papers.html", papers=data)


@app.route("/papers/new", methods=["GET", "POST"])
def paper_new():
    if request.method == "POST":
        d = paper_form_data(request.form)
        ok, pid = save(lambda c: save_paper(c, d), "Paper created.")
        if ok:
            return redirect(url_for("paper_detail", paper_id=pid))
    else:
        d = {"status": "submitted", "authors": [{"author_id": None, "position": None}] * AUTHOR_SLOTS,
             "corresponding": 0}
    return paper_form(d, None)


@app.route("/papers/<int:paper_id>")
def paper_detail(paper_id):
    p = one("""SELECT p.*, t.name AS track, c.acronym, c.conference_id, s.title AS session_title
               FROM paper p JOIN track t ON t.track_id = p.track_id
               JOIN conference c ON c.conference_id = t.conference_id
               LEFT JOIN conference_session s ON s.session_id = p.session_id
               WHERE p.paper_id = :id""", id=paper_id)
    if p is None:
        flash("Paper not found.", "error")
        return redirect(url_for("papers_list"))
    return render_template(
        "paper_detail.html", p=p,
        authors=rows("""SELECT pa.*, u.given_name || ' ' || u.surname AS name, u.email
                        FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                        WHERE pa.paper_id = :id ORDER BY author_position""", id=paper_id),
        keywords=rows("SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY 1", id=paper_id),
        versions=rows("SELECT * FROM paper_version WHERE paper_id = :id ORDER BY version_no DESC", id=paper_id),
        reviews=rows("""SELECT rv.*, u.given_name || ' ' || u.surname AS reviewer
                        FROM review rv JOIN app_user u ON u.user_id = rv.reviewer_id
                        WHERE rv.paper_id = :id ORDER BY review_id""", id=paper_id),
        next_version=(one("SELECT COALESCE(MAX(version_no), 0) + 1 AS n FROM paper_version WHERE paper_id = :id",
                          id=paper_id)["n"]))


@app.route("/papers/<int:paper_id>/edit", methods=["GET", "POST"])
def paper_edit(paper_id):
    if request.method == "POST":
        d = paper_form_data(request.form)
        ok, _ = save(lambda c: save_paper(c, d, paper_id), "Paper updated.")
        if ok:
            return redirect(url_for("paper_detail", paper_id=paper_id))
    else:
        d = load_paper(paper_id)
        if d is None:
            flash("Paper not found.", "error")
            return redirect(url_for("papers_list"))
    return paper_form(d, paper_id)


@app.post("/papers/<int:paper_id>/delete")
def paper_delete(paper_id):
    ok, _ = save(lambda c: q(c, "DELETE FROM paper WHERE paper_id = :id", id=paper_id),
                 f"Paper {paper_id} deleted with its authorship, keywords, versions and reviews.")
    return redirect(url_for("papers_list") if ok else url_for("paper_detail", paper_id=paper_id))


# ---------------------------------------------------------------- paper versions
@app.post("/papers/<int:paper_id>/versions")
def version_add(paper_id):
    f = request.form

    def action(conn):
        if not f.get("file_location", "").strip():
            raise ValidationError("file location is required.")
        q(conn, """INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                   VALUES (:p, :v, :f, COALESCE(CAST(NULLIF(:u, '') AS TIMESTAMP), now()), :n)""",
          p=paper_id, v=int(f["version_no"]), f=f["file_location"].strip(),
          u=f.get("uploaded_at", ""), n=f.get("change_note", "").strip() or None)

    save(action, "Version added.")
    return redirect(url_for("paper_detail", paper_id=paper_id))


@app.route("/papers/<int:paper_id>/versions/<int:version_no>/edit", methods=["GET", "POST"])
def version_edit(paper_id, version_no):
    v = one("SELECT * FROM paper_version WHERE paper_id = :p AND version_no = :v", p=paper_id, v=version_no)
    if v is None:
        flash("Version not found.", "error")
        return redirect(url_for("paper_detail", paper_id=paper_id))
    if request.method == "POST":
        f = request.form
        ok, _ = save(lambda c: q(c, """UPDATE paper_version SET file_location = :f,
                                       uploaded_at = CAST(:u AS TIMESTAMP), change_note = :n
                                       WHERE paper_id = :p AND version_no = :v""",
                                 f=f["file_location"].strip(), u=f["uploaded_at"],
                                 n=f.get("change_note", "").strip() or None, p=paper_id, v=version_no),
                     "Version updated.")
        if ok:
            return redirect(url_for("paper_detail", paper_id=paper_id))
    return render_template("version_form.html", v=v)


@app.post("/papers/<int:paper_id>/versions/<int:version_no>/delete")
def version_delete(paper_id, version_no):
    def action(conn):
        n = q(conn, "SELECT COUNT(*) FROM paper_version WHERE paper_id = :p", p=paper_id).scalar()
        if n <= 1:
            raise ValidationError("every paper must keep at least one version.")
        q(conn, "DELETE FROM paper_version WHERE paper_id = :p AND version_no = :v", p=paper_id, v=version_no)

    save(action, f"Version {version_no} deleted.")
    return redirect(url_for("paper_detail", paper_id=paper_id))


# ===================================================================== reviews
def review_form_data(form):
    return {
        "paper_id": int_or_none(form.get("paper_id")),
        "reviewer_id": int_or_none(form.get("reviewer_id")),
        "overall_score": int_or_none(form.get("overall_score")),
        "recommendation": form.get("recommendation", ""),
        "comments_for_authors": form.get("comments_for_authors", "").strip(),
        "confidential_comments": form.get("confidential_comments", "").strip() or None,
        "review_submission_date": form.get("review_submission_date", "").strip(),
    }


def save_review(conn, d, review_id=None):
    if d["paper_id"] is None or d["reviewer_id"] is None:
        raise ValidationError("paper and reviewer are required.")
    if not d["comments_for_authors"] or not d["review_submission_date"]:
        raise ValidationError("only completed reviews are stored: comments and submission date are required.")
    check_self_review(conn, d["paper_id"], d["reviewer_id"])
    if review_id is None:
        return q(conn, """INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                                              comments_for_authors, confidential_comments, review_submission_date)
                          VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation,
                                  :comments_for_authors, :confidential_comments, :review_submission_date)
                          RETURNING review_id""", **d).scalar()
    q(conn, """UPDATE review SET paper_id = :paper_id, reviewer_id = :reviewer_id,
               overall_score = :overall_score, recommendation = :recommendation,
               comments_for_authors = :comments_for_authors, confidential_comments = :confidential_comments,
               review_submission_date = :review_submission_date
               WHERE review_id = :id""", id=review_id, **d)
    return review_id


def review_form(d, review_id):
    return render_template("review_form.html", r=d, review_id=review_id,
                           papers=papers_lookup(), reviewers=reviewers())


@app.route("/reviews")
def reviews_list():
    data = rows("""SELECT rv.review_id, rv.paper_id, p.title, rv.reviewer_id,
                          u.given_name || ' ' || u.surname AS reviewer,
                          rv.overall_score, rv.recommendation, rv.review_submission_date
                   FROM review rv JOIN paper p ON p.paper_id = rv.paper_id
                   JOIN app_user u ON u.user_id = rv.reviewer_id ORDER BY rv.review_id""")
    return render_template("reviews.html", reviews=data)


@app.route("/reviews/new", methods=["GET", "POST"])
def review_new():
    if request.method == "POST":
        d = review_form_data(request.form)
        ok, _ = save(lambda c: save_review(c, d), "Review saved.")
        if ok:
            return redirect(url_for("reviews_list"))
    else:
        d = {"paper_id": request.args.get("paper_id", type=int), "overall_score": 3,
             "recommendation": "accept"}
    return review_form(d, None)


@app.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
def review_edit(review_id):
    if request.method == "POST":
        d = review_form_data(request.form)
        ok, _ = save(lambda c: save_review(c, d, review_id), "Review updated.")
        if ok:
            return redirect(url_for("reviews_list"))
    else:
        r = one("SELECT * FROM review WHERE review_id = :id", id=review_id)
        if r is None:
            flash("Review not found.", "error")
            return redirect(url_for("reviews_list"))
        d = dict(r)
        d["review_submission_date"] = r["review_submission_date"].isoformat()
    return review_form(d, review_id)


@app.post("/reviews/<int:review_id>/delete")
def review_delete(review_id):
    save(lambda c: q(c, "DELETE FROM review WHERE review_id = :id", id=review_id),
         f"Review {review_id} deleted.")
    return redirect(url_for("reviews_list"))


# ===================================================================== sessions
def session_form_data(form):
    return {
        "conference_id": int_or_none(form.get("conference_id")),
        "title": form.get("title", "").strip(),
        "session_date": form.get("session_date", "").strip(),
        "start_time": form.get("start_time", "").strip(),
        "end_time": form.get("end_time", "").strip(),
        "room_label": form.get("room_label", "").strip(),
        "chair_id": int_or_none(form.get("chair_id")),
    }


def save_session(conn, d, session_id=None):
    for k, v in d.items():
        if v in (None, ""):
            raise ValidationError(f"{k.replace('_', ' ')} is required.")
    if session_id is None:
        return q(conn, """INSERT INTO conference_session (conference_id, title, session_date, start_time,
                                                          end_time, room_label, chair_id)
                          VALUES (:conference_id, :title, :session_date, :start_time, :end_time,
                                  :room_label, :chair_id) RETURNING session_id""", **d).scalar()
    check_session_conference_change(conn, session_id, d["conference_id"])
    q(conn, """UPDATE conference_session SET conference_id = :conference_id, title = :title,
               session_date = :session_date, start_time = :start_time, end_time = :end_time,
               room_label = :room_label, chair_id = :chair_id WHERE session_id = :id""", id=session_id, **d)
    return session_id


def session_form(d, session_id):
    return render_template("session_form.html", s=d, session_id=session_id,
                           confs=conferences(), reviewers=reviewers())


@app.route("/sessions")
def sessions_list():
    data = rows("""SELECT s.*, c.acronym, u.given_name || ' ' || u.surname AS chair,
                          (SELECT string_agg(p.paper_id::text, ', ' ORDER BY p.paper_id)
                           FROM paper p WHERE p.session_id = s.session_id) AS papers
                   FROM conference_session s JOIN conference c ON c.conference_id = s.conference_id
                   JOIN app_user u ON u.user_id = s.chair_id ORDER BY s.session_id""")
    return render_template("sessions.html", sessions=data)


@app.route("/sessions/new", methods=["GET", "POST"])
def session_new():
    if request.method == "POST":
        d = session_form_data(request.form)
        ok, _ = save(lambda c: save_session(c, d), "Session created.")
        if ok:
            return redirect(url_for("sessions_list"))
    else:
        d = {}
    return session_form(d, None)


@app.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
def session_edit(session_id):
    if request.method == "POST":
        d = session_form_data(request.form)
        ok, _ = save(lambda c: save_session(c, d, session_id), "Session updated.")
        if ok:
            return redirect(url_for("sessions_list"))
    else:
        s = one("SELECT * FROM conference_session WHERE session_id = :id", id=session_id)
        if s is None:
            flash("Session not found.", "error")
            return redirect(url_for("sessions_list"))
        d = dict(s)
        d["session_date"] = s["session_date"].isoformat()
        d["start_time"] = s["start_time"].strftime("%H:%M")
        d["end_time"] = s["end_time"].strftime("%H:%M")
    return session_form(d, session_id)


@app.post("/sessions/<int:session_id>/delete")
def session_delete(session_id):
    save(lambda c: q(c, "DELETE FROM conference_session WHERE session_id = :id", id=session_id),
         f"Session {session_id} deleted (its papers were unassigned).")
    return redirect(url_for("sessions_list"))


# ===================================================================== startup
@app.cli.command("init-db")
def init_db_command():
    """flask --app app init-db : drop, recreate and seed the database."""
    reset_database()
    print("Database reset to the seed data.")


if os.environ.get("AUTO_INIT_DB") == "1":
    try:
        if not is_initialised():
            reset_database()
    except Exception as exc:  # pragma: no cover - logged on the host
        print(f"Automatic database initialisation failed: {exc}")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
