from functools import wraps

import bcrypt
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models.company import Empresa
from models.role import Perfil
from models.ticket import Ticket
from models.tipo_ticket import TipoTicket
from models.user import User
from models.work_group import GrupoTrabajo


maintenance_bp = Blueprint(
    "maintenance",
    __name__,
    url_prefix="/mantenimientos"
)


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user.EsAdministrador:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def _is_duplicate(model, field, value, item_id=None):
    query = model.query.filter(field == value)
    if item_id is not None:
        primary_key = next(iter(model.__table__.primary_key.columns))
        query = query.filter(primary_key != item_id)
    return query.first() is not None


def _eliminar_registro(registro, nombre, endpoint):
    db.session.delete(registro)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            f"No se pudo eliminar {nombre} porque existen datos relacionados.",
            "error"
        )
    else:
        flash(f"{nombre.capitalize()} eliminado correctamente.")
    return redirect(url_for(endpoint))


@maintenance_bp.route("/")
@login_required
@admin_required
def index():
    return render_template("mantenimientos/index.html")


@maintenance_bp.route("/usuarios")
@login_required
@admin_required
def usuarios():
    users = User.query.order_by(User.Usuario).all()
    return render_template("mantenimientos/usuarios.html", usuarios=users)


@maintenance_bp.route("/usuarios/<int:user_id>/resetear-2fa", methods=["POST"])
@login_required
@admin_required
def resetear_2fa(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    user.totp_secret = None
    user.totp_verificado = False
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo resetear la verificación 2FA.", "error")
    else:
        flash("Verificación 2FA reseteada correctamente.")
    return redirect(url_for("maintenance.usuarios"))


@maintenance_bp.route("/empresas/<int:empresa_id>/grupos")
@login_required
@admin_required
def grupos_por_empresa(empresa_id):
    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        abort(404)
    return jsonify([
        {"id": grupo.IdGrupo, "nombre": grupo.NombreGrupo}
        for grupo in empresa.grupos
    ])


@maintenance_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@maintenance_bp.route("/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_usuario(user_id=None):
    user = db.session.get(User, user_id) if user_id is not None else User()
    if user is None:
        abort(404)

    perfiles = Perfil.query.order_by(Perfil.NombrePerfil).all()
    empresas = Empresa.query.order_by(Empresa.NombreEmpresa).all()
    valores = {
        "usuario": user.Usuario or "",
        "nombre": user.NombreCompleto or "",
        "correo": user.Correo or "",
        "perfil_id": str(user.IdPerfil or ""),
        "empresa_id": str(user.IdEmpresa or ""),
        "grupo_id": str(user.IdGrupo or ""),
        "activo": user.Activo is not False
    }
    errores = []

    if request.method == "POST":
        valores.update({
            "usuario": request.form.get("usuario", "").strip(),
            "nombre": request.form.get("nombre", "").strip(),
            "correo": request.form.get("correo", "").strip(),
            "perfil_id": request.form.get("perfil_id", ""),
            "empresa_id": request.form.get("empresa_id", ""),
            "grupo_id": request.form.get("grupo_id", ""),
            "activo": request.form.get("activo") == "on"
        })
        password = request.form.get("password", "")

        if not valores["usuario"]:
            errores.append("El usuario es obligatorio.")
        elif len(valores["usuario"]) > 100:
            errores.append("El usuario no puede superar los 100 caracteres.")
        elif _is_duplicate(User, User.Usuario, valores["usuario"], user_id):
            errores.append("El nombre de usuario ya está registrado.")

        if not valores["nombre"]:
            errores.append("El nombre completo es obligatorio.")
        elif len(valores["nombre"]) > 200:
            errores.append("El nombre completo no puede superar los 200 caracteres.")

        if not valores["correo"]:
            errores.append("El correo es obligatorio.")
        elif len(valores["correo"]) > 200 or "@" not in valores["correo"]:
            errores.append("Ingresa un correo válido de hasta 200 caracteres.")

        perfil = db.session.get(Perfil, valores["perfil_id"])
        empresa = db.session.get(Empresa, valores["empresa_id"])
        grupo = db.session.get(GrupoTrabajo, valores["grupo_id"])
        if perfil is None:
            errores.append("Selecciona un perfil válido.")
        if empresa is None:
            errores.append("Selecciona una empresa válida.")
        if grupo is None:
            errores.append("Selecciona un grupo válido.")
        elif empresa is not None and grupo not in empresa.grupos:
            errores.append("El grupo seleccionado no pertenece a la empresa.")

        if user_id is None and len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        elif password and len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")

        if errores:
            return render_template(
                "mantenimientos/usuario_form.html",
                usuario=user,
                valores=valores,
                perfiles=perfiles,
                empresas=empresas,
                errores=errores
            ), 400

        # Do not let an administrator remove the last administrator account.
        if (
            user_id is not None
            and user.EsAdministrador
            and (not perfil.EsAdministrador or not valores["activo"])
        ):
            administradores = User.query.join(Perfil).filter(
                Perfil.EsAdministrador.is_(True)
            ).count()
            if administradores <= 1:
                errores.append(
                    "No se puede quitar ni desactivar el último usuario administrador."
                )
                return render_template(
                    "mantenimientos/usuario_form.html",
                    usuario=user,
                    valores=valores,
                    perfiles=perfiles,
                    empresas=empresas,
                    errores=errores
                ), 400

        user.Usuario = valores["usuario"]
        user.NombreCompleto = valores["nombre"]
        user.Correo = valores["correo"]
        user.IdPerfil = perfil.IdPerfil
        user.IdEmpresa = empresa.IdEmpresa
        user.IdGrupo = grupo.IdGrupo
        user.Activo = valores["activo"]
        if password:
            user.PasswordHash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar el usuario por un dato duplicado.", "error")
            return redirect(url_for("maintenance.usuarios"))

        flash("Usuario guardado correctamente.")
        return redirect(url_for("maintenance.usuarios"))

    return render_template(
        "mantenimientos/usuario_form.html",
        usuario=user,
        valores=valores,
        perfiles=perfiles,
        empresas=empresas,
        errores=errores
    )


@maintenance_bp.route("/perfiles")
@login_required
@admin_required
def perfiles():
    return render_template(
        "mantenimientos/perfiles.html",
        perfiles=Perfil.query.order_by(Perfil.NombrePerfil).all()
    )


@maintenance_bp.route("/perfiles/nuevo", methods=["GET", "POST"])
@maintenance_bp.route("/perfiles/<int:perfil_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_perfil(perfil_id=None):
    perfil = db.session.get(Perfil, perfil_id) if perfil_id is not None else Perfil()
    if perfil is None:
        abort(404)

    errores = []
    nombre = perfil.NombrePerfil or ""
    es_administrador = bool(perfil.EsAdministrador)
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        es_administrador = request.form.get("es_administrador") == "on"
        if not nombre:
            errores.append("El nombre del perfil es obligatorio.")
        elif len(nombre) > 100:
            errores.append("El nombre del perfil no puede superar los 100 caracteres.")
        elif _is_duplicate(Perfil, Perfil.NombrePerfil, nombre, perfil_id):
            errores.append("Ya existe un perfil con ese nombre.")

        if perfil.IdPerfil and perfil.EsAdministrador and not es_administrador:
            administradores = User.query.join(Perfil).filter(
                Perfil.EsAdministrador.is_(True)
            ).count()
            asignados = User.query.filter_by(IdPerfil=perfil.IdPerfil).count()
            if administradores <= asignados:
                errores.append("No se puede quitar el último perfil administrador.")

        if errores:
            return render_template(
                "mantenimientos/perfil_form.html",
                perfil=perfil,
                nombre=nombre,
                es_administrador=es_administrador,
                errores=errores
            ), 400

        perfil.NombrePerfil = nombre
        perfil.EsAdministrador = es_administrador
        db.session.add(perfil)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar el perfil por un nombre duplicado.", "error")
            return redirect(url_for("maintenance.perfiles"))

        flash("Perfil guardado correctamente.")
        return redirect(url_for("maintenance.perfiles"))

    return render_template(
        "mantenimientos/perfil_form.html",
        perfil=perfil,
        nombre=nombre,
        es_administrador=es_administrador,
        errores=errores
    )


@maintenance_bp.route("/tipos-ticket")
@login_required
@admin_required
def tipos_ticket():
    return render_template(
        "mantenimientos/tipos_ticket.html",
        tipos_ticket=TipoTicket.query.order_by(TipoTicket.NombreTipo).all()
    )


@maintenance_bp.route("/tipos-ticket/nuevo", methods=["GET", "POST"])
@maintenance_bp.route(
    "/tipos-ticket/<int:tipo_id>/editar",
    methods=["GET", "POST"]
)
@login_required
@admin_required
def editar_tipo_ticket(tipo_id=None):
    tipo = (
        db.session.get(TipoTicket, tipo_id)
        if tipo_id is not None
        else TipoTicket()
    )
    if tipo is None:
        abort(404)

    errores = []
    nombre = tipo.NombreTipo or ""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            errores.append("El nombre del tipo es obligatorio.")
        elif len(nombre) > 100:
            errores.append("El nombre del tipo no puede superar los 100 caracteres.")
        elif any(
            otro_tipo.IdTipoTicket != tipo.IdTipoTicket
            and otro_tipo.NombreTipo.casefold() == nombre.casefold()
            for otro_tipo in TipoTicket.query.all()
        ):
            errores.append("Ya existe un tipo con ese nombre.")

        if errores:
            return render_template(
                "mantenimientos/tipo_ticket_form.html",
                tipo=tipo,
                nombre=nombre,
                errores=errores
            ), 400

        tipo.NombreTipo = nombre
        db.session.add(tipo)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar el tipo por un nombre duplicado.", "error")
            return redirect(url_for("maintenance.tipos_ticket"))

        flash("Tipo guardado correctamente.")
        return redirect(url_for("maintenance.tipos_ticket"))

    return render_template(
        "mantenimientos/tipo_ticket_form.html",
        tipo=tipo,
        nombre=nombre,
        errores=errores
    )


@maintenance_bp.route("/empresas")
@login_required
@admin_required
def empresas():
    return render_template(
        "mantenimientos/empresas.html",
        empresas=Empresa.query.order_by(Empresa.NombreEmpresa).all()
    )


@maintenance_bp.route("/empresas/nueva", methods=["GET", "POST"])
@maintenance_bp.route("/empresas/<int:empresa_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_empresa(empresa_id=None):
    empresa = db.session.get(Empresa, empresa_id) if empresa_id is not None else Empresa()
    if empresa is None:
        abort(404)

    errores = []
    nombre = empresa.NombreEmpresa or ""
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            errores.append("El nombre de la empresa es obligatorio.")
        elif len(nombre) > 200:
            errores.append("El nombre de la empresa no puede superar los 200 caracteres.")
        elif _is_duplicate(Empresa, Empresa.NombreEmpresa, nombre, empresa_id):
            errores.append("Ya existe una empresa con ese nombre.")

        if errores:
            return render_template(
                "mantenimientos/empresa_form.html",
                empresa=empresa,
                nombre=nombre,
                errores=errores
            ), 400

        empresa.NombreEmpresa = nombre
        db.session.add(empresa)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar la empresa por un nombre duplicado.", "error")
            return redirect(url_for("maintenance.empresas"))

        flash("Empresa guardada correctamente.")
        return redirect(url_for("maintenance.empresas"))

    return render_template(
        "mantenimientos/empresa_form.html",
        empresa=empresa,
        nombre=nombre,
        errores=errores
    )


@maintenance_bp.route("/grupos")
@login_required
@admin_required
def grupos():
    return render_template(
        "mantenimientos/grupos.html",
        grupos=GrupoTrabajo.query.order_by(GrupoTrabajo.NombreGrupo).all()
    )


@maintenance_bp.route("/grupos/nuevo", methods=["GET", "POST"])
@maintenance_bp.route("/grupos/<int:grupo_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar_grupo(grupo_id=None):
    grupo = (
        db.session.get(GrupoTrabajo, grupo_id)
        if grupo_id is not None
        else GrupoTrabajo()
    )
    if grupo is None:
        abort(404)

    empresas = Empresa.query.order_by(Empresa.NombreEmpresa).all()
    nombre = grupo.NombreGrupo or ""
    empresa_ids = [str(empresa.IdEmpresa) for empresa in grupo.empresas]
    errores = []

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        empresa_ids = list(dict.fromkeys(request.form.getlist("empresa_ids")))
        empresas_seleccionadas = [
            empresa for empresa in empresas
            if str(empresa.IdEmpresa) in empresa_ids
        ]

        if not nombre:
            errores.append("El nombre del grupo es obligatorio.")
        elif len(nombre) > 150:
            errores.append("El nombre del grupo no puede superar los 150 caracteres.")
        elif any(
            otro_grupo.IdGrupo != grupo.IdGrupo
            and otro_grupo.NombreGrupo.casefold() == nombre.casefold()
            for otro_grupo in GrupoTrabajo.query.all()
        ):
            errores.append("Ya existe un grupo con ese nombre.")

        if not empresas_seleccionadas:
            errores.append("Asigna el grupo al menos a una empresa.")
        if len(empresas_seleccionadas) != len(empresa_ids):
            errores.append("Selecciona empresas válidas.")
        if grupo.IdGrupo:
            empresas_seleccionadas_ids = {
                empresa.IdEmpresa for empresa in empresas_seleccionadas
            }
            for empresa_actual in grupo.empresas:
                if (
                    empresa_actual.IdEmpresa not in empresas_seleccionadas_ids
                    and User.query.filter_by(
                        IdEmpresa=empresa_actual.IdEmpresa,
                        IdGrupo=grupo.IdGrupo
                    ).first()
                ):
                    errores.append(
                        "No puedes quitar una empresa con usuarios asignados a este grupo."
                    )
                    break

        if errores:
            return render_template(
                "mantenimientos/grupo_form.html",
                grupo=grupo,
                nombre=nombre,
                empresas=empresas,
                empresa_ids=empresa_ids,
                errores=errores
            ), 400

        grupo.NombreGrupo = nombre
        grupo.empresas = empresas_seleccionadas
        db.session.add(grupo)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("No fue posible guardar el grupo por un nombre duplicado.", "error")
            return redirect(url_for("maintenance.grupos"))

        flash("Grupo guardado correctamente.")
        return redirect(url_for("maintenance.grupos"))

    return render_template(
        "mantenimientos/grupo_form.html",
        grupo=grupo,
        nombre=nombre,
        empresas=empresas,
        empresa_ids=empresa_ids,
        errores=errores
    )


@maintenance_bp.route("/usuarios/<int:user_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_usuario(user_id):
    usuario = db.session.get(User, user_id)
    if usuario is None:
        abort(404)
    if usuario.IdUsuario == current_user.IdUsuario:
        flash("No puedes eliminar la cuenta con la que iniciaste sesión.", "error")
        return redirect(url_for("maintenance.usuarios"))
    if Ticket.query.filter_by(UsuarioCreacion=usuario.IdUsuario).first():
        flash(
            "No se puede eliminar el usuario porque tiene tickets asociados.",
            "error"
        )
        return redirect(url_for("maintenance.usuarios"))
    if usuario.EsAdministrador and not User.query.join(Perfil).filter(
        Perfil.EsAdministrador.is_(True),
        User.IdUsuario != usuario.IdUsuario
    ).first():
        flash(
            "No se puede eliminar el último usuario administrador.",
            "error"
        )
        return redirect(url_for("maintenance.usuarios"))
    return _eliminar_registro(
        usuario,
        "el usuario",
        "maintenance.usuarios"
    )


@maintenance_bp.route("/perfiles/<int:perfil_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_perfil(perfil_id):
    perfil = db.session.get(Perfil, perfil_id)
    if perfil is None:
        abort(404)
    if User.query.filter_by(IdPerfil=perfil.IdPerfil).first():
        flash(
            "No se puede eliminar el perfil porque está asignado a usuarios.",
            "error"
        )
        return redirect(url_for("maintenance.perfiles"))
    if perfil.EsAdministrador and not Perfil.query.filter(
        Perfil.EsAdministrador.is_(True),
        Perfil.IdPerfil != perfil.IdPerfil
    ).first():
        flash(
            "No se puede eliminar el último perfil administrador.",
            "error"
        )
        return redirect(url_for("maintenance.perfiles"))
    return _eliminar_registro(
        perfil,
        "el perfil",
        "maintenance.perfiles"
    )


@maintenance_bp.route(
    "/tipos-ticket/<int:tipo_id>/eliminar",
    methods=["POST"]
)
@login_required
@admin_required
def eliminar_tipo_ticket(tipo_id):
    tipo = db.session.get(TipoTicket, tipo_id)
    if tipo is None:
        abort(404)
    if Ticket.query.filter_by(IdTipoTicket=tipo.IdTipoTicket).first():
        flash(
            "No se puede eliminar el tipo porque está asociado a tickets.",
            "error"
        )
        return redirect(url_for("maintenance.tipos_ticket"))
    return _eliminar_registro(
        tipo,
        "el tipo de ticket",
        "maintenance.tipos_ticket"
    )


@maintenance_bp.route("/empresas/<int:empresa_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_empresa(empresa_id):
    empresa = db.session.get(Empresa, empresa_id)
    if empresa is None:
        abort(404)
    if User.query.filter_by(IdEmpresa=empresa.IdEmpresa).first():
        flash(
            "No se puede eliminar la empresa porque tiene usuarios asignados.",
            "error"
        )
        return redirect(url_for("maintenance.empresas"))
    return _eliminar_registro(
        empresa,
        "la empresa",
        "maintenance.empresas"
    )


@maintenance_bp.route("/grupos/<int:grupo_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def eliminar_grupo(grupo_id):
    grupo = db.session.get(GrupoTrabajo, grupo_id)
    if grupo is None:
        abort(404)
    if User.query.filter_by(IdGrupo=grupo.IdGrupo).first():
        flash(
            "No se puede eliminar el grupo porque tiene usuarios asignados.",
            "error"
        )
        return redirect(url_for("maintenance.grupos"))
    return _eliminar_registro(
        grupo,
        "el grupo",
        "maintenance.grupos"
    )
