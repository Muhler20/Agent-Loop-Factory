import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.config import Config, detect_gates, load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            agent = tmp_path / ".agent"
            agent.mkdir()
            (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
            config = load_config(agent / "config.yaml")
            self.assertIsInstance(config, Config)
            self.assertEqual(config.target_repo_path, ".")
            self.assertEqual(config.implementer, "none")
            self.assertEqual(config.codex_exec_args, [])
            self.assertFalse(config.auto_merge)
            self.assertEqual(
                config.gates,
                [
                    {"name": "pytest", "command": "pytest", "required": True},
                    {"name": "ruff check .", "command": "ruff check .", "required": True},
                    {"name": "mypy .", "command": "mypy .", "required": True},
                ],
            )

    def test_detect_node_gates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            (tmp_path / "package.json").write_text("{}\n")
            self.assertEqual(detect_gates(tmp_path), ["npm test", "npm run lint", "npm run typecheck"])

    def test_load_config_parses_empty_codex_args(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            agent = tmp_path / ".agent"
            agent.mkdir()
            (agent / "config.yaml").write_text("codex_exec_args: []\n")
            self.assertEqual(load_config(agent / "config.yaml").codex_exec_args, [])

    def test_string_gate_normalizes_to_required_gate(self) -> None:
        config = loaded_config('gates:\n  - "python3 -m unittest discover -s tests"\n')

        self.assertEqual(
            config.gates,
            [
                {
                    "name": "python3 -m unittest discover -s tests",
                    "command": "python3 -m unittest discover -s tests",
                    "required": True,
                }
            ],
        )

    def test_named_gate_object_works(self) -> None:
        config = loaded_config(
            'gates:\n'
            "  - name: unit tests\n"
            '    command: "python3 -m unittest discover -s tests"\n'
            "    required: true\n"
        )

        self.assertEqual(
            config.gates,
            [{"name": "unit tests", "command": "python3 -m unittest discover -s tests", "required": True}],
        )

    def test_gate_object_defaults_required_and_name(self) -> None:
        config = loaded_config('gates:\n  - command: "python3 -m unittest discover -s tests"\n')

        self.assertEqual(
            config.gates,
            [
                {
                    "name": "python3 -m unittest discover -s tests",
                    "command": "python3 -m unittest discover -s tests",
                    "required": True,
                }
            ],
        )

    def test_gate_missing_command_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing command"):
            loaded_config("gates:\n  - name: unit tests\n")

    def test_gate_non_string_command_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "command must be a string"):
            loaded_config("gates:\n  - command: 123\n")

    def test_gate_non_string_name_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "name must be a string"):
            loaded_config('gates:\n  - name: 123\n    command: "pytest"\n')

    def test_gate_non_boolean_required_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "required must be boolean"):
            loaded_config('gates:\n  - command: "pytest"\n    required: yes\n')


def loaded_config(text: str) -> Config:
    with tempfile.TemporaryDirectory() as raw:
        tmp_path = Path(raw)
        agent = tmp_path / ".agent"
        agent.mkdir()
        (agent / "config.yaml").write_text(text)
        return load_config(agent / "config.yaml")


if __name__ == "__main__":
    unittest.main()
