"""Signals request a stop; only committed boundaries actually pause execution."""
from contextlib import contextmanager
import signal
import os

requested = False
parent_pid = None


class Paused(BaseException):
    pass


def request(*_):
    global requested
    requested = True


def boundary():
    if parent_pid is not None and os.getppid()!=parent_pid:
        request()
    if requested:
        raise Paused('Manual stop at a committed boundary')


@contextmanager
def handlers(*,watch_parent=False):
    global requested,parent_pid
    requested = False
    parent_pid=int(os.environ['FLY_PHASE11_LAUNCHER_PID']) if watch_parent and os.environ.get('FLY_PHASE11_LAUNCHER_PID') else None
    old = {s: signal.signal(s, request) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for s, handler in old.items():
            signal.signal(s, handler)
        requested = False
        parent_pid = None
