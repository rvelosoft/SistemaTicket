from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import extract, func

from models import db
from models.company import Empresa
from models.ticket import Ticket
from models.tipo_ticket import TipoTicket
from models.user import User


estadisticas_bp = Blueprint("estadisticas", __name__)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.EsAdministrador:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def _years_with_tickets():
    years = db.session.query(
        extract("year", Ticket.FechaApertura).label("anio")
    ).filter(
        Ticket.FechaApertura.isnot(None)
    ).distinct().order_by("anio").all()
    return [int(row.anio) for row in years]


@estadisticas_bp.get("/estadisticas")
@login_required
@admin_required
def pagina_estadisticas():
    return render_template(
        "estadisticas.html",
        empresas=Empresa.query.order_by(Empresa.NombreEmpresa).all(),
        anios=_years_with_tickets()
    )


@estadisticas_bp.get("/estadisticas/api/usuarios")
@login_required
@admin_required
def usuarios_por_empresa():
    try:
        empresa_id = int(request.args.get("empresa_id", ""))
    except (TypeError, ValueError):
        return jsonify(error="Selecciona una empresa válida."), 400

    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        return jsonify(error="La empresa seleccionada no existe."), 404

    usuarios = User.query.filter_by(
        IdEmpresa=empresa_id
    ).order_by(User.NombreCompleto, User.Usuario).all()

    return jsonify([
        {
            "id": usuario.IdUsuario,
            "nombre": usuario.NombreCompleto or usuario.Usuario or str(usuario.IdUsuario)
        }
        for usuario in usuarios
    ])


@estadisticas_bp.get("/estadisticas/api")
@login_required
@admin_required
def datos_estadisticas():
    try:
        empresa_id = int(request.args.get("empresa_id", ""))
        anio = int(request.args.get("anio", ""))
    except (TypeError, ValueError):
        return jsonify(error="Selecciona una empresa y un año válidos."), 400

    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        return jsonify(error="La empresa seleccionada no existe."), 404
    if anio not in _years_with_tickets():
        return jsonify(error="El año seleccionado no tiene tickets registrados."), 400

    usuario_id = request.args.get("usuario_id", "")
    if usuario_id:
        try:
            usuario_id = int(usuario_id)
        except ValueError:
            return jsonify(error="Selecciona un usuario válido."), 400

        usuario = User.query.filter_by(
            IdUsuario=usuario_id,
            IdEmpresa=empresa_id
        ).first()
        if usuario is None:
            return jsonify(error="El usuario no pertenece a la empresa seleccionada."), 400

    periodos = []
    for mes in range(1, 13):
        inicio = datetime(anio, mes, 10)
        siguiente_mes = 1 if mes == 12 else mes + 1
        siguiente_anio = anio + 1 if mes == 12 else anio
        fin = datetime(siguiente_anio, siguiente_mes, 10)

        consulta = db.session.query(
            TipoTicket.NombreTipo,
            func.count(Ticket.IdTicket)
        ).join(
            Ticket, Ticket.IdTipoTicket == TipoTicket.IdTipoTicket
        ).join(
            User, Ticket.UsuarioCreacion == User.IdUsuario
        ).filter(
            User.IdEmpresa == empresa_id,
            Ticket.FechaApertura >= inicio,
            Ticket.FechaApertura < fin
        )
        if usuario_id:
            consulta = consulta.filter(Ticket.UsuarioCreacion == usuario_id)

        totales = {"inc": 0, "req": 0, "warning": 0}
        for nombre_tipo, cantidad in consulta.group_by(TipoTicket.NombreTipo).all():
            tipo = (nombre_tipo or "").strip().casefold()
            if tipo.startswith("inc"):
                totales["inc"] += cantidad
            elif tipo.startswith("req"):
                totales["req"] += cantidad
            elif "warning" in tipo:
                totales["warning"] += cantidad

        periodos.append({
            "anio": anio,
            "mes": mes,
            **totales,
            "total": sum(totales.values())
        })

    return jsonify(periodos=periodos)
