import click
import requests
from cli.utils.config import BASE_URL
from cli.utils.api import save_token
from cli.utils.crypto import gen_keypair_if_none

from email_validator import validate_email as lib_validate_email, EmailNotValidError

## email validation helper ##

def validate_email(_ctx, _param, value):
    try:
        info = lib_validate_email(value, check_deliverability=True)
        return info.normalized
    except EmailNotValidError as e:
        raise click.BadParameter(str(e))


@click.command()
@click.option('--email', prompt='Email', callback=validate_email, help='Your email address.')
@click.password_option(help='Choose a strong password.')
def register(email, password):
    """--email <email>"""
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
@click.option('--password', prompt=True, hide_input=True, help='Your password.') 
def login(email, password):
    """--email <email>"""
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
            try:
                msg = response.json().get('error', 'Invalid email or password.')
            except ValueError:
                msg = response.text or 'Invalid email or password.'
            click.secho(f"Login failed: {msg}", fg="red")
            
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to the server. Is it running on port 7070?", fg="red")
