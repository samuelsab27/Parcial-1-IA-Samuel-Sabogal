# Diseño del agente

El entorno de operaciones críticas se caracteriza por ser totalmente observable, determinista, secuencial, estático y discreto. Dado que no hay incertidumbre en los efectos de las acciones, el problema se formula bajo el marco de la Búsqueda Clásica Constructiva. El agente fue diseñado para explorar sistemáticamente los nodos del grafo y construir un plan completo antes de ejecutar cualquier movimiento físico. Al evaluar el costo acumulado de los caminos disponibles, el algoritmo optimiza la ruta minimizando el gasto de energía y planificando visitas estratégicas a los cargadores para asegurar que se cumpla la meta sin agotar la batería.

# Estado
# Definicion formal

El estado físico del entorno se modela matemáticamente como una tupla:

$$s = \langle p, B, I, G, U, R, A \rangle$$

Donde:
* $p$: La posición actual del robot.
* $B$: El nivel de batería restante.
* $I$: El inventario actual del robot (conjunto inmutable de objetos).
* $G$: Los objetos disponibles en el suelo (conjunto de pares zona-objeto).
* $U$: El conjunto de puertas desbloqueadas.
* $R$: El conjunto de paneles reparados.
* $A$: El conjunto de estaciones activadas.

---



### Por qué cada variable es necesaria

Aplicando el criterio de la función `Applicable`, una variable es estrictamente necesaria si su ausencia o modificación altera las acciones legales futuras o sus resultados:

* **Posición ($p$):** Es fundamental porque determina el origen de cualquier movimiento. Sin ella, el agente no sabría qué movimientos son válidos para la acción `MOVE`, ni sabría si está en la misma zona que un objeto para hacer `PICKUP`, o frente al panel correcto para hacer `REPAIR`.
* **Batería ($B$):** Forma parte íntegra de la situación física del robot. Toda acción tiene un costo de energía. Si no se almacena, el agente no podría evaluar la precondición lógica de $B \ge costo$, permitiendo movimientos ilegales que violan el contrato del entorno.
* **Inventario ($I$) y Suelo ($G$):** La ubicación exacta de los objetos condiciona el futuro. No se deducen del estado inicial porque el robot puede soltarlos (`DROP`). Si el agente no sabe qué lleva en $I$, no sabrá si tiene la llave para abrir una puerta o el espacio físico libre para recoger un fusible.
* **Cambios permanentes ($U, R, A$):** Las puertas abiertas, paneles reparados y estaciones activadas modifican la topología y las reglas del mapa. Son necesarias para no repetir acciones (y desperdiciar batería) y para cumplir las dependencias lógicas previas de otras estaciones.

### Qué información se deriva y NO se almacena

Cosas como la capacidad máxima de carga del robot, el mapa con las conexiones de los corredores, la batería máxima o cuánto cuesta cada acción, no se guardan en el estado. Como es información estática que se saca directamente del archivo del escenario y no cambia tras hacer un movimiento, meterla en cada estado solo haría que el agente consuma memoria RAM de forma innecesaria.

### Qué pertenece al historial de búsqueda y no al estado físico

El costo acumulado de energía `g(n)`, el nodo padre del que venimos y la acción que acabamos de realizar son parte de la estructura del Nodo, no del estado físico[cite: 1]. Estos datos explican *cómo* llegamos a ese punto de la misión, pero no describen *dónde* estamos[cite: 1]. Si llegamos a mezclar el historial de búsqueda dentro del estado lógico, la lista `CLOSED` no podría reconocer cuando alcanzamos la misma situación física por dos caminos distintos, lo que haría que el algoritmo genere ramas redundantes y explote.

### Cuándo dos configuraciones son el mismo estado

Dos configuraciones son iguales cuando las variables físicas del mapa y del robot coinciden, sin importar qué camino tomó para llegar ahí. Además, si hay dos materiales del mismo tipo (como dos cables), son equivalentes y no importa en qué orden se recogieron. Por eso, en el código agrupamos el inventario y las puertas abiertas usando `frozenset` (conjuntos inmutables); esto garantiza que la prueba de igualdad matemática (`__eq__`) y el hash funcionen a la perfección[cite: 1]. Gracias a esto, la lista `CLOSED` puede detectar los estados repetidos casi al instante en tiempo $\mathcal{O}(1)$[cite: 1].

### Relevancia: objetos que ya no cambian el futuro

Cuando usamos una llave para abrir una puerta o una herramienta para arreglar un panel, ese objeto prácticamente ya cumplió su misión. Si el robot se pone a recoger y botar esa misma llave usada en todos los cuartos posibles, el algoritmo va a registrar cada posición como si fuera un estado nuevo. Esto genera un montón de combinaciones inútiles que no nos sirven para nada. Ignorar en dónde quedaron tirados esos "objetos muertos" nos ahorra muchísima memoria y no afecta el resultado, porque su ubicación final no nos ayuda a conseguir un plan más barato.

---

## Acciones

Estas son las acciones que mi agente puede decidir hacer. (Nota importante: para poder hacer cualquiera de ellas, la regla de oro es que el robot debe tener una `batería >= costo` de la acción).

| Acción | Precondiciones | Efectos | Costo |
| :--- | :--- | :--- | :--- |
| **MOVE** | Estar en un cuarto conectado al destino y que la puerta (si la hay) ya esté abierta. | La posición del robot cambia al nuevo cuarto. | El costo específico de ese corredor |
| **PICKUP** | Estar en el mismo cuarto que el objeto y tener espacio libre en el inventario. | El objeto desaparece del piso y pasa al inventario. | El costo de pickup |
| **DROP** | Tener al menos un objeto guardado en el inventario. | El objeto sale del inventario y queda en el piso de ese cuarto. | El costo de drop |
| **OPEN_DOOR** | Estar en el cuarto de la puerta y tener la llave correcta guardada. | La puerta se marca como abierta para el resto de la misión. | El costo de interact |
| **REPAIR** | Estar donde está el panel dañado, tener la herramienta necesaria y el material de consumo. | El panel queda arreglado y el material desaparece del inventario. | El costo de interact |
| **ACTIVATE** | Estar en la estación, y cumplir los requisitos previos (paneles ya reparados o estaciones previas prendidas). | La estación se enciende. | El costo de interact |
| **RECHARGE** | Estar en un cuarto que tenga un cargador y no tener la batería al máximo. | La batería se llena de nuevo al 100%. | El costo de recharge |

### `Applicable` interno vs legalidad del contrato

El simulador permite soltar (`DROP`) cualquier objeto que llevemos en cualquier momento. Eso es legal para el contrato. Pero, si el código de mi agente se pone a calcular qué pasaría si suelta cada objeto en cada cuarto por el que pasa, la cantidad de caminos a evaluar explota y la computadora se queda sin memoria en segundos.

Por eso, mi agente no genera la acción de `DROP` a lo loco. Para mantener la búsqueda enfocada, solo consideramos soltar objetos cuando tenemos algo en el inventario y necesitamos moverlo. Restringir el `DROP` de esta manera no nos hace perder la ruta óptima, porque en la vida real ningún plan perfecto y barato implica gastar energía recogiendo y tirando cosas al piso por diversión; el camino de menor costo siempre va a ser el más directo.

## Modelo de transición

$$s \xrightarrow{a} s' \quad \text{solo si } a \in Applicable(s)$$

El modelo de transición es básicamente cómo se actualiza nuestro mundo cuando el robot ejecuta una acción. Como no hay azar en este mapa, el resultado es 100% predecible (determinista)[cite: 1]. Si el robot hace un movimiento válido, tomamos el estado actual, le restamos la batería que costó esa acción, actualizamos su posición o inventario según corresponda, y creamos un nuevo estado. Al final, siempre ordenamos todo en nuestros conjuntos inmutables para que el estado quede limpio y no tengamos problemas al compararlo con los que ya visitamos.

---

## Prueba de meta

$$Goal(s) \iff \text{Estaciones Objetivo} \subseteq A$$

La prueba de meta es la condición que le dice al código: "¡Listo, ya ganamos!". Lo importante aquí es que el éxito se verifica mirando cómo quedó el mundo al final (que las estaciones principales estén prendidas), y no comprobando si el robot siguió un libreto de tareas. Abrir puertas y arreglar paneles no es la meta en sí, son solo los pasos necesarios (los medios) para poder encender las estaciones que nos pide la misión.

---

## Función de costo

$$g(n) = \sum \text{costos de las acciones del camino}$$

Nuestra función de costo $g(n)$ es la suma de toda la energía que el robot fue gastando desde que arrancó hasta el punto actual. Es súper clave entender que en este juego tener menos pasos no significa que la ruta sea mejor[cite: 1]. Por ejemplo, dar tres pasos por un pasillo que gasta muchísima energía puede salir más caro que dar cinco pasos por un camino económico y reparando cosas[cite: 1]. Por eso, nuestra IA siempre busca minimizar el costo total oficial, no la cantidad de movimientos.
---

## Estrategia de búsqueda

Elegimos usar la **Búsqueda de Costo Uniforme (UCS o Dijkstra)**. En este mapa los costos de movernos o hacer cosas son diferentes (unos pasillos gastan más batería que otros), así que no nos sirve un algoritmo que solo cuente la cantidad de pasos.

*   **Completitud y Optimalidad:** UCS nos garantiza que si hay una solución, la va a encontrar, y además va a ser la más barata de todas. Esto funciona porque nuestra lista de pendientes (Frontera) siempre saca primero el camino que lleva menos energía gastada. Ojo, la prueba de meta la hacemos al *sacar* el estado de la lista, no cuando recién lo descubrimos, para asegurar que no nos vayamos por una ruta que parecía buena pero terminaba siendo más cara.
*   **Tiempo y Espacio:** El punto débil de este algoritmo es que consume muchísima memoria RAM probando combinaciones. Por eso fue vital restringir acciones como el `DROP`, para no generar miles de ramificaciones inútiles.
*   **¿Cuándo falla?** Este algoritmo se rompería si el mapa tuviera costos negativos o de cero, porque el robot se quedaría dando vueltas gratis para siempre. Afortunadamente, las reglas del contrato aseguran que todo cuesta algo.

### Batería como recurso

La batería es parte de nuestro estado físico. Pero aquí hay un truco gigante: si le decimos al código que llegar al Cuarto 1 con 90% de batería es un mundo, y llegar al mismo Cuarto 1 con 89% es un mundo totalmente distinto, el algoritmo va a explorar millones de variaciones inútiles hasta quedarse sin memoria. 

Para arreglar eso, usamos la **dominancia**. Nuestra lista de visitados (`CLOSED`) guarda cómo está el mapa y con cuánta batería máxima logramos llegar hasta ahí. Si más tarde el robot encuentra otra ruta que lo lleva al mismo lugar y con las mismas puertas abiertas, pero con *igual o menos batería*, simplemente la descartamos. Ese camino está "dominado" y no nos sirve. Si llega con *más* batería, sí lo dejamos pasar porque significa que encontramos una mejor ruta (por ejemplo, pasando por un cargador).

---

## Formulación y tamaño del espacio (obligatorio)

1. **¿Por qué «5 zonas, ~10 objetos, capacidad 3» puede generar millones de nodos en un UCS ingenuo?**
   Porque el juego no solo combina los 5 cuartos. Multiplica esos cuartos por todas las combinaciones posibles de los objetos en el inventario, multiplicado por las combinaciones de puertas abiertas o cerradas y los paneles. Matemáticamente, el espacio de posibilidades crece de forma masiva.

2. **¿Qué papel tiene `DROP` en esa explosión?**
   Si el robot puede tirar cualquier objeto al piso en cualquier cuarto y en cualquier turno, el árbol de posibilidades se vuelve infinito. El robot empezaría a evaluar la opción de dar un paso, botar una llave, recogerla, botarla en la otra esquina, etc., ahogando la memoria RAM.

3. **¿Qué podas o abstracciones aplicó y por qué no pierden el óptimo?**
   Aplicamos dos cosas clave: la dominancia de la batería (para ignorar caminos que nos dejan más descargados sin ningún beneficio) y restringir el `DROP` para que no bote cosas a lo loco. Esto no pierde el óptimo porque, lógicamente, el camino perfecto y más barato nunca va a incluir dar vueltas tontas desperdiciando batería en recoger y botar la misma herramienta.

4. **¿Por qué no es solución subir la capacidad, bajar las estaciones o ignorar la batería?**
   Porque eso sería hacer trampa modificando el juego (`scenario.json`) para esconder los errores de nuestro código. Si el profe prueba nuestro agente en un mapa más grande o con menos capacidad, un algoritmo ingenuo volvería a explotar. La verdadera inteligencia artificial consiste en que el agente sepa descartar las malas decisiones desde su programación, no en bajarle la dificultad al juego.