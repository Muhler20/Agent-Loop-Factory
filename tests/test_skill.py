import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_loop_factory.skill import load_skill


class SkillTests(unittest.TestCase):
    def test_loads_valid_skill(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill_dir = root / "skills" / "failing-test-fix"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text("# Fix\n\nKeep diff small.\n")

            skill = load_skill(root, "failing-test-fix")

            self.assertEqual(skill.skill_name, "failing-test-fix")
            self.assertEqual(skill.skill_body, skill_file.read_text())
            self.assertEqual(skill.skill_file_path, str(skill_file))

    def test_missing_skill_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(ValueError, "skill file does not exist"):
                load_skill(Path(raw), "missing")

    def test_empty_skill_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            skill_dir = root / "skills" / "empty"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("\n\n")

            with self.assertRaisesRegex(ValueError, "skill file is empty"):
                load_skill(root, "empty")

    def test_unsafe_skill_names_fail_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ["../anything", "/absolute/path", "name/with/slash", "Upper"]:
                with self.subTest(name=name):
                    with self.assertRaisesRegex(ValueError, "skill name"):
                        load_skill(root, name)

    def test_valid_slug_names_work(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ["abc", "abc-123", "abc_123"]:
                with self.subTest(name=name):
                    skill_dir = root / "skills" / name
                    skill_dir.mkdir(parents=True)
                    (skill_dir / "SKILL.md").write_text("body\n")
                    self.assertEqual(load_skill(root, name).skill_name, name)


if __name__ == "__main__":
    unittest.main()
