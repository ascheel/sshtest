import sqlite3
import sys
import os
import datetime
from dateutil.parser import parse
import csv


class Inventory:
    def __init__(self):
        self.root = "/home/scheel/git/tmp/s3"
        self.db_file = os.path.join(self.root, "s3_inventory.db")
        print("File: {}".format(self.db_file))
        self.db = sqlite3.connect(
            os.path.join(self.root, "s3_inventory.db"),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )

        self.__init_db()
    
    def __init_db(self):
        self.db_exec("CREATE TABLE IF NOT EXISTS files (file TEXT, bucket TEXT, size INT, modified TIMESTAMP)")
        self.db_exec("CREATE INDEX IF NOT EXISTS idx_files_file ON files(file)")
        self.db.commit()

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
        
    def add_to_db(self, _file=None):
        for _file in os.listdir(self.root):
            print("test: {}".format(repr(_file)))
            if not _file.endswith(".csv"):
                continue
            _fullfile = os.path.join(self.root, _file)
            print("Parsing {}".format(_fullfile))
            with open(_fullfile, "r") as f_in:
                f_in.readline() # Get rid of the header, we don't want it.
                reader = csv.reader(f_in)
                count = 0
                for row in reader:
                    count += 1
                    if not count % 100000:
                        print(count)
                        self.db.commit()
                    _bucket, _key, _size, _modified = row
                    _modified = parse(_modified)
                    _values = (_key, _bucket, _size, _modified)
                    _sql = "INSERT INTO files (file, bucket, size, modified) VALUES (?, ?, ?, ?)"
                    self.db_exec(_sql, _values)
                self.db.commit()

        # print("Input file: {}".format(_file))

        # _fullfile = os.path.join(self.root, _file)
        # print("Parsing {}".format(_fullfile))
        # with open(_fullfile, "r") as f_in:
        #     f_in.readline() # Get rid of the header, we don't want it.
        #     reader = csv.reader(f_in)
        #     count = 0
        #     for row in reader:
        #         count += 1
        #         if not count % 100000:
        #             print(count)
        #             self.db.commit()
        #         _bucket, _key, _size, _modified = row
        #         _sql = "SELECT count(*) FROM files WHERE bucket = ? AND file = ?"
        #         _values = (_bucket, _key)
        #         _exists = True if self.get_scalar(_sql, _values) else False
        #         if _exists:
        #             continue
        #         _modified = parse(_modified)
        #         _values = (_key, _bucket, _size, _modified)
        #         _sql = "INSERT INTO files (file, bucket, size, modified) VALUES (?, ?, ?, ?)"
        #         self.db_exec(_sql, _values)
        #     self.db.commit()


def main():
    i = Inventory()
    if len(sys.argv) > 1:
        i.add_to_db(sys.argv[1])


if __name__ == "__main__":
    main()
