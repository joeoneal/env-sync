import click
import requests
from cli.utils.config import BASE_URL
from cli.utils.api import get_token

@click.command()
@click.option('--name', required=True, help='The human-readable name of your new team (e.g. "Project Apollo")')
def create_team(name):
    """Creates a new team and makes you the admin."""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to create a team. Run 'envsync login' first.", fg="red")
        return

    headers = {
        "Authorization": f"Bearer {token}", 
        "Content-Type": "application/json"
    }

    click.echo(f"Creating team '{name}'...")
    
    try:
        res = requests.post(f"{BASE_URL}/teams", json={"name": name}, headers=headers)
        
        if res.status_code == 201:
            data = res.json()
            slug = data.get('slug')
            click.secho(f"Success! Team created.", fg="green")
            click.secho(f"Your team slug is: {slug}", fg="cyan", bold=True)
            click.echo(f"You can now push secrets using: envsync push --team {slug}")
        else:
            msg = res.json().get('error', res.text)
            click.secho(f"Failed to create team: {msg}", fg="red")
            
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to the server.", fg="red")