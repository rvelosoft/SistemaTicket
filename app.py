from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from auth.routes import auth_bp
from config import Config
from models import db
from models.company import Empresa
from models.role import Perfil
from models.user import User
from routes.home import home_bp
from routes.maintenance import maintenance_bp
from routes.tickets import ticket_bp

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.Activo is not False else None


app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(ticket_bp)
app.register_blueprint(maintenance_bp)

with app.app_context():
    db.create_all()
    columnas_usuario = {
        columna["name"]
        for columna in inspect(db.engine).get_columns("Usuarios")
    }
    if "IdPerfil" not in columnas_usuario:
        db.session.execute(text(
            'ALTER TABLE "Usuarios" ADD COLUMN "IdPerfil" '
            'INTEGER REFERENCES "Perfiles" ("IdPerfil")'
        ))
    if "IdEmpresa" not in columnas_usuario:
        db.session.execute(text(
            'ALTER TABLE "Usuarios" ADD COLUMN "IdEmpresa" '
            'INTEGER REFERENCES "Empresas" ("IdEmpresa")'
        ))

    if not Perfil.query.filter_by(NombrePerfil="Administrador").first():
        db.session.add(Perfil(
            NombrePerfil="Administrador",
            EsAdministrador=True
        ))
    if not Perfil.query.filter_by(NombrePerfil="Usuario").first():
        db.session.add(Perfil(
            NombrePerfil="Usuario",
            EsAdministrador=False
        ))
    db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
