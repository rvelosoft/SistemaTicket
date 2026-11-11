from flask import Flask
from config import Config

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from models import db
from flask_login import (
    LoginManager
)

from models.user import User
from auth.routes import auth_bp
from routes.home import home_bp
from routes.tickets import ticket_bp

app = Flask(__name__)
app.config.from_object(
    Config
)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):

    return User.query.get(
        int(user_id)
    )

app.register_blueprint(
    auth_bp
)

app.register_blueprint(
    home_bp
)

app.register_blueprint(
    ticket_bp
)

if __name__ == "__main__":

    app.run(
        debug=True
    )