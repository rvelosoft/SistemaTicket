from flask import Flask
from flask_login import LoginManager
from sqlalchemy import inspect, text

from auth.routes import auth_bp
from config import Config
from models import db
from models.company import Empresa
from models.role import Perfil
from models.tipo_ticket import TipoTicket
from models.user import User
from models.work_group import GrupoTrabajo
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
    if "IdGrupo" not in columnas_usuario:
        db.session.execute(text(
            'ALTER TABLE "Usuarios" ADD COLUMN "IdGrupo" '
            'INTEGER REFERENCES "GruposTrabajo" ("IdGrupo")'
        ))

    if not TipoTicket.query.first():
        db.session.add_all([
            TipoTicket(NombreTipo="Incidente"),
            TipoTicket(NombreTipo="Requerimiento"),
            TipoTicket(NombreTipo="Warnings")
        ])
    db.session.flush()

    columnas_ticket = {
        columna["name"]
        for columna in inspect(db.engine).get_columns("Tickets")
    }
    if "IdTipoTicket" not in columnas_ticket:
        db.session.execute(text(
            'ALTER TABLE "Tickets" ADD COLUMN "IdTipoTicket" '
            'INTEGER REFERENCES "TiposTicket" ("IdTipoTicket")'
        ))

    tipo_predeterminado = TipoTicket.query.filter_by(
        NombreTipo="Incidente"
    ).first() or TipoTicket.query.order_by(TipoTicket.IdTipoTicket).first()
    if tipo_predeterminado is None:
        raise RuntimeError("No hay tipos de ticket para asignar a tickets existentes.")
    db.session.execute(
        text(
            'UPDATE "Tickets" SET "IdTipoTicket" = :tipo_id '
            'WHERE "IdTipoTicket" IS NULL'
        ),
        {"tipo_id": tipo_predeterminado.IdTipoTicket}
    )

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
