import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

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


if __name__ == "__main__":
    unittest.main()
