# Network Fantasy War — Manual de Reglas (v1.0)

> **Estado**: Borrador formalizado a partir del documento de diseño original.
> Los contenidos nuevos (no presentes en el diseño original) se marcan con `[NUEVO]`.
> Las decisiones de diseño pendientes de validación se marcan con `[PENDIENTE]`.

---

## 1. Concepto general

Network Fantasy War es un Trading Card Game para dos jugadores. Cada jugador comanda una civilización organizada como una **red**: las cartas son **nodos** y las conexiones entre ellas son **vínculos**. Las propiedades emergentes de la red —escuadrones, potenciamiento mutuo, coordinación— son más importantes que las estadísticas individuales de cada carta.

El objetivo es destruir el **grimorio** del rival, protegido por 30 sellos. Gana el jugador que rompe el último sello.

---

## 2. Componentes

| Componente | Cantidad | Notas |
|---|---|---|
| Mazo principal | 50 cartas por jugador | Más sideboard opcional de 10 |
| Carta de Grimorio | 1 por jugador | Marcador de sellos (30) |
| Playmat | 1 por jugador | Territorio con 3 layers × 15 meridianos |
| Varillas de vínculo | ~40 por jugador | 3 tamaños: cortas, medianas, largas |
| Contadores de colores | ~20 por jugador | Para marcar estados, sellos, modificadores |
| Dado de 6 caras | 1 compartido | Uso acotado (ver §14) |

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

*Nota: En los playmats, el L3 de cada jugador está junto a la frontera y enfrentado al L3 enemigo.*

### 3.3 Ubicación de cartas

**Regla fundamental**: No puede ubicarse una carta en una celda horizontalmente adyacente a otra celda ocupada (en el mismo layer). Esto no aplica a la frontera.

> *Ejemplo*: si hay una carta en (L2, m5), las celdas (L2, m4) y (L2, m6) quedan bloqueadas para nuevas cartas en L2.

**Regla de entrada**: Toda carta debe entrar al campo de batalla en **L1** (retaguardia). No puede jugarse directamente en L2 o L3, con dos excepciones:

- **Vanguardia**: habilidad pasiva que permite entrar directamente en **L2**.
- **Línea de fuego**: habilidad pasiva que permite entrar directamente en **L3** (también permite L2).
- **Espías**: entran directamente en la frontera (ver §11).

Aproximadamente el 30% de las cartas con acceso a capas superiores poseen Vanguardia o Línea de fuego. Las cartas sin estas habilidades deben ascender para alcanzar L2 o L3 (ver §5.3).

**Movimiento horizontal**: En cualquier momento de tu turno, puedes desplazar cartas horizontalmente sin costo en acciones. Sin embargo, si un movimiento horizontal deja dos cartas vinculadas a una distancia mayor que la permitida por su varilla de vínculo, ese vínculo se disuelve inmediatamente.

**Movimiento vertical**: Solo mediante la acción de **ascenso** (ver §5.3).

---

## 4. La red: nodos, vínculos y escuadrones

### 4.1 Nodos
Toda carta en el territorio de guerra es un **nodo** de la red.

### 4.2 Vínculos
Dos nodos pueden conectarse mediante una **varilla de vínculo**. Una varilla colocada entre dos cartas representa un **vínculo directo**. Si dos cartas no están conectadas directamente entre sí pero comparten una carta vecina, tienen un **vínculo indirecto** (cuenta como distancia de red = 2).

Cada carta tiene una **capacidad de vínculos (V)**: el número máximo de vínculos directos que puede sostener. Este valor está impreso en la carta (ver §13). Una carta no puede exceder su capacidad V. Si un vínculo se disuelve, la carta recupera ese espacio.

### 4.3 Distancia espacial y costo de vínculos

La distancia entre dos cartas determina el costo en acciones para vincularlas:

| Tipo | Distancia | Costo base |
|---|---|---|
| **Próxima (corta)** | 0 filas × 2 columnas, o 1 fila × 0-1 columna | 1 acción |
| **Media** | 0 filas × 3 columnas, o 1 fila × 2 columnas | 1 acción (mismo color) / 2 acciones (distinto color) |
| **Distante (larga)** | 2 filas × 0-1 columna, o 1 fila × 3 columnas | 3 acciones |
| **Inválida** | Cualquier distancia mayor | No se puede vincular |

**Excepciones**:
- Vínculos que involucran **logistrones**: siempre 1 acción, independientemente de la distancia. **Esta excepción prevalece sobre cualquier otra**: si un vínculo involucra un logistrón y además conecta frontera con L3, cuesta 1 acción (no 4).
- Vínculos entre la **frontera** y cualquier carta en **L3**: 4 acciones (salvo que intervenga un logistrón).

> **Aclaración sobre color en vínculos `[NUEVO]`**: La distinción "mismo color" / "distinto color" en la fila de distancia Media se refiere al **indicador de color impreso** de cada carta (el círculo/icono de color en la anatomía, §13), no a sus habilidades de color (que pueden diferir del color propio, §8.4).

> **Vínculos entre territorios `[NUEVO]`**: Todo vínculo que cruce entre territorios de jugadores distintos debe obligatoriamente involucrar al menos un nodo situado en la **frontera** (espía o carta especial con capacidad de frontera). No existen vínculos directos entre L3 propio y L3 enemigo que salteen la frontera.

### 4.4 Escuadrones

Varios nodos conectados entre sí forman un **escuadrón**. Los escuadrones se clasifican por su forma geométrica:

| Tipo | Nodos mínimos | Vínculos requeridos |
|---|---|---|
| **Línea** | 2 | 1 vínculo directo |
| **Triángulo** | 3 | 3 vínculos (polígono cerrado) |
| **Cuadrilátero básico** | 4 | 4 vínculos (ciclo cerrado) |
| **Cuadrilátero ampliado** | 4 perimetrales + N internos | 4 perimetrales + vínculos internos que triangulan el interior. Si N=0, es idéntico a un cuadrilátero básico. |
| **Pentágono básico** | 5 | 5 vínculos (ciclo cerrado) |
| **Pentágono ampliado** `[NUEVO]` | 5 perimetrales + N internos | 5 perimetrales + vínculos internos que triangulan el interior |

> **Nota sobre la Línea `[NUEVO]`**: La Línea (2 nodos, 1 vínculo) es un caso especial de escuadrón que no constituye un polígono cerrado. Por esta razón, **toda carta puede formar parte de una Línea** salvo indicación contraria en su texto. El campo "Restricciones de polígono" en la anatomía de carta (§13) solo lista Triángulo, Cuadrilátero y Pentágono porque la Línea no tiene restricción.

> **Polígono máximo `[NUEVO]`**: El **Pentágono es el polígono máximo reconocido** por las reglas. Cualquier ciclo cerrado de 6 o más nodos debe dividirse en dos o más escuadrones conectados por un logistrón. Si no es posible dividirlo, el conjunto permanece como un conjunto no clasificado: no forma un escuadrón válido y no puede atacar como unidad.

> **Definición `[NUEVO]`**: Un escuadrón es "ampliado" cuando, además del polígono perimetral cerrado, contiene al menos un nodo en su interior conectado a tres o más nodos del perímetro. El interior triangulado otorga poder adicional (+X en cuadriláteros, +Y en pentágonos). Estos modificadores se definen en la **Tabla de Potenciamiento** (§7).

**Regla de pertenencia exclusiva `[NUEVO]`**: Cada nodo pertenece a **un único escuadrón por turno**, elegido por su controlador al inicio de la Fase de Ataque. Dicha asignación debe respetar la conectividad real de vínculos: no pueden reutilizarse los mismos vínculos para justificar dos escuadrones distintos simultáneos.

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
1. **Habilidades de inicio**: Se activan todas las habilidades que digan *"Al comienzo del turno…"* en el orden que el dueño del turno elija. Luego, el rival activa las suyas que digan *"Al comienzo del turno de tu oponente…"*.
2. **Robar**: El jugador activo roba 2 cartas de su reserva.

### 5.2 Fase de Acciones (4 acciones)

El jugador dispone de **4 acciones** por turno, que puede gastar en cualquier combinación de:

- **Jugar cartas** (1 acción por carta): Colocar una carta de la mano en el territorio. **Por defecto, toda carta entra en L1** (ver §3.3, Regla de entrada), salvo que posea Vanguardia (entra en L2), Línea de fuego (entra en L3), o sea un Espía (entra en la frontera).
- **Ascender nodos** (ver §5.3).
- **Establecer vínculos** (ver §4.3).
- **Activar habilidades** con coste `[N]`: cuentan como N acciones.

Además, las habilidades con la forma *"Durante tu turno…"* no consumen acciones. Las habilidades con ícono `[N]` consumen N acciones.

### 5.3 Ascensos

Mover un nodo a un layer superior. **Solo puede ascenderse a capas listadas en `allowed_layers` de la carta**. Una carta con `L1,L2` puede ascender de L1 a L2 pero no de L2 a L3.

| Movimiento | Costo en acciones |
|---|---|
| L1 → L2 | 1 acción |
| L2 → L3 | 2 acciones |
| Infiltrar espía en territorio enemigo | 1 acción (se considera ascenso) |

### 5.4 Fase de Ataque

Ver §6 (Sistema de combate).

### 5.5 Fase de Salida

1. **Purgar nodos aislados** `[NUEVO]`: Cada jugador debe remover de su territorio cualquier nodo enemigo que no tenga al menos un vínculo directo con otro nodo (aliado o enemigo). Los nodos removidos van a la pila de descartes de su dueño.

> **Asimetría intencional `[NUEVO]`**: La purga es unilateral por diseño: solo afecta nodos enemigos aislados, no a los propios. Esto penaliza la infiltración fallida (espías enemigos que pierden sus vínculos), pero no castiga la desconexión accidental de cartas propias. Las cartas propias aisladas solo se ven afectadas si tienen la keyword **Autofobia** (ver §9.2).
2. **Habilidades de cierre**: Activar todas las habilidades de *"Al final del turno…"*. El dueño del turno resuelve primero las suyas, luego el rival. Esto incluye **Autofobia**: si una carta con Autofobia no tiene ningún vínculo directo en este momento (tras la purga), va a la pila de descartes.

> **Orden de resolución `[NUEVO]`**: Los pasos de la Fase de Salida se resuelven en el orden estricto listado. Cada paso usa el estado de la red **ya actualizado** tras el paso anterior. Esto implica que la Purga (paso 1) puede alterar la conectividad antes de que se evalúe Autofobia (paso 2).
3. **Descartar**: El jugador activo descarta cartas de su mano hasta quedarse con exactamente 5 cartas. `[NUEVO]` Por cada carta descartada de esta manera, el dueño del turno **pierde 1 sello** de su propio grimorio. Esto representa el costo de desprenderse de recursos mágicos no utilizados.
4. **Efectos de escuadrones al final del turno** `[NUEVO]`: Se resuelven en orden:
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

### 6.2 Cálculo del daño de ataque `[COMPLETADO con defensa]`

El daño total del escuadrón atacante se calcula así:

```
DAÑO = DAÑO_BASE + POTENCIAMIENTO + DAÑO_EXTRA
```

1. **Daño base**: según el tipo de escuadrón (ver Tabla de Daño, §7).
2. **Potenciamiento**: suma de las bonificaciones de todos los escuadrones aliados conectados al escuadrón atacante a través de la red. El potenciamiento decae con la distancia de red (ver §7).
3. **Daño extra**: suma de los modificadores de daño (+D) de todas las cartas que componen el escuadrón atacante, más bonificaciones por habilidades activas.

### 6.3 Defensa `[NUEVO]`

El jugador defensor puede elegir **un escuadrón defensor** para bloquear el ataque. Si no elige ninguno, el daño se aplica íntegro al objetivo.

Si elige un escuadrón defensor:

```
DAÑO_NETO = DAÑO_ATACANTE - DEFENSA_ESCUADRÓN
```

Donde `DEFENSA_ESCUADRÓN` se calcula como:

```
DEFENSA = POTENCIAMIENTO_DEFENSIVO + ARMADURA + BONUS_DEFENSA
```

- **Potenciamiento defensivo**: análogo al potenciamiento ofensivo, pero usando las bonificaciones defensivas de los escuadrones conectados. Cada escuadrón conectado aporta +1 a la defensa.
- **Armadura**: bonus por habilidades de color/facción (ej: escuadrones festivos tienen +2 de armadura en sus vínculos).
- **Bonus de defensa**: por habilidades de carta (ej: Guardaespaldas).

Si `DAÑO_NETO > 0`, ese valor se aplica al objetivo. Si `DAÑO_NETO <= 0`, el ataque es completamente absorbido.

> **Regla de Guardaespaldas**: Cuando una carta con Guardaespaldas es atacada, su controlador puede redirigir el daño neto a cualquier nodo vinculado directamente a ella.

### 6.4 Aplicación del daño

- **Contra el grimorio**: cada punto de daño neto rompe 1 sello. El grimorio empieza con 30 sellos.
- **Contra un nodo**: cada punto de daño neto reduce el HP del nodo en 1. Si el HP llega a 0, el nodo es destruido. Todos sus vínculos se disuelven.

---

## 7. Tabla de Daño y Potenciamiento

| Escuadrón | Fuerza de ataque | Potenciamiento a vecinos | Alcance del potenciamiento |
|---|---|---|---|
| **Línea** | 1 | +1 | Distancia de red 2 |
| **Triángulo** | 2 | +3 | Distancia de red 2 |
| **Cuadrilátero básico** | 3 | +5 | Distancia de red 2 |
| **Cuadrilátero ampliado** | 3 + X | 5 + X | Distancia de red 2 |
| **Pentágono básico** | 4 | +7 | Ilimitado |
| **Pentágono ampliado** | 4 + 2Y | 7 + 2Y | Ilimitado |

Donde `[NUEVO]`:
- **X** = número de nodos internos en el cuadrilátero ampliado.
- **Y** = número de nodos internos en el pentágono ampliado.

### 7.1 Cómo funciona el potenciamiento

Cuando el escuadrón A ataca, recibe el potenciamiento de todo escuadrón B tal que:
- B está conectado a A a través de la red. **Toda conexión entre escuadrones distintos requiere al menos un logistrón como puente.** Los vínculos indirectos entre escuadrones siempre atraviesan un logistrón.
- La **distancia de red** entre A y B (número mínimo de vínculos que los separan) es menor o igual al alcance de potenciamiento de B.

El potenciamiento **no es simétrico**: un pentágono potencia con +7 a cualquier escuadrón conectado (alcance ilimitado), pero un triángulo solo potencia con +3 a escuadrones a distancia de red 2.

**Múltiples fuentes**: El potenciamiento se acumula. Si un escuadrón está conectado a tres triángulos a distancia de red 2 cada uno, recibe +9 de potenciamiento total.

> **Nota sobre distancia de red 1**: La distancia de red 1 solo existe dentro de un mismo escuadrón (nodos directamente vinculados entre sí). Dado que toda conexión entre escuadrones distintos requiere al menos un logistrón como puente —lo que introduce distancia mínima 2—, ningún efecto de potenciamiento con alcance 1 puede alcanzar a otro escuadrón.

---

## 8. Colores y facciones `[REFORMULADO]`

El juego tiene **12 colores** de carta. Cada color representa un segmento de la civilización mágica con un rol mecánico específico.

### 8.1 Facciones principales

| # | Color | Rol mecánico |
|---|---|---|
| 1 | **Selladores** (blanco) | Defensa del grimorio: reparan y añaden sellos |
| 2 | **Guerreros** (rojo) | Ofensiva: alto daño de ataque, especialmente en L2/L3 |
| 3 | **Políticos** (naranja) | Gestión de red: intercambian posiciones de nodos |
| 4 | **Saboteadores** (negro) | Sabotaje: destruyen vínculos enemigos |
| 5 | **Alquimistas** (púrpura) | Versatilidad de color: activan todas las habilidades de color |
| 6 | **Militares** (azul) | Ascensos: promociones sin costo y ascensos extra |
| 7 | **Festivos** (verde) | Refuerzo de vínculos: armadura aumentada en sus escuadrones |
| 8 | **Monstruos** (gris) | Destrucción de nodos enemigos |
| 9 | **Sabios** (amarillo) | Ventaja de cartas: robo adicional |
| 10 | **Naturaleza** (marrón) `[REDISEÑADO]` | Fortalecimiento: sus unidades en escuadrón aportan +1 al daño de ataque y +1 al potenciamiento |

### 8.2 Unidades especiales (no son colores estándar)

| Tipo | Color en carta | Rol |
|---|---|---|
| **Logistrones** | Plateado | Conectan escuadrones entre sí. No forman polígonos. |
| **Espías** | Dorado | Infiltran territorio enemigo. Nacen en la frontera, no pueden volver. Solo forman polígonos enemigos. |

> **Nota sobre "Druidas"**: En el diseño original aparecía "Druidas" como una facción separada en los efectos de escuadrón. En esta versión, **Naturaleza** absorbe el concepto de druidas/herbolarios y su mecánica es: *"En los escuadrones de Naturaleza, las unidades aportan +1 de daño de ataque y +1 de daño de potenciación"*. Si se desea mantener "Druidas" como una sub-facción, sería una keyword, no un color independiente.

### 8.3 Color de un escuadrón

Cuando más de la mitad de las cartas de un escuadrón comparten un mismo color, el escuadrón es **de ese color**. Si ningún color alcanza la mayoría, el escuadrón es **incoloro** y no se beneficia de las habilidades de color.

### 8.4 Habilidades de color vs. color de carta

Cada carta tiene un color propio, pero sus **habilidades de color** pueden ser de un color distinto. Por ejemplo, un Guerrero (rojo) puede tener una habilidad de color Azul que solo se active si forma parte de un escuadrón azul.

---

## 9. Habilidades

### 9.1 Tipos de habilidades

| Tipo | Condición de activación |
|---|---|
| **Habilidad de color** | La carta forma parte de un escuadrón del color indicado |
| **Habilidad de formación** | La carta forma parte de un escuadrón con la forma poligonal indicada |
| **Habilidad general** | La carta está en el territorio de guerra (salvo que indique otra zona) |

Una habilidad de formación puede estar **anidada** dentro de una habilidad de color: *"[Azul][Pentágono]: efecto"* significa que se requiere **ambas** condiciones.

### 9.2 Keywords (habilidades con nombre propio)

| Keyword | Efecto |
|---|---|
| **Caudillismo** | Al ser promovido a L3, establece automáticamente 1 vínculo con un nodo en L2 (sin costo de acción). Si no hay objetivo válido, no ocurre nada. |
| **Guardaespaldas** | Cuando esta carta es atacada, su controlador puede redirigir el daño neto a un nodo con vínculo directo a ella. |
| **Vanguardia** | Esta carta entra en juego directamente en L2. |
| **Sigilo** | Esta carta no puede ser blanco de ataques enemigos. |
| **Autofobia** | Al final del turno, si esta carta no tiene ningún vínculo directo, va a la pila de descartes. |
| **Reticencia (a colores X, Y, Z)** | Esta carta no puede establecer vínculos con nodos de los colores indicados. |

### 9.3 Efectos de facción por escuadrón (resumen)

| Facción | Efecto | Timing |
|---|---|---|
| Selladores | +10 sellos al grimorio por escuadrón | Fin del turno |
| Guerreros | Daño base +1 por cada nodo del escuadrón en L2 o L3 | Al atacar |
| Políticos | Intercambiar las posiciones de 2 cartas propias ubicadas en cualquier parte del propio territorio (no necesariamente del escuadrón político), respetando las reglas de adyacencia (§3.3) en las posiciones resultantes | Inicio del turno |
| Saboteadores | Deshacer hasta 2 vínculos cortos en red enemiga por escuadrón | Fin del turno |
| Alquimistas | En un escuadrón que contenga al menos un Alquimista, se activan las habilidades de color de **cada carta según su propio color impreso**, incluso si el escuadrón en conjunto es incoloro o de color mayoritario distinto | Permanente |
| Militares | Ascender 1 unidad sin costo por escuadrón | Inicio del turno |
| Festivos | +2 de armadura a los vínculos del escuadrón | Permanente |
| Monstruos | Remover 1 nodo enemigo cuyo Grado (G) sea menor que el ataque del escuadrón, por escuadrón | Fin del turno |
| Sabios | +1 carta extra en el paso de robar por escuadrón | Al robar |
| Naturaleza | Las unidades del escuadrón aportan +1 al daño de ataque y +1 al potenciamiento del escuadrón | Permanente |

---

## 10. Espías `[REDISEÑADO]`

Los espías son unidades de infiltración con reglas únicas:

1. **Despliegue**: Los espías se juegan directamente en la **frontera** (no en el territorio propio). Jugar un espía cuenta como 1 acción.
2. **Movimiento**: Desde la frontera, un espía puede infiltrarse en territorio enemigo. Esto cuenta como un ascenso (1 acción). Una vez en territorio enemigo, **no puede regresar** a territorio propio ni a la frontera.
3. **Vínculos**: Los espías pueden vincularse con unidades enemigas y con otros espías. También pueden mantener vínculos con unidades propias **únicamente mientras permanezcan en la frontera**. Estos vínculos con unidades propias se disuelven automáticamente cuando el espía se infiltra en territorio enemigo (incluso a L1 enemigo).
4. **Polígonos**: Los espías **siempre forman parte de los polígonos del jugador en cuyo territorio se encuentran**, nunca de los del dueño del espía. Sin embargo, el dueño del espía **parasita** ese escuadrón y obtiene las siguientes ventajas:
   - **Sabotaje encubierto**: Una vez por turno, durante tu Fase de Acciones, puedes gastar 1 acción por cada espía tuyo infiltrado para deshacer un vínculo del escuadrón enemigo que lo contiene.
   - **Inteligencia**: Cuando el escuadrón que contiene a tu espía declara un ataque, miras 1 carta al azar de la mano del jugador atacante.
   - **Contraespionaje**: Si un espía enemigo está en tu territorio, puedes declarar un ataque de cualquier escuadrón propio contra ese espía directamente (ignorando Sigilo si lo tuviera), como si estuvieras purgando a un infiltrado.

---

## 11. El grimorio `[EXPANDIDO]`

- Cada jugador comienza con **30 sellos** protegiendo su grimorio.
- Los sellos se representan con contadores sobre la Carta de Grimorio.
- Cada punto de daño neto que atraviesa la defensa rompe 1 sello.
- Cuando el último sello es destruido, el grimorio colapsa y ese jugador pierde la partida.
- Los escuadrones de Selladores añaden 10 sellos al grimorio al final del turno.

---

## 12. La reserva (mazo) y la mano `[NUEVO]`

- Mazo principal: 50 cartas.
- Mano inicial: 5 cartas.
- Robo por turno: 2 cartas (+1 extra por cada escuadrón de Sabios).
- Límite de mano al final del turno: 5 cartas.
- **Regla de descarte**: Por cada carta descartada para cumplir el límite de mano, el jugador pierde 1 sello de su propio grimorio. Esto representa la disipación de recursos mágicos no aprovechados y añade presión estratégica para usar las cartas en lugar de acumularlas.
- Si la reserva se agota y debes robar una o más cartas, por cada carta que no puedas robar pierdes inmediatamente 1 sello de tu grimorio. Esto se conoce como **daño de fatiga**. La partida puede continuar sin reserva siempre que el grimorio resista.

### 12.1 Pila de descartes (cementerio)

Las cartas destruidas, descartadas o removidas van a la pila de descartes de su dueño. Algunas cartas pueden tener habilidades que interactúan con la pila de descartes.

---

## 13. Anatomía de una carta `[FORMALIZADO]`

Cada carta contiene:

| Campo | Descripción |
|---|---|
| **Nombre** | Identificador único de la carta |
| **Indicador de color** | Círculo/icono con el color de la carta (puede ser distinto a sus habilidades de color) |
| **Copias máximas (C's)** | Número máximo de copias de esta carta permitidas en el mazo (1, 3 o 5) |
| **HP (Puntos de Vida)** | Resistencia del nodo. Al llegar a 0, es destruido |
| **D (Daño adicional)** | Daño extra que esta carta aporta al escuadrón cuando ataca |
| **V (Capacidad de vínculos)** | Número máximo de vínculos directos que este nodo puede sostener. Típicamente 2-3; cartas raras 4-5. Logistrones suelen tener V=5+ |
| **G (Grado)** `[NUEVO]` | Nivel jerárquico de la carta. Se usa en mecánicas que comparan poder relativo entre cartas (ej: efecto de Monstruos). Típicamente 1-3 |
| **Restricciones de layer** | Capas en las que puede ubicarse (L1, L2, L3) |
| **Restricciones de polígono** | Tipos de escuadrón que puede integrar (Triángulo, Cuadrilátero, Pentágono) |
| **Habilidades de color** | Efectos condicionados al color del escuadrón |
| **Habilidades de formación** | Efectos condicionados a la forma poligonal del escuadrón |
| **Habilidades generales** | Efectos incondicionales o con condiciones de timing |

---

## 14. El dado `[NUEVO]`

El dado de 6 caras se usa exclusivamente para resolver **empates de prioridad** y ciertos efectos de carta que expliciten una tirada. No se usa para el combate ni para el daño.

Situaciones que requieren dado:
- Dos habilidades con timing idéntico que dependen del orden de resolución y ningún jugador cede la prioridad.
- Efectos de carta que digan "tira un dado".

---

## 15. Setup de la partida `[NUEVO]`

1. Cada jugador coloca su playmat frente a sí, con la frontera en contacto con el playmat rival.
2. Cada jugador sitúa su Carta de Grimorio junto a su playmat, con 30 contadores de sellos.
3. Cada jugador baraja su mazo de 50 cartas y roba 5 cartas como mano inicial.
4. Se decide quién juega primero (dado o acuerdo mutuo).
5. El primer jugador comienza su Fase de Entrada.

> **Regla de mulligan**: El jugador que comienza puede hacer mulligan: barajar su mano inicial en la reserva, robar 5 nuevas cartas y perder 1 sello de su grimorio. Luego, el otro jugador puede hacer lo mismo. Se repite alternadamente hasta que ambos jugadores se planten consecutivamente. Cada mulligan cuesta 1 sello adicional (el primero: 1 sello, el segundo: 2 sellos, etc.). No hay límite de mulligans — la penalización acumulativa escala con cada intento.

---

## 16. Glosario

| Término | Definición |
|---|---|
| **Nodo** | Una carta en el territorio de guerra |
| **Vínculo directo** | Conexión física (varilla) entre dos nodos |
| **Vínculo indirecto** | Caso particular de distancia de red = 2: dos nodos que no están vinculados directamente entre sí pero comparten al menos un nodo vecino en común. Para distancias mayores, se usa el concepto general de distancia de red |
| **Distancia de red** | Número mínimo de vínculos entre dos nodos |
| **Escuadrón** | Conjunto de 2 o más nodos conectados que conforman una unidad táctica capaz de atacar, ya sea en forma de línea abierta (2 nodos, 1 vínculo) o de polígono cerrado (Triángulo, Cuadrilátero, Pentágono) |
| **Logistrón** | Unidad especial que conecta escuadrones entre sí |
| **Potenciamiento** | Bonificación que un escuadrón otorga a otros escuadrones conectados |
| **Grimorio** | Fuente de poder de la civilización, protegida por 30 sellos |
| **Sello** | Punto de protección del grimorio. 1 de daño = 1 sello roto |
| **Frontera** | Línea divisoria entre los dos territorios |
| **Ascenso** | Movimiento de un nodo a un layer superior |

---

## 17. Issues pendientes de resolución `[PENDIENTE]`

1. ~~Mulligan~~ → **Resuelto**: Mulligan con costo de sellos acumulativo (§15).
2. ~~Deck-out~~ → **Resuelto**: Daño de fatiga: 1 sello por carta no robada (§12).
3. ~~Espías y formación de polígonos~~ → **Resuelto**: Mecánica de parasitismo. Inteligencia = 1 carta al azar (§10).
4. ~~Número exacto de colores~~ → **Resuelto**: 10 facciones estándar + 2 especiales (Logistrones, Espías) = 12. Confirmado (§8).
5. ~~Cuadrilátero ampliado con 0 nodos internos~~ → **Resuelto**: Con X=0, daño = 3 (idéntico al básico). Es el mismo escuadrón. Se explicita en §4.4.
6. ~~Límite de varillas~~ → **Resuelto**: Cada carta indica su capacidad máxima de vínculos (V). Típicamente 2-3, cartas raras 4-5 (§4.2, §13).
7. ~~Ataque múltiple~~ → **Resuelto**: Cada escuadrón puede declarar un ataque por turno. Ataques secuenciales, defensor puede usar escuadrones distintos (§6.1).
8. ~~Coste de jugar cartas~~ → **Resuelto**: Todas las cartas cuestan 1 acción para jugar. Sin excepciones (§5.2).

---

*Documento generado a partir del diseño original de Eduardo Fuentes Caro. Versión formalizada y expandida por Hermes Agent.*
