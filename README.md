# SistemaTicket

Aplicación web de gestión de tickets con Flask, Flask-Login y SQLAlchemy.
Esta rama usa SQLite como base de datos.

## Ejecución local

```bash
pip install -r requirements.txt
python app.py
```

Al iniciar, la aplicación crea las tablas que falten en `instance/tickets.db`.
También agrega las columnas de perfil y empresa a bases existentes sin eliminar
los usuarios ni tickets. Para guardar la base en otra ruta, configura
`SQLITE_DATABASE_PATH` antes de iniciar la aplicación.

Crear el primer usuario de acceso:

```bash
python crear_usuario.py
```

El usuario se guarda en la misma base configurada para la aplicación.
La aplicación crea los perfiles iniciales `Administrador` y `Usuario`. En una
instalación nueva, `crear_usuario.py` asigna el perfil administrador a la
primera cuenta. Si ya existe una cuenta, asigna explícitamente el administrador
una sola vez con:

```bash
python configurar_administrador.py
```

El mantenedor de tablas y parámetros solo está disponible para usuarios con un
perfil marcado como administrador. Desde allí se mantienen usuarios, perfiles
y empresas; cada usuario debe tener un perfil y una empresa asignados para
guardarse desde el mantenedor.

En la consulta de tickets, los administradores pueden filtrar por fecha de
apertura, empresa, usuario y estado. Los usuarios consultan solo sus propios
tickets y pueden filtrar por fecha de apertura y estado. El listado tiene
paginación y los administradores pueden exportar todos los resultados filtrados
a Excel o CSV.

Los usuarios no administradores también pueden ingresar varios tickets desde
la grilla de carga masiva, pegando columnas copiadas desde Excel. Si alguna fila
tiene errores, el lote completo se rechaza; las fechas aceptan `AAAA-MM-DD` o
`DD/MM/AAAA`, Total HH admite coma o punto decimal y la fecha de cierre puede
omitirse para tickets abiertos o en progreso. El estado pegado desde Excel no
distingue mayúsculas de minúsculas.

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
