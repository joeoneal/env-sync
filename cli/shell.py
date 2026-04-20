import shlex

import click

from cli.commands.auth import whoami
from cli.services.team_ops import (
    ensure_team_access,
    add_member_op,
    promote_member_op,
    demote_member_op,
    leave_team_op,
    delete_team_op,
)
from cli.services.vault_ops import push_vault_op, pull_vault_op


def print_shell_help():
    click.echo("Available commands:")
    click.echo("  push")
    click.echo("  pull")
    click.echo("  add-member --email <email>")
    click.echo("  promote --email <email>")
    click.echo("  demote --email <email>")
    click.echo("  leave-team")
    click.echo("  delete-team")
    click.echo("  whoami")
    click.echo("  help")
    click.echo("  exit")
    click.echo("  quit")


def parse_email_arg(args):
    if len(args) != 2 or args[0] != "--email":
        return None
    return args[1]


def print_result(op_result):
    fg = "green" if op_result["ok"] else "red"
    click.secho(op_result["message"], fg=fg)


def confirm_delete(team_slug):
    warning = click.style(
        f"WARNING: This will permanently delete team '{team_slug}'.",
        fg="red",
        bold=True,
    )
    click.echo(warning)
    typed = click.prompt("Type the team slug to confirm", default="", show_default=False)
    return typed == team_slug


def run_team_shell(team_slug):
    access = ensure_team_access(team_slug)
    if not access["ok"]:
        print_result(access)
        return

    click.secho(f"Entered team shell for {team_slug}. Type 'help' for commands.", fg="cyan")

    while True:
        try:
            raw = input(f"{team_slug}> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo()
            break

        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as e:
            click.secho(f"Parse error: {str(e)}", fg="red")
            continue

        command = parts[0]
        args = parts[1:]

        if command in ("exit", "quit"):
            break

        if command == "help":
            print_shell_help()
            continue

        if command == "whoami":
            whoami.main(args=[], standalone_mode=False)
            continue

        if command == "push":
            print_result(push_vault_op(team_slug))
            continue

        if command == "pull":
            print_result(pull_vault_op(team_slug))
            continue

        if command == "add-member":
            email = parse_email_arg(args)
            if not email:
                click.secho("Usage: add-member --email <email>", fg="yellow")
                continue
            print_result(add_member_op(team_slug, email))
            continue

        if command == "promote":
            email = parse_email_arg(args)
            if not email:
                click.secho("Usage: promote --email <email>", fg="yellow")
                continue
            print_result(promote_member_op(team_slug, email))
            continue

        if command == "demote":
            email = parse_email_arg(args)
            if not email:
                click.secho("Usage: demote --email <email>", fg="yellow")
                continue
            print_result(demote_member_op(team_slug, email))
            continue

        if command == "leave-team":
            print_result(leave_team_op(team_slug))
            break

        if command == "delete-team":
            if not confirm_delete(team_slug):
                click.echo("Aborted.")
                continue
            print_result(delete_team_op(team_slug))
            break

        click.secho(f"Unknown command: {command}", fg="red")
        click.echo("Type 'help' to see available commands.")
