from models import db


class TipoTicket(db.Model):
    __tablename__ = "TiposTicket"

    IdTipoTicket = db.Column(db.Integer, primary_key=True)
    NombreTipo = db.Column(db.String(100), unique=True, nullable=False)
