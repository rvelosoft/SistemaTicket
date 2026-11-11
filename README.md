# SistemaTicket

Aplicación web de gestión de tickets con Flask, Flask-Login y SQLAlchemy.
Esta rama usa SQLite como base de datos.

## Ejecución local

```bash
pip install -r requirements.txt
python app.py
```

Al iniciar, la aplicación crea las tablas que falten en `instance/tickets.db`.
Para guardar la base en otra ruta, configura `SQLITE_DATABASE_PATH` antes de
iniciar la aplicación.

Crear el primer usuario de acceso:

```bash
python crear_usuario.py
```

El usuario se guarda en la misma base configurada para la aplicación.

## Despliegue en Render

- Usa `pip install -r requirements.txt` como comando de build. El `Procfile`
  inicia Gunicorn con `gunicorn app:app`.
- Configura `SECRET_KEY` con un valor aleatorio y privado.
- Para conservar los tickets entre reinicios y despliegues, agrega un disco
  persistente en Render montado en `/var/data` y configura
  `SQLITE_DATABASE_PATH=/var/data/tickets.db`.
- Ejecuta `python crear_usuario.py` en el entorno del servicio para crear el
  usuario inicial.

Sin un disco persistente, el archivo SQLite queda en el almacenamiento
efímero del servicio y se puede perder al reiniciar o desplegar. Los discos
persistentes de Render requieren un plan que los admita.
