"""Lossless storage for large native STLs; download bytes stay unchanged."""
from contextlib import contextmanager
import gzip
import hashlib
from pathlib import Path
import shutil
import struct


def physical(path):
    path=Path(path)
    return path if path.is_file() else path.with_suffix(path.suffix+'.gz')


def open_artifact(path):
    target=physical(path)
    return gzip.open(target,'rb') if target.suffix=='.gz' else target.open('rb')


def artifact_digest(path):
    with open_artifact(path) as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def artifact_size(path):
    target=physical(path)
    if target.suffix!='.gz':return target.stat().st_size
    with target.open('rb') as stream:stream.seek(-4,2);return struct.unpack('<I',stream.read(4))[0]


def compact_stl(path):
    path=Path(path)
    if path.suffix!='.stl' or not path.is_file():raise ValueError('Only a local STL may be compacted')
    target=path.with_suffix('.stl.gz');temporary=target.with_suffix('.gz.tmp')
    with path.open('rb') as source:expected=hashlib.file_digest(source,'sha256').hexdigest()
    with path.open('rb') as source,gzip.open(temporary,'wb',compresslevel=1) as dst:shutil.copyfileobj(source,dst,1024*1024)
    with gzip.open(temporary,'rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=expected:raise ValueError('Compressed STL verification failed')
    temporary.replace(target);path.unlink()


@contextmanager
def materialized_stl(path,*,writeback=False):
    path=Path(path)
    if path.exists():
        yield path
        if writeback:compact_stl(path)
        return
    work=path.with_suffix('.working.stl')
    if work.exists():raise ValueError('Unexpected existing STL work file')
    with open_artifact(path) as source,work.open('wb') as dst:shutil.copyfileobj(source,dst,1024*1024)
    try:
        yield work
        if writeback:
            compact_stl(work)
            work.with_suffix('.stl.gz').replace(path.with_suffix('.stl.gz'))
    finally:
        work.unlink(missing_ok=True)
