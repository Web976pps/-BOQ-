import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "src/extract_zones_codes.py", "--help"], capture_output=True, check=False
    )
    assert result.returncode == 0
    assert b"Extract A1 drawing zones" in result.stdout
