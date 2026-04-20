import click
import requests
from halo import Halo
from cli.utils.config import BASE_URL
from cli.utils.api import save_token, get_token, delete_token
from cli.utils.crypto import gen_keypair_if_none

from email_validator import validate_email as lib_validate_email, EmailNotValidError

## helpers ##

def validate_email(_ctx, _param, value):
    try:
        info = lib_validate_email(value, check_deliverability=True)
        return info.normalized
    except EmailNotValidError as e:
        raise click.BadParameter(str(e))
    
class LongPass(click.ParamType):
    name = 'password'

    def convert(self, value, _param, _ctx):
        if len(value) < 6:
            raise click.BadParameter('Password must be at least 6 characters in length.')
        return value


def prompt_for_password():
    password_type = LongPass()

    while True:
        raw_password = click.prompt('Password', hide_input=True)

        try:
            password = password_type.convert(raw_password, None, None)
        except click.BadParameter as e:
            click.secho(f"Error: {e.message}", fg="red")
            continue

        confirmation = click.prompt('Repeat for confirmation', hide_input=True)
        if password != confirmation:
            click.secho("Error: The two entered values do not match.", fg="red")
            continue

        return password

@click.command()
@click.option('--email', prompt='Email', callback=validate_email, help='Your email address.')
def register(email):
    """--email <email> [flag optional]"""
    password = prompt_for_password()

    spinner = Halo(text=f"Registering account for {email}...", spinner='flip')
    spinner.start()
    try:
        response = requests.post(
            f"{BASE_URL}/register",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 201:
            spinner.stop()
            click.clear()
            click.secho('Success!', fg='green')
            click.echo("You can now log in by running: ", nl=False)
            click.secho("envsync login", fg="cyan", bold=True)
        else:
            # Safely try to get the error message from the JSON respnse
            try:
                msg = response.json().get('error', 'Unknown error occurred')
            except ValueError:
                msg = response.text
            spinner.stop()
            click.secho(f"Registration failed: {msg}", fg='red')
        
    except requests.exceptions.ConnectionError:
        spinner.stop()
        click.secho("Error: Could not connect to the server. Please try again.", fg='red')

@click.command()
@click.option('--email', required = False, help='Your registered email.')
@click.option('--password', required = False, hide_input=True, help='Your password.') 
def login(email, password):
    """--email <email> [flag optional]"""
    token = get_token()
    if token:
        click.secho('You are already logged in. Please log out if you wish to log in as another user.', fg='yellow')
        return

    if not email:
        email = click.prompt("Email")

    if not password:
        password = click.prompt("Password", hide_input=True)

    spinner = Halo(text=f"Attempting to login as {email}...", spinner='flip')
    spinner.start()


    try:
        response = requests.post(
            f"{BASE_URL}/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            save_token(token)
            gen_keypair_if_none(token)
            click.clear()
            spinner.stop()
            click.secho("Logged in and token saved locally.", fg="green")
        else:
            try:
                msg = response.json().get('error', 'Invalid email or password.')
            except ValueError:
                msg = response.text or 'Invalid email or password.'
            spinner.stop()
            click.secho(f"Login failed: {msg}", fg="red")
            
    except requests.exceptions.ConnectionError:
        spinner.stop()
        click.secho("Error: Could not connect to the server. Please try again.", fg="red")

@click.command()
def logout():
    """[no flags]"""
    token = get_token()
    if not token:
        click.secho('You were not logged in!', fg='yellow')
        return

    if click.confirm('Are you sure you would like to log out?'):
        pass
    else:
        click.echo('Aborted.')
        return
    
    spinner = Halo(text=f"Logging out...", spinner='flip')
    spinner.start()

    
    deleted = delete_token()
    if deleted:
        spinner.stop()
        click.clear()
        click.secho('Sucessfully logged out.', fg='green')
    else:
        spinner.stop()
        click.secho('Something went wrong. Please try again.', fg='red')

@click.command(name='whoami')
def whoami():
    """[no flags]"""
    token = get_token()
    if not token:
        click.secho('You are not logged in!', fg='yellow')
        return
    
    
    try:
        response=requests.get(
            f'{BASE_URL}/whoami',
            headers={"Authorization": f'Bearer {token}'}
        )

        if response.status_code ==200:
            email = response.json().get('email')
            click.echo("Logged in as: ", nl=False)
            click.secho(email, fg="cyan", bold=True)
        else:
            click.secho("Session expired. Please log in again.", fg="red")
            delete_token() # Clean up the bad token!
            
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to server.", fg="red")

    
