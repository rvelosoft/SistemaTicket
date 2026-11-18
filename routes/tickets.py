import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    send_file
)

from flask_login import (
    login_required,
    current_user
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager
from openpyxl import Workbook
from openpyxl.styles import Font

from models.ticket import Ticket
from models import db
from models.company import Empresa
from models.tipo_ticket import TipoTicket
from models.user import User

ticket_bp = Blueprint(
    "tickets",
    __name__
)

ESTADOS_EDITABLES = {"Abierto", "En Progreso"}
ESTADOS_VALIDOS = ("Abierto", "En Progreso", "Cerrado")
TICKETS_POR_PAGINA = 20
CAMPOS_TICKET = (
    "fecha_apertura",
    "fecha_cierre",
    "titulo",
    "descripcion",
    "total_hh",
    "tipo_ticket",
    "estado"
)


def _obtener_ticket_editable(ticket_id):
    if current_user.EsAdministrador:
        abort(403)

    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)
    if (
        ticket.UsuarioCreacion != current_user.IdUsuario
        or ticket.Estado not in ESTADOS_EDITABLES
    ):
        abort(403)

    return ticket


def _parsear_fecha_ticket(valor):
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(valor, formato)
        except ValueError:
            continue
    return None


def _parsear_total_hh_ticket(valor):
    normalizado = valor.replace(" ", "")
    if "," in normalizado and "." in normalizado:
        if normalizado.rfind(",") > normalizado.rfind("."):
            normalizado = normalizado.replace(".", "").replace(",", ".")
        else:
            normalizado = normalizado.replace(",", "")
    else:
        normalizado = normalizado.replace(",", ".")
    return Decimal(normalizado)


def _obtener_tipos_ticket():
    return TipoTicket.query.order_by(TipoTicket.NombreTipo).all()


def _mapear_tipos_ticket(tipos_ticket):
    return {
        tipo.NombreTipo.casefold(): tipo
        for tipo in tipos_ticket
    }


def _validar_valores_ticket(valores, tipos_por_nombre):
    errores = []
    fechas = {}

    for campo, etiqueta in (
        ("fecha_apertura", "Fecha de apertura"),
        ("fecha_cierre", "Fecha de cierre")
    ):
        if not valores[campo]:
            if campo == "fecha_cierre" and valores["estado"] != "Cerrado":
                continue
            errores.append(f"{etiqueta} es obligatoria.")
            continue

        fecha = _parsear_fecha_ticket(valores[campo])
        if fecha is None:
            errores.append(f"{etiqueta} no es válida.")
        else:
            fechas[campo] = fecha

    if (
        "fecha_apertura" in fechas
        and "fecha_cierre" in fechas
        and fechas["fecha_apertura"] > fechas["fecha_cierre"]
    ):
        errores.append(
            "La fecha de apertura debe ser menor o igual a la fecha de cierre."
        )
   

    if (
        "fecha_apertura" in fechas
        and fechas["fecha_apertura"].date() > datetime.now().date()
    ):
        errores.append(
            "La fecha de apertura no puede ser posterior a la fecha actual."
        )


    if (
        "fecha_cierre" in fechas
        and fechas["fecha_cierre"].date() > datetime.now().date()
    ):
        errores.append(
            "La fecha de cierre no puede ser posterior a la fecha actual."
        )



    if not valores["titulo"]:
        errores.append("El título es obligatorio.")
    elif len(valores["titulo"]) > 300:
        errores.append("El título no puede superar los 300 caracteres.")

    if not valores["descripcion"]:
        errores.append("La descripción es obligatoria.")

    if valores["estado"] not in ESTADOS_VALIDOS:
        errores.append("Selecciona un estado válido.")

    tipo_ticket = tipos_por_nombre.get(valores["tipo_ticket"].casefold())
    if tipo_ticket is None:
        errores.append("Selecciona un tipo válido.")

    total_hh = None
    if not valores["total_hh"]:
        errores.append("Total HH es obligatorio.")
    else:
        try:
            total_hh = _parsear_total_hh_ticket(valores["total_hh"])
            if not total_hh.is_finite() or total_hh < 0:
                errores.append("Total HH debe ser un número mayor o igual a cero.")
            elif total_hh > Decimal("99999999.99"):
                errores.append("Total HH supera el valor máximo permitido.")
            elif total_hh % Decimal("0.5") != 0:
                errores.append("Total HH debe avanzar en incrementos de 0.5.")
        except InvalidOperation:
            errores.append("Total HH debe ser un número válido.")

    return errores, fechas, total_hh, tipo_ticket


@ticket_bp.route(
    "/ticket/nuevo"
)
@login_required
def nuevo_ticket():

    hoy = datetime.now()

    return render_template(
        "tickets/nuevo_ticket.html",
        fecha=hoy,
        fecha_actual=hoy.strftime("%Y-%m-%d"),
        valores={},
        errores=[],
        modo_edicion=False,
        tipos_ticket=_obtener_tipos_ticket()
    )


@ticket_bp.route("/tickets/carga-masiva")
@login_required
def carga_masiva():
    if current_user.EsAdministrador:
        abort(403)
    return render_template(
        "tickets/carga_masiva.html",
        tipos_ticket=_obtener_tipos_ticket()
    )


@ticket_bp.route("/tickets/guardar-masivo", methods=["POST"])
@login_required
def guardar_tickets_masivos():
    if current_user.EsAdministrador:
        abort(403)

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or not isinstance(datos.get("tickets"), list):
        return jsonify({
            "success": False,
            "mensaje": "La solicitud no contiene una lista de tickets válida.",
            "tickets_guardados": 0,
            "errores": []
        }), 400

    errores = []
    tickets_validos = []
    tipos_por_nombre = _mapear_tipos_ticket(_obtener_tipos_ticket())
    for numero_fila, fila in enumerate(datos["tickets"], start=1):
        if not isinstance(fila, dict):
            errores.append(f"Fila {numero_fila}: datos de fila inválidos.")
            continue

        valores = {}
        for campo in CAMPOS_TICKET:
            valor = fila.get(campo)
            valores[campo] = "" if valor is None else str(valor).strip()
        if not any(valores.values()):
            continue

        estado_normalizado = valores["estado"].casefold()
        valores["estado"] = next(
            (
                estado
                for estado in ESTADOS_VALIDOS
                if estado.casefold() == estado_normalizado
            ),
            valores["estado"]
        )
        errores_fila, fechas, total_hh, tipo_ticket = _validar_valores_ticket(
            valores,
            tipos_por_nombre
        )
        if errores_fila:
            errores.append(
                f"Fila {numero_fila}: {'; '.join(errores_fila)}"
            )
            continue

        tickets_validos.append(Ticket(
            FechaApertura=fechas["fecha_apertura"],
            FechaCierre=fechas.get("fecha_cierre"),
            Titulo=valores["titulo"],
            Descripcion=valores["descripcion"],
            TotalHH=total_hh,
            Estado=valores["estado"],
            tipo_ticket=tipo_ticket,
            UsuarioCreacion=current_user.IdUsuario
        ))

    if not tickets_validos and not errores:
        errores.append("Ingresa al menos un ticket antes de guardar.")

    if errores:
        return jsonify({
            "success": False,
            "mensaje": (
                "No se guardó ningún ticket. "
                f"Se encontraron {len(errores)} problema(s)."
            ),
            "tickets_guardados": 0,
            "errores": errores
        }), 400

    try:
        db.session.add_all(tickets_validos)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("No se pudo guardar el lote de tickets.")
        return jsonify({
            "success": False,
            "mensaje": "Ocurrió un error al guardar. No se guardó ningún ticket.",
            "tickets_guardados": 0,
            "errores": []
        }), 500

    cantidad = len(tickets_validos)
    sustantivo = "ticket" if cantidad == 1 else "tickets"
    return jsonify({
        "success": True,
        "mensaje": f"Se guardaron {cantidad} {sustantivo} correctamente.",
        "tickets_guardados": cantidad,
        "errores": []
    })


@ticket_bp.route(
    "/ticket/<int:ticket_id>/editar"
)
@login_required
def editar_ticket(ticket_id):
    ticket = _obtener_ticket_editable(ticket_id)
    valores = {
        "fecha_apertura": ticket.FechaApertura.strftime("%Y-%m-%d"),
        "fecha_cierre": (
            ticket.FechaCierre.strftime("%Y-%m-%d")
            if ticket.FechaCierre
            else ""
        ),
        "titulo": ticket.Titulo,
        "descripcion": ticket.Descripcion,
        "total_hh": str(ticket.TotalHH),
        "estado": ticket.Estado,
        "tipo_ticket": (
            ticket.tipo_ticket.NombreTipo
            if ticket.tipo_ticket
            else ""
        )
    }

    return render_template(
        "tickets/nuevo_ticket.html",
        fecha=ticket.FechaApertura,
        fecha_actual=datetime.now().strftime("%Y-%m-%d"),
        valores=valores,
        errores=[],
        modo_edicion=True,
        ticket=ticket,
        tipos_ticket=_obtener_tipos_ticket()
    )


@ticket_bp.route(
    "/tickets"
)
@login_required
def listar_tickets():
    (
        consulta,
        errores,
        valores_filtro,
        empresas,
        usuarios
    ) = _consulta_tickets_filtrada()
    paginacion = None

    if not errores:
        pagina = request.args.get("page", 1, type=int) or 1
        pagina = max(pagina, 1)
        paginacion = consulta.order_by(
            Ticket.IdTicket.desc()
        ).paginate(
            page=pagina,
            per_page=TICKETS_POR_PAGINA,
            error_out=False
        )
        if pagina > (paginacion.pages or 1):
            paginacion = consulta.order_by(
                Ticket.IdTicket.desc()
            ).paginate(
                page=paginacion.pages or 1,
                per_page=TICKETS_POR_PAGINA,
                error_out=False
            )

    filtros_enlace = {
        campo: valor
        for campo, valor in valores_filtro.items()
        if valor
    }
    exportar_csv_url = url_for(
        "tickets.exportar_tickets",
        formato="csv",
        **filtros_enlace
    )
    exportar_excel_url = url_for(
        "tickets.exportar_tickets",
        formato="xlsx",
        **filtros_enlace
    )

    return render_template(
        "tickets/listar_tickets.html",
        tickets=paginacion.items if paginacion else [],
        paginacion=paginacion,
        errores=errores,
        valores_filtro=valores_filtro,
        filtros_enlace=filtros_enlace,
        exportar_csv_url=exportar_csv_url,
        exportar_excel_url=exportar_excel_url,
        empresas=empresas,
        usuarios=usuarios,
        estados=ESTADOS_VALIDOS,
        tipos_ticket=_obtener_tipos_ticket()
    ), 400 if errores else 200


def _consulta_tickets_filtrada():
    fecha_desde_predeterminada = ""
    if (
        "fecha_desde" not in request.args
        and "fecha_hasta" not in request.args
    ):
        fecha_desde_predeterminada = (
            datetime.now() - timedelta(days=30)
        ).date().isoformat()

    valores_filtro = {
        "fecha_desde": request.args.get(
            "fecha_desde",
            fecha_desde_predeterminada
        ).strip(),
        "fecha_hasta": request.args.get("fecha_hasta", "").strip(),
        "estado": request.args.get("estado", "").strip(),
        "tipo_ticket_id": request.args.get("tipo_ticket_id", "").strip()
    }
    errores = []
    fecha_desde = None
    fecha_hasta = None
    fechas_filtro = {}

    for campo, etiqueta in (
        ("fecha_desde", "Fecha desde"),
        ("fecha_hasta", "Fecha hasta")
    ):
        if not valores_filtro[campo]:
            continue
        try:
            fechas_filtro[campo] = datetime.strptime(
                valores_filtro[campo],
                "%Y-%m-%d"
            ).date()
        except ValueError:
            errores.append(f"{etiqueta} no es válida.")

    fecha_desde = fechas_filtro.get("fecha_desde")
    fecha_hasta = fechas_filtro.get("fecha_hasta")
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        errores.append("La fecha desde debe ser menor o igual a la fecha hasta.")

    if valores_filtro["estado"] and valores_filtro["estado"] not in ESTADOS_VALIDOS:
        errores.append("Selecciona un estado válido.")

    tipo_ticket_id = None
    if valores_filtro["tipo_ticket_id"]:
        try:
            tipo_ticket_id = int(valores_filtro["tipo_ticket_id"])
        except ValueError:
            errores.append("Selecciona un tipo válido.")
        else:
            if db.session.get(TipoTicket, tipo_ticket_id) is None:
                errores.append("El tipo seleccionado no existe.")
                tipo_ticket_id = None

    valores_filtro["empresa_id"] = ""
    valores_filtro["usuario_id"] = ""
    empresas = []
    usuarios = []
    if current_user.EsAdministrador:
        valores_filtro["empresa_id"] = request.args.get("empresa_id", "").strip()
        valores_filtro["usuario_id"] = request.args.get("usuario_id", "").strip()
        empresas = Empresa.query.order_by(Empresa.NombreEmpresa).all()
        usuarios = User.query.order_by(User.Usuario).all()

    empresa_id = None
    usuario_id = None
    for campo, modelo, etiqueta in (
        ("empresa_id", Empresa, "empresa"),
        ("usuario_id", User, "usuario")
    ):
        valor = valores_filtro[campo]
        if not valor:
            continue
        try:
            identificador = int(valor)
        except ValueError:
            if etiqueta == "empresa":
                errores.append("Selecciona una empresa válida.")
            else:
                errores.append("Selecciona un usuario válido.")
            continue
        if db.session.get(modelo, identificador) is None:
            if etiqueta == "empresa":
                errores.append("La empresa seleccionada no existe.")
            else:
                errores.append("El usuario seleccionado no existe.")
            continue
        if campo == "empresa_id":
            empresa_id = identificador
        else:
            usuario_id = identificador

    consulta = Ticket.query
    if not current_user.EsAdministrador:
        consulta = consulta.filter(
            Ticket.UsuarioCreacion == current_user.IdUsuario
        )
    else:
        consulta = consulta.outerjoin(
            Ticket.usuario_creacion
        ).outerjoin(
            User.empresa
        ).options(
            contains_eager(
                Ticket.usuario_creacion
            ).contains_eager(User.empresa)
        )

    if fecha_desde:
        consulta = consulta.filter(
            Ticket.FechaApertura >= datetime.combine(
                fecha_desde,
                datetime.min.time()
            )
        )
    if fecha_hasta:
        consulta = consulta.filter(
            Ticket.FechaApertura < datetime.combine(
                fecha_hasta + timedelta(days=1),
                datetime.min.time()
            )
        )
    if valores_filtro["estado"]:
        consulta = consulta.filter(Ticket.Estado == valores_filtro["estado"])
    if tipo_ticket_id is not None:
        consulta = consulta.filter(Ticket.IdTipoTicket == tipo_ticket_id)
    if empresa_id is not None and current_user.EsAdministrador:
        consulta = consulta.filter(User.IdEmpresa == empresa_id)
    if usuario_id is not None and current_user.EsAdministrador:
        consulta = consulta.filter(Ticket.UsuarioCreacion == usuario_id)

    return consulta, errores, valores_filtro, empresas, usuarios


def _valor_exportacion_segura(valor):
    if isinstance(valor, str) and valor.lstrip(" \t\r\n").startswith(
        ("=", "+", "-", "@")
    ):
        return "'" + valor
    return valor


def _fila_exportacion(ticket):
    usuario = ticket.usuario_creacion
    empresa = usuario.empresa if usuario else None
    grupo = usuario.grupo if usuario else None
    return [
        ticket.IdTicket,
        usuario.Usuario if usuario else "Sin usuario",
        empresa.NombreEmpresa if empresa else "Sin empresa",
        grupo.NombreGrupo if grupo else "Sin grupo",
        ticket.Titulo or "",
        ticket.Descripcion or "",
        ticket.tipo_ticket.NombreTipo if ticket.tipo_ticket else "",
        ticket.FechaApertura.strftime("%d/%m/%Y") if ticket.FechaApertura else "",
        ticket.FechaCierre.strftime("%d/%m/%Y") if ticket.FechaCierre else "",
        ticket.Estado or "",
        float(ticket.TotalHH) if ticket.TotalHH is not None else None
    ]


@ticket_bp.route("/tickets/exportar/<formato>")
@login_required
def exportar_tickets(formato):
    if not current_user.EsAdministrador:
        abort(403)
    if formato not in {"csv", "xlsx"}:
        abort(404)

    consulta, errores, _, _, _ = _consulta_tickets_filtrada()
    if errores:
        return redirect(url_for(
            "tickets.listar_tickets",
            **request.args.to_dict()
        ))

    tickets = consulta.order_by(
        Ticket.FechaApertura.desc(),
        Ticket.IdTicket.desc()
    ).all()
    encabezados = [
        "N.º",
        "Usuario",
        "Empresa",
        "Grupo",
        "Título",
        "Descripción",
        "Tipo",
        "Fecha apertura",
        "Fecha cierre",
        "Estado",
        "Total HH"
    ]
    filas = [_fila_exportacion(ticket) for ticket in tickets]

    if formato == "csv":
        salida = io.StringIO(newline="")
        escritor = csv.writer(salida)
        escritor.writerow(encabezados)
        for fila in filas:
            escritor.writerow(
                _valor_exportacion_segura(valor)
                for valor in fila
            )
        return Response(
            "\ufeff" + salida.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="tickets.csv"'
            }
        )

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Tickets"
    hoja.append(encabezados)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for fila in filas:
        hoja.append([
            _valor_exportacion_segura(valor)
            for valor in fila
        ])
        for celda in hoja[hoja.max_row]:
            if isinstance(celda.value, str):
                celda.data_type = "s"
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions

    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    return send_file(
        salida,
        as_attachment=True,
        download_name="tickets.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


@ticket_bp.route(
    "/ticket/guardar",
    methods=["POST"],
    defaults={"ticket_id": None}
)
@ticket_bp.route(
    "/ticket/guardar/<int:ticket_id>",
    methods=["POST"]
)
@login_required
def guardar_ticket(ticket_id=None):

    ticket = (
        _obtener_ticket_editable(ticket_id)
        if ticket_id is not None
        else Ticket()
    )

    valores = {
        campo: request.form.get(campo, "").strip()
        for campo in CAMPOS_TICKET
    }
    tipos_ticket = _obtener_tipos_ticket()
    errores, fechas, total_hh, tipo_ticket = _validar_valores_ticket(
        valores,
        _mapear_tipos_ticket(tipos_ticket)
    )

    if errores:
        return render_template(
            "tickets/nuevo_ticket.html",
            fecha=datetime.now(),
            fecha_actual=datetime.now().strftime("%Y-%m-%d"),
            valores=valores,
            errores=errores,
            modo_edicion=ticket_id is not None,
            ticket=ticket,
            tipos_ticket=tipos_ticket
        ), 400

    ticket.FechaApertura = fechas["fecha_apertura"]
    ticket.FechaCierre = fechas.get("fecha_cierre")
    ticket.Titulo = valores["titulo"]
    ticket.Descripcion = valores["descripcion"]
    ticket.TotalHH = total_hh
    ticket.Estado = valores["estado"]
    ticket.tipo_ticket = tipo_ticket

    if ticket_id is None:
        ticket.UsuarioCreacion = current_user.IdUsuario

    db.session.add(ticket)

    db.session.commit()

    if ticket_id is None:
        flash("Ticket registrado correctamente")
        return redirect(url_for(
            "tickets.listar_tickets"
            if current_user.EsUsuario
            else "home.menu"
        ))

    flash("Ticket actualizado correctamente")
    return redirect(url_for("tickets.listar_tickets"))
