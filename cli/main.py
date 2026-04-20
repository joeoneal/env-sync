import click
from cli.commands.auth import register, login, logout, whoami
from cli.commands.vault import push, pull
from cli.commands.team import create_team, add_member, list_members, list_teams, leave_team, delete_team, promote, demote, team_shell

CONTEXT_SETTINGS = dict(max_content_width=300)

SECTION_ORDER = [
    "Getting Started",
    "Team Management",
    "Vault Operations",
    "Team Shell",
]

COMMAND_METADATA = {
    "register": {
        "section": "Getting Started",
        "description": "Create a new Env-Sync account.",
    },
    "login": {
        "section": "Getting Started",
        "description": "Log in and save your access token locally.",
    },
    "whoami": {
        "section": "Getting Started",
        "description": "Show the account currently logged in.",
    },
    "logout": {
        "section": "Getting Started",
        "description": "Remove your local login session.",
    },
    "create-team": {
        "section": "Team Management",
        "description": "Create a new team and initialize its encrypted vault.",
    },
    "list-members": {
        "section": "Team Management",
        "description": "List team members and their roles.",
    },
    "list-teams": {
        "section": "Team Management",
        "description": "List the teams you belong to.",
    },
    "add-member": {
        "section": "Team Management",
        "description": "Add a team member by email.",
    },
    "promote": {
        "section": "Team Management",
        "description": "Grant admin access to a team member.",
    },
    "demote": {
        "section": "Team Management",
        "description": "Remove admin access from a team member.",
    },
    "leave-team": {
        "section": "Team Management",
        "description": "Leave a team you belong to.",
    },
    "delete-team": {
        "section": "Team Management",
        "description": "Permanently delete a team you administer.",
    },
    "pull": {
        "section": "Vault Operations",
        "description": "Download and decrypt the team .env file.",
    },
    "push": {
        "section": "Vault Operations",
        "description": "Encrypt and upload the local .env file.",
    },
    "team": {
        "section": "Team Shell",
        "description": "Enter an interactive shell scoped to one team.",
    },
}


class Ordered(click.Group):
    def list_commands(self, ctx):
        return ['register', 'login', 'logout', 'whoami', 'create-team', 'add-member', 'list-members', 'promote', 'demote', 'push', 'pull', 'list-teams', 'leave-team', 'delete-team', 'team']

    def get_help_option(self, ctx):
        return None

    def parse_args(self, ctx, args):
        if args == ["help"]:
            click.echo(self.get_help(ctx))
            ctx.exit()
        return super().parse_args(ctx, args)

    def format_options(self, ctx, formatter):
        with formatter.section("Options"):
            formatter.write_dl([("help", "Show this message and exit.")])
        self.format_commands(ctx, formatter)

    def format_commands(self, ctx, formatter):
        commands = self.list_commands(ctx)
        grouped = {section: [] for section in SECTION_ORDER}

        for command_name in commands:
            metadata = COMMAND_METADATA.get(command_name)
            if not metadata:
                continue
            grouped[metadata["section"]].append((command_name, metadata))

        for section in SECTION_ORDER:
            rows = grouped.get(section, [])
            if not rows:
                continue
            with formatter.section(section):
                command_width = max(len(command_name) for command_name, _ in rows)
                for command_name, metadata in rows:
                    formatter.write(
                        f"  {command_name:<{command_width}}   {metadata['description']}\n"
                    )
                formatter.write("\n")

    def format_epilog(self, ctx, formatter):
        formatter.write_paragraph()
        formatter.write_text("Tips:")
        formatter.write_text("  Run `envsync COMMAND help` for command-specific options.")


@click.group(
    context_settings=CONTEXT_SETTINGS,
    cls=Ordered,
    invoke_without_command=True,
)
@click.pass_context
def cli(ctx):
    """Env-Sync: Securely manage encrypted .env files across teams."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


cli.add_command(register)
cli.add_command(login)
cli.add_command(push)
cli.add_command(pull)
cli.add_command(create_team)
cli.add_command(add_member)
cli.add_command(list_members)
cli.add_command(promote)
cli.add_command(demote)
cli.add_command(list_teams)
cli.add_command(leave_team)
cli.add_command(logout)
cli.add_command(whoami)
cli.add_command(delete_team)
cli.add_command(team_shell)

if __name__ == '__main__':
    cli()
