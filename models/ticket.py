from models import db

class Ticket(db.Model):

    __tablename__ = "Tickets"

    IdTicket = db.Column(
        db.Integer,
        primary_key=True
    )

    FechaApertura = db.Column(
        db.DateTime
    )

    FechaCierre = db.Column(
        db.DateTime
    )

    Titulo = db.Column(
        db.String(300)
    )

    Descripcion = db.Column(
        db.Text
    )

    TotalHH = db.Column(
        db.Numeric(10,2)
    )

    Estado = db.Column(
        db.String(30)
    )

    UsuarioCreacion = db.Column(
        db.Integer,
        db.ForeignKey(
            "Usuarios.IdUsuario"
        )
    )

    usuario_creacion = db.relationship(
        "User",
        foreign_keys=[UsuarioCreacion]
    )