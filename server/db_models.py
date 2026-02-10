from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(120), unique = True, nullable = False)
    password_hash = db.Column(db.String(256), nullable = False)
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    ## public_key = db.Column(db.Text, nullable = True)

    memberships = db.relationship('TeamMembership', backref = 'user', lazy = 'True')

class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100), nullable = False)
    creation_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    memberships = db.relationship('TeamMembership', backref='team', lazy = True)
    secrets = db.relationship('Vault', backref='team', lazy = True)
    
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

    ## WILL CHANGE AFTER COMPLETING MVP 
    ## --> will need to add on blob per user per team INSTEAD of one blob per team
    ## user_id = db.Column(db.Integer, db.ForeignKey('users.id))