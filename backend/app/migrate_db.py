"""
Database schema migration / synchronization utility for SQLite and PostgreSQL.
Ensures that all columns and tables defined in SQLAlchemy models exist in the database
without dropping tables or losing existing data.
"""

import os
import sqlite3
import sys
from pathlib import Path
from sqlalchemy import text
from .models import Base
from .database import engine, DEFAULT_DB_PATH


def sync_sqlite_database(db_file: Path | str):
    db_path = Path(db_file)
    if not db_path.exists():
        print(f"Database file {db_path} does not exist, creating with Base.metadata.create_all.")
        return

    print(f"Synchronizing schema for {db_path}...")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    type_map = {
        "BOOLEAN": "BOOLEAN DEFAULT 0",
        "INTEGER": "INTEGER",
        "VARCHAR": "VARCHAR",
        "TEXT": "TEXT",
        "DATETIME": "TIMESTAMP",
        "FLOAT": "FLOAT",
    }

    added_columns = 0
    added_tables = 0

    # Ensure tables exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cur.fetchall()}

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            print(f"Creating missing table: {table_name}")
            table.create(bind=engine, checkfirst=True)
            existing_tables.add(table_name)
            added_tables += 1
            continue

        cur.execute(f"PRAGMA table_info({table_name})")
        existing_cols = {row[1]: row for row in cur.fetchall()}

        for col in table.columns:
            if col.name not in existing_cols:
                col_type_str = str(col.type)
                sqlite_type = "TEXT"
                for prefix, mapped in type_map.items():
                    if prefix in col_type_str.upper():
                        sqlite_type = mapped
                        break

                default_clause = ""
                if col.default is not None:
                    arg = col.default.arg
                    if isinstance(arg, bool):
                        default_clause = f" DEFAULT {1 if arg else 0}"
                    elif isinstance(arg, (int, float)):
                        default_clause = f" DEFAULT {arg}"
                    elif isinstance(arg, str):
                        default_clause = f" DEFAULT '{arg}'"

                sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {sqlite_type}{default_clause}"
                print(f"  Adding column: {table_name}.{col.name} ({sqlite_type}{default_clause})")
                cur.execute(sql)
                added_columns += 1

    conn.commit()
    conn.close()
    print(f"Sync complete for {db_path}: {added_tables} tables created, {added_columns} columns added.")


def run_migrations():
    # 1. Main backend database
    if DEFAULT_DB_PATH.exists():
        sync_sqlite_database(DEFAULT_DB_PATH)

    # 2. Backup database if present
    backup_path = DEFAULT_DB_PATH.parent / "guardslm.db.backup"
    if backup_path.exists():
        sync_sqlite_database(backup_path)


if __name__ == "__main__":
    run_migrations()
