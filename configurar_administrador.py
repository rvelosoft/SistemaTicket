from getpass import getpass

import bcrypt

from app import app
from models import db
from models.role import Perfil
from models.user import User


def configurar_administrador():
    usuario = input("Usuario existente que será administrador: ").strip()
    with app.app_context():
        cuenta = User.query.filter_by(Usuario=usuario).first()
        if cuenta is None:
            print("No existe una cuenta con ese nombre de usuario.")
            return

        password = getpass("Contraseña del usuario para confirmar: ")
        if not password:
            print("La contraseña no puede estar vacía.")
            return
        if not cuenta.PasswordHash or not bcrypt.checkpw(
            password.encode("utf-8"),
            cuenta.PasswordHash.encode("utf-8")
        ):
            print("La contraseña no es correcta.")
            return

        perfil = Perfil.query.filter_by(EsAdministrador=True).first()
        if perfil is None:
            perfil = Perfil(
                NombrePerfil="Administrador",
                EsAdministrador=True
            )
            db.session.add(perfil)
            db.session.flush()

        cuenta.IdPerfil = perfil.IdPerfil
        db.session.commit()

    print(f"Se asignó el perfil administrador a {usuario}.")


if __name__ == "__main__":
    configurar_administrador()
