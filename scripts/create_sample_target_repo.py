#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT.parent / "sample-target-repo"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    target = args.path.expanduser().resolve()
    if target.exists() and any(target.iterdir()) and not (target / ".git").exists():
        raise SystemExit(f"refusing to write into non-git directory: {target}")

    (target / "sample_math").mkdir(parents=True, exist_ok=True)
    (target / "tests").mkdir(exist_ok=True)
    (target / "sample_math" / "__init__.py").write_text("def add(a, b):\n    return a + b\n")
    (target / "tests" / "test_sample_math.py").write_text(
        "import unittest\n\n"
        "from sample_math import add\n\n\n"
        "class SampleMathTests(unittest.TestCase):\n"
        "    def test_adds_numbers(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n\n\n"
        "if __name__ == \"__main__\":\n"
        "    unittest.main()\n"
    )

    subprocess.run(["git", "init"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "sample@example.invalid"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "Sample Target"], cwd=target, check=True)
    subprocess.run(["git", "add", "."], cwd=target, check=True)
    status = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=target, check=False)
    if status.returncode:
        subprocess.run(["git", "commit", "-m", "Initial sample target"], cwd=target, check=True)

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
