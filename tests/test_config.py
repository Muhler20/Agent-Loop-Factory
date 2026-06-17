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
            self.assertFalse(config.auto_merge)
            self.assertEqual(config.gates, ["pytest", "ruff check .", "mypy ."])

    def test_detect_node_gates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            tmp_path = Path(raw)
            (tmp_path / "package.json").write_text("{}\n")
            self.assertEqual(detect_gates(tmp_path), ["npm test", "npm run lint", "npm run typecheck"])


if __name__ == "__main__":
    unittest.main()
