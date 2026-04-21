import os

from cli.utils.api import (
    get_token,
    create_team_api,
    list_teams_api,
    leave_team_api,
    pull_vault_api,
    prepare_add_member_api,
    list_members_api,
    confirm_add_member_api,
    delete_team_api,
    update_member_role_api,
)
from cli.utils.crypto import CryptoEngine
from cli.utils.config import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE


def result(ok, message, data=None):
    return {
        "ok": ok,
        "message": message,
        "data": data or {},
    }


def get_error_message(response):
    if response is None:
        return "No response from server"

    try:
        payload = response.json()
    except ValueError:
        return response.text or f"Server returned status {response.status_code}"

    return (
        payload.get("error")
        or payload.get("message")
        or response.text
        or f"Server returned status {response.status_code}"
    )


def require_login(action_text):
    token = get_token()
    if not token:
        return result(False, f"Error: You must be logged in to {action_text}.")
    return None


def create_team_op(name):
    auth_error = require_login("create a team")
    if auth_error:
        return auth_error

    if not os.path.exists(".env"):
        env_text = ""
    else:
        with open(".env", "r") as f:
            env_text = f.read()

    if not os.path.exists(PUBLIC_KEY_FILE):
        return result(False, "Error: Local public key not found. Please log in or generate keys first.")

    with open(PUBLIC_KEY_FILE, "r") as f:
        public_key_pem = f.read()

    try:
        vault_key = CryptoEngine.generate_vault_key()
        env_blob = CryptoEngine.encrypt_env(env_text, vault_key)
        encrypted_key = CryptoEngine.wrap_key(vault_key, public_key_pem)

        response = create_team_api(name, env_blob, encrypted_key)
        if response is not None and response.status_code == 201:
            data = response.json()
            slug = data.get("slug")
            return result(True, f"Team created and vault secured.", {"slug": slug})

        return result(False, f"Failed to create team: {get_error_message(response)}")
    except Exception as e:
        return result(False, f"An unexpected error occurred: {str(e)}")


def add_member_op(team_slug, email):
    auth_error = require_login("add a team member")
    if auth_error:
        return auth_error

    if not os.path.exists(PRIVATE_KEY_FILE):
        return result(False, "Error: Private key not found. Please log in again to generate your keys.")

    with open(PRIVATE_KEY_FILE, "r") as f:
        private_key_pem = f.read()

    prepare_res = prepare_add_member_api(team_slug, email)
    if prepare_res is None or prepare_res.status_code != 200:
        return result(False, f"Failed to prepare member add: {get_error_message(prepare_res)}")

    prepare_data = prepare_res.json()
    target_user = prepare_data.get("target_user", {})
    target_user_id = target_user.get("id")
    target_public_key = target_user.get("public_key")
    target_email = target_user.get("email", email)

    if not target_user_id or not target_public_key:
        return result(False, "Error: Server returned incomplete user information.")

    pull_res = pull_vault_api(team_slug)
    if pull_res is None or pull_res.status_code != 200:
        return result(False, f"Failed to fetch vault data: {get_error_message(pull_res)}")

    vault_data = pull_res.json()
    encrypted_key = vault_data.get("encrypted_key")
    if not encrypted_key:
        return result(False, "Error: Server returned incomplete vault data.")

    try:
        vault_key = CryptoEngine.unwrap_key(encrypted_key, private_key_pem)
        wrapped_key_for_member = CryptoEngine.wrap_key(vault_key, target_public_key)
    except Exception as e:
        return result(False, f"Failed to prepare member access: {str(e)}")

    confirm_res = confirm_add_member_api(team_slug, target_user_id, wrapped_key_for_member)
    if confirm_res is not None and confirm_res.status_code == 201:
        return result(True, f"Success! {target_email} was added to {team_slug}.")

    return result(False, f"Failed to add member: {get_error_message(confirm_res)}")


def list_teams_op():
    auth_error = require_login("list teams")
    if auth_error:
        return auth_error

    response = list_teams_api()
    if response is None or response.status_code != 200:
        return result(False, f"Failed to list teams: {get_error_message(response)}")

    teams = response.json().get("teams", [])
    if not teams:
        return result(True, "You are not a member of any teams yet.", {"teams": []})

    return result(True, "Teams loaded.", {"teams": teams})


def list_members_op(team_slug):
    auth_error = require_login("list team members")
    if auth_error:
        return auth_error

    response = list_members_api(team_slug)
    if response is None or response.status_code != 200:
        return result(False, f"Failed to list team members: {get_error_message(response)}")

    members = response.json().get("members", [])
    if not members:
        return result(True, f"No members were found for {team_slug}.", {"members": []})

    return result(True, f"Members loaded for {team_slug}.", {"members": members})


def ensure_team_access(team_slug):
    teams_result = list_teams_op()
    if not teams_result["ok"]:
        return teams_result

    teams = teams_result["data"].get("teams", [])
    for team in teams:
        if team.get("team_slug") == team_slug:
            return result(True, "Team found.", {"team": team})

    return result(False, f"Team '{team_slug}' was not found in your memberships.")


def leave_team_op(team_slug):
    auth_error = require_login("leave a team")
    if auth_error:
        return auth_error

    response = leave_team_api(team_slug)
    if response is None or response.status_code != 200:
        return result(False, f"Failed to leave team: {get_error_message(response)}")

    payload = response.json()
    if payload.get("deleted_team"):
        return result(True, f"Success! You left {team_slug}, and the empty team was deleted.", payload)

    return result(True, f"Success! You left {team_slug}.", payload)


def delete_team_op(team_slug):
    auth_error = require_login("delete a team")
    if auth_error:
        return auth_error

    response = delete_team_api(team_slug)
    if response is not None and response.status_code == 200:
        return result(True, f"Team {team_slug} successfully deleted")

    return result(False, f"Failed to delete team {team_slug}: {get_error_message(response)}")


def promote_member_op(team_slug, email):
    auth_error = require_login("promote a team member")
    if auth_error:
        return auth_error

    response = update_member_role_api(team_slug, email, "admin")
    if response is not None and response.status_code == 200:
        message = response.json().get("message", f"Success! {email} is now an admin of {team_slug}.")
        if message == "Role updated successfully":
            message = f"Success! {email} is now an admin of {team_slug}."
        return result(True, message)

    return result(False, f"Failed to promote member: {get_error_message(response)}")


def demote_member_op(team_slug, email):
    auth_error = require_login("demote a team member")
    if auth_error:
        return auth_error

    response = update_member_role_api(team_slug, email, "member")
    if response is not None and response.status_code == 200:
        message = response.json().get("message", f"Success! {email} is now a member of {team_slug}.")
        if message == "Role updated successfully":
            message = f"Success! {email} is now a member of {team_slug}."
        return result(True, message)

    return result(False, f"Failed to demote member: {get_error_message(response)}")
