import os
import click
from cli.utils.config import PRIVATE_KEY_FILE
from cli.utils.api import push_vault_api, pull_vault_api, get_token
from cli.utils.crypto import CryptoEngine

@click.command()
@click.option('--team', required=True, help='The slug of the team vault')
def push(team):
    """--team <team slug>"""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to push secrets.", fg="red")
        return

    if not os.path.exists('.env'):
        click.secho("Error: No .env file found in this directory.", fg="red")
        return

    with open('.env', 'r') as f:
        env_text = f.read()

    if not os.path.exists(PRIVATE_KEY_FILE):
        click.secho("Error: Private key not found. Please log in again to generate your keys.", fg="red")
        return

    with open(PRIVATE_KEY_FILE, 'r') as f:
        private_key_pem = f.read()

    click.echo("Fetching your encryption envelope...")
    
    # 1. Silent Pull: We need the team_id and your specific envelope to get the Vault Key
    pull_res = pull_vault_api(team)
    if not pull_res or pull_res.status_code != 200:
        click.secho(f"Failed to fetch vault data: {pull_res.text if pull_res else 'No response'}", fg="red")
        return
        
    data = pull_res.json()
    team_id = data.get('team_id')
    encrypted_key = data.get('encrypted_key')

    if not team_id or not encrypted_key:
        click.secho("Error: Server returned incomplete vault data.", fg="red")
        return

    click.echo("Encrypting file...")
    try:
        # 2. Unwrap the master vault key using our local private key
        vault_key = CryptoEngine.unwrap_key(encrypted_key, private_key_pem)
        
        # 3. Encrypt the new file contents with the symmetric vault key
        encrypted_env_blob = CryptoEngine.encrypt_env(env_text, vault_key)
    except Exception as e:
        click.secho(f"Failed to encrypt payload: {str(e)}", fg="red")
        return

    click.echo("Pushing updated vault to server...")
    
    # 4. O(1) Push: Send ONLY the blob and the team_id! No other user keys are touched.
    push_res = push_vault_api(team_id, encrypted_env_blob)
    
    if push_res and push_res.status_code == 200:
        click.secho("Success! Vault securely updated.", fg="green")
    else:
        msg = push_res.json().get('error', push_res.text) if push_res else 'Unknown error'
        click.secho(f"Upload failed: {msg}", fg="red")


@click.command()
@click.option('--team', required=True, help='The slug of the team vault')
def pull(team):
    """--team <team slug>"""
    token = get_token()
    if not token:
        click.secho("Error: You must be logged in to pull secrets.", fg="red")
        return

    if not os.path.exists(PRIVATE_KEY_FILE):
        click.secho("Error: Private key not found. Please log in again to generate your keys.", fg="red")
        return

    with open(PRIVATE_KEY_FILE, 'r') as f:
        private_key_pem = f.read()

    click.echo("Fetching locked vault from server...")
    res = pull_vault_api(team)
    
    if not res or res.status_code != 200:
        click.secho(f"Failed to fetch vault: {res.text if res else 'No response'}", fg="red")
        return
        
    data = res.json()
    env_blob = data.get('env_blob')
    encrypted_key = data.get('encrypted_key')

    if not env_blob or not encrypted_key:
        click.secho("Error: Server returned incomplete vault data.", fg="red")
        return

    click.echo("Unlocking data key and decrypting payload...")
    try:
        # 1. Unwrap the master vault key using your private RSA key
        vault_key = CryptoEngine.unwrap_key(encrypted_key, private_key_pem)
        
        # 2. Decrypt the actual .env content using the unwrapped vault key
        plaintext_env = CryptoEngine.decrypt_env(env_blob, vault_key)
    except Exception as e:
        click.secho(f"Failed to decrypt the vault payload. Are you using the correct private key? Error: {e}", fg="red")
        return

    # 3. Save to disk
    with open('.env', 'w') as f:
        f.write(plaintext_env)

    click.secho("Success! .env file securely pulled and decrypted.", fg="green")
