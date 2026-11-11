import bcrypt

password = "Admin123*"

hash_generado = bcrypt.hashpw(
    password.encode(),
    bcrypt.gensalt()
)

print(hash_generado.decode())