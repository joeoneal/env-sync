import click
from cli.commands.auth import register, login, logout, whoami
from cli.commands.vault import push, pull
from cli.commands.team import create_team, add_member, list_teams, leave_team

CONTEXT_SETTINGS = dict(max_content_width=300)

class Ordered(click.Group):
    def list_commands(self, ctx):
        return ['register', 'login', 'logout', 'create-team', 'add-member', 'push', 'pull', 'list-teams', 'leave-team']

@click.group(context_settings=CONTEXT_SETTINGS, cls=Ordered)
def cli():
    """Env-Sync: Securely manage your .env files across teams."""
    pass

cli.add_command(register)
cli.add_command(login)
cli.add_command(push)
cli.add_command(pull)
cli.add_command(create_team)
cli.add_command(add_member)
cli.add_command(list_teams)
cli.add_command(leave_team)
cli.add_command(logout)
cli.add_command(whoami)

if __name__ == '__main__':
    cli()
