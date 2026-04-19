from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from db_models import db, User, Team, TeamMembership, Vault, VaultKey
from datetime import datetime, timezone

import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# postgresql://[user]:[password]@[host]:[port]/[database_name]
# config
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/envsync_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# jwt config
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_KEY')

CORS(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
db.init_app(app)
migrate = Migrate(app, db)

############################## endpoints ################################

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'User already exists with this email'}), 409
    
    hash = bcrypt.generate_password_hash(data['password'])
    hashed_pw = hash.decode('utf-8')

    user = User(email = data['email'], password_hash = hashed_pw)

    try: 
        db.session.add(user)
        db.session.commit()
        return jsonify({'message' : 'User created successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error' : 'Database error as follows', 'details' : str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not data or not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400
    
    user = User.query.filter_by(email=data['email']).first()

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful!',
        'access_token': token
    }), 200

@app.route('/teams', methods=['POST'])
@jwt_required()
def create_team():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    team_name = data.get('name')
    if not team_name:
        return jsonify({'error': 'No team specified'}), 400
    
    slug = Team.generate_slug(team_name)
    
    if Team.query.filter_by(slug=slug).first():
        return jsonify({'error': 'Team with this name already exists'}), 409
    
    try:
        new_team = Team(name=team_name, slug=slug)
        db.session.add(new_team)
        
        db.session.flush()

        membership = TeamMembership(
            user_id = current_user_id,
            team_id= new_team.id,
            role = 'admin'
        )
        db.session.add(membership)

        db.session.commit()

        return jsonify({
            'message': f'Team {team_name} successfully created.',
            'team_id': new_team.id
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Database error', 
            'details': str(e)
        }), 500
    

@app.route('/teams', methods=['GET'])
@jwt_required()
def list_teams():
    current_user_id = get_jwt_identity()

    memberships = TeamMembership.query.filter_by(user_id=current_user_id).all()

    teams = []
    for membership in memberships:
        team = membership.team
        if team:
            teams.append({
                'team_id': team.id,
                'team_name': team.name,
                'role': membership.role,
                'joined_at': team.joined_timestamp
            })
    return jsonify({
        'teams': teams
    }), 200

@app.route('/vault', methods=['POST'])
@jwt_required()
def save_secret():
    # 1. Cast user_id to int to ensure DB compatibility
    user_id = int(get_jwt_identity()) 
    data = request.get_json()
    team_id = data.get('team_id')
    env_blob = data.get('env_blob')
    encrypted_keys = data.get('encrypted_keys', {})

    if not team_id or not env_blob:
        return jsonify({'error': 'Missing team_id or encrypted_blob'}), 400

    membership = TeamMembership.query.filter_by(user_id=user_id, team_id=team_id).first()
    if not membership:
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 403
    
    try:
        vault = Vault.query.filter_by(team_id=team_id).first()
        if vault:
            vault.encrypted_blob = env_blob
            vault.version += 1
            vault.updated_at = datetime.now(timezone.utc)
        else:
            vault = Vault(team_id=team_id, encrypted_blob=env_blob)
            db.session.add(vault)
        
        db.session.flush() 

        VaultKey.query.filter_by(vault_id=vault.id).delete()

        for uid_str, enc_key in encrypted_keys.items():
            new_vault_key = VaultKey(
                vault_id=vault.id, 
                user_id=int(uid_str), 
                encrypted_key=enc_key
            )
            db.session.add(new_vault_key)

        db.session.commit()
        return jsonify({'message': f'Vault securely updated to version {vault.version}'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500
            

@app.route('/vault', methods=['GET'])
@jwt_required()
def get_secrets():
    user_id = int(get_jwt_identity())
    team_slug = request.args.get('team')

    team = Team.query.filter_by(slug=team_slug).first()
    if not team:
        return jsonify({'eror': 'Team not found'}), 404
    
    membership = TeamMembership.query.filter_by(user_id = user_id, team_id = team.id).first()
    if not membership:
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 400
    
    vault = Vault.query.filter_by(team_id = team.id).first()
    if not vault:
        return jsonify({'error': 'No secrets yet for this team'}), 404
    
    user_vault_key = VaultKey.query.filter_by(vault_id=vault.id, user_id=user_id).first()
    if not user_vault_key:
        return jsonify({'error': 'No access key found for this user in this vault'}), 403

    return jsonify({
        'team_id': team.id,
        'version': vault.version,
        'env_blob': vault.encrypted_blob,
        'encrypted_key': user_vault_key.encrypted_key,
        'updated_at': vault.updated_at
    }), 200
        

@app.route('/public_key', methods=['POST'])
@jwt_required()
def upload_pubkey():
    user_id = get_jwt_identity()

    data = request.json
    pub = data.get('public_key')

    if not pub:
        return jsonify({'message': 'No public key available'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return({'error': 'User not found. '}), 404
    
    user.public_key = pub
    db.session.commit()
    
    return jsonify({'message': 'Public key successfully saved to database'}), 200

@app.route('/team/<int:team_id>/keys', methods=['GET'])
@jwt_required()
def get_team_keys(team_id):
    user_id = get_jwt_identity()
    
    membership = TeamMembership.query.filter_by(user_id=user_id, team_id=team_id).first()
    if not membership:
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 403
        
    team_members = TeamMembership.query.filter_by(team_id=team_id).all()
    
    keys = {}
    for member in team_members:
        user = User.query.get(member.user_id)
        if user and user.public_key:
            keys[user.id] = user.public_key
            
    return jsonify({'keys': keys}), 200

if __name__ == '__main__':
    app.run(debug=True, port=7070)
