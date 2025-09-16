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

- Estructural del evento (JSON):
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
    "diff": {
      "changed": {
        "status_id": {
          "to": 2,
          "from": 1
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
