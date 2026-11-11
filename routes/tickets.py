from datetime import datetime
from decimal import Decimal, InvalidOperation
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
        fecha=hoy,
        valores={},
        errores=[]
    )


@ticket_bp.route(
    "/ticket/guardar",
    methods=["POST"]
)
@login_required
def guardar_ticket():

    valores = {
        campo: request.form.get(campo, "").strip()
        for campo in (
            "fecha_apertura",
            "fecha_cierre",
            "titulo",
            "descripcion",
            "total_hh",
            "estado"
        )
    }
    errores = []
    fechas = {}

    for campo, etiqueta in (
        ("fecha_apertura", "Fecha de apertura"),
        ("fecha_cierre", "Fecha de cierre")
    ):
        if not valores[campo]:
            errores.append(f"{etiqueta} es obligatoria.")
            continue

        try:
            fechas[campo] = datetime.strptime(
                valores[campo],
                "%Y-%m-%d"
            )
        except ValueError:
            errores.append(f"{etiqueta} no es válida.")

    if (
        "fecha_apertura" in fechas
        and "fecha_cierre" in fechas
        and fechas["fecha_apertura"] > fechas["fecha_cierre"]
    ):
        errores.append(
            "La fecha de apertura debe ser menor o igual a la fecha de cierre."
        )

    if not valores["titulo"]:
        errores.append("El título es obligatorio.")
    elif len(valores["titulo"]) > 300:
        errores.append("El título no puede superar los 300 caracteres.")

    if not valores["descripcion"]:
        errores.append("La descripción es obligatoria.")

    estados_validos = {"Abierto", "En Progreso", "Cerrado"}
    if valores["estado"] not in estados_validos:
        errores.append("Selecciona un estado válido.")

    total_hh = None
    if not valores["total_hh"]:
        errores.append("Total HH es obligatorio.")
    else:
        try:
            total_hh = Decimal(valores["total_hh"])
            if not total_hh.is_finite() or total_hh < 0:
                errores.append("Total HH debe ser un número mayor o igual a cero.")
            elif total_hh > Decimal("99999999.99"):
                errores.append("Total HH supera el valor máximo permitido.")
            elif total_hh % Decimal("0.5") != 0:
                errores.append("Total HH debe avanzar en incrementos de 0.5.")
        except InvalidOperation:
            errores.append("Total HH debe ser un número válido.")

    if errores:
        return render_template(
            "tickets/nuevo_ticket.html",
            fecha=datetime.now(),
            valores=valores,
            errores=errores
        ), 400

    ticket = Ticket()

    ticket.FechaApertura = fechas["fecha_apertura"]
    ticket.FechaCierre = fechas["fecha_cierre"]
    ticket.Titulo = valores["titulo"]
    ticket.Descripcion = valores["descripcion"]
    ticket.TotalHH = total_hh
    ticket.Estado = valores["estado"]

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