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

    totp_secret = db.Column(
        db.Text,
        nullable=True
    )

    totp_verificado = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    Activo = db.Column(
        db.Boolean,
        default=True
    )

    IdPerfil = db.Column(
        db.Integer,
        db.ForeignKey("Perfiles.IdPerfil")
    )

    IdEmpresa = db.Column(
        db.Integer,
        db.ForeignKey("Empresas.IdEmpresa")
    )

    IdGrupo = db.Column(
        db.Integer,
        db.ForeignKey("GruposTrabajo.IdGrupo")
    )

    perfil = db.relationship("Perfil")
    empresa = db.relationship("Empresa")
    grupo = db.relationship("GrupoTrabajo", back_populates="usuarios")

    @property
    def EsAdministrador(self):
        return bool(self.perfil and self.perfil.EsAdministrador)

    @property
    def EsUsuario(self):
        return bool(
            self.perfil
            and self.perfil.NombrePerfil.casefold() == "usuario"
        )

    def get_id(self):
        return str(self.IdUsuario)
