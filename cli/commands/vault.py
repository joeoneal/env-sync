import os
import base64
import requests
import click
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from cli.utils.config import BASE_URL, PRIVATE_KEY_FILE
from cli.utils.api import get_token

@click.command()
@click.option('--team', required=True, help='The name of the team vault')
def push(team):
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
    key_res = requests.get(f"{BASE_URL}/team/{team}/keys", headers=headers)
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
        "team": team,
        "env_blob": encrypted_env_blob,
        "encrypted_keys": encrypted_data_keys # bundle of entire teams locked pub keys
    }
    
    upload_res = requests.post(f"{BASE_URL}/vault", json=payload, headers=headers)
    if upload_res.status_code == 200:
        click.secho("Success! Vault securely pushed.", fg="green")
    else:
        click.secho(f"Upload failed: {upload_res.text}", fg="red")

@click.command()
@click.option('--team', required=True, help='The name of the team vault')
def pull(team):
    """Pulls the encrypted .env from the team vault and decrypts it."""
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    click.echo("Fetching locked vault from server...")
    res = requests.get(f"{BASE_URL}/vault?team={team}", headers=headers)
    
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