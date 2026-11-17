from models import db


class Empresa(db.Model):
    __tablename__ = "Empresas"

    IdEmpresa = db.Column(db.Integer, primary_key=True)
    NombreEmpresa = db.Column(db.String(200), unique=True, nullable=False)

    grupos = db.relationship(
        "GrupoTrabajo",
        secondary="EmpresasGrupos",
        back_populates="empresas",
        order_by="GrupoTrabajo.NombreGrupo"
    )
