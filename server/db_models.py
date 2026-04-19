from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import re

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(120), unique = True, nullable = False)
    password_hash = db.Column(db.String(256), nullable = False)
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    public_key = db.Column(db.Text, nullable = True)

    memberships = db.relationship('TeamMembership', backref = 'user', lazy = True)

class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    slug = db.Column(db.String(100), unique = True, nullable = False)
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    memberships = db.relationship('TeamMembership', backref='team', lazy = True)
    secrets = db.relationship('Vault', backref='team', lazy = True)

    @staticmethod
    def generate_slug(name):
        """Converts 'My Team' to 'my-team'"""
        return re.sub(r'[\s_]+', '-', re.sub(r'[^\w\s-]', '', name).lower()).strip('-')
    
class TeamMembership(db.Model):
    __tablename__ = 'team_memberships'

    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable = False)
    role = db.Column(db.String(20), default = 'member') ## options are 'member' or 'admin'
    joined_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Vault(db.Model):
    __tablename__ = 'secrets'

    id = db.Column(db.Integer, primary_key = True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable = False)

    ## have to use Text type to avoid size limits of String type
    encrypted_blob = db.Column(db.Text, nullable = False)

    version = db.Column(db.Integer, default = 1)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

## e2e encryption method to deliver team keys
class VaultKey(db.Model):
    __tablename__ = 'vault_keys'

    id = db.Column(db.Integer, primary_key=True)
    
    vault_id = db.Column(db.Integer, db.ForeignKey('secrets.id'), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    encrypted_key = db.Column(db.Text, nullable=False)