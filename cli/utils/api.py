import os
import json
import requests
from cli.utils.config import TOKEN_FILE, BASE_URL

def save_token(token):
    """Saves the JWT to a local hidden file."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump({"access_token": token}, f)

def get_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            return data.get("access_token")
    except (json.JSONDecodeError, KeyError):
        return None
    
def delete_token():
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            return True
    except OSError as e:
        return ('os error as follows: ', e)
    return False

def get_auth_headers():
    """Helper to inject the JWT into the request headers."""
    token = get_token()
    if not token:
        return None
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

# --- New Envelope Encryption Endpoints ---

def create_team_api(team_name, env_blob, encrypted_key):
    """Sends the initial encrypted payload and the Admin's envelope to the server."""
    headers = get_auth_headers()
    if not headers:
        return None

    payload = {
        "name": team_name,
        "env_blob": env_blob,
        "encrypted_key": encrypted_key
    }
    
    return requests.post(f"{BASE_URL}/teams", json=payload, headers=headers)

def push_vault_api(team_id, env_blob):
    """O(1) Scaling: Sends ONLY the updated vault payload to the server."""
    headers = get_auth_headers()
    if not headers:
        return None

    payload = {
        "team_id": team_id,
        "env_blob": env_blob
    }
    
    return requests.post(f"{BASE_URL}/vault", json=payload, headers=headers)

def pull_vault_api(team_slug):
    """Fetches the encrypted vault payload and the user's specific envelope."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.get(f"{BASE_URL}/vault?team={team_slug}", headers=headers)

def prepare_add_member_api(team_slug, email):
    """Fetches the target user's public key after admin authorization checks."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.post(
        f"{BASE_URL}/teams/{team_slug}/members/prepare",
        json={"email": email},
        headers=headers
    )

def list_members_api(team_slug):
    """Lists all members of a team along with their roles."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.get(f"{BASE_URL}/teams/{team_slug}/members", headers=headers)

def confirm_add_member_api(team_slug, target_user_id, encrypted_key):
    """Completes membership creation with a client-wrapped team vault key."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.post(
        f"{BASE_URL}/teams/{team_slug}/members/confirm",
        json={
            "target_user_id": target_user_id,
            "encrypted_key": encrypted_key,
        },
        headers=headers
    )

def list_teams_api():
    """Lists the teams available to the currently logged-in user."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.get(f"{BASE_URL}/teams", headers=headers)

def leave_team_api(team_slug):
    """Removes the current user from a team when permitted."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.delete(f"{BASE_URL}/teams/{team_slug}/members/me", headers=headers)

def delete_team_api(team_slug):
    """Deletes the specified team by slug."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.delete(f"{BASE_URL}/teams/{team_slug}", headers=headers)

def update_member_role_api(team_slug, email, role):
    """Promotes or demotes an existing team member by email."""
    headers = get_auth_headers()
    if not headers:
        return None

    return requests.patch(
        f"{BASE_URL}/teams/{team_slug}/members/role",
        json={"email": email, "role": role},
        headers=headers
    )
