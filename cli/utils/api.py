import os
import json
from cli.utils.config import TOKEN_FILE

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
        return data.get("access_token")