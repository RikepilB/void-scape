import sys
import time

import pytest

from process_deadline import ProcessDeadlineError, run


def test_worker_must_receive_handshake_and_can_finish(tmp_path):
    target = tmp_path / 'done'
    code = 'import sys,pathlib; assert sys.stdin.readline()=="GO\\n"; pathlib.Path(sys.argv[1]).write_text("done")'
    run([sys.executable, '-c', code, str(target)], timeout=10, log=tmp_path / 'log')
    assert target.read_text() == 'done'


def test_timeout_terminates_descendant_before_late_write(tmp_path):
    marker, ready = tmp_path / 'must-not-exist', tmp_path / 'ready'
    worker = tmp_path / 'worker.py'
    worker.write_text('''import sys,subprocess,time,pathlib
assert sys.stdin.readline() == 'GO\\n'
child = "import pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(3); pathlib.Path(sys.argv[2]).write_text('escaped')"
subprocess.Popen([sys.executable, '-c', child, sys.argv[1], sys.argv[2]])
time.sleep(30)
''')
    started = time.monotonic()
    with pytest.raises(ProcessDeadlineError, match='deadline'):
        run([sys.executable, str(worker), str(ready), str(marker)], timeout=2, log=tmp_path / 'log')
    assert time.monotonic() - started < 8
    assert ready.is_file(), 'test must actually launch the descendant'
    time.sleep(3.2)
    assert not marker.exists()


def test_nonzero_worker_is_reported(tmp_path):
    with pytest.raises(ProcessDeadlineError, match='worker failed'):
        run([sys.executable, '-c', 'import sys; sys.stdin.readline(); sys.exit(6)'],
            timeout=10, log=tmp_path / 'log')
