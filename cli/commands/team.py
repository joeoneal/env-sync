import click
from halo import Halo

from cli.help_command import HelpCommand
from cli.services.team_ops import (
    create_team_op,
    add_member_op,
    list_members_op,
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


@click.command(cls=HelpCommand, short_help='Create a new team and initialize its encrypted vault.')
@click.option('--name', required=True, help='The human-readable name of your new team (e.g. "Project Apollo")')
def create_team(name):
    """
    Create a new team and initialize its encrypted vault.

    Example:
      envsync create-team --name "Project Apollo"
    """
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


@click.command(name='add-member', cls=HelpCommand, short_help='Add a team member by email.')
@click.option('--team', required=True, help='The team vault name')
@click.option('--email', required=True, help='The registered email address of the user to add')
def add_member(team, email):
    """
    Add a team member by email.

    Example:
      envsync add-member --team project-apollo --email bob@example.com
    """
    render_result(add_member_op(team, email))


@click.command(name='list-teams', cls=HelpCommand, short_help='List the teams you belong to.')
def list_teams():
    """
    List the teams you belong to.

    Example:
      envsync list-teams
    """
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


@click.command(name='list-members', cls=HelpCommand, short_help='List team members and their roles.')
@click.option('--team', required=True, help='The team vault name')
def list_members(team):
    """
    List team members and their roles.

    Example:
      envsync list-members --team project-apollo
    """
    op_result = list_members_op(team)
    if not op_result["ok"]:
        render_result(op_result)
        return

    members = op_result["data"].get("members", [])
    if not members:
        click.echo(op_result["message"])
        return

    click.echo(f"Members of {team}:")
    for member in members:
        email = member.get("email", "unknown")
        role = member.get("role", "member")
        joined_at = member.get("joined_at", "unknown")
        click.echo(f"- {email} [{role}] joined {joined_at}")


@click.command(name='leave-team', cls=HelpCommand, short_help='Leave a team you belong to.')
@click.option('--team', required=True, help='The team you would like to leave')
def leave_team(team):
    """
    Leave a team you belong to.

    Example:
      envsync leave-team --team project-apollo
    """
    render_result(leave_team_op(team))


@click.command(name='delete-team', cls=HelpCommand, short_help='Permanently delete a team you administer.')
@click.option('--team', required=True, help='The team that you would like to delete')
def delete_team(team):
    """
    Permanently delete a team you administer.

    Example:
      envsync delete-team --team project-apollo
    """
    warning = click.style('WARNING: This is a destructive action. Deleted teams cannot be recovered. Are you sure you would like to proceed?', fg='red', bold=True)

    if click.confirm(warning):
        op_result = delete_team_op(team)
        click.clear()
        render_result(op_result)
    else:
        click.echo('Aborted.')


@click.command(name='promote', cls=HelpCommand, short_help='Grant admin access to a team member.')
@click.option('--team', required=True, help='The team name')
@click.option('--email', required=True, help='The registered email address of the member to promote')
def promote(team, email):
    """
    Grant admin access to a team member.

    Example:
      envsync promote --team project-apollo --email bob@example.com
    """
    render_result(promote_member_op(team, email))


@click.command(name='demote', cls=HelpCommand, short_help='Remove admin access from a team member.')
@click.option('--team', required=True, help='The team name')
@click.option('--email', required=True, help='The registered email address of the admin to demote')
def demote(team, email):
    """
    Remove admin access from a team member.

    Example:
      envsync demote --team project-apollo --email bob@example.com
    """
    render_result(demote_member_op(team, email))


@click.command(name="team", cls=HelpCommand, short_help='Enter an interactive shell scoped to one team.')
@click.argument("team_slug")
def team_shell(team_slug):
    """
    Enter an interactive shell scoped to one team.

    Example:
      envsync team project-apollo
    """
    run_team_shell(team_slug)
