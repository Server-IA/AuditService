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

## 6. Anexos:

- Conexión al container de la db:
```bash
docker exec -it auditservice-audit-db-1 psql -U audit
```

- Endpoint base de API para consulta de eventos:
http://localhost:8070/audit-events

- Desglose estructural del evento (JSON):
```json
  {
    "event_id": "75262d10-9015-4d24-bd9d-40e198bde5c9",
    "ts": "2025-09-04T07:04:25.713351+00:00",
    "actor_id": null,
    "actor_role": null,
    "actor_type": "service",
    "request_id": "522f0119-4394-4751-befd-50c3968e04fe",
    "ip": "172.18.0.1",
    "user_agent": "PostmanRuntime/7.45.0",
    "service": "users",
    "module": "gestion_usuarios",
    "submodule": "roles",
    "feature": "create_role",
    "object_type": "role",
    "object_id": "51",
    "operation": "CREATE",
    "before": null,
    "after": {
      "id": 51,
      "name": "rol_nonloso",
      "status": 1,
      "description": "Descripción..",
      "permissions": [
        10
      ]
    },
    "meta": {
      "source": "roles.create_role"
    }
  }
```

## TEMPORAL AUDIT OUTPUT
```json
  {
    "event_id": "930c98c1-8158-46c3-94ce-8bebf08261d4",
    "ts": "2025-09-15T22:34:23.079994+00:00",
    "actor_id": "11",
    "actor_role": "for_testing",
    "actor_type": "user",
    "request_id": "6a2c29c4-c701-4255-8e75-444b33119d22",
    "ip": "172.18.0.1",
    "user_agent": "PostmanRuntime/7.46.0",
    "service": "users",
    "module": "gestion_usuarios",
    "submodule": "roles",
    "feature": "edit",
    "object_type": "role",
    "object_id": "79",
    "operation": "UPDATE",
    "before": {
      "id": 79,
      "name": "perito",
      "status": 1,
      "description": "Control sobre módulo de nómina.",
      "permissions": [
        13
      ]
    },
    "after": {
      "id": 79,
      "name": "perito",
      "status": 1,
      "description": "Control parcial sobre módulo nomina.",
      "permissions": [
        3
      ]
    },
    "meta": {
      "source": "roles.edit_role",
      "actor_roles_ids": [
        70
      ]
    },
    "permission_id": 15,
    "diff": {
      "added": {},
      "changed": {
        "description": {
          "to": "Control parcial sobre módulo nomina.",
          "from": "Control sobre módulo de nómina."
        },
        "permissions": {
          "to": [
            3
          ],
          "from": [
            13
          ]
        }
      },
      "removed": {}
    }
  }
```

## [+]. Consideraciones Finales

- Todo el desarrollo y ejecución de este backend se realiza dentro de **Docker**, por lo que **no es necesario configurar entornos virtuales locales**.  
- Antes de levantar este contenedor, valida siempre que:
  - La red **shared_net** esté creada.
  - El proyecto **main** se encuentre corriendo, ya que provee los servicios base (como la base de datos).  
