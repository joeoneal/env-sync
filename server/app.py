from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from db_models import db 

app = Flask(__name__)

# postgresql://[user]:[password]@[host]:[port]/[database_name]
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/envsync_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
db.init_app(app)
migrate = Migrate(app, db)

@app.route('/register', method=['POST'])
def register():
    pass

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
