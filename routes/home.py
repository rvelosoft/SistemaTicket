from flask import Blueprint
from flask import render_template
from flask_login import (
    login_required,
    current_user
)

home_bp = Blueprint(
    "home",
    __name__
)

@home_bp.route("/menu")
@login_required
def menu():

    return render_template(
        "menu.html",
        es_administrador=current_user.EsAdministrador
    )