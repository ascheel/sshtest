import sqlite3
import datetime
import os
import sys
import json


TESTING = False


class DB:
    def __init__(self):
        self.TEMPORARY_DIRECTORY = os.path.join(os.path.expanduser("~"), "tmp")
        if not os.path.exists(self.TEMPORARY_DIRECTORY):
            os.makedirs(self.TEMPORARY_DIRECTORY)
        os.environ["SQLITE_TMPDIR"] = self.TEMPORARY_DIRECTORY

        self.db_file = "s3.db"
        self.db = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

        self.stats = {}
    
    def get_accounts_and_buckets(self):
        print("Processing.  This may take several minutes.")
        a_and_b = {}
        latest_report = self.get_latest_report()
        sql = "SELECT bucket, account FROM files WHERE filename = ? GROUP BY account, bucket"
        values = (latest_report,)
        cur = self.db.cursor()
        cur.execute(sql, values)
        for row in cur:
            bucket  = row[0]
            account = row[1]

            if not a_and_b.get(account):
                a_and_b[account] = {}
            if not a_and_b[account].get(bucket):
                a_and_b[account][bucket] = 0
        return a_and_b

    def get_latest_report(self):
        latest_report = None
        latest_date = None
        data = self.get_rows("SELECT * FROM textfile")
        for row in data:
            _file, _date = row
            if not latest_date:
                latest_report = _file
                latest_date   = _date
                continue
            if _date > latest_date:
                latest_report = _file
                latest_date   = _date
        return latest_report

    def get_bucket_stats(self, a_and_b):
        stats = []
        _count = 0
        latest_report = self.get_latest_report()

        for account, keys in a_and_b.items():
            for bucket in keys:
                _count += 1
                if _count > 10 and TESTING:
                    return stats
                sql        = "SELECT SUM(size) FROM files WHERE account = ? AND bucket = ? AND filename = ?"
                values     = (account, bucket, latest_report)
                size       = self.get_scalar(sql, values)
                key        = f"{account} {bucket}"
                
                prefix_stats = self.get_prefix_stats(latest_report, account, bucket)

                # for prefix in self.get_prefixes(latest_report, account, bucket):
                #     prefix_stats.append((prefix, self.get_prefix_stats(latest_report, account, bucket, prefix)))
                stats.append((key, size, prefix_stats))
        return stats
    
    def get_prefixes(self, filename, account, bucket):
        cur = self.db.cursor()
        sql = """
        SELECT
            filekey
        FROM
            files
        WHERE
            account = ? AND
            bucket = ? AND
            filename = ?
        """
        values = (account, bucket, filename)
        cur.execute(sql, values)
        prefixes = []
        for row in cur:
            filename = row[0]
            if "/" in filename:
                prefix = filename.split("/")[0]
                if prefix not in prefixes:
                    prefixes.append(prefix)
        return sorted(prefixes)

    def get_prefix_stats(self, filename, account, bucket):
        sizes = []
        prefixes = self.get_prefixes(filename, account, bucket)
        for prefix in prefixes:
            cur = self.db.cursor()
            prefix2 = f"{prefix}/"
            sql = f"""
            SELECT
                SUM(size)
            FROM
                files
            WHERE
                filekey LIKE '{prefix2}%' AND
                filename = ? AND
                account = ? AND
                bucket = ?
            """
            values = (filename, account, bucket)
            size = self.get_scalar(sql, values)
            sizes.append((prefix, size))
        return self._sort(sizes)
    
    def _pad(self, text, width=0):
        output = ""
        text = str(text)
        return text + " " * (width - len(text) if len(text) <= width else 0)

    def print_stats(self, stats):
        stats = self._sort(stats)
        for stat in stats:
            print()
            line = self._pad(stat[0], 80) + " - "
            line += self._pad(f"{stat[1]:,}", 40) + " ("
            line += self.human_bytes(stat[1])
            line += ")"
            # print(f"{self._pad(stat[0])} - {stat[1]:,} ({self.human_bytes(stat[1])})")
            print(line)
            for prefix_stat in stat[2]:
                line = self._pad(f"{stat[0]}/{prefix_stat[0]}", 80) + " - "
                line += self._pad(f"{prefix_stat[1]:,}", 40) + " ("
                line += self.human_bytes(prefix_stat[1])
                line += ")"
                print(line)

                #print(f"{stat[0]}/{prefix_stat[0]:40} - {prefix_stat[1]:,} ({self.human_bytes(prefix_stat[1])})")

    def human_bytes(self, size, units=("bytes", "KB", "MB", "GB", "TB", "PB", "EB")):
        return str(size) + " " + units[0] if size < 1024 else self.human_bytes(size>>10, units[1:])

    def _sort(self, _list):
        """Sorts list of lists by second value"""
        print(json.dumps(_list, indent=4))
        return sorted(_list, key = lambda x: x[1])

    def go(self):
        a_and_b = self.get_accounts_and_buckets()
        stats   = self.get_bucket_stats(a_and_b)
        #print(json.dumps(stats, indent=4))
        self.print_stats(stats)
        
    def get_rows(self, sql, values=None):
        if not values:
            values = []
        cur = self.db.cursor()
        cur.execute(sql, values)
        return cur.fetchall()
    
    def get_row(self, sql, values=None):
        return self.get_rows(sql, values)[0]
    
    def get_scalar(self, sql, values=None):
        return self.get_row(sql, values)[0]
    
    def db_exec(self, sql, values=None):
        self.get_rows(sql, values)


def main():
    db = DB()
    db.go()


if __name__ == "__main__":
    main()
