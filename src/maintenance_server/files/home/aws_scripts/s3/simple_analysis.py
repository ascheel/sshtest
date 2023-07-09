import sys
import os
import csv


def main():
    _file = sys.argv[1]
    _bucket = sys.argv[2]
    with open(_file, "r") as f_in:
        reader = csv.reader(f_in)
        count = 0
        total_size = 0
        total_count = 0
        old_bucket = None
        for row in reader:
            if not count % 1000000:
                print(f"{count:,}")
            count += 1
            
            bucket = row[1]
            if old_bucket != bucket:
                old_bucket = bucket
                print(f"{bucket}")
            key    = row[2]
            size   = row[3]
            #print(f"{bucket} or {_bucket}")
            if bucket != _bucket:
                continue
            print("Match!")
            total_count += 1
            total_size += size
        print(f"{count:,}")
        print(f"Bucket: files: {total_count} - size: {total_size}")

if __name__ == "__main__":
    main()
