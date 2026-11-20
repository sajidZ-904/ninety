import sys
import os
import json
import argparse

# Ensure project root is in python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.seeder import seed_database
from backend.app.routers.report import generate_rules_report

REPORT_DB_PATH = os.path.join(PROJECT_ROOT, "rules_report.db")


def _remove_sqlite_files(path: str) -> None:
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(path + suffix)
        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Generate Ninety EOS rules report.")
    parser.add_argument("now", nargs="?", default=None, help="Optional APP_NOW ISO 8601 UTC timestamp")
    parser.add_argument("-o", "--output", default=None, help="Optional output file path")
    args = parser.parse_args()

    # The report is always computed on a freshly seeded database, so test runs
    # or manual edits can never leak into the committed output.
    _remove_sqlite_files(REPORT_DB_PATH)
    engine = create_engine(f"sqlite:///{REPORT_DB_PATH}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        seed_database(db=db)
        report_data = generate_rules_report(db, custom_now_str=args.now)
        json_str = json.dumps(report_data, indent=2)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_str)
        else:
            sys.stdout.buffer.write(json_str.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
    finally:
        db.close()
        engine.dispose()
        _remove_sqlite_files(REPORT_DB_PATH)


if __name__ == "__main__":
    main()
