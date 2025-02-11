import os
import hashlib
import shutil
from argparse import Namespace

import time
import logging
import sys
import threading
import argparse
from datetime import datetime

source = './source'
replica = './replica'
log_path = '.'
min_s = 1
running = True


def calc_md5(filepath: str):
    obj = hashlib.md5()
    if not os.path.isdir(filepath):
        with open(filepath, "rb") as fp:
            for blc in iter(lambda: fp.read(4096), b""):
                obj.update(blc)

            return obj.hexdigest()


def key_interrupt():
    global running
    sys.stdin.read(1)
    log('interrupted by user')
    running = False
    exit(0)


def copy(fp_from: str, fp_to: str, meta=True):
    if file_exists(fp_from):
        fp_to = f'{fp_to}/{spath(fp_from)}'
        if os.path.isfile(fp_from):
            if meta:
                shutil.copy2(fp_from, fp_to)
            else:
                shutil.copy(fp_from, fp_to)
        else:
            fp_to = f'{fp_to}/{spath(fp_from)}'
            shutil.copytree(fp_from, f'{fp_to}/{(fp_from.split(f"{source}")[1])}')


def no_slash_end(string: str = ''):
    if string.endswith('/') or string.endswith('\\'):
        return string[:-1]
    else:
        return string


def parse_args(args: Namespace):
    global source
    global replica
    global log_path
    global min_s

    if file_exists(args.source) and args.source != source:
        source = no_slash_end(args.source)
        log(f'source path updated to {source}')
    if file_exists(args.replica) and args.replica != replica:
        replica = no_slash_end(args.replica)
        log(f'replica path updated to {replica}')
    if file_exists(args.log_path) and args.log_path != log_path:
        log_path = no_slash_end(args.log_path)
        log(f'log path updated to {log_path}')
    if args.interval != min_s:
        min_s = args.interval
        log(f'interval updated to {min_s}')


def file_exists(filepath: str):
    return os.path.exists(filepath)


def log(obs: str):
    logging.info(obs)
    print(f'{datetime.now()} {obs}')


def chk_dirs():
    if not file_exists(source):
        os.makedirs(source)
    if not file_exists(replica):
        os.makedirs(replica)


def spath(path: str):
    if path.find(source) >= 0:
        return path.split(f'{source}/')[1]

    if path.find(replica) >= 0:
        return path.split(f'{replica}/')[1]


class Dir:
    def __init__(self, filepath: str):
        self.status = None
        self.path = filepath
        self.spath = spath(filepath)
        self.hash = calc_md5(filepath)


def file_dir(files: list, files_list: list, folder: str = ''):
    for file in files:
        _file = f'{folder}/{file}'
        if os.path.isfile(_file):
            files_list.append(Dir(_file))
        else:
            _dir = f"{replica}/{spath(_file)}"
            if file_exists(_dir) and not file_exists(f'{source}/{spath(_file)}'):
                try:
                    shutil.rmtree(_dir)
                    log(f'folder {_dir} removed')
                except PermissionError:
                    log(f"a file in {_dir} is open and can't be removed now")
            if _file.find(source) >= 0:
                if not file_exists(_dir):
                    os.makedirs(_dir)
            if file_exists(_file):
                file_dir(os.listdir(_file), files_list, _file)
    return files_list


class SourceFolder:
    def __init__(self):
        self.files = []
        file_dir(self.list(), self.files, source)

    @staticmethod
    def list():
        return os.listdir(source)


class ReplicaFolder:
    def __init__(self):
        self.files = []
        file_dir(self.list(), self.files, replica)

    @staticmethod
    def list():
        return os.listdir(replica)


class Sync:
    def __init__(self):
        self.replica_folder = ReplicaFolder()
        self.source_folder = SourceFolder()

    def run(self):
        for file_r in self.replica_folder.files:
            if file_r.spath not in [file.spath for file in self.source_folder.files]:
                if file_exists(file_r.path):
                    try:
                        os.remove(file_r.path)
                        log(f'file {file_r.path} removed')
                    except PermissionError:
                        log(f"file {file_r.path} is open and can't be removed now")
                        continue

        for file in self.source_folder.files:
            if file.spath not in [file_r.spath for file_r in self.replica_folder.files]:
                copy(file.path, replica)
                log(f'file {replica}/{file.spath} created')
                continue
            if file.spath in [file_r.spath for file_r in self.replica_folder.files] and file.hash not in [file_r.hash
                                                                                                          for file_r in
                                                                                                          self.replica_folder.files]:
                copy(file.path, replica)
                log(f'file {replica}/{file.spath} replicated')


logging.basicConfig(filename=f'{log_path}/log.txt', level=logging.INFO, format="%(asctime)s - %(message)s")

args_parser = argparse.ArgumentParser(description='source replica args parser')
args_parser.add_argument("-s", "--source", type=str, help="source path", default=source)
args_parser.add_argument("-r", "--replica", type=str, help="replica path", default=replica)
args_parser.add_argument("-i", "--interval", type=int, help="sync interval in minutes", default=min_s)
args_parser.add_argument("-l", "--log_path", type=str, help="log file path", default=log_path)

parse_args(args_parser.parse_args())

thread = threading.Thread(target=key_interrupt, daemon=True)
thread.start()

log(f'Started')
print("Press 'Enter' to interrupt.")

while running:
    chk_dirs()
    sync = Sync()
    sync.run()
    for tmr in range(60 * min_s):
        time.sleep(1)
        if not running:
            exit(0)
    print('...', end='')
