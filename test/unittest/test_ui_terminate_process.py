"""terminate_process() must kill the job's whole process tree, not just the job PID.

Regression test: abandoning a "Rip via ISO" job SIGTERMed only rip_iso.py, leaving
the `sh -c ddrescue ...` wrapper and ddrescue itself running and holding the drive.
"""
import importlib.util
import os
import subprocess
import sys
import time
import unittest
from unittest import mock

import psutil

# json_api pulls in Flask, the DB and /etc/arm config at import time; none of that
# matters for process handling, so stub out everything except psutil.
_STUBS = ['flask', 'arm', 'arm.config', 'arm.config.config', 'arm.models', 'arm.models.config',
          'arm.models.job', 'arm.models.notifications', 'arm.models.track',
          'arm.models.ui_settings', 'arm.ui', 'arm.ui.forms', 'arm.ui.utils',
          'arm.ui.settings']


def _load_json_api():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [os.path.join(here, '..', '..', 'arm', 'ui', 'json_api.py'),
                  '/opt/arm/arm/ui/json_api.py']
    path = next(p for p in candidates if os.path.exists(p))
    spec = importlib.util.spec_from_file_location('json_api_under_test', path)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {name: mock.MagicMock() for name in _STUBS}):
        spec.loader.exec_module(module)
    return module


json_api = _load_json_api()


def _wait_gone(pids, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(psutil.pid_exists(p) and psutil.Process(p).status() != psutil.STATUS_ZOMBIE
                   for p in pids):
            return True
        time.sleep(0.1)
    return False


class TestTerminateProcess(unittest.TestCase):
    def setUp(self):
        self.procs = []

    def tearDown(self):
        for proc in self.procs:
            try:
                for child in proc.children(recursive=True):
                    child.kill()
                proc.kill()
                proc.wait(timeout=2)
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                pass

    def _spawn_tree(self, cmd):
        popen = subprocess.Popen(cmd, shell=True)
        proc = psutil.Process(popen.pid)
        self.procs.append(proc)
        deadline = time.time() + 5
        while time.time() < deadline and not proc.children(recursive=True):
            time.sleep(0.05)
        self.popen = popen
        return proc

    def test_children_are_terminated_with_parent(self):
        # sh -> sh -> sleep, the same shape as rip_iso.py -> sh -c ddrescue -> ddrescue
        parent = self._spawn_tree("sh -c 'sleep 300; true'")
        pids = [parent.pid] + [c.pid for c in parent.children(recursive=True)]
        self.assertGreaterEqual(len(pids), 2)

        json_api.terminate_process(parent.pid)
        self.popen.wait(timeout=5)  # reap the direct child, as the real parent would

        self.assertTrue(_wait_gone(pids), f"processes still alive: {pids}")

    def test_sigterm_ignoring_child_is_killed(self):
        parent = self._spawn_tree("sh -c 'trap \"\" TERM; sleep 300; true'")
        pids = [parent.pid] + [c.pid for c in parent.children(recursive=True)]
        with mock.patch.object(json_api, 'TERMINATE_GRACE_SECONDS', 1):
            json_api.terminate_process(parent.pid)
        self.popen.wait(timeout=5)

        self.assertTrue(_wait_gone(pids), f"processes still alive: {pids}")

    def test_missing_pid_is_not_an_error(self):
        json_api.terminate_process(2 ** 22 + 12345)

    def test_none_pid_is_not_an_error(self):
        json_api.terminate_process(None)


if __name__ == '__main__':
    unittest.main()
