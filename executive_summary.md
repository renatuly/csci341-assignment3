# CSCI 341 Assignment 3: Executive Summary

**Members:** <Name Surname> (<Student ID>)

**Contributions:** <who did what, e.g. schema and seed data, Part 2 queries, web app, deployment, video>

**Completed work**
- Part 1: PostgreSQL schema with every required PK, FK, NOT NULL, UNIQUE and CHECK constraint;
  composite FKs for the coordinator and chair reviewer-pool rule; seed data covering every required
  case (13 users, 3 conferences, 13 papers, 18 versions, 18 reviews).
- Part 2: `part2_queries.py` runs tasks 1–8 through SQLAlchemy `text()` with bound parameters. It
  prints each SQL statement and its result, and it shows before/after rows for updates and deletes
  and then rolls them back.
- Part 3: Flask app with CRUD for users (author and reviewer profiles), papers (authors, keywords,
  versions), reviews and sessions. Each change runs in one transaction. Self-reviews and invalid
  session assignments are rejected with clear messages. Deployed at https://csci341-conference-dgkd.onrender.com with a persistent
  PostgreSQL database.

**Incomplete or nonworking requirements:** None known. <update if anything changes>

**Links:** video <VIDEO URL> · application https://csci341-conference-dgkd.onrender.com
