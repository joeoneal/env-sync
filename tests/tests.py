import os
import sys
import unittest

from flask_jwt_extended import create_access_token

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SERVER_DIR = os.path.join(ROOT_DIR, 'server')

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import app, bcrypt
from db_models import db, User, Team, TeamMembership, VaultKey


class AddMemberFlowTests(unittest.TestCase):
    def setUp(self):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            JWT_SECRET_KEY='test-secret',
        )
        self.app_context = app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()
        self.client = app.test_client()

        hashed_pw = bcrypt.generate_password_hash('pw').decode('utf-8')

        self.admin = User(
            email='admin@example.com',
            password_hash=hashed_pw,
            public_key='admin-public-key',
        )
        self.member = User(
            email='member@example.com',
            password_hash=hashed_pw,
            public_key='member-public-key',
        )
        self.no_key_user = User(
            email='nokey@example.com',
            password_hash=hashed_pw,
        )
        self.outsider = User(
            email='outsider@example.com',
            password_hash=hashed_pw,
            public_key='outsider-public-key',
        )

        db.session.add_all([self.admin, self.member, self.no_key_user, self.outsider])
        db.session.commit()

        self.team = Team(name='Project Apollo', slug='project-apollo', env_blob='encrypted-env')
        db.session.add(self.team)
        db.session.commit()

        db.session.add(
            TeamMembership(user_id=self.admin.id, team_id=self.team.id, role='admin')
        )
        db.session.add(
            VaultKey(user_id=self.admin.id, team_id=self.team.id, encrypted_key='admin-envelope')
        )
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def auth_headers(self, user_id):
        token = create_access_token(identity=str(user_id))
        return {'Authorization': f'Bearer {token}'}

    def test_prepare_add_member_succeeds_for_admin(self):
        response = self.client.post(
            f'/teams/{self.team.slug}/members/prepare',
            json={'email': self.member.email},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['team_slug'], self.team.slug)
        self.assertEqual(payload['target_user']['email'], self.member.email)
        self.assertEqual(payload['target_user']['public_key'], self.member.public_key)

    def test_prepare_add_member_requires_admin(self):
        response = self.client.post(
            f'/teams/{self.team.slug}/members/prepare',
            json={'email': self.member.email},
            headers=self.auth_headers(self.outsider.id),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()['error'], 'UNAUTHORIZED: admin access required')

    def test_prepare_add_member_requires_existing_user_public_key(self):
        response = self.client.post(
            f'/teams/{self.team.slug}/members/prepare',
            json={'email': self.no_key_user.email},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['error'], 'User has not uploaded a public key yet')

    def test_confirm_add_member_creates_membership_and_vault_key(self):
        response = self.client.post(
            f'/teams/{self.team.slug}/members/confirm',
            json={
                'target_user_id': self.member.id,
                'encrypted_key': 'wrapped-team-key-for-member',
            },
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(
            TeamMembership.query.filter_by(team_id=self.team.id, user_id=self.member.id).first()
        )
        new_vault_key = VaultKey.query.filter_by(team_id=self.team.id, user_id=self.member.id).first()
        self.assertIsNotNone(new_vault_key)
        self.assertEqual(new_vault_key.encrypted_key, 'wrapped-team-key-for-member')

    def test_confirm_add_member_rejects_existing_member(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.add(
            VaultKey(user_id=self.member.id, team_id=self.team.id, encrypted_key='existing-envelope')
        )
        db.session.commit()

        response = self.client.post(
            f'/teams/{self.team.slug}/members/confirm',
            json={
                'target_user_id': self.member.id,
                'encrypted_key': 'wrapped-team-key-for-member',
            },
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['error'], 'User is already a member of this team')

    def test_confirm_add_member_requires_admin(self):
        response = self.client.post(
            f'/teams/{self.team.slug}/members/confirm',
            json={
                'target_user_id': self.member.id,
                'encrypted_key': 'wrapped-team-key-for-member',
            },
            headers=self.auth_headers(self.outsider.id),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()['error'], 'UNAUTHORIZED: admin access required')

    def test_update_member_role_promotes_member_to_admin(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.commit()

        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.member.email, 'role': 'admin'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        updated_membership = TeamMembership.query.filter_by(
            team_id=self.team.id, user_id=self.member.id
        ).first()
        self.assertEqual(updated_membership.role, 'admin')

    def test_update_member_role_requires_admin(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.commit()

        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.member.email, 'role': 'admin'},
            headers=self.auth_headers(self.outsider.id),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()['error'], 'UNAUTHORIZED: admin access required')

    def test_update_member_role_blocks_demoting_last_admin(self):
        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.admin.email, 'role': 'member'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()['error'],
            'Cannot demote yourself because you are the last admin'
        )

    def test_update_member_role_allows_demoting_when_other_admin_exists(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='admin')
        )
        db.session.commit()

        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.admin.email, 'role': 'member'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        updated_membership = TeamMembership.query.filter_by(
            team_id=self.team.id, user_id=self.admin.id
        ).first()
        self.assertEqual(updated_membership.role, 'member')

    def test_update_member_role_reports_already_admin(self):
        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.admin.email, 'role': 'admin'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['message'], 'User is already an admin')

    def test_update_member_role_reports_already_member(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.commit()

        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.member.email, 'role': 'member'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['message'], 'User is already a member')

    def test_update_member_role_self_demote_last_admin_has_specific_message(self):
        response = self.client.patch(
            f'/teams/{self.team.slug}/members/role',
            json={'email': self.admin.email, 'role': 'member'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()['error'],
            'Cannot demote yourself because you are the last admin'
        )

    def test_list_teams_returns_membership_metadata(self):
        response = self.client.get(
            '/teams',
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        teams = response.get_json()['teams']
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0]['team_slug'], self.team.slug)
        self.assertEqual(teams[0]['role'], 'admin')

    def test_list_members_returns_team_members_and_roles(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.commit()

        response = self.client.get(
            f'/teams/{self.team.slug}/members',
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['team_slug'], self.team.slug)
        emails = {member['email']: member['role'] for member in payload['members']}
        self.assertEqual(emails['admin@example.com'], 'admin')
        self.assertEqual(emails['member@example.com'], 'member')

    def test_leave_team_removes_member_and_vault_key(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.add(
            VaultKey(user_id=self.member.id, team_id=self.team.id, encrypted_key='member-envelope')
        )
        db.session.commit()

        response = self.client.delete(
            f'/teams/{self.team.slug}/members/me',
            headers=self.auth_headers(self.member.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            TeamMembership.query.filter_by(team_id=self.team.id, user_id=self.member.id).first()
        )
        self.assertIsNone(
            VaultKey.query.filter_by(team_id=self.team.id, user_id=self.member.id).first()
        )
        self.assertIsNotNone(Team.query.filter_by(id=self.team.id).first())

    def test_leave_team_blocks_last_admin_when_members_remain(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.add(
            VaultKey(user_id=self.member.id, team_id=self.team.id, encrypted_key='member-envelope')
        )
        db.session.commit()

        response = self.client.delete(
            f'/teams/{self.team.slug}/members/me',
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()['error'],
            'Cannot leave team as the last admin while other members still belong to it'
        )

    def test_leave_team_deletes_empty_team(self):
        response = self.client.delete(
            f'/teams/{self.team.slug}/members/me',
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['deleted_team'])
        self.assertIsNone(Team.query.filter_by(id=self.team.id).first())

    def test_save_secret_updates_vault_for_admin(self):
        response = self.client.post(
            '/vault',
            json={
                'team_id': self.team.id,
                'env_blob': 'updated-encrypted-env',
                'password': 'pw',
            },
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['message'], 'Vault securely updated')
        updated_team = Team.query.get(self.team.id)
        self.assertEqual(updated_team.env_blob, 'updated-encrypted-env')

    def test_save_secret_rejects_non_admin_member(self):
        db.session.add(
            TeamMembership(user_id=self.member.id, team_id=self.team.id, role='member')
        )
        db.session.add(
            VaultKey(user_id=self.member.id, team_id=self.team.id, encrypted_key='member-envelope')
        )
        db.session.commit()

        response = self.client.post(
            '/vault',
            json={
                'team_id': self.team.id,
                'env_blob': 'updated-encrypted-env',
                'password': 'pw',
            },
            headers=self.auth_headers(self.member.id),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.get_json()['error'],
            'UNAUTHORIZED: admin access required to push'
        )

    def test_save_secret_requires_password(self):
        response = self.client.post(
            '/vault',
            json={'team_id': self.team.id, 'env_blob': 'updated-encrypted-env'},
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error'], 'Password required to push')

    def test_save_secret_rejects_invalid_password(self):
        response = self.client.post(
            '/vault',
            json={
                'team_id': self.team.id,
                'env_blob': 'updated-encrypted-env',
                'password': 'wrong-password',
            },
            headers=self.auth_headers(self.admin.id),
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['error'], 'Invalid username or password')


if __name__ == '__main__':
    unittest.main()
