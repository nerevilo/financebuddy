"""Save a Teller enrollment (access_token + institution) into SQLite."""
from __future__ import annotations

import argparse

from . import db


def link(institution_id: str, name: str, access_token: str) -> None:
    db.init()
    with db.cursor() as conn:
        conn.execute(
            """
            INSERT INTO institutions (id, name, access_token)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                access_token = excluded.access_token
            """,
            (institution_id, name, access_token),
        )
    print(f"Linked {name} ({institution_id})")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--id", required=True, help="Teller enrollment id")
    p.add_argument("--name", required=True, help="Institution display name")
    p.add_argument("--token", required=True, help="Teller access_token")
    args = p.parse_args()
    link(args.id, args.name, args.token)


if __name__ == "__main__":
    main()
