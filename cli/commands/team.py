import click
from halo import Halo

from cli.services.team_ops import (
    create_team_op,
    add_member_op,
    list_teams_op,
    leave_team_op,
    delete_team_op,
    promote_member_op,
    demote_member_op,
)
from cli.shell import run_team_shell


def render_result(op_result):
    fg = "green" if op_result["ok"] else "red"
    click.secho(op_result["message"], fg=fg)


@click.command()
@click.option('--name', required=True, help='The human-readable name of your new team (e.g. "Project Apollo")')
def create_team(name):
    """--name <team name>"""
    spinner = Halo(text=f'Creating team {name}...', spinner='flip')
    spinner.start()

    op_result = create_team_op(name)
    spinner.stop()

    if op_result["ok"]:
        slug = op_result["data"].get("slug")
        if not slug:
            render_result(op_result)
            return

        click.clear()
        click.secho("Success! ", fg="green", nl=False)
        click.secho(op_result["message"])
        click.secho(f"Your team name is: {slug}", fg="cyan", bold=True)
        click.secho(f"You can now push secrets using: envsync push --team {slug}", fg='black')
        return

    click.clear()
    render_result(op_result)


@click.command(name='add-member')
@click.option('--team', required=True, help='The slug of the team vault')
@click.option('--email', required=True, help='The registered email address of the user to add')
def add_member(team, email):
    """--team <team slug> --email <email of new member>"""
    render_result(add_member_op(team, email))


@click.command(name='list-teams')
def list_teams():
    """[no flags]"""
    op_result = list_teams_op()
    if not op_result["ok"]:
        render_result(op_result)
        return

    teams = op_result["data"].get("teams", [])
    if not teams:
        click.echo(op_result["message"])
        return

    click.echo("Your teams:")
    for team in teams:
        team_name = team.get('team_name', 'Unknown')
        team_slug = team.get('team_slug', 'unknown')
        role = team.get('role', 'member')
        joined_at = team.get('joined_at', 'unknown')
        click.echo(f"- {team_name} ({team_slug}) [{role}] joined {joined_at}")


@click.command(name='leave-team')
@click.option('--team', required=True, help='The slug of the team you would like to leave')
def leave_team(team):
    """--team <team slug>"""
    render_result(leave_team_op(team))


@click.command(name='delete-team')
@click.option('--team', required=True, help='The slug of the team that you would like to delete')
def delete_team(team):
    """--team <team slug>"""
    warning = click.style('WARNING: This is a destructive action. Deleted teams cannot be recovered. Are you sure you would like to proceed?', fg='red', bold=True)

    if click.confirm(warning):
        op_result = delete_team_op(team)
        click.clear()
        render_result(op_result)
    else:
        click.echo('Aborted.')


@click.command(name='promote')
@click.option('--team', required=True, help='The slug of the team')
@click.option('--email', required=True, help='The registered email address of the member to promote')
def promote(team, email):
    """--team <team slug> --email <member email>"""
    render_result(promote_member_op(team, email))


@click.command(name='demote')
@click.option('--team', required=True, help='The slug of the team')
@click.option('--email', required=True, help='The registered email address of the admin to demote')
def demote(team, email):
    """--team <team slug> --email <member email>"""
    render_result(demote_member_op(team, email))


@click.command(name="team")
@click.argument("team_slug")
def team_shell(team_slug):
    """team <team slug>"""
    run_team_shell(team_slug)
