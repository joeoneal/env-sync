import click

from cli.services.vault_ops import push_vault_op, pull_vault_op


def render_result(op_result):
    fg = "green" if op_result["ok"] else "red"
    click.secho(op_result["message"], fg=fg)


@click.command()
@click.option('--team', required=True, help='The slug of the team vault')
def push(team):
    """--team <team slug>"""
    render_result(push_vault_op(team))


@click.command()
@click.option('--team', required=True, help='The slug of the team vault')
def pull(team):
    """--team <team slug>"""
    render_result(pull_vault_op(team))
