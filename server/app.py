from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from db_models import db, User

app = Flask(__name__)
bcrypt = Bcrypt(app)

# postgresql://[user]:[password]@[host]:[port]/[database_name]
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/envsync_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db.init_app(app)
migrate = Migrate(app, db)

@app.route('/register', method=['POST'])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'User already exists with this email'}), 409
    
    hash = bcrypt.generate_password_hash(data['password'])
    hashed_pw = hash.decode('utf-8')

    user = User(email = data['email'], password = hashed_pw)

    try: 
        db.session.add(user)
        db.sessions.commit()
        return jsonify({'message' : 'User created successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error' : 'Database error as follows', 'details' : str(e)}), 500

@app.route('/login', method=['GET'])
def login():
    pass

@app.route('/vault', method=['POST'])
def create_secret():
    pass

@app.route('/vault', method=['GET'])
def get_secrets():
    pass

if __name__ == '__main__':
    app.run(debug=True, port=7070)
