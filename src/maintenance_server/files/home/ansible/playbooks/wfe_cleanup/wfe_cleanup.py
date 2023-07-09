#!/usr/bin/env python3

import os
import re
import subprocess
import shlex
import sys
import datetime
# import shut


def execute(cmd):
    cmdObject = subprocess.run(
        shlex.split(cmd),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return cmdObject


class Docker:
    def __init__(self):
        self.threshold = 30
        self.days_to_keep = 7
        self.__id = None
        self.__earliest_date = None

    def strip_non_ascii(self, text):
        output = b""
        for c in text:
            if c < 128:
                output += chr(c).encode()
        return output

    def go(self):
        if not self.is_scheduler_container():
            print("No scheduler container found.")
            sys.exit()
        # if self.usage_too_high():
        #     print(f"Container exceeds threshold.")
        #     self.prune()
        # else:
        #     print(f"Container does not exceed threshold.")
        self.prune()
    
    @property
    def id(self):
        if not self.__id:
            self.__id = self.get_scheduler_container_id()
        return self.__id

    def file_date(self, fullname):
        filename = fullname.split("/")[-1]
        filedate = datetime.datetime.strptime(filename, "%Y-%m-%d")
        return filedate
        # age = (datetime.datetime.now() - filedate).days
        # return age

    def iterate_files(self):
        pattern = re.compile('[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
        cmd = f"docker exec -t {self.id} find logs/scheduler -maxdepth 1"
        results = execute(cmd).stdout.decode()
        for line in results.splitlines():
            if pattern.match(line.split('/')[-1]):
                yield line

    def earliest_date(self):
        if not self.__earliest_date:
            oldest_file_date = datetime.datetime.min
            for fullname in self.iterate_files():
                filedate = datetime.datetime.strptime(fullname.split('/')[-1], "%Y-%m-%d")
                if filedate > oldest_file_date:
                    oldest_file_date = filedate
            self.__earliest_date = oldest_file_date - datetime.timedelta(days=self.days_to_keep)
            print(f"Threshold:           {self.days_to_keep} days")
            print(f"Found oldest date:   {oldest_file_date}")
            print(f"Found earliest date: {self.__earliest_date}")
        return self.__earliest_date

    def prune(self):
        for fullname in self.iterate_files():
            filename = fullname.split('/')[-1]

            _list = []
            if self.file_date(fullname) < self.earliest_date():
                _list.append(fullname)
                print(f"Directory {filename} too old.")
            else:
                print(f"Directory {filename} is young.")
            if len(_list) > 0:
                delete_cmd = f"docker exec -t {self.id} rm -rf {' '.join(_list)}"
                print(f"Executing: {delete_cmd}")
                # delete_results = execute(cmd).stdout.decode()
            else:
                print(f"No files to remove.")
                
    # def usage_too_high(self):
    #     usage = self.get_container_usage()
    #     return usage > self.threshold

    def is_scheduler_container(self):
        if self.id:
            return True

    def get_scheduler_container_id(self):
        stdout = self.strip_non_ascii(execute("docker ps").stdout).decode()
        for line in stdout.splitlines():
            if 'SchedulerService' in line:
                return line.split()[0]

    # def get_container_usage(self):
    #     cmd = f"docker exec -t {self.id} df -h"
    #     print(f"Executing: {cmd}")
    #     results = execute(cmd).stdout.decode()
    #     for line in results.splitlines():
    #         if "/dev/mapper/docker" in line:
    #             return int(line.split()[4].replace("%", ""))
    #     return 100


def main():
    d = Docker()
    d.go()


if __name__ == "__main__":
    main()

