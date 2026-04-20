from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import re

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    public_key = db.Column(db.Text, nullable=True)

    # relationships #
    memberships = db.relationship('TeamMembership', back_populates='user', cascade='all, delete-orphan')
    vault_keys = db.relationship('VaultKey', back_populates='user', cascade='all, delete-orphan')

class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    
    # The actual .env payload encrypted with the symmetric Vault Key
    env_blob = db.Column(db.Text, nullable=True) 
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # relationships #
    memberships = db.relationship('TeamMembership', back_populates='team', cascade='all, delete-orphan')
    vault_keys = db.relationship('VaultKey', back_populates='team', cascade='all, delete-orphan')

    @staticmethod
    def generate_slug(name):
        """Converts 'My Team' to 'my-team'"""
        slug = re.sub(r'[\s_]+', '-', re.sub(r'[^\w\s-]', '', name).lower()).strip('-')
        if name != slug:
            print('Team names with spaces or capitalization are converted to a standard format:')
        return slug

class TeamMembership(db.Model):
    __tablename__ = 'team_memberships'
    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', name='uq_team_membership_team_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    role = db.Column(db.String(20), default='member') ## options are 'member' or 'admin'
    joined_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', back_populates='memberships')
    team = db.relationship('Team', back_populates='memberships')


## e2e encryption method to deliver team keys
class VaultKey(db.Model):
    __tablename__ = 'vault_keys'
    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', name='uq_vault_key_team_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    
    # Points directly to the team now
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # The symmetric vault key, encrypted with this specific user's RSA public key
    encrypted_key = db.Column(db.Text, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='vault_keys')
    team = db.relationship('Team', back_populates='vault_keys')
