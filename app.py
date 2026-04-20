from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError
from db_models import db, User, Team, TeamMembership, VaultKey
from datetime import timedelta
from email_validator import validate_email as lib_validate_email, EmailNotValidError

import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# postgresql://[user]:[password]@[host]:[port]/[database_name]
# config
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# jwt config
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_KEY')
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)

CORS(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
db.init_app(app)
migrate = Migrate(app, db)

############################## endpoints ################################

def get_team_by_slug(team_slug):
    return Team.query.filter_by(slug=team_slug).first()

def get_membership(team_id, user_id):
    return TeamMembership.query.filter_by(team_id=team_id, user_id=user_id).first()

def get_admin_membership(team_id, user_id):
    return TeamMembership.query.filter_by(team_id=team_id, user_id=user_id, role='admin').first()

def get_other_admin_membership(team_id, excluded_user_id):
    return TeamMembership.query.filter(
        TeamMembership.team_id == team_id,
        TeamMembership.user_id != excluded_user_id,
        TeamMembership.role == 'admin'
    ).first()

def get_user_by_email(email):
    if not email:
        return None
    return User.query.filter_by(email=email.strip().lower()).first()

def get_user_or_404(user_id):
    return User.query.get(user_id)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    try:
        valid = lib_validate_email(email, check_deliverability=True)
        normalized_email = valid.normalized
    except EmailNotValidError as _:
        return jsonify({'error': 'Please try again with a valid email address!'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters in length'}), 400
    
    if User.query.filter_by(email=normalized_email).first():
        return jsonify({'error': 'An account has already been created with this email!'}), 409

    hash = bcrypt.generate_password_hash(data['password'])
    hashed_pw = hash.decode('utf-8')

    user = User(email=normalized_email, password_hash=hashed_pw)

    try: 
        db.session.add(user)
        db.session.commit()
        return jsonify({'message' : 'User created successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        print(f'CRITICAL DB ERROR DURING REGISTRATION: {e}')
        return jsonify({'error' : 'An internal server error occured! Please try again.'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    email = data.get('email')
    password = data.get('password')

    if not data or not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400
    
    try:
        valid = lib_validate_email(email, check_deliverability=False)
        email = valid.normalized
    except EmailNotValidError:
        # If it's a completely invalid string, they definitely don't have an account
        return jsonify({'error': 'Invalid username or password'}), 401
    
    user = User.query.filter_by(email=email).first()

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
    env_blob = data.get('env_blob', '') # encrypted vault payload
    encrypted_key = data.get('encrypted_key') # The Vault Key wrapped in Admin's RSA Public Key

    if not team_name:
        return jsonify({'error': 'No team specified'}), 400
    if not encrypted_key:
        return jsonify({'error': 'Must provide the initial encrypted_key envelope'}), 400
    
    slug = Team.generate_slug(team_name)
    
    if Team.query.filter_by(slug=slug).first():
        return jsonify({'error': 'Team with this name already exists'}), 409
    
    try:
        new_team = Team(name=team_name, slug=slug, env_blob=env_blob)
        db.session.add(new_team)
        db.session.flush() # new team id

        # created added as admin
        membership = TeamMembership(
            user_id=current_user_id,
            team_id=new_team.id,
            role='admin'
        )
        db.session.add(membership)

        # save admins envelope
        vault_key = VaultKey(
            team_id=new_team.id,
            user_id=current_user_id,
            encrypted_key=encrypted_key
        )
        db.session.add(vault_key)

        db.session.commit()

        return jsonify({
            'message': f'Team {team_name} successfully created with persistent vault key.',
            'team_id': new_team.id,
            'slug': new_team.slug
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Database error', 
            'details': str(e)
        }), 500
    

@app.route('/teams', methods=['GET'])
@jwt_required()
def list_teams():
    current_user_id = int(get_jwt_identity())

    memberships = TeamMembership.query.filter_by(user_id=current_user_id).all()

    teams = []
    for membership in memberships:
        team = membership.team
        if team:
            teams.append({
                'team_id': team.id,
                'team_slug': team.slug,
                'team_name': team.name,
                'role': membership.role,
                'joined_at': membership.joined_timestamp
            })
    return jsonify({
        'teams': teams
    }), 200

@app.route('/teams/<string:team_slug>/members/me', methods=['DELETE'])
@jwt_required()
def leave_team(team_slug):
    current_user_id = int(get_jwt_identity())

    team = get_team_by_slug(team_slug)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    membership = get_membership(team.id, current_user_id)
    if not membership:
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 403

    remaining_memberships = TeamMembership.query.filter(
        TeamMembership.team_id == team.id,
        TeamMembership.user_id != current_user_id
    ).all()

    is_last_admin = (
        membership.role == 'admin' and
        not any(other.role == 'admin' for other in remaining_memberships)
    )

    if is_last_admin and remaining_memberships:
        return jsonify({
            'error': 'Cannot leave team as the last admin while other members still belong to it'
        }), 409

    try:
        VaultKey.query.filter_by(team_id=team.id, user_id=current_user_id).delete()
        db.session.delete(membership)

        deleted_team = False
        if not remaining_memberships:
            db.session.delete(team)
            deleted_team = True

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({
        'message': 'Left team successfully',
        'team_slug': team.slug,
        'deleted_team': deleted_team,
    }), 200

@app.route('/teams/<string:team_slug>/members/prepare', methods=['POST'])
@jwt_required()
def prepare_add_member(team_slug):
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({'error': 'Missing email'}), 400

    team = get_team_by_slug(team_slug)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    if not get_admin_membership(team.id, current_user_id):
        return jsonify({'error': 'UNAUTHORIZED: admin access required'}), 403

    target_user = get_user_by_email(email)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404

    if not target_user.public_key:
        return jsonify({'error': 'User has not uploaded a public key yet'}), 409

    if get_membership(team.id, target_user.id):
        return jsonify({'error': 'User is already a member of this team'}), 409

    return jsonify({
        'team_id': team.id,
        'team_slug': team.slug,
        'team_name': team.name,
        'target_user': {
            'id': target_user.id,
            'email': target_user.email,
            'public_key': target_user.public_key,
        }
    }), 200

@app.route('/teams/<string:team_slug>/members', methods=['GET'])
@jwt_required()
def list_team_members(team_slug):
    current_user_id = int(get_jwt_identity())

    team = get_team_by_slug(team_slug)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    if not get_membership(team.id, current_user_id):
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 403

    memberships = TeamMembership.query.filter_by(team_id=team.id).all()
    members = []
    for membership in memberships:
        user = User.query.get(membership.user_id)
        if user:
            members.append({
                'user_id': user.id,
                'email': user.email,
                'role': membership.role,
                'joined_at': membership.joined_timestamp,
            })

    return jsonify({
        'team_slug': team.slug,
        'members': members,
    }), 200

@app.route('/teams/<string:team_slug>/members/confirm', methods=['POST'])
@jwt_required()
def confirm_add_member(team_slug):
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    target_user_id = data.get('target_user_id')
    encrypted_key = data.get('encrypted_key')

    if not target_user_id or not encrypted_key:
        return jsonify({'error': 'Missing target_user_id or encrypted_key'}), 400

    team = get_team_by_slug(team_slug)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    if not get_admin_membership(team.id, current_user_id):
        return jsonify({'error': 'UNAUTHORIZED: admin access required'}), 403

    target_user = get_user_or_404(target_user_id)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404

    if not target_user.public_key:
        return jsonify({'error': 'User has not uploaded a public key yet'}), 409

    if get_membership(team.id, target_user.id):
        return jsonify({'error': 'User is already a member of this team'}), 409

    membership = TeamMembership(
        user_id=target_user.id,
        team_id=team.id,
        role='member'
    )
    vault_key = VaultKey(
        team_id=team.id,
        user_id=target_user.id,
        encrypted_key=encrypted_key
    )

    try:
        db.session.add(membership)
        db.session.add(vault_key)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'User is already a member of this team'}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({
        'message': 'Member added successfully',
        'team_id': team.id,
        'team_slug': team.slug,
        'user_id': target_user.id,
        'email': target_user.email,
    }), 201

@app.route('/teams/<string:team_slug>/members/role', methods=['PATCH'])
@jwt_required()
def update_member_role(team_slug):
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    new_role = data.get('role')

    if not email:
        return jsonify({'error': 'Missing email'}), 400

    if new_role not in ('admin', 'member'):
        return jsonify({'error': 'Invalid role'}), 400

    team = get_team_by_slug(team_slug)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    if not get_admin_membership(team.id, current_user_id):
        return jsonify({'error': 'UNAUTHORIZED: admin access required'}), 403

    target_user = get_user_by_email(email)
    if not target_user:
        return jsonify({'error': 'User not found'}), 404

    target_membership = get_membership(team.id, target_user.id)
    if not target_membership:
        return jsonify({'error': 'User is not a member of this team'}), 404

    if target_membership.role == new_role:
        return jsonify({
            'message': 'Role already set',
            'team_slug': team.slug,
            'email': target_user.email,
            'role': new_role,
        }), 200

    if target_membership.role == 'admin' and new_role == 'member':
        if not get_other_admin_membership(team.id, target_user.id):
            return jsonify({'error': 'Cannot demote the last admin'}), 409

    target_membership.role = new_role

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({
        'message': 'Role updated successfully',
        'team_slug': team.slug,
        'email': target_user.email,
        'role': new_role,
    }), 200

@app.route('/vault', methods=['POST'])
@jwt_required()
def save_secret():
    user_id = int(get_jwt_identity()) 
    data = request.get_json()
    
    team_id = data.get('team_id')
    env_blob = data.get('env_blob')

    if not team_id or not env_blob:
        return jsonify({'error': 'Missing team_id or env_blob'}), 400

    membership = TeamMembership.query.filter_by(user_id=user_id, team_id=team_id).first()
    if not membership:
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 403
    
    try:
        team = Team.query.get(team_id)
        if not team:
            return jsonify({'error': 'Team not found'}), 404

        if not get_admin_membership(team.id, user_id):
            return jsonify({'error': 'UNAUTHORIZED: admin access required to push'}), 403

        team.env_blob = env_blob
        db.session.commit()
        
        return jsonify({'message': 'Vault securely updated'}), 200
    
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
        return jsonify({'error': 'Team not found'}), 404
    
    membership = TeamMembership.query.filter_by(user_id=user_id, team_id=team.id).first()
    if not membership:
        return jsonify({'error': 'UNAUTHORIZED: not a team member'}), 403
    
    # Grab the specific envelope for THIS user
    user_vault_key = VaultKey.query.filter_by(team_id=team.id, user_id=user_id).first()
    if not user_vault_key:
        return jsonify({'error': 'No access key found for this user in this vault'}), 403

    return jsonify({
        'team_id': team.id,
        'env_blob': team.env_blob,
        'encrypted_key': user_vault_key.encrypted_key,
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

@app.route('/whoami', methods=['GET'])
@jwt_required()
def who_am_i():
    user_id = get_jwt_identity()
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return jsonify({'error': 'No user found.'}), 404
    
    return jsonify({'email': user.email}), 200

@app.route('/teams/<string:team_slug>', methods=['DELETE'])
@jwt_required()
def delete_team(team_slug):
    current_user_id = int(get_jwt_identity())

    team = get_team_by_slug(team_slug)
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    admin_membership = get_admin_membership(team.id, current_user_id)
    if not admin_membership:
        return jsonify({'error': 'UNAUTHORIZED: admin access required'}), 403

    try:
        db.session.delete(team)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({
        'message': 'Team deleted successfully',
        'team_slug': team.slug,
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7070))
    app.run(host='0.0.0.0', port=port)
