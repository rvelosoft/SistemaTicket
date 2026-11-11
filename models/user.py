from flask_login import UserMixin
from models import db

class User(UserMixin, db.Model):

    __tablename__ = "Usuarios"

    IdUsuario = db.Column(
        db.Integer,
        primary_key=True
    )

    Usuario = db.Column(
        db.String(100),
        unique=True
    )

    NombreCompleto = db.Column(
        db.String(200)
    )

    Correo = db.Column(
        db.String(200)
    )

    PasswordHash = db.Column(
        db.String(500)
    )

    Activo = db.Column(
        db.Boolean,
        default=True
    )

    def get_id(self):
        return str(self.IdUsuario)