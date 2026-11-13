from functools import wraps

import bcrypt
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from models import db
from models.company import Empresa
from models.role import Perfil
from models.user import User


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
        if perfil is None:
            errores.append("Selecciona un perfil válido.")
        if empresa is None:
            errores.append("Selecciona una empresa válida.")

        if user_id is None and len(password) < 12:
            errores.append("La contraseña debe tener al menos 12 caracteres.")
        elif password and len(password) < 12:
            errores.append("La contraseña debe tener al menos 12 caracteres.")

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
