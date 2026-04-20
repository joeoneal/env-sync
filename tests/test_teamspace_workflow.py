import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from click.testing import CliRunner

from cli.main import cli
from cli.services import team_ops
from cli.shell import run_team_shell


class TeamOpsTests(unittest.TestCase):
    def test_ensure_team_access_returns_matching_team(self):
        with patch("cli.services.team_ops.list_teams_op", return_value={
            "ok": True,
            "message": "Teams loaded.",
            "data": {
                "teams": [
                    {"team_slug": "project-apollo", "role": "admin"},
                    {"team_slug": "other-team", "role": "member"},
                ]
            },
        }):
            result = team_ops.ensure_team_access("project-apollo")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["team"]["team_slug"], "project-apollo")

    def test_ensure_team_access_rejects_unknown_team(self):
        with patch("cli.services.team_ops.list_teams_op", return_value={
            "ok": True,
            "message": "Teams loaded.",
            "data": {"teams": [{"team_slug": "other-team"}]},
        }):
            result = team_ops.ensure_team_access("project-apollo")

        self.assertFalse(result["ok"])
        self.assertIn("project-apollo", result["message"])

    def test_promote_member_op_uses_role_update_api(self):
        response = Mock(status_code=200)
        with patch("cli.services.team_ops.get_token", return_value="token"), patch(
            "cli.services.team_ops.update_member_role_api", return_value=response
        ) as update_member_role_api:
            result = team_ops.promote_member_op("project-apollo", "member@example.com")

        self.assertTrue(result["ok"])
        update_member_role_api.assert_called_once_with(
            "project-apollo", "member@example.com", "admin"
        )

    def test_demote_member_op_requires_login(self):
        with patch("cli.services.team_ops.get_token", return_value=None):
            result = team_ops.demote_member_op("project-apollo", "member@example.com")

        self.assertFalse(result["ok"])
        self.assertIn("logged in", result["message"])

    def test_list_members_op_returns_members(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "members": [
                {"email": "admin@example.com", "role": "admin"},
                {"email": "member@example.com", "role": "member"},
            ]
        }

        with patch("cli.services.team_ops.get_token", return_value="token"), patch(
            "cli.services.team_ops.list_members_api", return_value=response
        ) as list_members_api:
            result = team_ops.list_members_op("project-apollo")

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["data"]["members"]), 2)
        list_members_api.assert_called_once_with("project-apollo")


class TeamShellTests(unittest.TestCase):
    def test_shell_dispatches_promote_with_active_team_context(self):
        stdout = io.StringIO()
        with patch("cli.shell.ensure_team_access", return_value={"ok": True, "message": "", "data": {}}), patch(
            "cli.shell.promote_member_op",
            return_value={"ok": True, "message": "promoted", "data": {}},
        ) as promote_member_op, patch(
            "builtins.input",
            side_effect=["promote --email member@example.com", "exit"],
        ):
            with redirect_stdout(stdout):
                run_team_shell("project-apollo")

        promote_member_op.assert_called_once_with("project-apollo", "member@example.com")

    def test_shell_delete_team_requires_typed_confirmation(self):
        stdout = io.StringIO()
        with patch("cli.shell.ensure_team_access", return_value={"ok": True, "message": "", "data": {}}), patch(
            "cli.shell.delete_team_op",
            return_value={"ok": True, "message": "deleted", "data": {}},
        ) as delete_team_op, patch(
            "builtins.input",
            side_effect=["delete-team", "exit"],
        ), patch(
            "cli.shell.click.prompt",
            return_value="project-apollo",
        ):
            with redirect_stdout(stdout):
                run_team_shell("project-apollo")

        delete_team_op.assert_called_once_with("project-apollo")

    def test_shell_unknown_command_shows_help_hint(self):
        stdout = io.StringIO()
        with patch("cli.shell.ensure_team_access", return_value={"ok": True, "message": "", "data": {}}), patch(
            "builtins.input",
            side_effect=["wat", "exit"],
        ):
            with redirect_stdout(stdout):
                run_team_shell("project-apollo")

        output = stdout.getvalue()
        self.assertIn("Unknown command: wat", output)
        self.assertIn("Type 'help' to see available commands.", output)

    def test_shell_list_members_prints_team_members(self):
        stdout = io.StringIO()
        with patch("cli.shell.ensure_team_access", return_value={"ok": True, "message": "", "data": {}}), patch(
            "cli.shell.list_members_op",
            return_value={
                "ok": True,
                "message": "Members loaded.",
                "data": {
                    "members": [
                        {"email": "admin@example.com", "role": "admin", "joined_at": "today"},
                        {"email": "member@example.com", "role": "member", "joined_at": "today"},
                    ]
                },
            },
        ), patch(
            "builtins.input",
            side_effect=["list-members", "exit"],
        ):
            with redirect_stdout(stdout):
                run_team_shell("project-apollo")

        output = stdout.getvalue()
        self.assertIn("Members of project-apollo:", output)
        self.assertIn("admin@example.com [admin]", output)
        self.assertIn("member@example.com [member]", output)


class CliHelpTests(unittest.TestCase):
    def test_top_level_help_groups_commands_and_examples(self):
        runner = CliRunner()

        result = runner.invoke(cli, ["help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Getting Started", result.output)
        self.assertIn("Team Management", result.output)
        self.assertIn("Vault Operations", result.output)
        self.assertIn("Team Shell", result.output)
        self.assertIn("register   Create a new Env-Sync account.", result.output)
        self.assertIn("create-team", result.output)
        self.assertIn("Create a new team and initialize its encrypted vault.", result.output)
        self.assertIn("list-members", result.output)
        self.assertIn("List team members and their roles.", result.output)
        self.assertIn("team   Enter an interactive shell scoped to one team.", result.output)
        self.assertIn("Run `envsync COMMAND help` for command-specific options.", result.output)

    def test_command_help_includes_description_and_example(self):
        runner = CliRunner()

        result = runner.invoke(cli, ["promote", "help"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Grant admin access to a team member.", result.output)
        self.assertIn(
            "envsync promote --team project-apollo --email bob@example.com",
            result.output,
        )


if __name__ == "__main__":
    unittest.main()
