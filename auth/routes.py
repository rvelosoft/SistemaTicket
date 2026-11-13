import bcrypt

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for
)

from flask_login import (
    login_user,
    logout_user
)

from models.user import User

auth_bp = Blueprint(
    'auth',
    __name__
)

@auth_bp.route('/')
def login():

    return render_template(
        'login.html'
    )

@auth_bp.route("/login",
    methods=['POST']
)
def do_login():

    usuario = request.form["usuario"]

    password = request.form["password"]

    user = User.query.filter_by(
        Usuario=usuario
    ).first()

    if user and user.Activo is not False:

        if bcrypt.checkpw(
            password.encode(),
            user.PasswordHash.encode()
        ):

            login_user(user)

            return redirect(
                url_for(
                    'home.menu'
                )
            )

    flash("Credenciales inválidas")

    return redirect("/")
    

@auth_bp.route("/logout")
def logout():

    logout_user()

    return redirect("/")