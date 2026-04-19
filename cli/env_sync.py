import base64
import os
import requests
import click
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding

# this file will live in the home dir
TOKEN_FILE = os.path.expanduser("~/.envsync_config")
BASE_URL = "http://127.0.0.1:7070"

PRIVATE_KEY_FILE = os.path.expanduser("~/.envsync_private.pem")
PUBLIC_KEY_FILE = os.path.expanduser("~/.envsync_public.pem")

@click.group()
def cli():
    """Env-Sync: Securely manage your .env files across teams."""
    pass

######### helpers #########

def save_token(token):
    """Saves the JWT to a local hidden file."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump({"access_token": token}, f)

def get_token():
    """Retrieves the JWT from the local hidden file."""
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, 'r') as f:
        data = json.load(f)
        return data.get("access_token")\
        
def gen_keypair_if_none(token):
    """Generates RSA key pair if one doesn't already exists locally"""
    if os.path.exists(PRIVATE_KEY_FILE) and os.path.exists(PUBLIC_KEY_FILE):
        return
    
    click.echo("Generating your unique end-to-end ecryption key pair...")

    priv = rsa.generate_private_key(
        public_exponent = 65537, 
        key_size = 2048
    )

    pub = priv.public_key()

    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save Public Key (This goes to the server)
    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    
    click.secho("Key pair generated successfully!", fg="green")

    click.secho('Uploading public key to server...', fg='blue')
    with open(PUBLIC_KEY_FILE, 'r') as f:
        pub_text = f.read()

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(f"{BASE_URL}/public_key", json={"public_key": pub_text}, headers=headers)
        if response.status_code == 200:
            click.secho("Public key securely registered with server!", fg="green")
        else:
            click.secho(f"Failed to upload public key: {response.text}", fg="red")
    except requests.exceptions.ConnectionError:
        click.secho("Error: Could not connect to the server to upload key.", fg="red")

## LOGIN ##
@cli.command()
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

## PUSH ##
@cli.command()
@click.option('--team_id', prompt='Team ID', type=int, help='The ID of the team vault')
def push(team_id):
    """Encrypts local .env and pushes it to the team vault."""

    token = get_token() 
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if not os.path.exists('.env'):
        click.secho("Error: No .env file found in this directory.", fg="red")
        return
        
    with open('.env', 'rb') as f:
        raw_env_data = f.read()

    click.echo("Encrypting file...")
    data_key = Fernet.generate_key()
    f_cipher = Fernet(data_key)
    encrypted_env_blob = f_cipher.encrypt(raw_env_data).decode('utf-8')

    click.echo("Fetching team public keys...")
    key_res = requests.get(f"{BASE_URL}/team/{team_id}/keys", headers=headers)
    if key_res.status_code != 200:
        click.secho(f"Failed to fetch keys: {key_res.text}", fg="red")
        return
        
    team_keys = key_res.json().get('keys', {})

    click.secho(f"DEBUG: Fetched {len(team_keys)} public keys from the server.", fg="magenta")

    encrypted_data_keys = {}
    for user_id_str, pub_key_pem in team_keys.items():
        public_key = serialization.load_pem_public_key(pub_key_pem.encode('utf-8'))
        
        encrypted_key_bytes = public_key.encrypt(
            data_key,
            asymmetric_padding.OAEP(
                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        encrypted_data_keys[user_id_str] = base64.b64encode(encrypted_key_bytes).decode('utf-8')

    click.echo("Pushing locked vault to server...")
    payload = {
        "team_id": team_id,
        "env_blob": encrypted_env_blob,
        "encrypted_keys": encrypted_data_keys # bundle of entire teams locked pub keys
    }
    
    upload_res = requests.post(f"{BASE_URL}/vault", json=payload, headers=headers)
    if upload_res.status_code == 200:
        click.secho("Success! Vault securely pushed.", fg="green")
    else:
        click.secho(f"Upload failed: {upload_res.text}", fg="red")

## PULL ##
@cli.command()
@click.option('--team_id', prompt='Team ID', type=int, help='The ID of the team vault')
def pull(team_id):
    """Pulls the encrypted .env from the team vault and decrypts it."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    click.echo("Fetching locked vault from server...")
    res = requests.get(f"{BASE_URL}/vault?team_id={team_id}", headers=headers)
    
    if res.status_code != 200:
        click.secho(f"Failed to fetch vault: {res.text}", fg="red")
        return
        
    data = res.json()
    encrypted_env_blob = data.get('env_blob')
    b64_encrypted_key = data.get('encrypted_key')

    if not encrypted_env_blob or not b64_encrypted_key:
        click.secho("Error: Server returned incomplete vault data.", fg="red")
        return

    click.echo("Unlocking data key...")
    
    if not os.path.exists(PRIVATE_KEY_FILE):
        click.secho("Error: Private key not found. Please log in again to generate your keys.", fg="red")
        return
        
    with open(PRIVATE_KEY_FILE, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None, 
        )

    encrypted_key_bytes = base64.b64decode(b64_encrypted_key)
    try:
        data_key = private_key.decrypt(
            encrypted_key_bytes,
            asymmetric_padding.OAEP(
                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    except Exception as e:
        click.secho(f"Failed to unlock the data key. Are you using the correct private key? Error: {e}", fg="red")
        return

    click.echo("Decrypting .env file...")
    f_cipher = Fernet(data_key)
    try:
        decrypted_env_data = f_cipher.decrypt(encrypted_env_blob.encode('utf-8'))
    except Exception as e:
        click.secho(f"Failed to decrypt the vault payload: {e}", fg="red")
        return

    with open('.env', 'wb') as f:
        f.write(decrypted_env_data)

    click.secho("Success! .env file securely pulled and decrypted.", fg="green")

if __name__ == '__main__':
    cli()