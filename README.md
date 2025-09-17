# AuditService
Este repositorio contiene el backend de auditorías para el proyecto **Sigma**. Su arquitectura está dispuesta como microservicio ligero. Este documento describe la infraestructura lógica del servicio y una guía para su implementación.

---

## 1. Organización del Repositorio y Ramas

- **Ramas principales:**
  - **develop:** Desarrollo y Pull Requests.
  - **main:** Recibe los cambios aprobados desde `develop`.
  - **test:** El equipo de QA trae cambios desde `main` para ejecutar pruebas.
  - **dokploy:** Se actualiza tras aprobar pruebas para despliegue/producción.

- **Flujo de trabajo:**
  1. Desarrollo en **develop** (PRs).
  2. Aprobación por el líder → merge a **main**.
  3. QA trae cambios de **main** a **test** y realiza pruebas.
  4. Si todo OK, se actualiza **dokploy** para despliegue.

---

## 2. Configurar Variables de Entorno

Copia el archivo `.env.example` a `.env` y ajusta los valores:

**Desde el proyecto que consumirá el microservicio (UsersMachPay), adicionar:**
```dotenv
SERVICE_NAME=users
AUDIT_URL=http://audit-service:8000/audit-events
AUDIT_TOKEN=devtoken
AUDIT_HTTP_TIMEOUT=1.5
```

**Desde el microservicio (AuditService):**
```dotenv
# INTERNAL CONTAINER
AUDIT_DB_DSN=postgresql://audit:audit@audit-db:5432/audit

# AUTH API 
AUDIT_TOKEN=devtoken

# POSTGRES VARS
POSTGRES_DB=audit
POSTGRES_USER=audit
POSTGRES_PASSWORD=audit
```

## 3. Crear la Red de Docker

Antes de levantar el contenedor de este proyecto, es necesario crear una red compartida en Docker para permitir la comunicación entre los distintos servicios.  

Este paso solo debe ejecutarse una vez en la máquina local:  

```bash
docker network create shared_net
```

## 4. Levantar el Contenedor (UsersMachPay)

El backend de **Users Sigma** depende de los servicios definidos en el proyecto **main**, especialmente la base de datos.  
Por esta razón, **antes de iniciar este contenedor debes asegurarte de que el proyecto `main` ya esté levantado** con su `docker-compose`.

Una vez verificado lo anterior, puedes construir e iniciar el servicio de este proyecto con:

```bash
docker-compose up --build
```
## 5. Levantar el Contenedor (AuditService):
Desde el directorio del repositorio ejecutar el siguiente comando:

```bash
docker-compose up --build -d
```

## 6. Contexto de uso y alcance:
El microservico de auditoría contempla las siguientes acciones:

```rb
Create role 
Create permission 
Edit role 
Change rol status 
Update user roles 
Update rol permissions 
Assign role 
Revoke rol 
Delete rol 

Create user by admin 
Complete pre register (validate doc) [?]
Complete pre register [?]
Activate account [?]
Edit profile 
Editar información completa del usuario (como Admin) 

Change user status 
Change password 

Admin/User auth login 
Update password via token [?]

Request reset password [?]
```
**NOTA:**
> Para las acciones que al final de la línea tienen un **"[?]"**, no se incluye información del actor (actor_id, rol_id) y del permiso (permission_id), debido a que no hay contexto de autenticación y/o permiso contemplado en las respectivas funciones.

### Filtros (query parameters)
El microservicio permite filtrar resultados de manera directa a través los siguientes parámetros:

	•	actor_id — ID del actor que ejecutó la acción (string).
	•	operation — Tipo de operación (ACCESS, CREATE, UPDATE, DELETE, etc.).
	•	module — Módulo canónico (ej. users_management).
	•	submodule — Submódulo (ej. roles, users, auth).
	•	feature — Acción/feature (ej. login, create, edit, change_user_password).
	•	object_type — Tipo de objeto (ej. user, role, permission).
	•	object_id — ID del objeto afectado (string).
	•	source — Atajo para meta->>'source' (ej. roles.edit_role, auth.login).
	•	permission_id — ID del permiso bajo el cual se ejecutó la acción (int).
	•	date_from — ISO 8601 (inclusive). Filtra ts >= date_from.
	•	date_to — ISO 8601 (inclusive). Filtra ts <= date_to.
	•	limit — Límite de filas (por defecto 100).
	•	offset — Desplazamiento para paginación (por defecto 0).

 - Endpoint base de API para consulta de eventos:
http://localhost:8070/audit-events

 - **Ejemplo**: <br>
 Búsqueda con filtros anidados:
 ```bash
curl -s "http://localhost:8070/audit-events\
?operation=UPDATE\
&submodule=roles\
&feature=edit\
&permission_id=15\
&actor_id=11\
&date_from=2025-09-16T00:00:00Z"
```
**Nota:**
> Los atributos flexibles viven en meta (JSON). Estos son útiles en contextos de autenticación.
- **Ejemplo:** <br>
Inicio de sesión no exitoso:
```json
  {
    "event_id": "c08b14c6-ed8f-453b-ab64-3e7a584346c7",
    "ts": "2025-09-16T06:07:33.527065+00:00",
    "actor_id": null,
    "actor_role": null,
    "request_id": "4fb518f6-f211-4c89-a403-d195d19dba15",
    "ip": "172.18.0.1",
    "user_agent": "PostmanRuntime/7.46.0",
    "module": "gestion_usuarios",
    "submodule": "auth",
    "feature": "login",
    "object_type": "user",
    "object_id": null,
    "operation": "ACCESS",
    "before": null,
    "after": null,
    "meta": { // justo aquí
      "reason": "invalid_credentials",
      "result": "failed",
      "source": "auth.login",
      "username_hint": "correo@usco.edu.co",
      "actor_roles_ids": []
    },
    "permission_id": null,
    "diff": null
  }
```

- Estructural de un evento 'UPDATE':
```json
  {
    "event_id": "6fae6134-7747-4006-916c-3d4124a12a30",
    "ts": "2025-09-16T05:46:20.395532+00:00",
    "actor_id": "1",
    "actor_role": "administrador",
    "request_id": "f7178180-e51a-47c0-87fd-8698ec00cb56",
    "ip": "172.18.0.1",
    "user_agent": "PostmanRuntime/7.46.0",
    "module": "users management",
    "submodule": "users",
    "feature": "change_status",
    "object_type": "user_status",
    "object_id": "10",
    "operation": "UPDATE",
    "before": {
      "id": 10,
      "name": "joseph",
      "email": "tester123@gmail.com",
      "roles": [
        83
      ],
      "gender_id": 1,
      "status_id": 1,
      "first_last_name": "mendez",
      "second_last_name": "vega"
    },
    "after": {
      "id": 10,
      "name": "joseph",
      "email": "tester123@gmail.com",
      "roles": [
        83
      ],
      "gender_id": 1,
      "status_id": 2,
      "first_last_name": "mendez",
      "second_last_name": "vega"
    },
    "meta": {
      "source": "users.change_user_status",
      "new_status": 2,
      "actor_roles_ids": [
        56,
        32,
        13,
        14
      ]
    },
    "permission_id": 10,
    "diff": { // Permite obtener el campo(s) alterado o eliminado
      "changed": {
        "status_id": {
          "to": 2, // estado actual (luego de la transacción)
          "from": 1 // estado anterior
        }
      },
      "removed": {}
    }
  }
```

## 7. Anexos:
- Conexión al container de la db:
```bash
docker exec -it auditservice-audit-db-1 psql -U audit
```

## [+]. Consideraciones Finales

- Todo el desarrollo y ejecución de este backend se realiza dentro de **Docker**, por lo que **no es necesario configurar entornos virtuales locales**.  
- Antes de levantar este contenedor, valida siempre que:
  - La red **shared_net** esté creada.
  - El proyecto **main** se encuentre corriendo, ya que provee los servicios base (como la base de datos).  
