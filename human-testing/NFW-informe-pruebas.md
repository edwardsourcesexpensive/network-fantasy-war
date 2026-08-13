# Network Fantasy War — Informe de pruebas

**Versión:** despliegue en `network-fantasy-war-production.up.railway.app`
**Partida:** sala `PSEI`, jugador 1 (`pid=0`). Partida a dos, seis turnos jugados.
**Estado al interrumpirse:** J1 con 30 sellos, J2 con 20. Fin por caída de sesión.

---

## 1. Fallos de implementación

### 1.1 Pérdida de sesión sin recuperación — *crítico*

Durante el turno 5, al intentar ejecutar una acción, el cliente devuelve la alerta
«No estás en ninguna sala». Ni el botón *Refresh* ni la recarga completa de la URL
—conservando `code=PSEI&pid=0`— restauran la partida. El estado se pierde por
completo: no hay reconexión ni persistencia del tablero.

Es el fallo más grave del lote, porque invalida todo lo demás.

### 1.2 «Carta no encontrada» al activar el Recaudador de Impuestos

Con el Recaudador ya en el tablero (L1, m4), al activar su habilidad `[1]: el
oponente pierde 2 sellos` aparece una alerta con el texto «Carta no encontrada».
El efecto no se resuelve. Por el mensaje, parece que la rutina de activación busca
la carta en la mano en lugar de en el territorio.

Conviene comprobar si la acción se descuenta igualmente: en nuestra partida el
contador quedó descuadrado —sobró una acción al final del turno— y esta es la
causa más probable.

### 1.3 Los vínculos de logistrón no aplican la excepción de distancia

El §4.3 del manual establece que los vínculos que involucran logistrones cuestan
siempre 1 acción **con independencia de la distancia**, y añade que esa excepción
prevalece sobre cualquier otra.

Al intentar vincular el Conmutador (logistrón, L1 m6) con el Señor de la Guerra
(L1 m2), el juego lo rechaza por distancia no válida. Está aplicando la tabla
general de distancias en lugar de la excepción.

Nota: no pudimos descartar del todo una segunda hipótesis —que el rechazo se deba
a la carta interpuesta en el m4—, pero el manual no contempla bloqueo por
interposición en ningún punto. Si esa regla existe y es intencionada, no está
documentada.

### 1.4 La habilidad de duplicación del Alcalde de Guerra nunca se ofrece

El Alcalde de Guerra reza «Al atacar, gasta 1 acción extra para duplicar s…».
Reservamos deliberadamente una acción en dos turnos distintos para usarla, y el
flujo de ataque nunca la ofreció. Tampoco aparece botón de activación al
seleccionar la carta en el tablero durante la fase de acciones.

Sin poder leer el texto completo, no sabemos si falta un disparador o si la
habilidad exige una condición no cumplida.

---

## 2. Problemas de interfaz

Ninguno de estos puntos es una carencia: la información existe y funciona. El
problema es de *localización* —está toda en la esquina inferior derecha, fuera del
recorrido visual natural de un jugador nuevo, que mira al centro del tablero y a
la barra superior de botones.

**Los textos de habilidad aparecen truncados en las fichas de mano.** Al clicar la
carta se despliegan legibles abajo a la derecha, pero nada en la ficha truncada
sugiere que clicarla sirva para eso. Un *tooltip* al pasar el cursor, o unos
puntos suspensivos con aspecto de enlace, resolverían la duda sin cambiar la
arquitectura actual.

**El objetivo de ataque cuesta encontrarlo.** Al pulsar «Atacar →», la selección
de objetivo aparece también abajo a la derecha, mientras que el botón que la
dispara está arriba del todo. Esa distancia entre la acción y su respuesta es lo
que bloquea: uno pulsa, no ve cambiar nada donde está mirando y da por hecho que
no ha funcionado. Bastaría con destacar el panel al abrirse —un borde, una
animación breve— o con acercar la selección al punto donde se pulsa.

**No hay retroalimentación del daño.** Tras resolver un ataque, la única forma de
saber cuánto entró es comparar el contador de sellos antes y después. Un registro
de combate, aunque sea de una línea, ahorraría mucha incertidumbre.

---

## 3. Ambigüedades del reglamento

Dos puntos que ninguna implementación puede resolver sin una decisión de diseño
previa.

### 3.1 La purga de la fase de salida (§5.5)

El texto dice: «Cada jugador debe remover de su territorio cualquier **nodo
enemigo** que no tenga al menos un vínculo directo».

Literalmente, la purga solo alcanza a nodos enemigos —es decir, a espías
infiltrados—. Pero la lectura habitual es que toda carta aislada muere, y ahí
entra en conflicto con la palabra clave **Autofobia** (§9.2), que hace
exactamente eso a cartas concretas. Si todas las cartas aisladas murieran,
Autofobia no tendría ninguna función.

Sospechamos que la redacción correcta es la literal y que Autofobia es la
excepción que sí mata a las propias. Convendría reformularlo, porque cambia
por completo cuándo es seguro dejar una carta suelta en el tablero.

### 3.2 Vínculos entre un escuadrón y una carta suelta

El §4.5 dice que los nodos de un escuadrón no pueden vincularse directamente con
nodos de otro escuadrón. No queda claro qué ocurre al vincular un nodo de un
escuadrón con una carta que no pertenece a ninguno: ¿la absorbe el escuadrón,
altera su forma poligonal, o queda colgando sin integrarse?

---

## 4. Lo que sí funcionó

Merece decirse, porque es lo esencial del juego:

- La regla de adyacencia horizontal se aplica correctamente y obliga a pensar la
  colocación desde el primer turno.
- El cálculo de daño del triángulo fue exacto: 2 de base + 1 del Señor de la
  Guerra + 4 de daño adicional = 7 sellos, verificado contra el contador.
- La distinción visual entre vínculos normales (amarillos) y de logistrón
  (turquesa discontinuo) es clara y se agradece.
- El bucle de aprendizaje funciona: la progresión de daño 3 → 7 en dos turnos deja
  ver de inmediato por qué compensa cerrar polígonos, que es justo lo que el juego
  quiere enseñar.
