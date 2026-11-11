import os

class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "helpdesk-secret-key"
    )

    SQLALCHEMY_DATABASE_URI = (
        "mssql+pyodbc://LAPTOP-ELMVRCVU/"
        "SistemaTicket"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&trusted_connection=yes"
        "&TrustServerCertificate=yes"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False