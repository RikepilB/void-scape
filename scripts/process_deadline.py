"""Run a cooperating worker with a deadline over its owned process tree."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import time


class ProcessDeadlineError(RuntimeError):
    pass


class WindowsJob:
    """The worker waits on stdin until assignment; children cannot escape early."""
    def __init__(self, process):
        import ctypes
        from ctypes import wintypes as w
        class Basic(ctypes.Structure):
            _fields_ = [('per_process', ctypes.c_longlong), ('per_job', ctypes.c_longlong),
                        ('flags', w.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', w.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', w.DWORD), ('scheduling', w.DWORD)]
        class Counters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
        class Extended(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', Counters), ('process_mem', ctypes.c_size_t),
                        ('job_mem', ctypes.c_size_t), ('peak_process', ctypes.c_size_t),
                        ('peak_job', ctypes.c_size_t)]
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.api.SetInformationJobObject.restype = w.BOOL
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.AssignProcessToJobObject.restype = w.BOOL
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.api.CloseHandle.restype = w.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ProcessDeadlineError('cannot create worker job')
        limits = Extended()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or
                not self.api.AssignProcessToJobObject(self.handle, int(process._handle))):
            self.close()
            raise ProcessDeadlineError('cannot contain worker process')

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def run(command, *, timeout, log, cwd=None):
    """Command must implement the GO stdin handshake before performing any work."""
    if not 0 < timeout <= 86400:
        raise ValueError('worker deadline must be between zero and one day')
    started = time.monotonic()
    job = None
    process = None
    with Path(log).open('xb') as output:
        try:
            process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                                       stdout=output, stderr=output,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                                       start_new_session=os.name != 'nt')
            if os.name == 'nt':
                job = WindowsJob(process)
            process.stdin.write(b'GO\n')
            process.stdin.close()
            try:
                code = process.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                raise ProcessDeadlineError('worker deadline exceeded') from None
            if code:
                raise ProcessDeadlineError('worker failed; inspect retained local evidence')
        finally:
            if process is not None:
                if job is not None:
                    job.close()
                elif os.name != 'nt':
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif process.poll() is None:
                    process.kill()  # Assignment failed before the GO handshake.
                process.wait()
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
