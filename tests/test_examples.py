from pathlib import Path
import subprocess
import sys

import pytest


EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.py"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_example_runs_from_external_directory(example, tmp_path):
    # A pasta corrente é externa; o pacote precisa estar realmente instalado.
    completed = subprocess.run(
        [sys.executable, str(example)], cwd=tmp_path,
        capture_output=True, text=True, timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip()
