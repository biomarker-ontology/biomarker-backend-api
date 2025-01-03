"""Peak into the sqlite log database.

usage: parser.py [-h] server table limit

positional arguments:
  server      prd/beta/tst/dev
  table       api/frontend
  limit

options:
  -h, --help  show this help message and exit
"""

import sqlite3
import sys
import json
import os


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tutils.parser import standard_parser, parse_server
from tutils.config import get_config


def main():
    parser, server_list = standard_parser()
    parser.add_argument("table", help="api/frontend")
    parser.add_argument("limit", type=int, default=5)
    options = parser.parse_args()

    server = parse_server(parser=parser, server=options.server, server_list=server_list)
    table = options.table.lower().strip()
    limit = options.limit
    if table not in {"api", "frontend"}:
        print("Invalid table.")
        parser.print_help()
        sys.exit(1)

    config_obj = get_config()
    data_root_path = config_obj["data_path"]
    sqlite_db_path = os.path.join(data_root_path, "log_db", server, "api_logs.db")

    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]

    # get latest rows
    cursor.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT {limit}")
    rows = cursor.fetchall()

    for idx, row in enumerate(rows):
        print("-" * 40 + f" Row: {idx} " + "-" * 40)
        row_dict = dict(zip(columns, row))

        # Try to parse JSON fields if they exist
        for field in ["request", "data"]:
            if field in row_dict and row_dict[field]:
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except (json.JSONDecodeError, TypeError):
                    pass

        print(json.dumps(row_dict, indent=2, default=str))

    conn.close()


if __name__ == "__main__":
    main()
