import shlex
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.config import Config
from agent_loop_factory.run_gates import run_gates


class RunGatesTests(unittest.TestCase):
    def test_run_gates_preserves_logs_and_honors_quoted_args(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            command = (
                f"{shlex.quote(sys.executable)} -c "
                "\"import sys; print('hello world'); print('err msg', file=sys.stderr)\""
            )
            config = Config(allowed_commands=[command], gates=[command])
            (tmp_path / "stdout.log").write_text("initial stdout\n")
            (tmp_path / "stderr.log").write_text("initial stderr\n")

            results = run_gates(config, tmp_path, tmp_path)

            self.assertTrue(results[0]["ok"])
            self.assertIn("initial stdout\nhello world\n", (tmp_path / "stdout.log").read_text())
            self.assertIn("initial stderr\nerr msg\n", (tmp_path / "stderr.log").read_text())


if __name__ == "__main__":
    unittest.main()
