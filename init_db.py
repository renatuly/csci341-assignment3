"""Create the schema, load the seed data and create the view.

    python init_db.py           # only if the database is empty
    python init_db.py --reset   # drop everything and restore the original seed dataset
"""
import sys

from db import is_initialised, reset_database

if __name__ == "__main__":
    if "--reset" in sys.argv or not is_initialised():
        reset_database()
        print("Database created and seeded.")
    else:
        print("Database already initialised (use --reset to restore the seed data).")
