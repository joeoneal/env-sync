# Env-Sync

Env-Sync is a CLI tool for sharing encrypted `.env` files across a team without committing secrets to Git or sending them through chat.

Env-Sync has two main parts:

- A Flask API that stores encrypted vault payloads, team memberships, and per-user wrapped vault keys
- A Python CLI package, `envsync-vault`, that handles authentication, key generation, encryption, and pull/push workflows

## Core Features

- User registration and login through the CLI
- Local RSA key generation on first login
- Client-side encryption of the team `.env`
- Per-user wrapped vault keys for team access
- Team creation and membership management
- Admin/member role controls
- Pull and push workflows for encrypted vault updates
- Team-specific interactive subshell for faster team operations

## Install

Install from PyPI:

```bash
pip install envsync-vault
```

Verify the install:

```bash
envsync help
```

## Configuration

By default, the CLI points to the hosted Railway API:

```text
https://env-sync.up.railway.app
```

To use a different deployment:

```bash
export ENVSYNC_BASE_URL="http://127.0.0.1:7070"
```

## Basic Workflow

Register and log in:

```bash
envsync register --email alice@example.com
envsync login --email alice@example.com
```

Create a team and upload the initial vault:

```bash
envsync create-team --name "Project Apollo"
envsync push --team project-apollo
```

Add a team member:

```bash
envsync add-member --team project-apollo --email bob@example.com
```

Pull secrets on another machine or account:

```bash
envsync pull --team project-apollo
```

## Main Commands

Authentication:

```bash
envsync register --email you@example.com
envsync login --email you@example.com
envsync whoami
envsync logout
```

Teams:

```bash
envsync create-team --name "Project Apollo"
envsync list-teams
envsync list-members --team project-apollo
envsync add-member --team project-apollo --email bob@example.com
envsync promote --team project-apollo --email bob@example.com
envsync demote --team project-apollo --email bob@example.com
envsync leave-team --team project-apollo
envsync delete-team --team project-apollo
```

Vault operations:

```bash
envsync push --team project-apollo
envsync pull --team project-apollo
envsync team project-apollo
```

## Local Development

Set up the project locally:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Configure environment variables:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME"
export JWT_KEY="replace-me"
```

Run migrations and start the API:

```bash
python -m flask --app app db upgrade
python app.py
```

Point the CLI at the local API:

```bash
export ENVSYNC_BASE_URL="http://127.0.0.1:7070"
```
