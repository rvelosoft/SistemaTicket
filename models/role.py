from models import db


class Perfil(db.Model):
    __tablename__ = "Perfiles"

    IdPerfil = db.Column(db.Integer, primary_key=True)
    NombrePerfil = db.Column(db.String(100), unique=True, nullable=False)
    EsAdministrador = db.Column(db.Boolean, nullable=False, default=False)
