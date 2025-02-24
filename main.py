import os
import hashlib
import shutil
import time
import logging
import sys
import threading
import argparse

from datetime import datetime
from argparse import Namespace


class Parameters:
    source: str = './source'
    replica: str = './replica'
    log_path: str = '.'
    min_s: int = 1
    running: bool = True

    def __new__(cls):
        return cls


def calc_md5(filepath: str):
    obj = hashlib.md5()
    if is_file(filepath):
        with open(filepath, "rb") as fp:
            for blc in iter(lambda: fp.read(4096), b""):
                obj.update(blc)

            return obj.hexdigest()


def key_interrupt():
    sys.stdin.read(1)
    log('interrupted by user')
    Parameters.running = False
    exit(0)


def no_slash_end(string: str = ''):
    if string.endswith('/') or string.endswith('\\'):
        return string[:-1]
    else:
        return string


def parse_args(args: Namespace):
    if args.source != Parameters.source:
        Parameters.source = no_slash_end(args.source)
        log(f'source path updated to {Parameters.source}')
    if args.replica != Parameters.replica:
        Parameters.replica = no_slash_end(args.replica)
        log(f'replica path updated to {Parameters.replica}')
    if args.log_path != Parameters.log_path:
        Parameters.log_path = no_slash_end(args.log_path)
        log(f'log path updated to {Parameters.log_path}')
    if args.interval <= 0:
        log(f'invalid interval parameter {args.interval}')
    else:
        if args.interval != Parameters.min_s:
            Parameters.min_s = args.interval
            log(f'interval updated to {Parameters.min_s}')


def rm(filepath: str):
    if file_exists(filepath):
        if is_file(filepath):
            try:
                os.remove(filepath)
                log(f'file {filepath} removed')
            except PermissionError:
                log(f"file {filepath} is open and can't be removed now")
        else:
            try:
                shutil.rmtree(filepath)
                log(f'folder {filepath} removed')
            except PermissionError:
                log(f"a file in {filepath} is open and can't be removed now")


def is_file(filepath: str):
    if os.path.isfile(filepath):
        return True
    else:
        return False


def file_exists(filepath: str):
    return os.path.exists(filepath)


def log(obs: str):
    logging.info(obs)
    print(f'{datetime.now()} {obs}')


def mk_dir(filepath: str):
    if not is_file(filepath):
        os.makedirs(filepath, exist_ok=True)
        log(f'directory {filepath} created')


"""if not exists, creates the default source and replica paths"""
def chk_dirs():
    if not file_exists(Parameters.source):
        mk_dir(Parameters.source)
    if not file_exists(Parameters.replica):
        mk_dir(Parameters.replica)


"""returns the name of the file or folder"""
def spath(path: str):
    if path.find(Parameters.source) >= 0:
        return path.split(f'{Parameters.source}/')[1]

    if path.find(Parameters.replica) >= 0:
        return path.split(f'{Parameters.replica}/')[1]


class Dir:
    def __init__(self, filepath: str):
        self.status = None
        self.path = filepath
        self.spath = spath(filepath)
        self.hash = calc_md5(filepath)

"""copies a file from source to replica"""
def copy(file: Dir, meta=True):
    if file_exists(file.path):
        fp_to = f'{Parameters.replica}/{file.spath}'
        if meta:
            shutil.copy2(file.path, fp_to)
        else:
            shutil.copy(file.path, fp_to)
        log(f'file {fp_to} copied')


"""navigates the directory tree creating the list  of files"""
def file_dir(files: list, files_list: list, folder: str = ''):
    for file in files:
        _file = f'{folder}/{file}'
        if os.path.isfile(_file):
            files_list.append(Dir(_file))
        else:
            _dir = f"{Parameters.replica}/{spath(_file)}"
            if file_exists(_dir) and not file_exists(f'{Parameters.source}/{spath(_file)}'):
                rm(_dir)
            if _file.find(Parameters.source) >= 0:
                if not file_exists(_dir):
                    mk_dir(_dir)
            if file_exists(_file):
                file_dir(os.listdir(_file), files_list, _file)
    return files_list


class SourceFolder:
    def __init__(self):
        self.files = []
        file_dir(self.list(), self.files, Parameters.source)

    @staticmethod
    def list():
        return os.listdir(Parameters.source)


class ReplicaFolder:
    def __init__(self):
        self.files = []
        file_dir(self.list(), self.files, Parameters.replica)

    @staticmethod
    def list():
        return os.listdir(Parameters.replica)


class Sync:
    def __init__(self):
        self.replica_folder = ReplicaFolder()
        self.source_folder = SourceFolder()

    def run(self):
        for file_r in self.replica_folder.files:
            if file_r.spath not in [file.spath for file in self.source_folder.files]:
                if file_exists(file_r.path):
                    rm(file_r.path)

        for file in self.source_folder.files:
            if file.spath not in [file_r.spath for file_r in self.replica_folder.files]:
                copy(file)
                continue
            if file.spath in [file_r.spath for file_r in self.replica_folder.files] and file.hash not in [file_r.hash
                                                                                                          for file_r in
                                                                                                          self.replica_folder.files]:
                copy(file)


logging.basicConfig(filename=f'{Parameters.log_path}/log.txt', level=logging.INFO, format="%(asctime)s - %(message)s")

args_parser = argparse.ArgumentParser(description='source replica args parser')
args_parser.add_argument("-s", "--source", type=str, help="source path", default=Parameters.source)
args_parser.add_argument("-r", "--replica", type=str, help="replica path", default=Parameters.replica)
args_parser.add_argument("-i", "--interval", type=int, help="sync interval in minutes", default=Parameters.min_s)
args_parser.add_argument("-l", "--log_path", type=str, help="log file path", default=Parameters.log_path)

parse_args(args_parser.parse_args())

thread = threading.Thread(target=key_interrupt, daemon=True)
thread.start()

chk_dirs()

log(f'Started')
print("Press 'Enter' to interrupt.")

while Parameters.running:
    sync = Sync()
    sync.run()
    for tmr in range(60 * Parameters.min_s):
        time.sleep(1)
        if not Parameters.running:
            exit(0)
    print('...', end='')
