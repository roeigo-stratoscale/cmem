"""End-to-end tests: every case runs bin/cmem against a fake HOME. Run: python3 -m unittest discover tests"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

CMEM = Path(__file__).resolve().parent.parent / "bin" / "cmem"
AI_FACTORY_BLOCK = ("<!-- BEGIN ai-factory team rules: managed by another plugin -->\n"
                    "@~/.claude/ai-factory/team-rules.md\n<!-- END ai-factory team rules -->\n")
OLD_CMEM_LINES = "# Lessons that apply in every project (managed by cmem)\n@~/.claude/cmem/lessons.md\n"


class FakeHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith(("CMEM_", "CLAUDE_"))}
        self.env["HOME"] = str(self.home)
        self.env["GIT_CONFIG_GLOBAL"] = str(self.home / ".gitconfig")
        (self.home / ".gitconfig").write_text("[user]\n\tname = t\n\temail = t@example.com\n")

    def tearDown(self):
        self.tmp.cleanup()

    def cmem(self, *args, check=True, cwd=None, extra_env=None):
        result = subprocess.run(["python3", str(CMEM), *args], env={**self.env, **(extra_env or {})},
                                cwd=cwd or self.home, capture_output=True, text=True)
        if check and result.returncode:
            self.fail(f"cmem {' '.join(args)} failed: {result.stdout}{result.stderr}")
        return result

    def claude_md(self):
        return (self.home / ".claude" / "CLAUDE.md").read_text()

    def set_up_layers(self, general=True, workplace=True):
        if general:
            self.cmem("init-layer", "general", "~/claude-memory", "--apply")
        if workplace:
            self.cmem("init-layer", "workplace", "~/claude-memory-acme", "--name", "acme", "--owner", "acme-org",
                      "--apply")
        args = (["--general", "~/claude-memory"] if general else []) + \
               (["--workplace", "~/claude-memory-acme"] if workplace else [])
        self.cmem("config", *args, "--apply")

    def make_checkout(self, name="shop", owner="acme-org"):
        checkout = self.home / "work" / name
        checkout.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(checkout)], check=True, env=self.env)
        subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin",
                        f"git@github.com:{owner}/{name}.git"], check=True, env=self.env)
        return checkout

    def project_memory(self, checkout):
        slug = "".join(char if char.isalnum() else "-" for char in str(checkout.resolve()))
        return self.home / ".claude" / "projects" / slug / "memory"


class NotSetUp(FakeHome):
    def test_session_start_asks_for_setup_once(self):
        out = self.cmem("session-start").stdout
        self.assertIn("/cmem:setup", out)

    def test_commands_refuse_until_set_up(self):
        result = self.cmem("sync", "--apply", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not set up", result.stdout)
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())

    def test_doctor_reports_missing_config(self):
        items = {item["key"]: item for item in json.loads(self.cmem("doctor", "--json").stdout)}
        self.assertEqual(items["config"]["status"], "missing")
        self.assertEqual(items["general-layer"]["status"], "missing")

    def test_dry_run_changes_nothing(self):
        self.cmem("init-layer", "general", "~/claude-memory")
        self.cmem("config", "--general", "~/claude-memory")
        self.assertFalse((self.home / "claude-memory").exists())
        self.assertFalse((self.home / ".config" / "cmem" / "config.json").exists())


class SetUp(FakeHome):
    def test_init_layer_never_overwrites(self):
        self.set_up_layers()
        readme = self.home / "claude-memory" / "README.md"
        readme.write_text("mine\n")
        self.cmem("init-layer", "general", "~/claude-memory", "--apply")
        self.assertEqual(readme.read_text(), "mine\n")
        workplace = json.loads((self.home / "claude-memory-acme" / "workplace.json").read_text())
        self.assertEqual(workplace["github_owners"], ["acme-org"])
        self.assertTrue(any("acme" in pattern for pattern in workplace["internal_patterns"]))

    def test_claude_md_block_coexists_with_other_blocks(self):
        claude_dir = self.home / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("# My rules\nBe brief.\n\n" + AI_FACTORY_BLOCK)
        self.set_up_layers()
        self.cmem("sync", "--apply")
        self.cmem("sync", "--apply")
        text = self.claude_md()
        self.assertIn("# My rules\nBe brief.\n", text)
        self.assertIn(AI_FACTORY_BLOCK, text)
        self.assertEqual(text.count("<!-- BEGIN cmem"), 1)
        self.assertEqual(text.count("@~/.claude/cmem/lessons.md"), 1)

    def test_old_unmarked_lines_are_migrated(self):
        claude_dir = self.home / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("Be brief.\n" + OLD_CMEM_LINES + AI_FACTORY_BLOCK)
        self.set_up_layers()
        self.cmem("sync", "--apply")
        text = self.claude_md()
        self.assertNotIn("# Lessons that apply in every project", text)
        self.assertEqual(text.count("@~/.claude/cmem/lessons.md"), 1)
        self.assertIn(AI_FACTORY_BLOCK, text)
        self.assertIn("Be brief.\n", text)

    def test_workplace_lesson_wins_and_dropping_workplace_falls_back(self):
        self.set_up_layers()
        (self.home / "claude-memory" / "lessons" / "habit.md").write_text("generic\n")
        (self.home / "claude-memory-acme" / "lessons" / "habit.md").write_text("detailed\n")
        self.cmem("sync", "--apply")
        index = (self.home / ".claude" / "cmem" / "lessons.md").read_text()
        self.assertIn("@~/claude-memory-acme/lessons/habit.md", index)
        self.cmem("config", "--workplace", "none", "--apply")
        self.cmem("sync", "--apply")
        index = (self.home / ".claude" / "cmem" / "lessons.md").read_text()
        self.assertIn("@~/claude-memory/lessons/habit.md", index)

    def test_workplace_only_teammate(self):
        self.set_up_layers(general=False)
        (self.home / "claude-memory-acme" / "lessons" / "rule.md").write_text("x\n")
        self.cmem("sync", "--apply")
        self.assertIn("rule.md", (self.home / ".claude" / "cmem" / "lessons.md").read_text())
        self.assertIn("clean", self.cmem("check").stdout)

    def test_session_start_links_project_silently(self):
        self.set_up_layers()
        checkout = self.make_checkout()
        memory = self.project_memory(checkout)
        memory.mkdir(parents=True)
        (memory / "note.md").write_text("n\n")
        out = self.cmem("session-start", cwd=checkout, extra_env={"CLAUDE_PROJECT_DIR": str(checkout)}).stdout
        self.assertEqual(out, "")
        self.assertTrue(memory.is_symlink())
        self.assertTrue((self.home / "claude-memory-acme" / "repos" / "acme-org" / "shop" / "memory" / "note.md").exists())

    def test_sync_leaves_other_tools_skill_links_alone(self):
        self.set_up_layers()
        skills = self.home / ".claude" / "skills"
        other = self.home / ".agents" / "skills" / "other-tool"
        other.mkdir(parents=True)
        skills.mkdir(parents=True)
        (skills / "other-tool").symlink_to("../../.agents/skills/other-tool")
        (skills / "dangling").symlink_to("../../nowhere/skills/dangling")
        self.cmem("sync", "--apply")
        self.assertTrue((skills / "other-tool").is_symlink())
        self.assertTrue((skills / "dangling").is_symlink())

    def test_session_start_can_be_disabled(self):
        self.set_up_layers()
        self.cmem("session-start", extra_env={"CMEM_DISABLE": "1"})
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())


class Remove(FakeHome):
    def test_remove_restores_real_folders_and_keeps_other_blocks(self):
        claude_dir = self.home / ".claude"
        claude_dir.mkdir()
        (claude_dir / "CLAUDE.md").write_text("Be brief.\n" + AI_FACTORY_BLOCK)
        self.set_up_layers()
        checkout = self.make_checkout()
        memory = self.project_memory(checkout)
        memory.mkdir(parents=True)
        (memory / "note.md").write_text("n\n")
        skill = self.home / "claude-memory" / "skills" / "tidy"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("s\n")
        self.cmem("link", str(checkout), "--apply")
        self.cmem("sync", "--apply")
        self.assertTrue((claude_dir / "skills" / "tidy").is_symlink())

        self.cmem("remove")  # dry run
        self.assertTrue(memory.is_symlink())
        self.cmem("remove", "--apply")
        self.assertFalse(memory.is_symlink())
        self.assertEqual((memory / "note.md").read_text(), "n\n")
        self.assertFalse((claude_dir / "skills" / "tidy").is_symlink())
        self.assertTrue((claude_dir / "skills" / "tidy" / "SKILL.md").exists())
        self.assertEqual(self.claude_md(), "Be brief.\n" + AI_FACTORY_BLOCK)
        self.assertTrue((self.home / "claude-memory-acme" / "repos" / "acme-org" / "shop" / "memory" / "note.md").exists())


if __name__ == "__main__":
    unittest.main()
