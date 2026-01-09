# DO NOT USE THIS FOR REFERENCE!

import sqlite3
import json

conn = sqlite3.connect("docker-dorker.db")
cur = conn.cursor()
cur.execute("SELECT entries_json FROM layer_peek_cache")

for row in cur.fetchall():
    print(json.dumps(json.loads(row[0]), indent=2))

conn.close()

# Example output: 
# ...
#  {
#    "name": "Files/Program Files/Microsoft SQL Server/MSSQL14.SQLEXPRESS/MSSQL/DATA/Kentico12.mdf",
#    "size": 142606336,
#    "typeflag": "0",
#    "is_dir": false,
#    "mode": "----------",
#    "uid": 0,
#    "gid": 0,
#    "mtime": "2020-03-24 21:42",
#    "linkname": "",
#    "is_symlink": false
#  }
#]