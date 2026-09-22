# Fleet Log — Plataforma de Trazabilidad Vehicular

Sistema web para la **gestión y trazabilidad de registros operativos de vehículos**. El proyecto permite centralizar bitácoras, incidencias, mantenimientos, observaciones y evidencias multimedia asociadas a cada vehículo.

Fleet Log está diseñado como un **MVP orientado a pequeñas y medianas operaciones que necesitan mantener un historial digital de sus vehículos**, reemplazando registros dispersos en papel, Excel u otros medios.

## Demo y Documentación

* **API Base URL:** `https://...`
* **OpenAPI (Redoc):** `https://...`
* **OpenAPI (Swagger UI):** `https://...`

> Las URLs serán agregadas una vez desplegada la aplicación.

## Motivación

El proyecto nace de la necesidad de contar con un sistema simple para mantener la **trazabilidad de las actividades asociadas a una flota de vehículos**.

En operaciones pequeñas, información como mantenimientos, incidentes, observaciones y revisiones puede quedar registrada en distintos medios, dificultando consultar el historial de un vehículo y determinar qué actividades se han realizado.

Fleet Log busca centralizar esta información mediante una aplicación web que permita registrar y consultar eventos asociados a cada vehículo, manteniendo además información sobre **quién realizó cada registro y cuándo fue creado**.

## Tecnologías

### Backend

* Python
* Django
* Django REST Framework
* PostgreSQL
* Simple JWT
* Djoser

### Frontend

* React
* TypeScript
* Vite
* TanStack Router
* TanStack Query
* TanStack Table
* React Hook Form
* Zod
* Tailwind CSS
* shadcn/ui
* Lucide React

## Infraestructura y Herramientas

* Git
* GitHub
* Docker
* REST API
* OpenAPI

## Funcionalidades

### Gestión de vehículos

* CRUD de vehículos
* Consulta de vehículos
* Búsqueda por patente
* Visualización del historial de registros
* Información resumida de actividad por vehículo

### Registros de vehículos

Los usuarios autorizados pueden crear registros asociados a un vehículo, clasificándolos según su naturaleza:

* Incidente
* Mantenimiento
* Observación
* Limpieza

Cada registro mantiene información sobre:

* Título
* Detalle
* Usuario que realizó el registro
* Fecha de creación
* Estado
* Evidencias multimedia

### Estados de registros

Los registros pueden avanzar mediante distintos estados de seguimiento:

* Pendiente
* Revisado
* Resuelto

Esto permite diferenciar entre un evento simplemente registrado y uno que requiere seguimiento o resolución.

### Evidencias multimedia

Los registros pueden incluir archivos asociados, permitiendo adjuntar:

* Fotografías
* Videos

Las evidencias quedan vinculadas directamente al registro del vehículo.

### Autenticación y cuentas

* Autenticación mediante JWT
* Inicio y cierre de sesión
* Recuperación y cambio de contraseña
* Gestión de perfiles de usuario
* Invitación de usuarios
* Control de usuarios activos

### Roles y permisos

El sistema incorpora un mecanismo de autorización basado en:

* Grupos
* Permisos
* Permisos específicos por usuario

Esto permite separar las capacidades administrativas de las operaciones realizadas por los usuarios de terreno.

### Dashboard

El panel administrativo proporciona información agregada sobre la actividad de la flota, incluyendo:

* Total de vehículos
* Total de registros
* Registros creados durante el día
* Registros creados durante la semana
* Registros creados durante el mes
* Registros pendientes
* Incidentes pendientes
* Distribución de registros por estado
* Distribución de registros por tipo
* Vehículos con mayor cantidad de registros
* Usuarios con mayor cantidad de registros
* Resumen de archivos multimedia

## Arquitectura

El proyecto está dividido en dos aplicaciones principales:

* **fleet_log_api** → Backend desarrollado con Django REST Framework.
* **fleet_log_client** → Frontend desarrollado con React, TypeScript y Vite.

La comunicación entre ambas aplicaciones se realiza mediante una **API REST**.

### Backend

El backend utiliza una arquitectura basada en aplicaciones y dominios de Django, separando responsabilidades como:

* Autenticación y cuentas
* Usuarios y permisos
* Vehículos
* Registros de vehículos
* Archivos multimedia
* Dashboard

### Frontend

El frontend utiliza una organización basada en funcionalidades, separando cada dominio de negocio en sus propios módulos.

La aplicación cuenta con dos flujos principales:

* **Panel administrativo:** orientado a la gestión de vehículos, usuarios, permisos y consulta de información.
* **Flujo operativo:** orientado a que los usuarios puedan buscar un vehículo y registrar rápidamente una actividad desde dispositivos móviles.

## Flujo operativo

El flujo principal para un operador es:

1. Buscar un vehículo mediante su patente.
2. Seleccionar el vehículo.
3. Crear un nuevo registro.
4. Indicar el tipo de actividad.
5. Agregar una descripción.
6. Adjuntar fotografías o videos cuando sea necesario.
7. Guardar el registro.

El objetivo es que este flujo pueda utilizarse cómodamente desde **teléfonos y tablets**, reduciendo la cantidad de pasos necesarios para registrar una actividad en terreno.

## API

La API está desarrollada siguiendo los principios de una **API REST**, utilizando Django REST Framework.

Entre los principales recursos se encuentran:

* `/api/v1/vehicles/`
* `/api/v1/vehicles/{id}/`
* `/api/v1/vehicles/{vehicle_id}/logs/`
* `/api/v1/vehicles/{vehicle_id}/logs/{id}/`
* `/api/v1/permissions/`
* `/api/v1/groups/`
* `/api/v1/users/`

La documentación de la API se genera mediante **OpenAPI**.

## Estado del proyecto

Proyecto en desarrollo activo.

Actualmente se encuentran implementados los principales componentes del MVP:

* Autenticación
* Gestión de usuarios
* Gestión de vehículos
* Registros de vehículos
* Estados de registros
* Evidencias multimedia
* Grupos y permisos
* Dashboard administrativo
* Interfaz operativa responsive

Las funcionalidades y la arquitectura continúan evolucionando a medida que se valida el flujo completo de la aplicación.
