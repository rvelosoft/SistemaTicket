from flask import Flask
from flask_login import LoginManager

from auth.routes import auth_bp
from config import Config
from models import db
from models.user import User
from routes.home import home_bp
from routes.tickets import ticket_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(ticket_bp)

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
