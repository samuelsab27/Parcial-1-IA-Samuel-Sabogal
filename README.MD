# UNIVERSIDAD DE LA SABANA — FACULTAD DE INGENIERÍA
## Fundamentos de Inteligencia Artificial — Semestre 2026-2
# PRIMER PARCIAL
## Planificador Autónomo de Operaciones Críticas (UCS)

Este parcial implementa un agente de Inteligencia Artificial utilizando el algoritmo de Búsqueda de Costo Uniforme (Uniform Cost Search / Dijkstra) para resolver misiones de mantenimiento crítico en un entorno determinista.

## Requisitos Previos

* Python 3.10 o superior.
* Node.js y npm (para el frontend).

## 1. Instalar dependencias

Para el backend (Python):

```bash
cd backend
pip install -r requirements.txt
```

Para el frontend (React/Vite):

```bash
cd frontend
npm install
```

### 2. Iniciar el Backend

Desde la raíz del proyecto, navega a la carpeta del backend y ejecuta el servidor de FastAPI:

```bash
cd backend
python src/main.py
```

El servidor quedará corriendo en `http://localhost:8000`.

### 3. Iniciar el Frontend

Abre una nueva terminal, navega a la carpeta del frontend y arranca el servidor de desarrollo:

```bash
cd frontend
npm run dev
```

La interfaz visual estará disponible en `http://localhost:5173`.

### 4. Ejecutar el agente y probar la misión

1. Abre tu navegador en `http://localhost:5173`.
2. Verás el mapa del entorno cargado (`scenario.json`).
3. Haz clic en el botón "EXECUTE PLAN" en la esquina inferior izquierda.
4. El frontend hará una petición al backend (`/api/solve`), el cual calculará la ruta óptima utilizando UCS y devolverá los pasos.

### 5. Interpretar el resultado

- **Visualización:** El robot se moverá por el mapa ejecutando operaciones (MOVE, PICKUP, DROP, INTERACT).
- **Execution Log:** En el panel derecho podrás ver paso a paso las acciones generadas, su costo individual y el impacto en la batería.
- **Costo Acumulado:** El panel superior derecho mostrará la suma total de energía gastada para encontrar el plan óptimo. Si la misión es exitosa, el log terminará con "¡Misión Completada por la IA mediante UCS!".

### 6. Ejecutar pruebas (Validación IA)

Para verificar la completitud, optimalidad y manejo de dominancia de batería del agente:

```bash
cd backend
python tests/test_demo_plan.py
```
````
