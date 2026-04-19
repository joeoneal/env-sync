import click
from cli.commands.auth import register, login
from cli.commands.vault import push, pull
from cli.commands.team import create_team

@click.group()
def cli():
    """Env-Sync: Securely manage your .env files across teams."""
    pass

cli.add_command(register)
cli.add_command(login)
cli.add_command(push)
cli.add_command(pull)
cli.add_command(create_team)

if __name__ == '__main__':
    cli()