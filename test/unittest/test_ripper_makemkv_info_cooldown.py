import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, '/opt/arm')

from arm.ripper import makemkv  # noqa: E402
from arm.models.job import JobState  # noqa: E402


class TestMakeMkvInfoCooldown(unittest.TestCase):
    def run_info(self, others_active, max_processes=1):
        job = SimpleNamespace(status=JobState.IDLE.value, config=SimpleNamespace(MANUAL_WAIT_TIME=60))
        statuses = []
        db = MagicMock()
        db.session.commit.side_effect = lambda: statuses.append(job.status)
        with patch.object(makemkv, "db", db), \
                patch.object(makemkv, "run", return_value=iter([])), \
                patch.object(makemkv, "sleep") as sleep, \
                patch.object(makemkv, "other_jobs_active", return_value=others_active), \
                patch.object(makemkv.utils, "sleep_check_process") as sleep_check, \
                patch.object(makemkv.utils, "min_length_for", return_value=120), \
                patch.dict(makemkv.cfg.arm_config, {"MAX_CONCURRENT_MAKEMKVINFO": max_processes}):
            list(makemkv.makemkv_info(job))
        return job, statuses, sleep, sleep_check

    def test_no_cooldown_when_alone(self):
        """With no other job to give a turn to, the scan doesn't sleep afterwards or report waiting"""
        job, statuses, sleep, sleep_check = self.run_info(others_active=False)
        sleep.assert_not_called()
        self.assertEqual(sleep_check.call_count, 1)  # only the gate before the scan
        self.assertNotIn(JobState.VIDEO_WAITING.value, statuses[1:])
        self.assertEqual(job.status, JobState.IDLE.value)

    def test_cooldown_when_other_jobs_queued(self):
        """Other unfinished jobs still get the cooldown, and it is reported as waiting"""
        job, statuses, sleep, sleep_check = self.run_info(others_active=True)
        sleep.assert_called_once_with(60)
        self.assertEqual(sleep_check.call_count, 2)
        self.assertIn(JobState.VIDEO_WAITING.value, statuses[1:])
        self.assertEqual(job.status, JobState.IDLE.value)

    def test_disabled_when_limit_is_zero(self):
        job, statuses, sleep, _ = self.run_info(others_active=True, max_processes=0)
        sleep.assert_not_called()
        self.assertEqual(job.status, JobState.IDLE.value)


if __name__ == "__main__":
    unittest.main()
