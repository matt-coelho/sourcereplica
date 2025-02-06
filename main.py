import os
import hashlib
import shutil
import time
import logging
from datetime import datetime

source = './source'
replica = './replica'
mins = 1

def calc_md5(filepath):
    obj = hashlib.md5()
    with open(filepath, "rb") as fp:
        for blc in iter(lambda: fp.read(4096), b""):
            obj.update(blc)

        return obj.hexdigest()


def copy(fpfrom, fpto, meta = 1):
    if file_exists(fpfrom):
        if meta == 1:
            shutil.copy2(fpfrom, fpto)
        else:
            shutil.copy(fpfrom, fpto)

def file_exists(filepath):
    return os.path.exists(filepath)

def log(obs):
    logging.info(obs)
    print(f'{datetime.now()} {obs}')

def chkdirs():
    if not file_exists(source):
        os.makedirs(source)
    if not file_exists(replica):
        os.makedirs(replica)

def spath(path):
    if path.find(source) >= 0:
        return path.split(f'{source}/')[1]

    if path.find(replica) >= 0:
        return path.split(f'{replica}/')[1]

class Dir():
    def __init__(self, filepath = ''):
        self.status = None
        self.path = filepath
        self.spath = spath(filepath)
        self.hash = calc_md5(filepath)


class SourceFolder():
    def __init__(self):
        self.files = [Dir(f'{source}/{file}') for file in self.list()]

    @staticmethod
    def list():
        return os.listdir(source)


class ReplicaFolder():
    def __init__(self):
        self.files = [Dir(f'{replica}/{file}') for file in self.list()]

    @staticmethod
    def list():
        return os.listdir(replica)


class Sync():
    def __init__(self):
        self.source_folder = SourceFolder()
        self.replica_folder = ReplicaFolder()

    def run(self):
        for file_r in self.replica_folder.files:
            if file_r.spath not in [file.spath for file in self.source_folder.files]:
                if file_exists(file_r.path):
                    os.remove(file_r.path)
                    log(f'arquivo {file_r.path} removido')
        for file in self.source_folder.files:
            if file.spath not in [file_r.spath for file_r in self.replica_folder.files]:
                copy(file.path, replica)
                log(f'arquivo {file.path} criado')
                continue
            if file.spath in [file_r.spath for file_r in self.replica_folder.files] and file.hash not in [file_r.hash for file_r in self.replica_folder.files]:
                copy(file.path, replica)
                log(f'arquivo {file.path} replicado')



logging.basicConfig(filename='./log.txt', level=logging.INFO, format="%(asctime)s - %(message)s")

log(f'iniciado')

while 1 == 1:
    chkdirs()
    sync = Sync()
    sync.run()
    time.sleep(60 * mins)
    print('...', sep='')
