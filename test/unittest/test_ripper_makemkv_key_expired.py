import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, '/opt/arm')

from arm.ripper import makemkv  # noqa: E402

KEY_EXPIRED_OUTPUT = [
    'MSG:1005,0,1,"MakeMKV v1.18.4 linux(x64-release) started","%1 started","MakeMKV v1.18.4 linux(x64-release)"',
    'MSG:5073,260,0,"Your temporary key has expired and was removed. Please restart the application.",'
    '"Your temporary key has expired and was removed. Please restart the application."',
    'MSG:5021,131332,1,"This application version is too old.  Please download the latest version at '
    'http://www.makemkv.com/ or enter a registration key to continue using the current version.",'
    '"This application version is too old.  Please download the latest version at %1 or enter a registration '
    'key to continue using the current version.","http://www.makemkv.com/"',
]


def fake_popen(lines, returncode):
    proc = MagicMock()
    proc.stdout = iter(line + "\n" for line in lines)
    proc.returncode = None

    def finish(*_):
        proc.returncode = returncode
        return False

    proc.__enter__.return_value = proc
    proc.__exit__.side_effect = finish
    return MagicMock(return_value=proc)


class TestKeyExpired(unittest.TestCase):
    def run_makemkv(self, lines, returncode):
        with patch("subprocess.Popen", fake_popen(lines, returncode)), \
                patch("shutil.which", return_value="/usr/bin/makemkvcon"):
            return list(makemkv.run(["info", "disc:9999"], makemkv.OutputType.MSG))

    def test_expired_key_raises_clear_error(self):
        """An expired key gets a specific error, not just 'failed with code: 253'"""
        with self.assertRaises(makemkv.MakeMkvKeyExpiredError) as ctx:
            self.run_makemkv(KEY_EXPIRED_OUTPUT, 253)
        self.assertIn("beta key has expired", str(ctx.exception))
        self.assertIsInstance(ctx.exception, makemkv.MakeMkvRuntimeError)

    def test_other_failures_keep_generic_error(self):
        """A failure that isn't about the key still raises the plain runtime error"""
        lines = ['MSG:5010,0,0,"Failed to open disc","Failed to open disc"']
        with self.assertRaises(makemkv.MakeMkvRuntimeError) as ctx:
            self.run_makemkv(lines, 1)
        self.assertNotIsInstance(ctx.exception, makemkv.MakeMkvKeyExpiredError)
        self.assertIn("failed with code: 1", str(ctx.exception))

    def test_key_message_with_success_exit_does_not_raise(self):
        """Only fail when makemkvcon itself fails"""
        self.run_makemkv(KEY_EXPIRED_OUTPUT[:2], 0)


if __name__ == "__main__":
    unittest.main()
