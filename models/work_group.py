from models import db


empresas_grupos = db.Table(
    "EmpresasGrupos",
    db.Column(
        "IdEmpresa",
        db.Integer,
        db.ForeignKey("Empresas.IdEmpresa"),
        primary_key=True
    ),
    db.Column(
        "IdGrupo",
        db.Integer,
        db.ForeignKey("GruposTrabajo.IdGrupo"),
        primary_key=True
    )
)


class GrupoTrabajo(db.Model):
    __tablename__ = "GruposTrabajo"

    IdGrupo = db.Column(db.Integer, primary_key=True)
    NombreGrupo = db.Column(db.String(150), unique=True, nullable=False)

    empresas = db.relationship(
        "Empresa",
        secondary=empresas_grupos,
        back_populates="grupos",
        order_by="Empresa.NombreEmpresa"
    )
    usuarios = db.relationship("User", back_populates="grupo")