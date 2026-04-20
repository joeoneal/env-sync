import os
import click
from cli.utils.api import (
    get_token,
    create_team_api,
    list_teams_api,
    leave_team_api,
    pull_vault_api,
    prepare_add_member_api,
    confirm_add_member_api,
)
from cli.utils.crypto import CryptoEngine
from cli.utils.config import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE


def get_error_message(response):
    if response is None:
        return 'No response from server'

    try:
        payload = response.json()
    except ValueError:
        return response.text or f'Server returned status {response.status_code}'

    return payload.get('error') or payload.get('message') or response.text or f'Server returned status {response.status_code}'

@click.command()
@click.option('--name', required=True, help='The human-readable name of your new team (e.g. "Project Apollo")')
def create_team(name):
    """--name <team name>"""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to create a team.", fg="red")
        return

    # 1. Read the local .env file (or default to empty if it doesn't exist yet)
    if not os.path.exists('.env'):
        click.secho("No .env file found in current directory. Initializing an empty vault.", fg="yellow")
        env_text = ""
    else:
        with open('.env', 'r') as f:
            env_text = f.read()

    # 2. Grab the local Public Key (to create the Admin's envelope)
    if not os.path.exists(PUBLIC_KEY_FILE):
        click.secho("Error: Local public key not found. Please log in or generate keys first.", fg="red")
        return
        
    with open(PUBLIC_KEY_FILE, 'r') as f:
        public_key_pem = f.read()

    click.echo("Generating end-to-end encryption keys and wrapping payload...")

    try:
        # 3. The Cryptography Engine
        vault_key = CryptoEngine.generate_vault_key()
        env_blob = CryptoEngine.encrypt_env(env_text, vault_key)
        encrypted_key = CryptoEngine.wrap_key(vault_key, public_key_pem)
        
        click.echo(f"Creating team '{name}' on server...")
        
        # 4. Send it up using our clean API layer
        res = create_team_api(name, env_blob, encrypted_key)
        
        if res is not None and res.status_code == 201:
            data = res.json()
            slug = data.get('slug')
            click.secho(f"Success! Team created and vault secured.", fg="green")
            click.secho(f"Your team name is: {slug}", fg="cyan", bold=True)
            click.echo(f"You can now push secrets using: envsync push --team {slug}")
        else:
            msg = get_error_message(res)
            click.secho(f"Failed to create team: {msg}", fg="red")
            
    except Exception as e:
        click.secho(f"An unexpected error occurred: {str(e)}", fg="red")

@click.command(name='add-member')
@click.option('--team', required=True, help='The slug of the team vault')
@click.option('--email', required=True, help='The registered email address of the user to add')
def add_member(team, email):
    """--team <team slug> --email <email of new member>"""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to add a team member.", fg="red")
        return

    if not os.path.exists(PRIVATE_KEY_FILE):
        click.secho("Error: Private key not found. Please log in again to generate your keys.", fg="red")
        return

    with open(PRIVATE_KEY_FILE, 'r') as f:
        private_key_pem = f.read()

    click.echo("Looking up user and verifying admin access...")
    prepare_res = prepare_add_member_api(team, email)
    if prepare_res is None or prepare_res.status_code != 200:
        msg = get_error_message(prepare_res)
        click.secho(f"Failed to prepare member add: {msg}", fg="red")
        return

    prepare_data = prepare_res.json()
    target_user = prepare_data.get('target_user', {})
    target_user_id = target_user.get('id')
    target_public_key = target_user.get('public_key')
    target_email = target_user.get('email', email)

    if not target_user_id or not target_public_key:
        click.secho("Error: Server returned incomplete user information.", fg="red")
        return

    click.echo("Fetching your vault access envelope...")
    pull_res = pull_vault_api(team)
    if pull_res is None or pull_res.status_code != 200:
        msg = get_error_message(pull_res)
        click.secho(f"Failed to fetch vault data: {msg}", fg="red")
        return

    vault_data = pull_res.json()
    encrypted_key = vault_data.get('encrypted_key')
    if not encrypted_key:
        click.secho("Error: Server returned incomplete vault data.", fg="red")
        return

    click.echo("Wrapping team key for new member...")
    try:
        vault_key = CryptoEngine.unwrap_key(encrypted_key, private_key_pem)
        wrapped_key_for_member = CryptoEngine.wrap_key(vault_key, target_public_key)
    except Exception as e:
        click.secho(f"Failed to prepare member access: {str(e)}", fg="red")
        return

    click.echo("Adding member to team...")
    confirm_res = confirm_add_member_api(team, target_user_id, wrapped_key_for_member)
    if confirm_res is not None and confirm_res.status_code == 201:
        click.secho(f"Success! {target_email} was added to {team}.", fg="green")
    else:
        msg = get_error_message(confirm_res)
        click.secho(f"Failed to add member: {msg}", fg="red")

@click.command(name='list-teams')
def list_teams():
    """[no flags]"""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to list teams.", fg="red")
        return

    response = list_teams_api()
    if response is None or response.status_code != 200:
        msg = get_error_message(response)
        click.secho(f"Failed to list teams: {msg}", fg="red")
        return

    teams = response.json().get('teams', [])
    if not teams:
        click.echo("You are not a member of any teams yet.")
        return

    click.echo("Your teams:")
    for team in teams:
        team_name = team.get('team_name', 'Unknown')
        team_slug = team.get('team_slug', 'unknown')
        role = team.get('role', 'member')
        joined_at = team.get('joined_at', 'unknown')
        click.echo(f"- {team_name} ({team_slug}) [{role}] joined {joined_at}")

@click.command(name='leave-team')
@click.option('--team', required=True, help='The slug of the team to leave')
def leave_team(team):
    """--team <team slug>"""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to leave a team.", fg="red")
        return

    click.echo(f"Leaving team '{team}'...")
    response = leave_team_api(team)
    if response is None or response.status_code != 200:
        msg = get_error_message(response)
        click.secho(f"Failed to leave team: {msg}", fg="red")
        return

    payload = response.json()
    if payload.get('deleted_team'):
        click.secho(f"Success! You left {team}, and the empty team was deleted.", fg="green")
    else:
        click.secho(f"Success! You left {team}.", fg="green")

