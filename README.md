# Env-Sync

Env-Sync is a CLI-first tool for sharing encrypted `.env` files across a team without committing secrets to Git or sending them through chat.

The current architecture has two pieces:

- A Flask API that stores encrypted vault payloads, team memberships, and per-user wrapped vault keys.
- A Python CLI published as `envsync-vault` that handles local authentication, RSA key generation, encryption, and pull/push workflows.

## What It Does

- Registers users and authenticates them with JWTs
- Generates an RSA key pair locally on first login
- Encrypts the team `.env` with a symmetric vault key
- Wraps that vault key separately for each authorized team member
- Lets admins create teams, add members, promote/demote roles, and delete teams
- Lets members pull and decrypt the team `.env` into their local project directory

## MVP Scope

Env-Sync is currently aimed at small internal teams, class projects, and early pilots. It is not yet positioned as a hardened enterprise secrets manager.

## Install The CLI

From PyPI:

```bash
pip install envsync-vault
```

Verify the install:

```bash
envsync help
```

## CLI Configuration

By default the CLI points at the hosted Railway API:

```text
https://env-sync.up.railway.app
```

Override that with an environment variable when testing locally or against another deployment:

```bash
export ENVSYNC_BASE_URL="http://127.0.0.1:7070"
```

## Quick Start

Inside the project directory whose `.env` you want to share:

```bash
envsync register --email alice@example.com
envsync login --email alice@example.com
envsync create-team --name "Project Apollo"
envsync push --team project-apollo
```

On another machine or for another team member:

```bash
envsync register --email bob@example.com
envsync login --email bob@example.com
```

Back on the admin account:

```bash
envsync add-member --team project-apollo --email bob@example.com
```

Then the invited member can pull:

```bash
envsync pull --team project-apollo
```

## Common Commands

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

Create a virtualenv and install the project dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Set the environment variables required by the Flask app:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:PORT/DBNAME"
export JWT_KEY="replace-me"
```

Run migrations:

```bash
python -m flask --app app db upgrade
```

Start the API locally:

```bash
python app.py
```

Then point the CLI at the local API:

```bash
export ENVSYNC_BASE_URL="http://127.0.0.1:7070"
```

## Railway Deployment

This repo includes Railway deployment configuration:

- [railway.toml](/Users/joeoneal/senior/spring/capstone/env-sync/railway.toml)
- [Procfile](/Users/joeoneal/senior/spring/capstone/env-sync/Procfile)

Current deploy behavior:

- Runs Alembic migrations before deploy
- Starts the Flask app with Gunicorn

Required deployment environment variables:

- `DATABASE_URL`
- `JWT_KEY`

## Tests

Run the tests with the project virtualenv so the Flask dependencies are available:

```bash
.venv/bin/python -m unittest discover -s tests
```

## Project Layout

- [app.py](/Users/joeoneal/senior/spring/capstone/env-sync/app.py): Flask API
- [db_models.py](/Users/joeoneal/senior/spring/capstone/env-sync/db_models.py): SQLAlchemy models
- [cli](/Users/joeoneal/senior/spring/capstone/env-sync/cli): CLI package
- [migrations](/Users/joeoneal/senior/spring/capstone/env-sync/migrations): Alembic migrations
- [tests](/Users/joeoneal/senior/spring/capstone/env-sync/tests): unit and smoke tests

## Known Limitations

- The CLI currently stores its local auth token on disk.
- The private key is generated locally and stored for reuse.
- `pull` writes a `.env` file into the current working directory.
- This project has not yet completed a full production hardening pass.
