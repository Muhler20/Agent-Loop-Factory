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
            self.assertEqual(results[0]["name"], command)
            self.assertEqual(results[0]["command"], command)
            self.assertTrue(results[0]["required"])
            self.assertEqual(results[0]["returncode"], 0)
            self.assertIn("initial stdout\nhello world\n", (tmp_path / "stdout.log").read_text())
            self.assertIn("initial stderr\nerr msg\n", (tmp_path / "stderr.log").read_text())

    def test_named_required_gate_records_shape(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            command = f"{shlex.quote(sys.executable)} -c \"print('ok')\""
            config = Config(allowed_commands=[command], gates=[{"name": "unit tests", "command": command, "required": True}])

            results = run_gates(config, tmp_path, tmp_path)

            self.assertEqual(results[0]["name"], "unit tests")
            self.assertEqual(results[0]["command"], command)
            self.assertTrue(results[0]["required"])
            self.assertTrue(results[0]["ok"])
            self.assertEqual(results[0]["returncode"], 0)
            self.assertIsNone(results[0]["warning"])

    def test_optional_failing_gate_records_warning(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            command = f"{shlex.quote(sys.executable)} -c \"raise SystemExit(7)\""
            config = Config(allowed_commands=[command], gates=[{"name": "lint", "command": command, "required": False}])

            results = run_gates(config, tmp_path, tmp_path)

            self.assertEqual(results[0]["name"], "lint")
            self.assertFalse(results[0]["required"])
            self.assertFalse(results[0]["ok"])
            self.assertEqual(results[0]["returncode"], 7)
            self.assertEqual(results[0]["warning"], "optional gate failed")

    def test_allowed_commands_checks_object_command_field(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            command = f"{shlex.quote(sys.executable)} -c \"print('ok')\""
            config = Config(allowed_commands=["different command"], gates=[{"name": "unit tests", "command": command}])

            results = run_gates(config, tmp_path, tmp_path)

            self.assertFalse(results[0]["ok"])
            self.assertIn(f"command not allowed by config: {command!r}", str(results[0]["warning"]))
            self.assertIn("allowed_commands uses exact command strings", str(results[0]["warning"]))
            self.assertIn("different command", str(results[0]["warning"]))
            self.assertEqual(results[0]["returncode"], None)

    def test_allowed_commands_requires_exact_command_string(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            config = Config(allowed_commands=["python3 -m unittest discover -s tests"], gates=["python3  -m unittest discover -s tests"])

            results = run_gates(config, tmp_path, tmp_path, dry_run=True)

            self.assertFalse(results[0]["ok"])
            self.assertIn("allowed_commands uses exact command strings", str(results[0]["warning"]))

    def test_named_gate_checks_command_not_name(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            config = Config(allowed_commands=["unit tests"], gates=[{"name": "unit tests", "command": "python3 -m unittest"}])

            results = run_gates(config, tmp_path, tmp_path, dry_run=True)

            self.assertFalse(results[0]["ok"])
            self.assertIn("python3 -m unittest", str(results[0]["warning"]))


if __name__ == "__main__":
    unittest.main()
