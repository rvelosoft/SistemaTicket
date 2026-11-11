from getpass import getpass

import bcrypt

from app import app
from models import db
from models.user import User


def crear_usuario():
    usuario = input("Nombre de usuario: ").strip()
    nombre = input("Nombre completo: ").strip()
    correo = input("Correo: ").strip()

    if not usuario or not nombre or not correo:
        print("Usuario, nombre completo y correo son obligatorios.")
        return

    password = getpass("Contraseña (mínimo 12 caracteres): ")
    confirmar = getpass("Confirmar contraseña: ")

    if len(password) < 12:
        print("La contraseña debe tener al menos 12 caracteres.")
        return

    if password != confirmar:
        print("Las contraseñas no coinciden.")
        return

    with app.app_context():
        if User.query.filter_by(Usuario=usuario).first():
            print("El usuario ya existe.")
            return

        user = User(
            Usuario=usuario,
            NombreCompleto=nombre,
            Correo=correo,
            PasswordHash=bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8"),
            Activo=True
        )
        db.session.add(user)
        db.session.commit()

    print(f"Usuario {usuario} creado correctamente.")


if __name__ == "__main__":
    crear_usuario()
