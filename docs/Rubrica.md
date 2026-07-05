# Rubrica de Evaluacion Automatizada - Backend y API

## Objetivo

Evaluar exclusivamente:

- API Backend
- Aplicacion Web Administrativa
- Integracion Backend ↔ Base de Datos
- Coleccion Postman
- Reportes y Estadisticas

No evaluar:

- Frontend Movil
- Diseño UI/UX
- Apariencia visual

Puntaje Maximo: 100

---

## 1. Gestion de Usuarios (CRUD Completo)

Puntaje: 15

### Verificaciones

- Crear usuario
- Obtener usuario por ID
- Listar usuarios
- Actualizar usuario
- Eliminar usuario
- Validaciones de datos
- Persistencia correcta

### Puntuacion

- Cumple completamente: 15
- Cumple parcialmente: 7
- No cumple: 0

---

## 2. Modulo de Estadisticas

Puntaje: 15

### Verificaciones

- Estadisticas de gastos
- Estadisticas de ganancias
- Estadisticas de productos
- Datos obtenidos desde la base de datos

### Puntuacion

- Cumple completamente: 15
- Cumple parcialmente: 7
- No cumple: 0

---

## 3. Modulo de Reportes

Puntaje: 15

### Verificaciones

Reportes de:

- Productos
- Pedidos
- Inventario

Formatos:

- PDF
- XLSX

### Puntuacion

- Cumple completamente: 15
- Cumple parcialmente: 7
- No cumple: 0

---

## 4. Aplicacion Web Administrativa + API

Puntaje: 15

### Verificaciones

- Front administrativo funcional
- Consume correctamente la API
- Operaciones CRUD ejecutadas correctamente
- Sin errores críticos

### Puntuacion

- Cumple completamente: 15
- Cumple parcialmente: 7
- No cumple: 0

---

## 5. API Modulo Cocina

Puntaje: 15

### Verificaciones

Endpoints Postman para:

- Gestion de menu
- Gestion de suministros

### Puntuacion

- Todos funcionales: 15
- Parcialmente funcionales: 7
- No funcionales: 0

---

## 6. API Modulo Caja

Puntaje: 15

### Verificaciones

Endpoints Postman para:

- Gestion monetaria
- Compras

### Puntuacion

- Todos funcionales: 15
- Parcialmente funcionales: 7
- No funcionales: 0

---

## 7. API Modulo Mesero

Puntaje: 10

### Verificaciones

Endpoints Postman para:

- Levantamiento de pedidos
- Consulta de pedidos

### Puntuacion

- Todos funcionales: 10
- Parcialmente funcionales: 5
- No funcionales: 0

---

# Reglas para el Agente Evaluador

1. Solo otorgar puntos cuando exista evidencia verificable.
2. No asumir funcionalidad por existencia de código.
3. Priorizar pruebas ejecutables sobre documentación.
4. Si un endpoint responde error 500, considerarlo no funcional.
5. Si la colección Postman no puede ejecutarse, asignar 0 al criterio correspondiente.
6. Incluir observaciones detalladas por cada criterio.
7. Generar puntuación total y porcentaje final.

---

# Formato de Respuesta

```json
{
  "criterios": {
    "gestion_usuarios": {
      "score": 15,
      "max_score": 15,
      "evidencia": [],
      "observaciones": []
    },
    "estadisticas": {
      "score": 15,
      "max_score": 15,
      "evidencia": [],
      "observaciones": []
    },
    "reportes": {
      "score": 15,
      "max_score": 15,
      "evidencia": [],
      "observaciones": []
    },
    "web_api": {
      "score": 15,
      "max_score": 15,
      "evidencia": [],
      "observaciones": []
    },
    "api_cocina": {
      "score": 15,
      "max_score": 15,
      "evidencia": [],
      "observaciones": []
    },
    "api_caja": {
      "score": 15,
      "max_score": 15,
      "evidencia": [],
      "observaciones": []
    },
    "api_mesero": {
      "score": 10,
      "max_score": 10,
      "evidencia": [],
      "observaciones": []
    }
  },
  "total": 100,
  "max_total": 100,
  "porcentaje": 100
}
```
