import bcrypt
import base64
from io import BytesIO

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session
)

from flask_login import (
    login_user,
    logout_user
)
import pyotp
import qrcode
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models.user import User

auth_bp = Blueprint(
    'auth',
    __name__
)


def _crear_qr_data_uri(user):
    uri = pyotp.TOTP(user.totp_secret).provisioning_uri(
        name=user.Correo,
        issuer_name="Sistema de Tickets"
    )
    imagen = qrcode.make(uri)
    salida = BytesIO()
    imagen.save(salida, format="PNG")
    contenido = base64.b64encode(salida.getvalue()).decode("ascii")
    return f"data:image/png;base64,{contenido}"


def _obtener_usuario_pendiente():
    user_id = session.get("pending_2fa_user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if user is None or user.Activo is False:
        session.pop("pending_2fa_user_id", None)
        return None
    return user


@auth_bp.route('/')
def login():

    return render_template(
        'login.html'
    )

@auth_bp.route("/login",
    methods=['POST']
)
def do_login():

    correo = request.form.get("correo", "").strip()

    password = request.form.get("password", "")

    user = User.query.filter_by(
        Correo=correo
    ).first()

    if user and user.Activo is not False:

        if bcrypt.checkpw(
            password.encode(),
            user.PasswordHash.encode()
        ):

            if not user.totp_verificado:
                session["pending_2fa_user_id"] = user.IdUsuario
                return redirect(url_for("auth.verificar_2fa"))

            login_user(user)

            return redirect(
                url_for(
                    'tickets.listar_tickets'
                    if user.EsUsuario
                    else 'home.menu'
                )
            )

    flash("Credenciales inválidas")

    return redirect("/")


@auth_bp.route("/2fa", methods=["GET", "POST"])
def verificar_2fa():
    user = _obtener_usuario_pendiente()
    if user is None:
        flash("Inicia sesión con tu correo y contraseña.", "error")
        return redirect(url_for("auth.login"))

    if not user.totp_secret:
        user.totp_secret = pyotp.random_base32()
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception(
                "No se pudo generar el secreto 2FA para el usuario %s.",
                user.IdUsuario
            )
            flash("No se pudo preparar la verificación 2FA.", "error")
            return redirect(url_for("auth.login"))

    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        if len(codigo) == 6 and codigo.isdigit() and pyotp.TOTP(
            user.totp_secret
        ).verify(codigo):
            user.totp_verificado = True
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception(
                    "No se pudo completar el 2FA para el usuario %s.",
                    user.IdUsuario
                )
                flash("No se pudo completar la verificación 2FA.", "error")
            else:
                session.pop("pending_2fa_user_id", None)
                login_user(user)
                return redirect(
                    url_for(
                        "tickets.listar_tickets"
                        if user.EsUsuario
                        else "home.menu"
                    )
                )
        else:
            flash("El código 2FA no es válido. Inténtalo nuevamente.", "error")

    return render_template(
        "auth/verificar_2fa.html",
        usuario=user,
        qr_data_uri=_crear_qr_data_uri(user)
    )

@auth_bp.route("/logout")
def logout():

    logout_user()
    session.pop("pending_2fa_user_id", None)

    return redirect("/")