import click
from halo import Halo

from cli.help_command import HelpCommand
from cli.services.vault_ops import push_vault_op, pull_vault_op


def render_result(op_result):
    fg = "green" if op_result["ok"] else "red"
    click.secho(op_result["message"], fg=fg)


@click.command(cls=HelpCommand, short_help='Encrypt and upload the local .env file.')
@click.option('--team', required=True, help='The team vault name')
def push(team):
    """
    Encrypt and upload the local .env file.

    Example:
      envsync push --team project-apollo
    """
    spinner = Halo(text=f"Pushing encrypted vault for {team}...", spinner='flip')
    spinner.start()
    op_result = push_vault_op(team)
    spinner.stop()
    render_result(op_result)


@click.command(cls=HelpCommand, short_help='Download and decrypt the team .env file.')
@click.option('--team', required=True, help='The team vault name')
def pull(team):
    """
    Download and decrypt the team .env file.

    Example:
      envsync pull --team project-apollo
    """
    spinner = Halo(text=f"Pulling encrypted vault for {team}...", spinner='flip')
    spinner.start()
    op_result = pull_vault_op(team)
    spinner.stop()
    render_result(op_result)
