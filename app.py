from flask import Flask
from flask.cli import load_dotenv
from flask_cors import CORS
from config.database import db
from config.marshmallow import ma
from config.bcrypt import bcrypt
from apis.users import users
from apis.authentication import authentication


import os

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_CONFIG")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
CORS(app, supports_credentials=True)

db.app = app
db.init_app(app)
ma.app = app
ma.init_app(app)
bcrypt.app = app
bcrypt.init_app(app)

app.register_blueprint(users)
app.register_blueprint(authentication)


@app.route("/", methods=["GET"])
def home():
    return "Welcome to FYP backend !"


if __name__ == "__main__":

    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", debug=True)
