from flask import Blueprint, redirect, render_template, url_for
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
    if current_user.EsUsuario:
        return redirect(url_for("tickets.listar_tickets"))

    return render_template(
        "menu.html",
        es_administrador=current_user.EsAdministrador
    )