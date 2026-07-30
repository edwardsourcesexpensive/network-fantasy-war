# Network Fantasy War — Manual de Reglas

*Un juego de **The Eduardos Company**.*

---

## 1. Concepto general

Network Fantasy War es un Trading Card Game para dos jugadores. Cada jugador comanda una civilización organizada como una **red**: las cartas son **nodos** y las conexiones entre ellas son **vínculos**. Las propiedades emergentes de la red —escuadrones, potenciamiento mutuo, coordinación— son más importantes que las estadísticas individuales de cada carta.

El objetivo es destruir el **grimorio** del rival, protegido por 30 sellos. Gana el jugador que rompe el último sello.

---

## 2. Componentes

- **Mazo principal**: 50 cartas por jugador (más sideboard opcional de 10).
- **Carta de Grimorio**: 1 por jugador, con marcador de 30 sellos.
- **Playmat**: 1 por jugador. Territorio con 3 layers × 15 meridianos.
- **Varillas de vínculo**: ~40 por jugador. 3 tamaños: cortas, medianas, largas.
- **Contadores de colores**: ~20 por jugador. Para marcar estados, sellos, modificadores.
- **Dado de 6 caras**: 1 compartido. Uso acotado.

---

## 3. El escenario de guerra

### 3.1 Territorios

Dos playmats enfrentados, uno por jugador, unidos por el borde. La línea de contacto es la **frontera**. Cada playmat representa el territorio de un jugador.

### 3.2 Estructura del territorio

Cada territorio se organiza en una cuadrícula de **3 layers** (filas) × **15 meridianos** (columnas):

- **Layer 1 (L1)** — Retaguardia. Más cercana al jugador.
- **Layer 2 (L2)** — Vanguardia. Zona intermedia.
- **Layer 3 (L3)** — Línea de fuego. Más cercana a la frontera y al enemigo.
- **Frontera** — La línea entre ambos territorios. Ambos jugadores pueden ubicar cartas aquí (solo espías y ciertas cartas especiales).

El territorio puede extenderse horizontalmente añadiendo meridianos si la red crece más allá de 15 columnas.

```
        JUGADOR ROJO (arriba)
   L3  [ ][ ][ ][ ]...[ ]  ← más cerca de la frontera
   L2  [ ][ ][ ][ ]...[ ]
   L1  [ ][ ][ ][ ]...[ ]  ← más cerca del jugador
        === FRONTERA ===
   L1  [ ][ ][ ][ ]...[ ]
   L2  [ ][ ][ ][ ]...[ ]
   L3  [ ][ ][ ][ ]...[ ]
        JUGADOR AZUL (abajo)
```

En los playmats, el L3 de cada jugador está junto a la frontera y enfrentado al L3 enemigo.

### 3.3 Ubicación de cartas

**Regla fundamental**: No puede ubicarse una carta en una celda horizontalmente adyacente a otra celda ocupada (en el mismo layer). Esto no aplica a la frontera.

Ejemplo: si hay una carta en (L2, m5), las celdas (L2, m4) y (L2, m6) quedan bloqueadas para nuevas cartas en L2.

**Regla de entrada**: Toda carta debe entrar al campo de batalla en **L1** (retaguardia). No puede jugarse directamente en L2 o L3, con excepciones:

- **Vanguardia**: habilidad pasiva que permite entrar directamente en **L2**.
- **Línea de fuego**: habilidad pasiva que permite entrar directamente en **L3** (también permite L2).
- **Espías**: entran directamente en la frontera.

Aproximadamente el 30% de las cartas con acceso a capas superiores poseen Vanguardia o Línea de fuego. Las cartas sin estas habilidades deben ascender para alcanzar L2 o L3.

**Movimiento horizontal**: En cualquier momento de tu turno, puedes desplazar cartas horizontalmente sin costo en acciones. Sin embargo, si un movimiento horizontal deja dos cartas vinculadas a una distancia mayor que la permitida por su varilla de vínculo, ese vínculo se disuelve inmediatamente.

**Movimiento vertical**: Solo mediante la acción de **ascenso**.

---

## 4. La red: nodos, vínculos y escuadrones

### 4.1 Nodos

Toda carta en el territorio de guerra es un **nodo** de la red.

### 4.2 Vínculos

Dos nodos pueden conectarse mediante una **varilla de vínculo**. Una varilla colocada entre dos cartas representa un **vínculo directo**. Si dos cartas no están conectadas directamente entre sí pero comparten una carta vecina, tienen un **vínculo indirecto** (cuenta como distancia de red = 2).

Cada carta tiene una **capacidad de vínculos (V)**: el número máximo de vínculos directos que puede sostener. Este valor está impreso en la carta. Una carta no puede exceder su capacidad V. Si un vínculo se disuelve, la carta recupera ese espacio.

### 4.3 Distancia espacial y costo de vínculos

La distancia entre dos cartas determina el costo en acciones para vincularlas:

**Próxima (corta)** — 0 filas × 2 columnas, o 1 fila × 0-1 columna. Cuesta **1 acción**.

**Media** — 0 filas × 3 columnas, o 1 fila × 2 columnas. Cuesta **1 acción** si las cartas son del mismo color (color impreso), o **2 acciones** si son de distinto color.

**Distante (larga)** — 2 filas × 0-1 columna, o 1 fila × 3 columnas. Cuesta **3 acciones**.

**Inválida** — Cualquier distancia mayor. No se puede vincular.

Excepciones:
- Vínculos que involucran **logistrones**: siempre 1 acción, independientemente de la distancia. Esta excepción prevalece sobre cualquier otra.
- Vínculos entre la **frontera** y cualquier carta en **L3**: 4 acciones (salvo que intervenga un logistrón).

Vínculos entre territorios: Todo vínculo que cruce entre territorios de jugadores distintos debe obligatoriamente involucrar al menos un nodo situado en la **frontera** (espía o carta especial con capacidad de frontera). No existen vínculos directos entre L3 propio y L3 enemigo que salteen la frontera.

### 4.4 Escuadrones

Varios nodos conectados entre sí forman un **escuadrón**. Los escuadrones se clasifican por su forma geométrica:

- **Línea**: 2 nodos, 1 vínculo directo. No es un polígono cerrado — toda carta puede formar parte de una Línea salvo indicación contraria en su texto.
- **Triángulo**: 3 nodos, 3 vínculos (polígono cerrado).
- **Cuadrilátero básico**: 4 nodos, 4 vínculos (ciclo cerrado).
- **Cuadrilátero ampliado**: 4 nodos perimetrales + N nodos internos. Si N=0, es idéntico al básico.
- **Pentágono básico**: 5 nodos, 5 vínculos (ciclo cerrado).
- **Pentágono ampliado**: 5 nodos perimetrales + N nodos internos.

El Pentágono es el polígono máximo reconocido. Cualquier ciclo cerrado de 6 o más nodos debe dividirse en dos o más escuadrones conectados por un logistrón. Si no es posible dividirlo, el conjunto no forma un escuadrón válido y no puede atacar como unidad.

Un escuadrón es "ampliado" cuando, además del polígono perimetral cerrado, contiene al menos un nodo en su interior conectado a tres o más nodos del perímetro. El interior triangulado otorga poder adicional (+X en cuadriláteros, +Y en pentágonos).

**Regla de pertenencia exclusiva**: Cada nodo pertenece a **un único escuadrón por turno**, elegido por su controlador al inicio de la Fase de Ataque. Dicha asignación debe respetar la conectividad real de vínculos.

**Regla**: Las cartas no atacan solas. Solo los escuadrones pueden declarar ataques.

### 4.5 Logistrones y conexión entre escuadrones

Los nodos de un escuadrón no pueden establecer vínculos directos con nodos de otro escuadrón. Para conectar escuadrones entre sí, se requiere un **logistrón**: una unidad especial que actúa como puente.

- Un logistrón puede vincularse con nodos de distintos escuadrones.
- Los logistrones **no forman parte de ningún polígono** (no cuentan para la forma del escuadrón).
- Sin embargo, los logistrones **sí son nodos de la red** y cuentan para la distancia de red entre escuadrones.

---

## 5. Estructura del turno

Cada turno se divide en cuatro fases:

### 5.1 Fase de Entrada

1. **Habilidades de inicio**: Se activan todas las habilidades que digan "Al comienzo del turno..." en el orden que el dueño del turno elija. Luego, el rival activa las suyas que digan "Al comienzo del turno de tu oponente...".
2. **Robar**: El jugador activo roba 2 cartas de su reserva.

### 5.2 Fase de Acciones (4 acciones)

El jugador dispone de **4 acciones** por turno, que puede gastar en cualquier combinación de:

- **Jugar cartas** (1 acción por carta): Colocar una carta de la mano en el territorio. Por defecto, toda carta entra en L1, salvo que posea Vanguardia (entra en L2), Línea de fuego (entra en L3), o sea un Espía (entra en la frontera).
- **Ascender nodos** (ver §5.3).
- **Establecer vínculos** (ver §4.3).
- **Activar habilidades** con coste [N]: cuentan como N acciones.

Las habilidades con la forma "Durante tu turno..." no consumen acciones. Las habilidades con ícono [N] consumen N acciones.

### 5.3 Ascensos

Mover un nodo a un layer superior. Solo puede ascenderse a capas listadas en allowed_layers de la carta. Una carta con L1, L2 puede ascender de L1 a L2 pero no de L2 a L3.

- L1 → L2: **1 acción**.
- L2 → L3: **2 acciones**.
- Infiltrar espía en territorio enemigo: **1 acción** (se considera ascenso).

### 5.4 Fase de Ataque

Ver §6 (Sistema de combate).

### 5.5 Fase de Salida

1. **Purgar nodos aislados**: Cada jugador debe remover de su territorio cualquier nodo enemigo que no tenga al menos un vínculo directo con otro nodo (aliado o enemigo). Los nodos removidos van a la pila de descartes de su dueño.
2. **Habilidades de cierre**: Activar todas las habilidades de "Al final del turno...". El dueño del turno resuelve primero las suyas, luego el rival. Incluye **Autofobia**: si una carta con Autofobia no tiene ningún vínculo directo tras la purga, va a la pila de descartes.
3. **Descartar**: El jugador activo descarta cartas de su mano hasta quedarse con exactamente 5 cartas. Por cada carta descartada de esta manera, el dueño del turno **pierde 1 sello** de su propio grimorio.
4. **Efectos de escuadrones al final del turno**: Se resuelven en orden:
   - Escuadrones de Sellado: +10 sellos al grimorio por cada uno.
   - Escuadrones de Sabotaje: deshacer hasta 2 vínculos cortos en la red enemiga por escuadrón.
   - Escuadrones de Monstruos: remover 1 nodo enemigo cuyo Grado (G) sea menor que el ataque del escuadrón, por escuadrón.

---

## 6. Sistema de combate

### 6.1 Declaración de ataque

El dueño del turno puede declarar ataques con **cada uno de sus escuadrones**, uno por uno. Por cada escuadrón atacante, elige un objetivo:

- **Atacar el grimorio**: el daño se aplica a los sellos protectores del grimorio enemigo.
- **Atacar un nodo**: el daño se aplica a los puntos de vida (HP) de una carta enemiga. Si el HP llega a 0, la carta es destruida y va a la pila de descartes de su dueño.

Los ataques se resuelven secuencialmente, en el orden que el atacante decida. El defensor puede elegir un escuadrón defensor distinto para cada ataque. Un mismo escuadrón no puede atacar más de una vez por turno.

### 6.2 Cálculo del daño de ataque

El daño total del escuadrón atacante se calcula así:

DAÑO = DAÑO_BASE + POTENCIAMIENTO + DAÑO_EXTRA

1. **Daño base**: según el tipo de escuadrón (ver §7).
2. **Potenciamiento**: suma de las bonificaciones de todos los escuadrones aliados conectados al escuadrón atacante a través de la red. El potenciamiento decae con la distancia de red.
3. **Daño extra**: suma de los modificadores de daño (+D) de todas las cartas que componen el escuadrón atacante, más bonificaciones por habilidades activas.

### 6.3 Defensa

El jugador defensor puede elegir **un escuadrón defensor** para bloquear el ataque. Si no elige ninguno, el daño se aplica íntegro al objetivo.

Si elige un escuadrón defensor:

DAÑO_NETO = DAÑO_ATACANTE - DEFENSA_ESCUADRÓN

Donde DEFENSA_ESCUADRÓN se calcula como:

DEFENSA = POTENCIAMIENTO_DEFENSIVO + ARMADURA + BONUS_DEFENSA

- **Potenciamiento defensivo**: análogo al ofensivo, usando bonificaciones defensivas de escuadrones conectados. Cada escuadrón conectado aporta +1 a la defensa.
- **Armadura**: bonus por habilidades de color/facción (ej: escuadrones festivos tienen +2 de armadura en sus vínculos).
- **Bonus de defensa**: por habilidades de carta (ej: Guardaespaldas).

Si DAÑO_NETO > 0, ese valor se aplica al objetivo. Si DAÑO_NETO <= 0, el ataque es completamente absorbido.

**Regla de Guardaespaldas**: Cuando una carta con Guardaespaldas es atacada, su controlador puede redirigir el daño neto a cualquier nodo vinculado directamente a ella.

### 6.4 Aplicación del daño

- **Contra el grimorio**: cada punto de daño neto rompe 1 sello. El grimorio empieza con 30 sellos.
- **Contra un nodo**: cada punto de daño neto reduce el HP del nodo en 1. Si el HP llega a 0, el nodo es destruido. Todos sus vínculos se disuelven.

---

## 7. Tabla de Daño y Potenciamiento

**Línea** — Fuerza de ataque: **1**. Potenciamiento a vecinos: **+1**. Alcance: distancia de red 2.

**Triángulo** — Fuerza de ataque: **2**. Potenciamiento a vecinos: **+3**. Alcance: distancia de red 2.

**Cuadrilátero básico** — Fuerza de ataque: **3**. Potenciamiento a vecinos: **+5**. Alcance: distancia de red 2.

**Cuadrilátero ampliado** — Fuerza de ataque: **3 + X**. Potenciamiento a vecinos: **5 + X**. Alcance: distancia de red 2. Donde X = número de nodos internos.

**Pentágono básico** — Fuerza de ataque: **4**. Potenciamiento a vecinos: **+7**. Alcance: **ilimitado**.

**Pentágono ampliado** — Fuerza de ataque: **4 + 2Y**. Potenciamiento a vecinos: **7 + 2Y**. Alcance: **ilimitado**. Donde Y = número de nodos internos.

### Cómo funciona el potenciamiento

Cuando el escuadrón A ataca, recibe el potenciamiento de todo escuadrón B tal que:
- B está conectado a A a través de la red. Toda conexión entre escuadrones distintos requiere al menos un logistrón como puente.
- La **distancia de red** entre A y B (número mínimo de vínculos que los separan) es menor o igual al alcance de potenciamiento de B.

El potenciamiento **no es simétrico**: un pentágono potencia con +7 a cualquier escuadrón conectado (alcance ilimitado), pero un triángulo solo potencia con +3 a escuadrones a distancia de red 2.

**Múltiples fuentes**: El potenciamiento se acumula. Si un escuadrón está conectado a tres triángulos a distancia de red 2 cada uno, recibe +9 de potenciamiento total.

**Distancia de red 1**: solo existe dentro de un mismo escuadrón (nodos directamente vinculados entre sí). Dado que toda conexión entre escuadrones distintos requiere al menos un logistrón como puente —lo que introduce distancia mínima 2—, ningún efecto con alcance 1 puede alcanzar a otro escuadrón.

---

## 8. Colores y facciones

El juego tiene **12 colores** de carta. Cada color representa un segmento de la civilización mágica con un rol mecánico específico.

Las facciones principales:
- **Selladores** (blanco) — Defensa de grimorio.
- **Guerreros** (rojo) — Ofensiva.
- **Políticos** (naranja) — Gestión de red.
- **Saboteadores** (negro) — Destrucción de vínculos.
- **Alquimistas** (púrpura) — Versatilidad de color.
- **Militares** (azul) — Ascensos.
- **Festivos** (verde) — Armadura de vínculos.
- **Monstruos** (gris) — Destrucción de nodos.
- **Sabios** (amarillo) — Robo de cartas.
- **Naturaleza** (marrón) — Fortalecimiento.

Además, dos tipos especiales:
- **Logistrones** (plateado) — Conectan escuadrones entre sí. No forman polígonos.
- **Espías** (dorado) — Infiltración en territorio enemigo.

### 8.1 Color de un escuadrón

Cuando más de la mitad de las cartas de un escuadrón comparten un mismo color, el escuadrón es **de ese color**. Si ningún color alcanza la mayoría, el escuadrón es **incoloro** y no se beneficia de las habilidades de color.

### 8.2 Habilidades de color vs. color de carta

Cada carta tiene un color propio, pero sus **habilidades de color** pueden ser de un color distinto. Por ejemplo, un Guerrero (rojo) puede tener una habilidad de color Azul que solo se active si forma parte de un escuadrón azul.

---

## 9. Habilidades

### 9.1 Tipos de habilidades

Las habilidades se clasifican en tres tipos:

- **Habilidad de color**: Se activa si la carta forma parte de un escuadrón del color indicado.
- **Habilidad de formación**: Se activa si la carta forma parte de un escuadrón con la forma poligonal indicada.
- **Habilidad general**: Se activa mientras la carta esté en el territorio de guerra (salvo que indique otra zona).

Una habilidad de formación puede estar anidada dentro de una habilidad de color. Por ejemplo: "[Azul][Pentágono]: efecto" significa que se requieren ambas condiciones.

### 9.2 Keywords (habilidades con nombre propio)

- **Caudillismo**: Al ser promovido a L3, establece automáticamente 1 vínculo con un nodo en L2 (sin costo de acción). Si no hay objetivo válido, no ocurre nada.
- **Guardaespaldas**: Cuando esta carta es atacada, su controlador puede redirigir el daño neto a un nodo con vínculo directo a ella.
- **Vanguardia**: Esta carta entra en juego directamente en L2.
- **Línea de fuego**: Esta carta entra en juego directamente en L3.
- **Sigilo**: Esta carta no puede ser blanco de ataques enemigos.
- **Autofobia**: Al final del turno, si esta carta no tiene ningún vínculo directo, va a la pila de descartes.
- **Reticencia (a colores X, Y, Z)**: Esta carta no puede establecer vínculos con nodos de los colores indicados.

### 9.3 Efectos de facción por escuadrón

- **Selladores**: +10 sellos al grimorio por escuadrón. Al final del turno.
- **Guerreros**: Daño base +1 por cada nodo del escuadrón en L2 o L3. Al atacar.
- **Políticos**: Intercambiar las posiciones de 2 cartas propias en cualquier parte del propio territorio (respetando reglas de adyacencia). Al inicio del turno.
- **Saboteadores**: Deshacer hasta 2 vínculos cortos en red enemiga por escuadrón. Al final del turno.
- **Alquimistas**: En un escuadrón con al menos un Alquimista, cada carta del escuadrón activa sus habilidades de color como si fuera de su propio color impreso. Efecto permanente.
- **Militares**: Ascender 1 unidad sin costo por escuadrón. Al inicio del turno.
- **Festivos**: +2 de armadura a los vínculos del escuadrón. Efecto permanente.
- **Monstruos**: Remover 1 nodo enemigo cuyo Grado (G) sea menor que el ataque del escuadrón, por escuadrón. Al final del turno.
- **Sabios**: +1 carta extra en el paso de robar por escuadrón. Al robar.
- **Naturaleza**: Las unidades del escuadrón aportan +1 al daño de ataque y +1 al potenciamiento del escuadrón. Efecto permanente.

---

## 10. Espías

Los espías son unidades de infiltración con reglas únicas:

1. **Despliegue**: Los espías se juegan directamente en la **frontera** (no en el territorio propio). Jugar un espía cuenta como 1 acción.
2. **Movimiento**: Desde la frontera, un espía puede infiltrarse en territorio enemigo. Esto cuenta como un ascenso (1 acción). Una vez en territorio enemigo, **no puede regresar** a territorio propio ni a la frontera.
3. **Vínculos**: Los espías pueden vincularse con unidades enemigas y con otros espías. También pueden mantener vínculos con unidades propias únicamente mientras permanezcan en la frontera. Estos vínculos se disuelven automáticamente cuando el espía se infiltra en territorio enemigo.
4. **Polígonos**: Los espías siempre forman parte de los polígonos del jugador en cuyo territorio se encuentran, nunca de los del dueño del espía. El dueño del espía **parasita** ese escuadrón y obtiene las siguientes ventajas:
   - **Sabotaje encubierto**: Una vez por turno, durante tu Fase de Acciones, puedes gastar 1 acción por cada espía tuyo infiltrado para deshacer un vínculo del escuadrón enemigo que lo contiene.
   - **Inteligencia**: Cuando el escuadrón que contiene a tu espía declara un ataque, miras 1 carta al azar de la mano del jugador atacante.
   - **Contraespionaje**: Si un espía enemigo está en tu territorio, puedes declarar un ataque de cualquier escuadrón propio contra ese espía directamente (ignorando Sigilo si lo tuviera).

---

## 11. El grimorio

- Cada jugador comienza con **30 sellos** protegiendo su grimorio.
- Los sellos se representan con contadores sobre la Carta de Grimorio.
- Cada punto de daño neto que atraviesa la defensa rompe 1 sello.
- Cuando el último sello es destruido, el grimorio colapsa y ese jugador pierde la partida.
- Los escuadrones de Selladores añaden 10 sellos al grimorio al final del turno.

---

## 12. La reserva (mazo) y la mano

- Mazo principal: **50 cartas**.
- Mano inicial: **5 cartas**.
- Robo por turno: **2 cartas** (+1 extra por cada escuadrón de Sabios).
- Límite de mano al final del turno: **5 cartas**.
- **Descarte forzoso**: Por cada carta descartada para cumplir el límite de mano, el jugador pierde 1 sello de su propio grimorio.
- **Daño de fatiga**: Si la reserva se agota y debes robar, por cada carta que no puedas robar pierdes inmediatamente 1 sello de tu grimorio.

### 12.1 Pila de descartes (cementerio)

Las cartas destruidas, descartadas o removidas van a la pila de descartes de su dueño. Algunas cartas pueden tener habilidades que interactúan con la pila de descartes.

---

## 13. Anatomía de una carta

Cada carta contiene los siguientes campos:

- **Nombre**: Identificador único de la carta.
- **Indicador de color**: Círculo o icono con el color de la carta (puede ser distinto a sus habilidades de color).
- **Copias máximas (C's)**: Número máximo de copias de esta carta permitidas en el mazo (1, 3 o 5).
- **HP (Puntos de Vida)**: Resistencia del nodo. Al llegar a 0, es destruido.
- **D (Daño adicional)**: Daño extra que esta carta aporta al escuadrón cuando ataca.
- **V (Capacidad de vínculos)**: Número máximo de vínculos directos que este nodo puede sostener. Típicamente 2-3; cartas raras 4-5. Logistrones suelen tener V=5+.
- **G (Grado)**: Nivel jerárquico de la carta. Por defecto, el Grado es igual al máximo layer alcanzable según la carta, a menos que su texto indique explícitamente un Grado distinto. Así, L1 = G1, L2 = G2, L3 = G3. Logistrones y espías tienen G=3. Se usa en mecánicas que comparan poder relativo entre cartas (ej: efecto de Monstruos).
- **Restricciones de layer**: Capas en las que puede ubicarse (L1, L2, L3).
- **Restricciones de polígono**: Tipos de escuadrón que puede integrar (Triángulo, Cuadrilátero, Pentágono).
- **Habilidades de color**: Efectos condicionados al color del escuadrón.
- **Habilidades de formación**: Efectos condicionados a la forma poligonal del escuadrón.
- **Habilidades generales**: Efectos incondicionales o con condiciones de timing.

---

## 14. El dado

El dado de 6 caras se usa exclusivamente para resolver empates de prioridad y ciertos efectos de carta que expliciten una tirada. No se usa para el combate ni para el daño.

Situaciones que requieren dado:
- Dos habilidades con timing idéntico que dependen del orden de resolución y ningún jugador cede la prioridad.
- Efectos de carta que digan "tira un dado".

---

## 15. Setup de la partida

1. Cada jugador coloca su playmat frente a sí, con la frontera en contacto con el playmat rival.
2. Cada jugador sitúa su Carta de Grimorio junto a su playmat, con 30 contadores de sellos.
3. Cada jugador baraja su mazo de 50 cartas y roba 5 cartas como mano inicial.
4. Se decide quién juega primero (dado o acuerdo mutuo).
5. El primer jugador comienza su Fase de Entrada.

**Regla de mulligan**: El jugador que comienza puede hacer mulligan: barajar su mano inicial en la reserva, robar 5 nuevas cartas y perder 1 sello de su grimorio. Luego, el otro jugador puede hacer lo mismo. Se repite alternadamente hasta que ambos jugadores se planten consecutivamente. Cada mulligan cuesta 1 sello adicional (el primero: 1 sello, el segundo: 2 sellos, etc.). No hay límite de mulligans.

---

## 16. Glosario

- **Nodo**: Una carta en el territorio de guerra.
- **Vínculo directo**: Conexión física (varilla) entre dos nodos.
- **Vínculo indirecto**: Dos nodos que no están vinculados directamente pero comparten al menos un nodo vecino en común. Distancia de red = 2.
- **Distancia de red**: Número mínimo de vínculos entre dos nodos.
- **Escuadrón**: Conjunto de 2 o más nodos conectados que conforman una unidad táctica, ya sea en línea abierta o polígono cerrado.
- **Logistrón**: Unidad especial que conecta escuadrones entre sí.
- **Potenciamiento**: Bonificación que un escuadrón otorga a otros escuadrones conectados.
- **Grimorio**: Fuente de poder de la civilización, protegida por 30 sellos.
- **Sello**: Punto de protección del grimorio. 1 de daño = 1 sello roto.
- **Frontera**: Línea divisoria entre los dos territorios.
- **Ascenso**: Movimiento de un nodo a un layer superior.
