 CREATE TABLE "Empresas" (
	"IdEmpresa" INTEGER NOT NULL, 
	"NombreEmpresa" VARCHAR(200) NOT NULL, 
	PRIMARY KEY ("IdEmpresa"), 
	UNIQUE ("NombreEmpresa")
);

CREATE TABLE "Perfiles" (
	"IdPerfil" INTEGER NOT NULL, 
	"NombrePerfil" VARCHAR(100) NOT NULL, 
	"EsAdministrador" BOOLEAN NOT NULL DEFAULT 0, 

	PRIMARY KEY ("IdPerfil"), 
	UNIQUE ("NombrePerfil")
);

CREATE TABLE "TiposTicket" (
	"IdTipoTicket" INTEGER NOT NULL, 
	"NombreTipo" VARCHAR(100) NOT NULL, 
	PRIMARY KEY ("IdTipoTicket"), 
	UNIQUE ("NombreTipo")
);

CREATE TABLE "Usuarios" (
	"IdUsuario" INTEGER NOT NULL, 
	"Usuario" VARCHAR(100), 
	"NombreCompleto" VARCHAR(200), 
	"Correo" VARCHAR(200), 
	"PasswordHash" VARCHAR(500), 
	"Activo" BOOLEAN NOT NULL DEFAULT 1, 
	"IdPerfil" INTEGER, 
	"IdEmpresa" INTEGER, 
	PRIMARY KEY ("IdUsuario"), 
	UNIQUE ("Usuario"),
	FOREIGN KEY("IdPerfil") REFERENCES "Perfiles" ("IdPerfil"),
	FOREIGN KEY("IdEmpresa") REFERENCES "Empresas" ("IdEmpresa")
);

CREATE TABLE "Tickets" (
	"IdTicket" INTEGER NOT NULL, 
	"FechaApertura" DATETIME, 
	"FechaCierre" DATETIME, 
	"Titulo" VARCHAR(300), 
	"Descripcion" TEXT, 
	"TotalHH" NUMERIC(10, 2), 
	"Estado" VARCHAR(30), 
	"UsuarioCreacion" INTEGER, 
	"IdTipoTicket" INTEGER, 
	PRIMARY KEY ("IdTicket"), 
	FOREIGN KEY("UsuarioCreacion") REFERENCES "Usuarios" ("IdUsuario"),
	FOREIGN KEY("IdTipoTicket") REFERENCES "TiposTicket" ("IdTipoTicket")
);