import sqlite3
import json
import sys


def main():
    bucket = sys.argv[1]
    prefix = sys.argv[2]

    db = sqlite3.connect("s3.db", detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    sql = "SELECT size FROM files WHERE bucket = ? AND file LIKE ?"
    values = (bucket, f"{prefix}%")

    cur = db.cursor()
    cur.execute(sql, values)
    print("Got results")
    for row in cur:
        print("Results:")
        print(row)




if __name__ == "__main__":
    main()

