import os
import tempfile
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from urllib.parse import urlsplit
from unittest.mock import patch

from click.testing import CliRunner

import cli.commands.auth as auth_commands
import cli.services.team_ops as team_ops
import cli.services.vault_ops as vault_ops
import cli.utils.api as api_utils
import cli.utils.config as config
import cli.utils.crypto as crypto_utils
from app import app
from cli.main import cli
from db_models import db, Team, TeamMembership, User, VaultKey


class FlaskResponseAdapter:
    def __init__(self, flask_response):
        self.status_code = flask_response.status_code
        self._response = flask_response
        self.text = flask_response.get_data(as_text=True)

    def json(self):
        return self._response.get_json()


class EndToEndSmokeTests(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            JWT_SECRET_KEY='test-secret',
        )
        self.app_context = app.app_context()
        self.app_context.push()
        db.session.remove()
        db.drop_all()
        db.create_all()

        self.client = app.test_client()
        self.runner = CliRunner()
        self.base_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = os.path.join(self.base_dir.name, 'workspace')
        self.admin_home = os.path.join(self.base_dir.name, 'admin-home')
        self.member_home = os.path.join(self.base_dir.name, 'member-home')
        os.makedirs(self.workspace_dir, exist_ok=True)
        os.makedirs(self.admin_home, exist_ok=True)
        os.makedirs(self.member_home, exist_ok=True)

        self.original_paths = {
            'config_token': config.TOKEN_FILE,
            'config_private': config.PRIVATE_KEY_FILE,
            'config_public': config.PUBLIC_KEY_FILE,
            'config_base_url': config.BASE_URL,
            'api_token': api_utils.TOKEN_FILE,
            'api_base_url': api_utils.BASE_URL,
            'crypto_private': crypto_utils.PRIVATE_KEY_FILE,
            'crypto_public': crypto_utils.PUBLIC_KEY_FILE,
            'crypto_base_url': crypto_utils.BASE_URL,
            'team_private': team_ops.PRIVATE_KEY_FILE,
            'team_public': team_ops.PUBLIC_KEY_FILE,
            'vault_private': vault_ops.PRIVATE_KEY_FILE,
            'auth_base_url': auth_commands.BASE_URL,
        }
        self.set_cli_profile(self.admin_home)

    def tearDown(self):
        config.TOKEN_FILE = self.original_paths['config_token']
        config.PRIVATE_KEY_FILE = self.original_paths['config_private']
        config.PUBLIC_KEY_FILE = self.original_paths['config_public']
        config.BASE_URL = self.original_paths['config_base_url']
        api_utils.TOKEN_FILE = self.original_paths['api_token']
        api_utils.BASE_URL = self.original_paths['api_base_url']
        crypto_utils.PRIVATE_KEY_FILE = self.original_paths['crypto_private']
        crypto_utils.PUBLIC_KEY_FILE = self.original_paths['crypto_public']
        crypto_utils.BASE_URL = self.original_paths['crypto_base_url']
        team_ops.PRIVATE_KEY_FILE = self.original_paths['team_private']
        team_ops.PUBLIC_KEY_FILE = self.original_paths['team_public']
        vault_ops.PRIVATE_KEY_FILE = self.original_paths['vault_private']
        auth_commands.BASE_URL = self.original_paths['auth_base_url']

        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.base_dir.cleanup()

    def set_cli_profile(self, home_dir):
        token_file = os.path.join(home_dir, '.envsync_config')
        private_key_file = os.path.join(home_dir, '.envsync_private.pem')
        public_key_file = os.path.join(home_dir, '.envsync_public.pem')
        base_url = 'https://env-sync.test'

        config.TOKEN_FILE = token_file
        config.PRIVATE_KEY_FILE = private_key_file
        config.PUBLIC_KEY_FILE = public_key_file
        config.BASE_URL = base_url
        api_utils.TOKEN_FILE = token_file
        api_utils.BASE_URL = base_url
        crypto_utils.PRIVATE_KEY_FILE = private_key_file
        crypto_utils.PUBLIC_KEY_FILE = public_key_file
        crypto_utils.BASE_URL = base_url
        team_ops.PRIVATE_KEY_FILE = private_key_file
        team_ops.PUBLIC_KEY_FILE = public_key_file
        vault_ops.PRIVATE_KEY_FILE = private_key_file
        auth_commands.BASE_URL = base_url

    def request_router(self, method, url, json_payload=None, headers=None):
        parsed = urlsplit(url)
        path = parsed.path or '/'
        if parsed.query:
            path = f'{path}?{parsed.query}'

        response = self.client.open(
            path=path,
            method=method,
            json=json_payload,
            headers=headers or {},
        )
        return FlaskResponseAdapter(response)

    def validate_email_stub(self, email, check_deliverability=False):
        del check_deliverability
        return SimpleNamespace(normalized=email.strip().lower())

    def invoke(self, args, user='admin', input_text=None):
        profile = self.admin_home if user == 'admin' else self.member_home
        self.set_cli_profile(profile)
        return self.runner.invoke(cli, args, input=input_text, catch_exceptions=False)

    def test_cli_smoke_flow_register_login_create_push_add_member_and_pull(self):
        env_contents = 'API_KEY=super-secret\nDEBUG=false\n'
        env_path = os.path.join(self.workspace_dir, '.env')

        with open(env_path, 'w') as f:
            f.write(env_contents)

        with ExitStack() as stack:
            stack.enter_context(patch('requests.post', side_effect=lambda url, json=None, headers=None: self.request_router('POST', url, json, headers)))
            stack.enter_context(patch('requests.get', side_effect=lambda url, headers=None: self.request_router('GET', url, None, headers)))
            stack.enter_context(patch('requests.delete', side_effect=lambda url, headers=None: self.request_router('DELETE', url, None, headers)))
            stack.enter_context(patch('requests.patch', side_effect=lambda url, json=None, headers=None: self.request_router('PATCH', url, json, headers)))
            stack.enter_context(patch('app.lib_validate_email', side_effect=self.validate_email_stub))
            stack.enter_context(patch('cli.commands.auth.lib_validate_email', side_effect=self.validate_email_stub))
            stack.enter_context(patch('click.clear', lambda: None))

            old_cwd = os.getcwd()
            os.chdir(self.workspace_dir)
            try:
                result = self.invoke(
                    ['register', '--email', 'admin@example.com'],
                    user='admin',
                    input_text='secretpw\nsecretpw\n',
                )
                self.assertEqual(result.exit_code, 0)
                self.assertIn('Success!', result.output)

                result = self.invoke(
                    ['login', '--email', 'admin@example.com', '--password', 'secretpw'],
                    user='admin',
                )
                self.assertEqual(result.exit_code, 0)
                self.assertIn('Logged in and token saved locally.', result.output)

                result = self.invoke(['logout'], user='admin', input_text='y\n')
                self.assertEqual(result.exit_code, 0)

                result = self.invoke(
                    ['register', '--email', 'member@example.com'],
                    user='member',
                    input_text='memberpw\nmemberpw\n',
                )
                self.assertEqual(result.exit_code, 0)

                result = self.invoke(
                    ['login', '--email', 'member@example.com', '--password', 'memberpw'],
                    user='member',
                )
                self.assertEqual(result.exit_code, 0)
                self.assertIn('Logged in and token saved locally.', result.output)

                result = self.invoke(['logout'], user='member', input_text='y\n')
                self.assertEqual(result.exit_code, 0)

                result = self.invoke(
                    ['login', '--email', 'admin@example.com', '--password', 'secretpw'],
                    user='admin',
                )
                self.assertEqual(result.exit_code, 0)

                result = self.invoke(['create-team', '--name', 'Project Apollo'], user='admin')
                self.assertEqual(result.exit_code, 0)
                self.assertIn('project-apollo', result.output)

                result = self.invoke(['push', '--team', 'project-apollo'], user='admin', input_text='secretpw\n')
                self.assertEqual(result.exit_code, 0)
                self.assertIn('Vault securely updated', result.output)

                result = self.invoke(
                    ['add-member', '--team', 'project-apollo', '--email', 'member@example.com'],
                    user='admin',
                )
                self.assertEqual(result.exit_code, 0)
                self.assertIn('member@example.com was added', result.output)

                result = self.invoke(['logout'], user='admin', input_text='y\n')
                self.assertEqual(result.exit_code, 0)

                with open(env_path, 'w') as f:
                    f.write('STALE=value\n')

                result = self.invoke(
                    ['login', '--email', 'member@example.com', '--password', 'memberpw'],
                    user='member',
                )
                self.assertEqual(result.exit_code, 0)

                result = self.invoke(['pull', '--team', 'project-apollo'], user='member')
                self.assertEqual(result.exit_code, 0)
                self.assertIn('.env file securely pulled and decrypted', result.output)

                with open(env_path, 'r') as f:
                    self.assertEqual(f.read(), env_contents)

                team = Team.query.filter_by(slug='project-apollo').first()
                self.assertIsNotNone(team)
                self.assertEqual(User.query.count(), 2)
                self.assertEqual(TeamMembership.query.filter_by(team_id=team.id).count(), 2)
                self.assertEqual(VaultKey.query.filter_by(team_id=team.id).count(), 2)
            finally:
                os.chdir(old_cwd)


if __name__ == '__main__':
    unittest.main()
