
import json
from pathlib import Path
from getpass import getpass
from werkzeug.security import generate_password_hash

ARCHIVO = Path(__file__).resolve().parent / "usuarios.json"


def crear_usuario():

    usuario = input("Nombre de usuario: ").strip()

    if not usuario:
        print("Debe ingresar un usuario.")
        return

    password = getpass("Contraseña: ")
    confirmar = getpass("Confirmar contraseña: ")

    if len(password) < 12:
        print("La contraseña debe tener al menos 12 caracteres.")
        return

    if password != confirmar:
        print("Las contraseñas no coinciden.")
        return

    usuarios = []

    if ARCHIVO.exists():
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            usuarios = json.load(f)

    if any(
        u["usuario"].lower() == usuario.lower()
        for u in usuarios
    ):
        print("El usuario ya existe.")
        return

    usuarios.append({
        "usuario": usuario,
        "password_hash": generate_password_hash(
            password,
            method="pbkdf2:sha256:600000"
        )
    })

    temporal = ARCHIVO.with_suffix(".tmp")

    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

    temporal.replace(ARCHIVO)

    print(f"Usuario {usuario} creado correctamente.")


if __name__ == "__main__":
    crear_usuario()
