import os
import click

from cli.services.team_ops import result, get_error_message
from cli.utils.api import get_token, pull_vault_api, push_vault_api
from cli.utils.config import PRIVATE_KEY_FILE
from cli.utils.crypto import CryptoEngine


def require_login(action_text):
    token = get_token()
    if not token:
        return result(False, f"Error: You must be logged in to {action_text}.")
    return None


def push_vault_op(team_slug):
    auth_error = require_login("push secrets")
    if auth_error:
        return auth_error

    if not os.path.exists(".env"):
        return result(False, "Error: No .env file found in this directory.")

    with open(".env", "r") as f:
        env_text = f.read()

    if not os.path.exists(PRIVATE_KEY_FILE):
        return result(False, "Error: Private key not found. Please log in again to generate your keys.")

    with open(PRIVATE_KEY_FILE, "r") as f:
        private_key_pem = f.read()

    pull_res = pull_vault_api(team_slug)
    if not pull_res or pull_res.status_code != 200:
        return result(False, f"Failed to fetch vault data: {get_error_message(pull_res)}")

    data = pull_res.json()
    team_id = data.get("team_id")
    encrypted_key = data.get("encrypted_key")

    if not team_id or not encrypted_key:
        return result(False, "Error: Server returned incomplete vault data.")

    try:
        vault_key = CryptoEngine.unwrap_key(encrypted_key, private_key_pem)
        encrypted_env_blob = CryptoEngine.encrypt_env(env_text, vault_key)
    except Exception as e:
        return result(False, f"Failed to encrypt payload: {str(e)}")

    password = click.prompt("Password", hide_input=True)
    push_res = push_vault_api(team_id, encrypted_env_blob, password)
    if push_res and push_res.status_code == 200:
        return result(True, "Success! Vault securely updated.")

    return result(False, f"Upload failed: {get_error_message(push_res)}")


def pull_vault_op(team_slug):
    auth_error = require_login("pull secrets")
    if auth_error:
        return auth_error

    if not os.path.exists(PRIVATE_KEY_FILE):
        return result(False, "Error: Private key not found. Please log in again to generate your keys.")

    with open(PRIVATE_KEY_FILE, "r") as f:
        private_key_pem = f.read()

    response = pull_vault_api(team_slug)
    if not response or response.status_code != 200:
        return result(False, f"Failed to fetch vault: {get_error_message(response)}")

    data = response.json()
    env_blob = data.get("env_blob")
    encrypted_key = data.get("encrypted_key")

    if not env_blob or not encrypted_key:
        return result(False, "Error: Server returned incomplete vault data.")

    try:
        vault_key = CryptoEngine.unwrap_key(encrypted_key, private_key_pem)
        plaintext_env = CryptoEngine.decrypt_env(env_blob, vault_key)
    except Exception as e:
        return result(False, f"Failed to decrypt the vault payload. Are you using the correct private key? Error: {e}")

    with open(".env", "w") as f:
        f.write(plaintext_env)

    return result(True, "Success! .env file securely pulled and decrypted.")
