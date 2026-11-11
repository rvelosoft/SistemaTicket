from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

from models.ticket import Ticket
from models import db

ticket_bp = Blueprint(
    "tickets",
    __name__
)

@ticket_bp.route(
    "/ticket/nuevo"
)
@login_required
def nuevo_ticket():

    hoy = datetime.now()

    return render_template(
        "tickets/nuevo_ticket.html",
        fecha=hoy
    )


@ticket_bp.route(
    "/ticket/guardar",
    methods=["POST"]
)
@login_required
def guardar_ticket():

    ticket = Ticket()

    ticket.FechaApertura = datetime.strptime(
        request.form["fecha_apertura"],
        "%Y-%m-%d"
    )

    ticket.FechaCierre = datetime.strptime(
        request.form["fecha_cierre"],
        "%Y-%m-%d"
    )

    ticket.Titulo = request.form["titulo"]

    ticket.Descripcion = request.form[
        "descripcion"
    ]

    ticket.TotalHH = request.form[
        "total_hh"
    ]

    ticket.Estado = request.form[
        "estado"
    ]

    ticket.UsuarioCreacion = (
        current_user.IdUsuario
    )

    db.session.add(ticket)

    db.session.commit()

    flash("Ticket registrado correctamente")

    return redirect(
        url_for(
            "home.menu"
        )
    )