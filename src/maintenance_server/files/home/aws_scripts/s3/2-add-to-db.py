import os
import sys
import json
import sqlite3
import csv
import argparse
import datetime


class Add:
    def __init__(self, files):
            self.files = files
            
            self.db_file = "s3.db"
            # if os.path.isfile(self.db_file):
            #     os.remove(self.db_file)
            self.db = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
            self.db_exec("""
            CREATE TABLE IF NOT EXISTS files(
                filename TEXT,
                filekey TEXT,
                bucket TEXT,
                size INT,
                modified TIMESTAMP,
                account TEXT,
                prefix TEXT,
                PRIMARY KEY (filename, filekey)
            )
            """)
            self.db_exec("""
            CREATE TABLE IF NOT EXISTS textfile(
                filename TEXT,
                date_recorded TIMESTAMP
            )
            """)
            self.db_exec("CREATE INDEX IF NOT EXISTS idx_files_file ON files(filekey)")
            self.db_exec("CREATE INDEX IF NOT EXISTS idx_files_bucket ON files(bucket)")
            self.db_exec("CREATE INDEX IF NOT EXISTS idx_files_prefix ON files(prefix)")
            self.db.commit()

    def add_csv(self, _file):
        _filedate = None
        try:
            _filedate = datetime.datetime.strptime(_file, "s3_%Y-%m-%d-%H%M_inventory.csv")
        except ValueError as e:
            return False
        sql    = "SELECT count(*) FROM textfile WHERE filename = ?"
        values = (_file,)
        count = self.get_scalar(sql, values)
        if not count:
            sql    = "INSERT INTO textfile (filename, date_recorded) VALUES (?, ?)"
            values = (_file, _filedate)
            self.db_exec(sql, values)
            self.db.commit()

    def add_key(self, filename, filekey, bucket, size, modified, account):
        if account == "Account":
            return
        sql = "SELECT count(*) FROM files WHERE filename = ? AND filekey = ?"
        values = (filename, filekey)
        count = self.get_scalar(sql, values)
        if count:
            return
        sql = """
        INSERT INTO
            files (
                filename,
                filekey,
                bucket,
                size,
                modified,
                account,
                prefix
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        prefix = filekey.split("/")[0]
        values = (filename, filekey, bucket, size, modified, account, prefix)
        self.db_exec(sql, values)

    def go(self):
        # Iterate over the files
        for _file in self.files:
            time_start = datetime.datetime.now()
            print(f"Processing {_file}...", end="")
            sys.stdout.flush()
            if self.add_csv(_file) == False:
                print(f"Skipping {_file}")
                continue

            f_in = open(_file, "r")
            reader = csv.reader(f_in)
            count = 0
            for row in reader:
                if not count % 100000:
                    print(f"{count:,}")
                    self.db.commit()
                count += 1
                account, bucket, key, size, modified = row
                self.add_key(_file, key, bucket, size, modified, account)
                # if row[0] == "Account" and row[1] == "Bucket" and row[2] == "Key" and row[3] == "Size" and row[4] == "Modified":
                #     continue
                # sql = "INSERT INTO files (filename, account, bucket, key, size, modified) VALUES (?, ?, ?, ?, ?, ?)"
                # values = 
                # self.db_exec("INSERT INTO files (filename, account, bucket, key, size_old, modified, size_new) VALUES (?, ?, ?, ?, ?, ?)", row)
            self.db.commit()
            time_end = datetime.datetime.now()
            time_diff = time_end - time_start
            secs = count//time_diff.seconds if time_diff.seconds > 0 else count
            print(f"Done. ({count:,} - {secs:,}/sec)")

    def file_exists(self, key):
        sql = "SELECT size_old FROM files WHERE file = ?"
        values = (key,)
        data = self.get_scalar(sql, values)
        if data:
            return data
        return -1

    def get_rows(self, sql, values=None):
        cur = self.db.cursor()
        if values:
            cur.execute(sql, values)
        else:
            cur.execute(sql)
        return cur.fetchall()
    
    def get_row(self, sql, values=None):
        return self.get_rows(sql, values)[0]
    
    def get_scalar(self, sql, values=None):
        return self.get_row(sql, values)[0]
    
    def db_exec(self, sql, values=None):
        self.get_rows(sql, values)
        

def main():
    files = sys.argv[1:]
    # parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     "-o",
    #     "--old",
    #     help="Old file to compare",
    #     required=True
    # )
    # parser.add_argument(
    #     "-n",
    #     "--new",
    #     help="New file to compare"
    # )
    # args = parser.parse_args()

    _add = Add(files=files)
    _add.go()


if __name__ == "__main__":
    main()
