import click
import requests
from cli.utils.config import BASE_URL
from cli.utils.api import save_token
from cli.utils.crypto import gen_keypair_if_none

@click.command()
@click.option('--email', prompt='Email', help='Your email address.')
@click.password_option(help='Choose a strong password.')
def register(email, password):
    """Create a new Env-Sync account."""
    click.echo(f"Registering account for {email}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/register",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 201:
            click.secho("Success! Account created.", fg="green")
            click.echo("You can now log in by running: ", nl=False)
            click.secho("envsync login", fg="cyan", bold=True)
        else:
            # Safely try to get the error message from the JSON respnse
            try:
                msg = response.json().get('error', 'Unknown error occurred')
            except ValueError:
                msg = response.text
            click.secho(f"Registration failed: {msg}", fg="red")
            
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to the server. Is it running on port 7070?", fg="red")

@click.command()
@click.option('--email', prompt='Email', help='Your registered email.')
@click.password_option(help='Your password.') # Automatically masks password input
def login(email, password):
    """Log in to Env-Sync and get an access token."""
    click.echo(f"Attempting to log in as {email}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            save_token(token)
            gen_keypair_if_none(token)
            click.secho("Success! Logged in and token saved locally.", fg="green")
        else:
            msg = response.json().get('message', 'Unknown error')
            click.secho(f"Login failed: {msg}", fg="red")
            
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to the server. Is it running on port 7070?", fg="red")