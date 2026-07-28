"""
Network Fantasy War - Digital Prototype
Card data structures and the complete 40-card set.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Color(Enum):
    SELLADOR = "Sellador"
    GUERRERO = "Guerrero"
    POLITICO = "Político"
    SABOTEADOR = "Saboteador"
    ALQUIMISTA = "Alquimista"
    MILITAR = "Militar"
    FESTIVO = "Festivo"
    MONSTRUO = "Monstruo"
    SABIO = "Sabio"
    NATURALEZA = "Naturaleza"
    LOGISTRON = "Logistrón"
    ESPIA = "Espía"
    INCOLORO = "Incoloro"


class AbilityType(Enum):
    COLOR = "color"
    FORMATION = "formation"
    GENERAL = "general"
    ACTIVE = "active"


@dataclass
class Ability:
    description: str
    ability_type: AbilityType
    trigger: str  # "on_attack", "end_of_turn", "start_of_turn", "permanent", "active", "on_enter", "on_ascend", "on_kill"
    color_required: Optional[Color] = None
    formation_required: Optional[str] = None  # "triangle", "square", "pentagon"
    action_cost: int = 0


@dataclass
class CardDef:
    name: str
    color: Color
    max_copies: int
    hp: int
    damage_bonus: int
    link_capacity: int
    allowed_layers: list[int]
    allowed_formations: list[str]
    abilities: list[Ability] = field(default_factory=list)
    is_logistron: bool = False
    is_spy: bool = False


@dataclass
class CardInstance:
    card_id: int
    definition: CardDef
    current_hp: int
    owner: int
    position: Optional[tuple] = None

    def __init__(self, card_id: int, definition: CardDef, owner: int):
        self.card_id = card_id
        self.definition = definition
        self.current_hp = definition.hp
        self.owner = owner
        self.position = None
        self._cannot_attack = False
        self._faction_disabled = False

    @property
    def is_alive(self):
        return self.current_hp > 0

    def clone(self, new_card_id: int, new_owner: int) -> "CardInstance":
        """Deep clone for Magnum Opus."""
        import copy
        cloned = CardInstance(new_card_id, copy.deepcopy(self.definition), new_owner)
        cloned.current_hp = self.current_hp
        return cloned


# ═══════════════════════════════════════════════════════════════
# Complete 40-Card Set
# ═══════════════════════════════════════════════════════════════

ALL_CARDS: list[CardDef] = []

def _c(name, color, copies, hp, dmg, v, layers, formations, abilities=None,
       logistron=False, spy=False):
    """Shorthand card constructor."""
    ALL_CARDS.append(CardDef(
        name=name, color=color, max_copies=copies,
        hp=hp, damage_bonus=dmg, link_capacity=v,
        allowed_layers=layers, allowed_formations=formations,
        abilities=abilities or [],
        is_logistron=logistron, is_spy=spy
    ))

# ─── Mini-Set (1-15) ───

_c("Abadesa del Voto Eterno", Color.SELLADOR, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al final del turno, si está en escuadrón Sellador, +5 sellos adicionales", AbilityType.COLOR, "end_of_turn", color_required=Color.SELLADOR)
])

_c("Campeón del Filo Carmesí", Color.GUERRERO, 3, 3, 1, 2, [1,2,3], ["triangle","square"], [
    Ability("En L2: +1 daño base adicional al atacar", AbilityType.GENERAL, "on_attack")
])

_c("Estratega de los Cien Hilos", Color.POLITICO, 3, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Intercambia posición con otro nodo de tu red. Ambos conservan vínculos.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Agente del Silencio", Color.SABOTEADOR, 3, 2, 0, 2, [1,2,3], ["triangle"], [
    Ability("En triángulo: +1 vínculo enemigo destruido al final del turno", AbilityType.FORMATION, "end_of_turn", formation_required="triangle")
])

_c("Transmutadora del Espectro", Color.ALQUIMISTA, 2, 2, 1, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Cambia color de una carta enemiga defensora hasta final del turno", AbilityType.COLOR, "on_attack", color_required=Color.GUERRERO),
    Ability("Los vínculos de ~ tienen +1 de armadura", AbilityType.COLOR, "permanent", color_required=Color.FESTIVO),
])

_c("Sargento de la Escala de Hierro", Color.MILITAR, 3, 3, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Caudillismo: al ascender a L3, vínculo gratis con nodo en L2", AbilityType.GENERAL, "on_ascend")
])

_c("Danzante del Vínculo Eterno", Color.FESTIVO, 3, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("Vínculos que involucran a ~ no pueden ser destruidos por efectos enemigos", AbilityType.GENERAL, "permanent")
])

_c("Engendro del Vacío", Color.MONSTRUO, 2, 4, 2, 1, [1,2], ["triangle","square","pentagon"], [
    Ability("Al destruir un nodo enemigo, gana +1 HP permanente", AbilityType.GENERAL, "on_kill")
])

_c("Archivera del Conocimiento Perdido", Color.SABIO, 3, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al inicio del turno, en escuadrón Sabio: +1 robo extra", AbilityType.COLOR, "start_of_turn", color_required=Color.SABIO)
])

_c("Guardián del Bosque de Raíces", Color.NATURALEZA, 3, 3, 1, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: otras cartas del escuadrón aportan +2 daño en vez de +1", AbilityType.FORMATION, "on_attack", formation_required="triangle")
])

_c("Núcleo de Enlace", Color.LOGISTRON, 5, 2, 0, 5, [1,2,3], [], logistron=True)

_c("Retransmisor de Batalla", Color.LOGISTRON, 5, 1, 1, 4, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones a distancia de red 1 reciben el D de ~ al atacar", AbilityType.GENERAL, "on_attack")
])

_c("Sombra Infiltrada", Color.ESPIA, 3, 1, 0, 2, [], [], spy=True, abilities=[
    Ability("Parasitismo: sabotaje (1 acción) e inteligencia (1 carta al azar al atacar)", AbilityType.GENERAL, "permanent")
])

_c("Eco de la Frontera", Color.ESPIA, 3, 2, 0, 3, [], [], spy=True, abilities=[
    Ability("En frontera: puede vincularse con L3 enemigo y propio sin formar polígonos", AbilityType.GENERAL, "permanent")
])

_c("Agente Durmiente", Color.ESPIA, 2, 2, 1, 2, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: el escuadrón elegido no puede atacar tu grimorio", AbilityType.GENERAL, "permanent")
])

# ─── Wave 2 (16-40) ───

_c("Monje del Sello Silente", Color.SELLADOR, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Sigilo: ~ no puede ser atacado", AbilityType.GENERAL, "permanent"),
    Ability("En escuadrón Sellador: +3 sellos adicionales al final del turno", AbilityType.COLOR, "end_of_turn", color_required=Color.SELLADOR)
])

_c("Arquitecta del Muro", Color.SELLADOR, 3, 2, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero Sellador: tu grimorio no puede perder más de 5 sellos por ataque", AbilityType.FORMATION, "permanent", formation_required="square", color_required=Color.SELLADOR)
])

_c("Berserker del Filo", Color.GUERRERO, 3, 2, 2, 1, [1,2], ["triangle"], [
    Ability("Autofobia: al final del turno, si no tiene vínculos, es destruido", AbilityType.GENERAL, "end_of_turn"),
    Ability("En L2: ignora 2 puntos de defensa enemiga al atacar", AbilityType.GENERAL, "on_attack")
])

_c("Estandarte Carmesí", Color.GUERRERO, 2, 1, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En L3: todos los Guerreros en tu red ganan +1 al daño adicional", AbilityType.GENERAL, "permanent")
])

_c("Tejedor de Alianzas", Color.POLITICO, 3, 2, 0, 4, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Mueve una carta enemiga 1 meridiano (rompe vínculos si excede distancia)", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Virrey de la Frontera", Color.POLITICO, 3, 3, 0, 2, [3], ["triangle","square"], [
    Ability("Vanguardia: entra en juego directamente en L3", AbilityType.GENERAL, "on_enter"),
    Ability("En triángulo Político: +1 acción por turno", AbilityType.FORMATION, "start_of_turn", formation_required="triangle", color_required=Color.POLITICO)
])

_c("Sabueso del Nexo", Color.SABOTEADOR, 3, 1, 0, 2, [1,2,3], ["triangle"], [
    Ability("Al ser jugado: rompe 1 vínculo enemigo a distancia corta de su posición", AbilityType.GENERAL, "on_enter")
])

_c("Anuladora de Enlaces", Color.SABOTEADOR, 2, 2, 1, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Reticencia a Festivos y Selladores: no puede vincularse con esos colores", AbilityType.GENERAL, "permanent"),
    Ability("En cuadrilátero: rompe +1 vínculo enemigo por nodo enemigo a distancia de red 1", AbilityType.FORMATION, "end_of_turn", formation_required="square")
])

_c("Mutacromática", Color.ALQUIMISTA, 3, 1, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Cambia el color de una carta (propia o enemiga) hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Sintetista de Esencias", Color.ALQUIMISTA, 2, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En escuadrón Negro: deshacer 1 vínculo enemigo al final del turno", AbilityType.COLOR, "end_of_turn", color_required=Color.SABOTEADOR),
    Ability("En escuadrón Azul: ascender 1 unidad sin costo al inicio del turno", AbilityType.COLOR, "start_of_turn", color_required=Color.MILITAR),
    Ability("En escuadrón Verde: vínculos de ~ tienen +1 de armadura", AbilityType.COLOR, "permanent", color_required=Color.FESTIVO),
])

_c("Recluta de la Escala", Color.MILITAR, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Asciende ~ un layer (no puede usarse en L3)", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("General de la Escala de Hierro", Color.MILITAR, 1, 4, 1, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Caudillismo doble: al ascender a L3, 2 vínculos gratis con nodos en L2", AbilityType.GENERAL, "on_ascend"),
    Ability("En pentágono Militar: todos los Caudillismos de tu red están activos permanentemente", AbilityType.FORMATION, "permanent", formation_required="pentagon", color_required=Color.MILITAR)
])

_c("Coro del Vínculo", Color.FESTIVO, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al ser vinculado: ese vínculo obtiene +3 de armadura (en vez de +2)", AbilityType.GENERAL, "permanent")
])

_c("Maestra de Ceremonias", Color.FESTIVO, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: 1 vínculo gratis entre cartas a distancia corta al inicio del turno", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])

_c("Acechador de las Sombras", Color.MONSTRUO, 3, 3, 1, 1, [1,2,3], ["triangle"], [
    Ability("Sigilo: ~ no puede ser atacado", AbilityType.GENERAL, "permanent"),
    Ability("Al destruir un nodo: el dueño pierde 2 sellos adicionales", AbilityType.GENERAL, "on_kill")
])

_c("Devorador de Redes", Color.MONSTRUO, 2, 5, 2, 1, [1,2], ["triangle"], [
    Ability("[N acciones]: Destruye un nodo enemigo. N = número de vínculos del objetivo", AbilityType.ACTIVE, "active", action_cost=0)
])

_c("Bibliotecaria de los Ecos", Color.SABIO, 3, 1, 0, 2, [1], ["triangle","square"], [
    Ability("Al inicio del turno: mira 2 cartas del tope de tu reserva, pon 1 al fondo", AbilityType.GENERAL, "start_of_turn")
])

_c("Oráculo del Nexo", Color.SABIO, 1, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono Sabio: roba 3 cartas adicionales al inicio del turno", AbilityType.FORMATION, "start_of_turn", formation_required="pentagon", color_required=Color.SABIO)
])

_c("Enredadera Vincular", Color.NATURALEZA, 3, 2, 0, 4, [1,2], ["triangle","square","pentagon"], [
    Ability("Los vínculos que involucran a ~ cuestan 0 acciones", AbilityType.GENERAL, "permanent")
])

_c("Árbol Primigenio", Color.NATURALEZA, 2, 4, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("Guardaespaldas: puede redirigir daño de cartas vinculadas hacia sí mismo", AbilityType.GENERAL, "permanent"),
    Ability("Al final del turno: recupera 2 HP", AbilityType.GENERAL, "end_of_turn")
])

_c("Enjambre de Enlace", Color.LOGISTRON, 5, 1, 0, 6, [1,2,3], [], logistron=True, abilities=[
    Ability("Al ser destruido: transfiere sus vínculos a otro Logistrón", AbilityType.GENERAL, "on_kill")
])

_c("Plataforma de Asedio", Color.LOGISTRON, 3, 3, 2, 3, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones conectados a distancia de red 1 ignoran 2 de defensa enemiga", AbilityType.GENERAL, "on_attack")
])

_c("Cazador de Secretos", Color.ESPIA, 2, 2, 1, 1, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: descarta 1 carta de la mano del rival", AbilityType.GENERAL, "on_enter")
])

_c("Mercenario sin Bandera", Color.INCOLORO, 5, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Incoloro: no cuenta para la mayoría de color de ningún escuadrón", AbilityType.GENERAL, "permanent")
])

_c("Arquitecto de la Red", Color.INCOLORO, 3, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("Al final del turno, si tiene exactamente 3 vínculos: roba 1 carta", AbilityType.GENERAL, "end_of_turn")
])

# ─── Wave 3 (41-80) ───

_c("Centinela del Umbral", Color.SELLADOR, 5, 2, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Mientras esté en L1, tu grimorio tiene +5 de defensa contra ataques directos", AbilityType.GENERAL, "permanent")
])

_c("Restauradora de Energía", Color.SELLADOR, 3, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En triángulo: al final del turno, recupera 1 HP a todas las cartas de su escuadrón", AbilityType.FORMATION, "end_of_turn", formation_required="triangle")
])

_c("Baluarte Inamovible", Color.SELLADOR, 2, 5, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Guardaespaldas del grimorio: redirige hasta 3 de daño del grimorio a sí mismo", AbilityType.GENERAL, "permanent"),
    Ability("Al final del turno: recupera 1 HP", AbilityType.GENERAL, "end_of_turn")
])

_c("Duelista de la Brecha", Color.GUERRERO, 3, 2, 1, 2, [1,2,3], ["triangle"], [
    Ability("Al atacar un nodo enemigo: daño base duplicado", AbilityType.GENERAL, "on_attack"),
    Ability("Sigilo mientras no tenga vínculos", AbilityType.GENERAL, "permanent")
])

_c("Legión de Acero", Color.GUERRERO, 3, 1, 1, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: Gana +1 HP y +1 D permanente (una sola vez)", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Kamikaze del Abismo", Color.GUERRERO, 3, 2, 2, 1, [1,2,3], ["triangle"], [
    Ability("Al ser destruido: inflige 3 de daño al grimorio enemigo", AbilityType.GENERAL, "on_kill")
])

_c("Demagogo de la Frontera", Color.POLITICO, 3, 2, 0, 2, [1,2,3], ["triangle","square"], [
    Ability("[1]: Destruye 1 vínculo enemigo", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Burócrata Imperial", Color.POLITICO, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[2]: Mira 5 cartas del tope, juega 1 sin costo, baraja el resto", AbilityType.ACTIVE, "active", action_cost=2)
])

_c("Diplomática de la Corte", Color.POLITICO, 3, 2, 0, 4, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: paga 1 sello para cancelar 1 ataque al grimorio por turno", AbilityType.FORMATION, "permanent", formation_required="triangle")
])

_c("Saboteadora de Capas", Color.SABOTEADOR, 3, 2, 0, 2, [1,2,3], ["triangle","square"], [
    Ability("Al vincularse con una carta enemiga: rompe 2 vínculos de esa carta", AbilityType.GENERAL, "permanent")
])

_c("Zapador de Trincheras", Color.SABOTEADOR, 3, 3, 1, 1, [1,2], ["triangle"], [
    Ability("Sigilo mientras esté en L1", AbilityType.GENERAL, "permanent"),
    Ability("En L1 al final del turno: rompe 1 vínculo enemigo en L3", AbilityType.GENERAL, "end_of_turn")
])

_c("Virus de Red", Color.SABOTEADOR, 1, 1, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: Rompe todos los vínculos de un escuadrón enemigo", AbilityType.ACTIVE, "active", action_cost=1),
    Ability("Autofobia: al final del turno, si no tiene vínculos, es destruido", AbilityType.GENERAL, "end_of_turn")
])

_c("Destiladora de Pigmentos", Color.ALQUIMISTA, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Un escuadrón se considera del color que elijas hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Alquimista de Guerra", Color.ALQUIMISTA, 3, 2, 2, 2, [1,2,3], ["triangle","square"], [
    Ability("En escuadrón Rojo: ignora armadura enemiga al atacar", AbilityType.COLOR, "on_attack", color_required=Color.GUERRERO),
    Ability("En escuadrón Gris: al destruir un nodo, roba 1 carta", AbilityType.COLOR, "on_kill", color_required=Color.MONSTRUO)
])

_c("Filósofa de la Piedra", Color.ALQUIMISTA, 1, 3, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Todas las habilidades de color de tu red están activas permanentemente", AbilityType.GENERAL, "permanent"),
    Ability("Autofobia si no está en pentágono al final del turno", AbilityType.GENERAL, "end_of_turn")
])

_c("Instructor de Reclutas", Color.MILITAR, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Al inicio del turno: asciende 1 unidad de L1 a L2 sin costo", AbilityType.GENERAL, "start_of_turn")
])

_c("Francotirador de Élite", Color.MILITAR, 3, 1, 2, 1, [3], ["triangle"], [
    Ability("Vanguardia: entra en L3", AbilityType.GENERAL, "on_enter"),
    Ability("Solo ataca nodos. Ignora su defensa al atacar.", AbilityType.GENERAL, "on_attack")
])

_c("Comandante de Teatro", Color.MILITAR, 2, 3, 1, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: +1 acción al inicio del turno", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])

_c("Percusionista de Guerra", Color.FESTIVO, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: +2 de potenciamiento adicional a escuadrones conectados", AbilityType.FORMATION, "permanent", formation_required="triangle")
])

_c("Bardo del Vínculo", Color.FESTIVO, 3, 1, 0, 4, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Establece un vínculo entre dos cartas ignorando distancia espacial", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Guardiana de la Celebración", Color.FESTIVO, 2, 3, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono: restaura armadura perdida y +1 armadura global permanente por turno", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Cría del Vacío", Color.MONSTRUO, 5, 1, 0, 1, [1], ["triangle"], [
    Ability("Al ser destruido: busca un Monstruo en tu reserva y ponlo en tu mano", AbilityType.GENERAL, "on_kill")
])

_c("Hidra Regenerativa", Color.MONSTRUO, 2, 3, 1, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Al recibir daño sin morir: gana +1 HP y +1 D permanente", AbilityType.GENERAL, "on_attack"),
    Ability("Autofobia si no recibió daño este turno", AbilityType.GENERAL, "end_of_turn")
])

_c("Titán del Abismo", Color.MONSTRUO, 1, 8, 3, 1, [1,2], ["triangle"], [
    Ability("No puede vincularse con Logistrones ni con Selladores/Festivos. No puede ascender.", AbilityType.GENERAL, "permanent")
])

_c("Cartógrafa de la Red", Color.SABIO, 3, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al inicio del turno: revela la mano del oponente", AbilityType.GENERAL, "start_of_turn")
])

_c("Cronista de Batallas", Color.SABIO, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: recupera 1 carta de tu pila de descartes al final del turno", AbilityType.FORMATION, "end_of_turn", formation_required="square")
])

_c("Visionaria del Nexo", Color.SABIO, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("Al inicio del turno: nombra un color, busca en top 4. Si aciertas, a la mano.", AbilityType.GENERAL, "start_of_turn")
])

_c("Espora Expansiva", Color.NATURALEZA, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al ser destruido: crea 2 fichas Espora (HP:1, D:0, V:1) en celdas adyacentes libres", AbilityType.GENERAL, "on_kill")
])

_c("Bosque Andante", Color.NATURALEZA, 2, 4, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Muévete 1 meridiano. Si quedas adyacente a otra Naturaleza, vínculo gratis.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Raíz Madre", Color.NATURALEZA, 2, 3, 0, 4, [1], ["triangle","square","pentagon"], [
    Ability("Cartas Naturaleza vinculadas a ~ ganan +1 HP permanente", AbilityType.GENERAL, "permanent"),
    Ability("En pentágono: todas las cartas Naturaleza ganan +1 V permanente", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Enrutador de Batalla", Color.LOGISTRON, 5, 2, 0, 4, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones conectados reducen en 1 la distancia de red para potenciamiento", AbilityType.GENERAL, "permanent")
])

_c("Nodo de Respaldo", Color.LOGISTRON, 5, 3, 0, 3, [1,2,3], [], logistron=True, abilities=[
    Ability("Mientras tenga 1+ vínculos: grimorio no pierde más de 8 sellos por ataque", AbilityType.GENERAL, "permanent")
])

_c("Conducto Primario", Color.LOGISTRON, 3, 4, 0, 5, [1,2,3], [], logistron=True, abilities=[
    Ability("Cuenta como 2 logistrones para efectos que los mencionen", AbilityType.GENERAL, "permanent")
])

_c("Doble Agente", Color.ESPIA, 2, 2, 0, 2, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: destruye un espía enemigo en tu territorio", AbilityType.GENERAL, "on_enter"),
    Ability("En frontera: paga 1 sello para ver 2 cartas al azar de la mano enemiga", AbilityType.GENERAL, "permanent")
])

_c("Topo Paciente", Color.ESPIA, 2, 3, 0, 1, [], [], spy=True, abilities=[
    Ability("Tras 2 turnos infiltrado: destruye todos los vínculos del escuadrón enemigo que lo contiene", AbilityType.GENERAL, "permanent")
])

_c("Maestro de Espías", Color.ESPIA, 1, 2, 0, 3, [], [], spy=True, abilities=[
    Ability("En frontera: todos tus espías infiltrados ganan Sigilo", AbilityType.GENERAL, "permanent"),
    Ability("Puede infiltrarse y regresar a la frontera (1 acción cada sentido)", AbilityType.GENERAL, "permanent")
])

_c("Nómada del Páramo", Color.INCOLORO, 5, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Una vez por turno: cambia de layer como acción gratuita (no es ascenso)", AbilityType.GENERAL, "permanent")
])

_c("Ingeniero de Sitio", Color.INCOLORO, 3, 2, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("[2]: Agrega 1 meridiano temporal hasta el final del próximo turno", AbilityType.ACTIVE, "active", action_cost=2)
])

_c("Mensajero Incansable", Color.INCOLORO, 3, 1, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: Intercambia posiciones de dos cartas propias. Los vínculos se mantienen.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Coloso de Guerra", Color.INCOLORO, 2, 5, 2, 2, [1,2], ["square","pentagon"], [
    Ability("No puede formar triángulos. Cuesta 2 acciones jugarlo.", AbilityType.GENERAL, "permanent")
])

# ─── Wave 4 (81-120) ───

_c("Prior del Sello Absoluto", Color.SELLADOR, 2, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono Sellador: grimorio invulnerable este turno", AbilityType.FORMATION, "permanent", formation_required="pentagon", color_required=Color.SELLADOR)
])

_c("Monaguillo del Voto", Color.SELLADOR, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Destrúyete. Tu grimorio gana 5 sellos.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Ermitaño del Grimorio", Color.SELLADOR, 1, 3, 0, 2, [1], ["pentagon"], [
    Ability("Solo puede formar pentágonos. En pentágono: +20 sellos (en vez de +10) al final del turno.", AbilityType.GENERAL, "permanent")
])

_c("Gladiador del Circuito", Color.GUERRERO, 3, 3, 1, 1, [1,2], ["triangle","square"], [
    Ability("Al atacar: +1 daño por cada vínculo que tenga (máx +3)", AbilityType.GENERAL, "on_attack")
])

_c("Asediador de Murallas", Color.GUERRERO, 2, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Ignora efectos de límite de daño por ataque (Arquitecta, Nodo de Respaldo)", AbilityType.GENERAL, "on_attack")
])

_c("Maestro de Armas", Color.GUERRERO, 2, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero Guerrero: todas las cartas del escuadrón ganan +1 D", AbilityType.FORMATION, "permanent", formation_required="square", color_required=Color.GUERRERO)
])

_c("Senador Vitalicio", Color.POLITICO, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[2]: Toma control de un nodo enemigo hasta final del turno. Puedes atacar con él.", AbilityType.ACTIVE, "active", action_cost=2)
])

_c("Canciller del Tesoro", Color.POLITICO, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo Político: jugar cartas cuesta 0 acciones", AbilityType.FORMATION, "permanent", formation_required="triangle", color_required=Color.POLITICO)
])

_c("Emperador de los Dos Territorios", Color.POLITICO, 1, 3, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: puedes atacar también durante la Fase de Acciones una vez por turno", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Incendiaria de Archivos", Color.SABOTEADOR, 3, 2, 0, 2, [1,2,3], ["triangle","square"], [
    Ability("[1]: El oponente descarta 2 cartas de su mano", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Minadora de Vínculos", Color.SABOTEADOR, 3, 1, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Al final del turno: rompe 1 vínculo enemigo por cada Logistrón en tu red", AbilityType.GENERAL, "end_of_turn")
])

_c("Saboteadora de Formaciones", Color.SABOTEADOR, 2, 2, 1, 2, [1,2,3], ["triangle"], [
    Ability("En triángulo: cada vínculo enemigo roto inflige 1 daño al grimorio enemigo", AbilityType.FORMATION, "permanent", formation_required="triangle")
])

_c("Alquimista de la Forma", Color.ALQUIMISTA, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Elige un escuadrón aliado. Gana +1 daño base hasta final del turno.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Catalizadora de Reacción", Color.ALQUIMISTA, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Intercambia los colores de dos cartas hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Nigromante Alquímico", Color.ALQUIMISTA, 1, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: resucita 1 carta de tu pila de descartes a L1 por turno", AbilityType.FORMATION, "start_of_turn", formation_required="pentagon")
])

_c("Estratega de Retaguardia", Color.MILITAR, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Intercambia las capas de dos cartas propias (no cuenta como ascenso)", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Artillero de Asedio", Color.MILITAR, 2, 2, 2, 1, [1,2,3], ["square","pentagon"], [
    Ability("No puede formar triángulos. En cuadrilátero: ignora completamente la defensa enemiga.", AbilityType.GENERAL, "on_attack")
])

_c("Mariscal de Campo", Color.MILITAR, 1, 4, 1, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono Militar: todos los ascensos en tu red cuestan 0 acciones", AbilityType.FORMATION, "permanent", formation_required="pentagon", color_required=Color.MILITAR)
])

_c("Acróbata del Circuito", Color.FESTIVO, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: Salta a cualquier celda libre de tu territorio", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Ilusionista del Vínculo", Color.FESTIVO, 2, 1, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Crea vínculo temporal entre 2 cartas. Se disuelve al final del turno sin costo.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Anfitriona del Gran Baile", Color.FESTIVO, 1, 2, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: auto-conecta todas las cartas cercanas al final del turno", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Enjambre de Sombras", Color.MONSTRUO, 3, 1, 1, 1, [1,2,3], ["triangle"], [
    Ability("Ignora la regla de adyacencia para copias de ~. Puedes jugar múltiples por turno.", AbilityType.GENERAL, "permanent")
])

_c("Parásito de Red", Color.MONSTRUO, 2, 2, 0, 1, [1,2,3], ["triangle"], [
    Ability("[1]: Adjunta ~ a un Logistrón enemigo. Pierde 1 HP/turno y no puede crear vínculos.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Kraken del Abismo", Color.MONSTRUO, 1, 6, 2, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Puede atacar hasta 3 objetivos distintos en la misma Fase de Ataque", AbilityType.GENERAL, "permanent")
])

_c("Calculadora de Probabilidades", Color.SABIO, 3, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Mira 3 cartas de cualquier reserva. Pon 1 al fondo.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Profeta del Fin", Color.SABIO, 2, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: mira posición N del mazo enemigo. Si es Logistrón/Espía, descártala.", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])

_c("Biblioteca Viviente", Color.SABIO, 1, 3, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: sin límite de mano. No pierdes sellos por descartar.", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Enredadera Estranguladora", Color.NATURALEZA, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Cartas enemigas vinculadas a ~ no pueden atacar mientras el vínculo exista", AbilityType.GENERAL, "permanent")
])

_c("Polinizadora de Esencias", Color.NATURALEZA, 3, 1, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Copia una habilidad de una carta aliada adyacente hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Árbol del Fin de los Tiempos", Color.NATURALEZA, 1, 8, 0, 5, [1], ["pentagon"], [
    Ability("Solo pentágonos. En pentágono: +2 HP a toda tu red. Inmunes a destrucción por Monstruos.", AbilityType.GENERAL, "permanent")
])

_c("Enrutador Cuántico", Color.LOGISTRON, 3, 2, 0, 4, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones conectados pueden potenciarse entre territorios", AbilityType.GENERAL, "permanent")
])

_c("Núcleo de Reserva", Color.LOGISTRON, 5, 1, 0, 3, [1,2,3], [], logistron=True, abilities=[
    Ability("Al destruirse un Logistrón aliado: transfiere todos sus vínculos a ~ (ignora V)", AbilityType.GENERAL, "permanent")
])

_c("Conducto de Energía", Color.LOGISTRON, 3, 2, 0, 3, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones a distancia de red 1 ganan +1 al daño base", AbilityType.GENERAL, "permanent")
])

_c("Infiltrado Quirúrgico", Color.ESPIA, 2, 1, 0, 1, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: destruye un nodo enemigo con exactamente 1 vínculo", AbilityType.GENERAL, "on_enter")
])

_c("Falsificador de Órdenes", Color.ESPIA, 2, 2, 0, 2, [], [], spy=True, abilities=[
    Ability("Infiltrado: [1] haz que un escuadrón enemigo ataque a otro escuadrón enemigo", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Espía Legendario", Color.ESPIA, 1, 3, 1, 2, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: elige: (a) destruir escuadrón, (b) robar 3 sellos, o (c) robar nodo enemigo", AbilityType.GENERAL, "on_enter")
])

_c("Comodín del Destino", Color.INCOLORO, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Cuenta como cualquier color para mayoría de escuadrón. Cambiable cada turno.", AbilityType.GENERAL, "start_of_turn")
])

_c("Viajero Interdimensional", Color.INCOLORO, 2, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[2]: Destrúyete. La partida se reinicia (mantienen mazos originales).", AbilityType.ACTIVE, "active", action_cost=2)
])

_c("Titiritero Cósmico", Color.INCOLORO, 1, 3, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: al final de tu turno, toma un turno adicional", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Árbitro del Juego", Color.INCOLORO, 1, 4, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: Niega un efecto de carta enemiga que se acabe de activar", AbilityType.ACTIVE, "active", action_cost=1)
])

# ─── Wave 5 (121-160) ───

_c("Novicia del Primer Sello", Color.SELLADOR, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar en juego: tu grimorio gana 2 sellos", AbilityType.GENERAL, "on_enter")
])

_c("Guardián del Umbral", Color.SELLADOR, 3, 3, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Guardaespaldas: redirige a sí mismo el daño que recibiría otra carta Sellador", AbilityType.GENERAL, "permanent")
])

_c("Suma Sacerdotisa", Color.SELLADOR, 1, 4, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: una vez por partida, restaura tu grimorio a 30 sellos", AbilityType.FORMATION, "active", formation_required="pentagon")
])

_c("Lancero de Vanguardia", Color.GUERRERO, 5, 2, 1, 1, [1,2,3], ["triangle"], [
    Ability("Si está en L3: gana +2 D adicional", AbilityType.GENERAL, "permanent")
])

_c("Destructor de Escuadrones", Color.GUERRERO, 2, 3, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Al atacar una carta que esté en un escuadrón: +3 de daño", AbilityType.GENERAL, "on_attack")
])

_c("Señor de la Guerra", Color.GUERRERO, 1, 5, 2, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: el daño de ~ no puede ser reducido por defensa ni armadura", AbilityType.FORMATION, "on_attack", formation_required="pentagon")
])

_c("Secretario de Actas", Color.POLITICO, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Roba 1 carta", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Ministro de Defensa", Color.POLITICO, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: escuadrones defensores con ~ ganan +3 de defensa", AbilityType.FORMATION, "permanent", formation_required="square")
])

_c("Cónsul del Pueblo", Color.POLITICO, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: accedes a todos los efectos de facción este turno", AbilityType.FORMATION, "start_of_turn", formation_required="pentagon")
])

_c("Saboteador Novato", Color.SABOTEADOR, 5, 1, 0, 1, [1,2,3], ["triangle"], [
    Ability("Al entrar en juego: rompe 1 vínculo enemigo a distancia corta", AbilityType.GENERAL, "on_enter")
])

_c("Cortacircuitos", Color.SABOTEADOR, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: Todos los miembros de un escuadrón enemigo pierden 1 HP", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Anarquista del Nexo", Color.SABOTEADOR, 1, 2, 1, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: destruye todos los Logistrones enemigos", AbilityType.FORMATION, "active", formation_required="pentagon")
])

_c("Aprendiz de Alquimia", Color.ALQUIMISTA, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar en juego: mira la primera carta de tu reserva", AbilityType.GENERAL, "on_enter")
])

_c("Duplicadora de Esencias", Color.ALQUIMISTA, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: el potenciamiento que recibe este escuadrón se duplica", AbilityType.FORMATION, "permanent", formation_required="triangle")
])

_c("Gran Alquimista", Color.ALQUIMISTA, 1, 3, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: puedes jugar cartas de tu pila de descartes", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Cadete", Color.MILITAR, 5, 2, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Asciende ~ a L2", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Oficial de Enlace", Color.MILITAR, 3, 2, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Cuando ~ asciende: mueve otra carta propia 1 meridiano (ignora adyacencia)", AbilityType.GENERAL, "on_ascend")
])

_c("Almirante de la Flota", Color.MILITAR, 1, 4, 1, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todos tus escuadrones ganan +1 al daño base este turno", AbilityType.FORMATION, "start_of_turn", formation_required="pentagon")
])

_c("Músico Ambulante", Color.FESTIVO, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar en juego: un vínculo gana +1 de armadura", AbilityType.GENERAL, "on_enter")
])

_c("Coreógrafa de Escuadrones", Color.FESTIVO, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: [1] intercambia posiciones de 2 cartas en tu escuadrón", AbilityType.FORMATION, "active", formation_required="square")
])

_c("Espíritu de la Fiesta", Color.FESTIVO, 1, 2, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todas las cartas en tu red ganan +1 V permanente", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Cría Voraz", Color.MONSTRUO, 5, 1, 1, 1, [1], ["triangle"], [
    Ability("Si destruye un nodo enemigo: gana +2 HP y +1 D", AbilityType.GENERAL, "on_kill")
])

_c("Depredador Nocturno", Color.MONSTRUO, 2, 3, 1, 1, [1,2,3], ["triangle"], [
    Ability("Sigilo tras atacar: no puede ser atacado el turno siguiente si atacó", AbilityType.GENERAL, "permanent")
])

_c("Dragón Ancestral", Color.MONSTRUO, 1, 10, 3, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Puede atacar 2 veces por Fase de Ataque. Inmune a destrucción por efectos.", AbilityType.GENERAL, "permanent")
])

_c("Estudiante Aplicado", Color.SABIO, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar en juego: roba 1, descarta 1", AbilityType.GENERAL, "on_enter")
])

_c("Analista de Patrones", Color.SABIO, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En triángulo: mira la mano del oponente gratis 1 vez por turno", AbilityType.FORMATION, "start_of_turn", formation_required="triangle")
])

_c("Mente Maestra", Color.SABIO, 1, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono: puedes jugar cartas de la mano del oponente", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Brote Temprano", Color.NATURALEZA, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar en juego: recupera 1 HP a una carta aliada", AbilityType.GENERAL, "on_enter")
])

_c("Manto de Hojas", Color.NATURALEZA, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Los vínculos que involucran a ~ no pueden ser rotos por Saboteadores", AbilityType.GENERAL, "permanent")
])

_c("Ent Primordial", Color.NATURALEZA, 1, 7, 1, 4, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: todas las cartas en tu red se curan completamente al final del turno", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Microenlace", Color.LOGISTRON, 5, 1, 0, 2, [1,2,3], [], logistron=True)

_c("Puente Táctico", Color.LOGISTRON, 3, 2, 0, 4, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones conectados pueden atacar nodos a distancia de red 2", AbilityType.GENERAL, "permanent")
])

_c("Núcleo Central", Color.LOGISTRON, 1, 5, 0, 8, [1,2,3], [], logistron=True, abilities=[
    Ability("Puede vincularse con cartas en ambos territorios sin ser espía. V=8", AbilityType.GENERAL, "permanent")
])

_c("Merodeador", Color.ESPIA, 5, 1, 0, 1, [], [], spy=True, abilities=[
    Ability("Inteligencia: al atacar el escuadrón parasitado, ves 1 carta al azar", AbilityType.GENERAL, "permanent")
])

_c("Envenenador", Color.ESPIA, 2, 1, 0, 1, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: un nodo enemigo pierde 1 HP al final de cada turno", AbilityType.GENERAL, "permanent")
])

_c("Espía de la Corona", Color.ESPIA, 1, 2, 0, 2, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: toma el control de un Logistrón enemigo permanentemente", AbilityType.GENERAL, "on_enter")
])

_c("Recluta Genérico", Color.INCOLORO, 5, 2, 0, 1, [1,2,3], ["triangle","square","pentagon"], [])

_c("Especialista en Formaciones", Color.INCOLORO, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Al entrar: muévelo a cualquier celda de su layer sin costo de acción", AbilityType.GENERAL, "on_enter")
])

_c("Ermitaño del Tablero", Color.INCOLORO, 2, 3, 1, 1, [1,2,3], [], [
    Ability("No forma escuadrones. Puede atacar solo con daño = su D.", AbilityType.GENERAL, "permanent")
])

_c("Avatar del Juego", Color.INCOLORO, 1, 6, 2, 5, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Cuenta como todos los colores. Activa todas las habilidades de color siempre.", AbilityType.GENERAL, "permanent")
])

# ─── Wave 6 (161-200) ───

_c("Acolito del Sello", Color.SELLADOR, 5, 2, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Mientras esté en L1: tu grimorio gana 1 sello al inicio de tu turno", AbilityType.GENERAL, "start_of_turn")
])

_c("Defensora Abnegada", Color.SELLADOR, 3, 3, 0, 1, [1,2], ["triangle","square","pentagon"], [
    Ability("Guardaespaldas del grimorio: redirige cualquier daño al grimorio a sí misma (1 vez/turno)", AbilityType.GENERAL, "permanent")
])

_c("Patriarca de los Sellos", Color.SELLADOR, 1, 5, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: al final del turno, gana 30 sellos en lugar de 10. Una vez por partida.", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Espadachín Veloz", Color.GUERRERO, 5, 2, 1, 1, [1,2,3], ["triangle"], [
    Ability("Puede atacar el mismo turno en que es jugado", AbilityType.GENERAL, "permanent")
])

_c("Rompe-escudos", Color.GUERRERO, 3, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: los ataques ignoran Guardaespaldas enemigo", AbilityType.FORMATION, "on_attack", formation_required="square")
])

_c("Héroe de Mil Batallas", Color.GUERRERO, 1, 6, 2, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Gana +1 D permanente por cada carta enemiga destruida (máx +5)", AbilityType.GENERAL, "on_kill")
])

_c("Asistente Parlamentario", Color.POLITICO, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: Intercambia una carta de tu mano con la primera de tu reserva", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Embajador Extranjero", Color.POLITICO, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: niega 1 ataque enemigo a un nodo por turno", AbilityType.FORMATION, "permanent", formation_required="square")
])

_c("Primer Ministro", Color.POLITICO, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: tienes 6 acciones por turno en lugar de 4", AbilityType.FORMATION, "start_of_turn", formation_required="pentagon")
])

_c("Saboteador Oportunista", Color.SABOTEADOR, 5, 2, 0, 1, [1,2,3], ["triangle"], [
    Ability("Si un vínculo enemigo se rompe este turno: gana +2 D hasta final del turno", AbilityType.GENERAL, "permanent")
])

_c("Demoledor de Puentes", Color.SABOTEADOR, 3, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: rompe todos los vínculos entre layers en la red enemiga", AbilityType.FORMATION, "active", formation_required="square")
])

_c("Némesis de la Red", Color.SABOTEADOR, 1, 3, 1, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: destruye la mitad de los vínculos enemigos (redondeando arriba)", AbilityType.FORMATION, "active", formation_required="pentagon")
])

_c("Alquimista de Campo", Color.ALQUIMISTA, 5, 1, 0, 1, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Cambia el color de ~ a cualquier color hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Fusionista de Redes", Color.ALQUIMISTA, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: dos escuadrones adyacentes pueden fusionarse en uno este turno", AbilityType.FORMATION, "start_of_turn", formation_required="triangle")
])

_c("Maestro de la Transmutación", Color.ALQUIMISTA, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: intercambia HP y D de todas las cartas enemigas con las tuyas", AbilityType.FORMATION, "active", formation_required="pentagon")
])

_c("Soldado Raso", Color.MILITAR, 5, 2, 0, 1, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Si está en L3: gana +1 D", AbilityType.GENERAL, "permanent")
])

_c("Capitán de Batallón", Color.MILITAR, 3, 3, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: cartas en L1 de tu escuadrón atacan como si estuvieran en L2", AbilityType.FORMATION, "permanent", formation_required="square")
])

_c("Generalísimo", Color.MILITAR, 1, 5, 2, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todos los ascensos son instantáneos y gratuitos. Multi-capa por turno.", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Malabarista", Color.FESTIVO, 5, 1, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: Intercambia la posición de ~ con otra carta propia", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Encantador de Masas", Color.FESTIVO, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: cartas enemigas adyacentes a tu red no pueden atacar este turno", AbilityType.FORMATION, "active", formation_required="triangle")
])

_c("Alma de la Celebración", Color.FESTIVO, 1, 3, 0, 5, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todos los efectos de fin de turno se resuelven dos veces", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Bestia Callejera", Color.MONSTRUO, 5, 2, 1, 1, [1,2], ["triangle"], [
    Ability("No puede ser bloqueado por cartas con V=1", AbilityType.GENERAL, "permanent")
])

_c("Devorador de Capas", Color.MONSTRUO, 2, 4, 1, 2, [1,2,3], ["triangle","square"], [
    Ability("Al destruir una carta en L2 o L3: gana +1 V permanente", AbilityType.GENERAL, "on_kill")
])

_c("Apocalipsis Viviente", Color.MONSTRUO, 1, 12, 4, 1, [1,2,3], [], [
    Ability("No forma escuadrones. Ataca solo. Al atacar, destruye cartas adyacentes.", AbilityType.GENERAL, "permanent")
])

_c("Aprendiz de Biblioteca", Color.SABIO, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Descarta 1: roba 1. Una vez por turno, sin acción.", AbilityType.GENERAL, "active")
])

_c("Estratega de Guerra", Color.SABIO, 2, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: scry 3 (mira y reorganiza top 3 de tu reserva)", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])

_c("Conocedor de Todos los Finales", Color.SABIO, 1, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono: busca cualquier carta en tu reserva y ponla en tu mano. Una vez por partida.", AbilityType.FORMATION, "active", formation_required="pentagon")
])

_c("Semilla Viajera", Color.NATURALEZA, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al final del turno: muévete 1 meridiano", AbilityType.GENERAL, "end_of_turn")
])

_c("Campo de Espinas", Color.NATURALEZA, 2, 3, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En cuadrilátero: atacantes enemigos contra tu escuadrón reciben 1 de daño", AbilityType.FORMATION, "permanent", formation_required="square")
])

_c("Diosa de la Cosecha", Color.NATURALEZA, 1, 5, 0, 4, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: al final del turno, roba 1 carta por cada carta Naturaleza en tu red", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])

_c("Nodo Portátil", Color.LOGISTRON, 5, 1, 0, 2, [1,2,3], [], logistron=True)

_c("Amplificador de Señal", Color.LOGISTRON, 3, 2, 0, 4, [1,2,3], [], logistron=True, abilities=[
    Ability("Potenciamiento que pasa a través de ~ no decae con la distancia", AbilityType.GENERAL, "permanent")
])

_c("Núcleo Definitivo", Color.LOGISTRON, 1, 6, 0, 10, [1,2,3], [], logistron=True, abilities=[
    Ability("Puede vincularse con cualquier carta en cualquier territorio. Al morir: -10 sellos.", AbilityType.GENERAL, "permanent")
])

_c("Observador", Color.ESPIA, 5, 1, 0, 1, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: ves 1 carta al azar de la mano enemiga", AbilityType.GENERAL, "on_enter")
])

_c("Saboteador Profundo", Color.ESPIA, 2, 2, 0, 2, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: un escuadrón enemigo no recibe potenciamiento este turno", AbilityType.GENERAL, "on_enter")
])

_c("Agente del Caos", Color.ESPIA, 1, 3, 1, 3, [], [], spy=True, abilities=[
    Ability("Al infiltrarse: baraja la mano enemiga en su reserva y roba esa misma cantidad", AbilityType.GENERAL, "on_enter")
])

_c("Ciudadano", Color.INCOLORO, 5, 2, 0, 1, [1,2,3], ["triangle","square","pentagon"], [])

_c("Trotamundos", Color.INCOLORO, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Una vez por turno: puede cambiar de territorio", AbilityType.GENERAL, "active")
])

_c("Coleccionista de Rarezas", Color.INCOLORO, 2, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Gana +1 D por cada carta legendaria (C's=1) en tu red", AbilityType.GENERAL, "permanent")
])

_c("Deus Ex Machina", Color.INCOLORO, 1, 10, 5, 5, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Cuesta 4 acciones jugarlo. Si ataca y el objetivo sobrevive, pierdes la partida.", AbilityType.GENERAL, "permanent")
])

# ─── Wave 7 (201-300) ───

_c("Iniciada del Círculo", Color.SELLADOR, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar: +1 sello al grimorio", AbilityType.GENERAL, "on_enter")
])
_c("Guardiana de la Muralla", Color.SELLADOR, 3, 3, 0, 2, [1], ["triangle","square"], [
    Ability("Escuadrones enemigos con V total < 5 no pueden atacar tu grimorio", AbilityType.GENERAL, "permanent")
])
_c("Cenobita del Voto", Color.SELLADOR, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("En triángulo Sellador: +2 sellos al inicio del turno", AbilityType.FORMATION, "start_of_turn", formation_required="triangle", color_required=Color.SELLADOR)
])
_c("Prior de la Fortaleza", Color.SELLADOR, 2, 4, 0, 3, [1], ["square","pentagon"], [
    Ability("Guardaespaldas: absorbe daño dirigido a Selladores", AbilityType.GENERAL, "permanent")
])
_c("Ángel del Sello", Color.SELLADOR, 1, 5, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono: una vez por partida, restaura todos los sellos rotos este turno", AbilityType.FORMATION, "active", formation_required="pentagon")
])
_c("Escriba de los Votos", Color.SELLADOR, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: roba 1 y gana 1 sello", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Torre del Silencio", Color.SELLADOR, 2, 6, 0, 1, [1], ["square"], [
    Ability("No puede moverse ni ascender. Grimorio gana +10 de defensa pasiva.", AbilityType.GENERAL, "permanent")
])
_c("Patriarca de la Orden", Color.SELLADOR, 1, 6, 0, 4, [1], ["pentagon"], [
    Ability("En pentágono: todas las habilidades de Sellador en tu red se duplican", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Veterano de Guerra", Color.GUERRERO, 5, 2, 1, 1, [1,2,3], ["triangle"], [
    Ability("Gana +1 D por cada turno que sobrevive (máx +3)", AbilityType.GENERAL, "start_of_turn")
])
_c("Incursor Veloz", Color.GUERRERO, 3, 2, 1, 2, [1,2,3], ["triangle","square"], [
    Ability("Vanguardia: entra en L2. Puede atacar el turno que entra.", AbilityType.GENERAL, "on_enter")
])
_c("Titán de Batalla", Color.GUERRERO, 2, 5, 2, 2, [1,2], ["triangle","square"], [
    Ability("No puede ascender. -1 acción para vincularse con ~.", AbilityType.GENERAL, "permanent")
])
_c("Catapulta de Guerra", Color.GUERRERO, 2, 1, 0, 1, [1,2], ["square","pentagon"], [
    Ability("En cuadrado: el escuadrón gana +4 de daño contra grimorios", AbilityType.FORMATION, "on_attack", formation_required="square")
])
_c("Asesino de Gigantes", Color.GUERRERO, 2, 3, 1, 2, [1,2,3], ["triangle"], [
    Ability("+3 daño contra cartas con HP >= 5", AbilityType.GENERAL, "on_attack")
])
_c("Jefe de Guerra", Color.GUERRERO, 1, 6, 3, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Cuesta 2 acciones jugarlo. Todos los Guerreros en tu red ganan +1 D.", AbilityType.GENERAL, "permanent")
])
_c("Berserker del Norte", Color.GUERRERO, 3, 2, 2, 1, [1,2], ["triangle"], [
    Ability("No puede defender. Daño que inflige no puede ser reducido.", AbilityType.GENERAL, "permanent")
])
_c("Portaestandarte", Color.GUERRERO, 2, 3, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrado Guerrero: los Guerreros ignoran restricciones de formación", AbilityType.FORMATION, "permanent", formation_required="square", color_required=Color.GUERRERO)
])

_c("Funcionario", Color.POLITICO, 5, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar: mueve 1 carta propia a un meridiano adyacente libre", AbilityType.GENERAL, "on_enter")
])
_c("Diplomático", Color.POLITICO, 3, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: intercambia 1 carta de tu mano con 1 del cementerio", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Senador", Color.POLITICO, 3, 2, 0, 2, [1], ["square","pentagon"], [
    Ability("En cuadrado: +1 acción por turno", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])
_c("Ministro de Guerra", Color.POLITICO, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: 1 ataque extra este turno", AbilityType.FORMATION, "start_of_turn", formation_required="triangle")
])
_c("Canciller Supremo", Color.POLITICO, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: intercambia los sellos de ambos grimorios", AbilityType.FORMATION, "active", formation_required="pentagon")
])
_c("Gobernador Provincial", Color.POLITICO, 3, 2, 0, 2, [1,2], ["triangle","square"], [
    Ability("Al entrar: mueve una carta enemiga 1 meridiano", AbilityType.GENERAL, "on_enter")
])
_c("Líder de la Oposición", Color.POLITICO, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: niega el efecto de facción de un escuadrón enemigo este turno", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Presidente", Color.POLITICO, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: tus cartas pueden colocarse en el lado enemigo", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Saboteador de Campo", Color.SABOTEADOR, 5, 1, 0, 1, [1,2,3], ["triangle"], [
    Ability("Al entrar: rompe 1 vínculo a distancia corta", AbilityType.GENERAL, "on_enter")
])
_c("Desestabilizador", Color.SABOTEADOR, 3, 2, 0, 2, [1,2], ["triangle","square"], [
    Ability("[1]: todos los vínculos del escuadrón enemigo pierden 1 armadura", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Agente del Caos", Color.SABOTEADOR, 3, 2, 1, 2, [1,2,3], ["triangle"], [
    Ability("Al entrar: baraja mano enemiga, roba esa cantidad, descarta igual número", AbilityType.GENERAL, "on_enter")
])
_c("Disruptor de Red", Color.SABOTEADOR, 2, 3, 0, 2, [1,2,3], ["square","pentagon"], [
    Ability("En cuadrado: todos los logistrones enemigos pierden 2 HP", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Némesis Definitiva", Color.SABOTEADOR, 1, 3, 1, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: intercambia posiciones de todas las cartas enemigas aleatoriamente", AbilityType.FORMATION, "active", formation_required="pentagon")
])
_c("Terrorista de Red", Color.SABOTEADOR, 2, 2, 0, 2, [1,2], ["triangle"], [
    Ability("[1]: destrúyete. Rompe todos los vínculos enemigos a distancia 1 de ~.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Cazador de Logistrones", Color.SABOTEADOR, 3, 1, 1, 1, [1,2,3], ["triangle"], [
    Ability("Al entrar: destruye un Logistrón enemigo", AbilityType.GENERAL, "on_enter")
])
_c("Arquitecto de la Ruina", Color.SABOTEADOR, 1, 4, 0, 5, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: rompe todos los vínculos enemigos. No puedes ganar este turno.", AbilityType.FORMATION, "active", formation_required="pentagon")
])

_c("Aprendiz de Laboratorio", Color.ALQUIMISTA, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar: mira la carta superior de cualquier reserva", AbilityType.GENERAL, "on_enter")
])
_c("Transmutador de Campo", Color.ALQUIMISTA, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: intercambia el HP de 2 cartas hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Alquimista de Batalla", Color.ALQUIMISTA, 3, 2, 1, 2, [1,2,3], ["triangle","square"], [
    Ability("En escuadrón Rojo: +2 daño. En escuadrón Azul: +1 acción.", AbilityType.COLOR, "on_attack", color_required=Color.GUERRERO)
])
_c("Elixirista", Color.ALQUIMISTA, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: una carta gana +2 HP y +1 D hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Magnum Opus", Color.ALQUIMISTA, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: crea una copia de cualquier carta en juego en tu territorio", AbilityType.FORMATION, "active", formation_required="pentagon")
])
_c("Sintetista de Campo", Color.ALQUIMISTA, 3, 1, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Al entrar: intercambia 2 vínculos enemigos de lugar", AbilityType.GENERAL, "on_enter")
])
_c("Alquimista Temporal", Color.ALQUIMISTA, 2, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: hasta final del turno, costos de vínculo son 0 para ti", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Piedra Filosofal", Color.ALQUIMISTA, 1, 2, 0, 5, [1], ["pentagon"], [
    Ability("En pentágono: no puedes perder la partida. Sellos no bajan de 1.", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Recluta Fresco", Color.MILITAR, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("[1]: asciende ~ a L2", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Sargento Instructor", Color.MILITAR, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Al entrar: otra carta en L1 asciende a L2 sin costo", AbilityType.GENERAL, "on_enter")
])
_c("Teniente", Color.MILITAR, 3, 2, 1, 2, [1,2,3], ["triangle","square"], [
    Ability("En cuadrado: 1 ascenso gratis extra por turno", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])
_c("Coronel", Color.MILITAR, 2, 4, 1, 3, [1,2,3], ["square","pentagon"], [
    Ability("Caudillismo doble: 2 vínculos gratis al ascender a L3", AbilityType.GENERAL, "on_ascend")
])
_c("Mariscal Supremo", Color.MILITAR, 1, 6, 2, 5, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: al final del turno, asciende todas tus cartas 1 capa", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])
_c("Ingeniero de Combate", Color.MILITAR, 3, 2, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Al entrar: mueve cualquier carta en tu territorio 1 meridiano", AbilityType.GENERAL, "on_enter")
])
_c("Artillero Pesado", Color.MILITAR, 2, 2, 3, 1, [1,2], ["square"], [
    Ability("No puede ascender. +2 daño extra a nodos en L3.", AbilityType.GENERAL, "on_attack")
])
_c("Almirante Supremo", Color.MILITAR, 1, 5, 2, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: escuadrones con al menos 1 Militar ganan +2 daño base", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Bailarín", Color.FESTIVO, 5, 1, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: intercambia ~ con otra carta en tu territorio", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Músico de la Corte", Color.FESTIVO, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Al entrar: todos los vínculos que elijas ganan +1 armadura", AbilityType.GENERAL, "on_enter")
])
_c("Artista del Vínculo", Color.FESTIVO, 3, 1, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("Los vínculos con ~ cuestan 0 acciones", AbilityType.GENERAL, "permanent")
])
_c("Celebración Eterna", Color.FESTIVO, 2, 2, 0, 3, [1], ["square","pentagon"], [
    Ability("En cuadrado: efectos de fin de turno de Festivos se duplican", AbilityType.FORMATION, "end_of_turn", formation_required="square")
])
_c("Festival del Nexo", Color.FESTIVO, 1, 4, 0, 5, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: conecta todas las cartas no vinculadas con vínculos gratis", AbilityType.FORMATION, "active", formation_required="pentagon")
])
_c("Acróbata Sagrado", Color.FESTIVO, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: ~ salta a cualquier celda libre ignorando adyacencia", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Poeta del Circuito", Color.FESTIVO, 2, 2, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En triángulo: roba 1. En cuadrado: +2 armadura global.", AbilityType.GENERAL, "permanent")
])
_c("Carismático Supremo", Color.FESTIVO, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todas las cartas en tu red se consideran Festivas además de su color", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Alimaña", Color.MONSTRUO, 5, 1, 1, 1, [1], ["triangle"], [
    Ability("No puede ser objetivo de habilidades enemigas", AbilityType.GENERAL, "permanent")
])
_c("Aberración", Color.MONSTRUO, 3, 3, 1, 1, [1,2], ["triangle"], [
    Ability("Gana +1 HP cuando una carta aliada es destruida", AbilityType.GENERAL, "on_kill")
])
_c("Bestia Alada", Color.MONSTRUO, 3, 2, 1, 2, [1,2,3], ["triangle","square"], [
    Ability("Vanguardia: entra en L3. Puede moverse 1 meridiano gratis por turno.", AbilityType.GENERAL, "on_enter")
])
_c("Gigante de Piedra", Color.MONSTRUO, 2, 7, 2, 1, [1], ["triangle"], [
    Ability("No puede ascender ni moverse", AbilityType.GENERAL, "permanent")
])
_c("Kaiju Primordial", Color.MONSTRUO, 1, 15, 5, 1, [1], ["triangle"], [
    Ability("No puede vincularse ni ascender. Destruye cartas adyacentes al atacar.", AbilityType.GENERAL, "permanent")
])
_c("Manada de Sombras", Color.MONSTRUO, 3, 1, 1, 1, [1,2,3], ["triangle"], [
    Ability("Puedes jugar hasta 3 copias en el mismo meridiano (ignora adyacencia)", AbilityType.GENERAL, "permanent")
])
_c("Depredador Alfa", Color.MONSTRUO, 2, 5, 2, 2, [1,2,3], ["triangle","square"], [
    Ability("Los otros Monstruos en tu red ganan +1 D", AbilityType.GENERAL, "permanent")
])
_c("Horror Cósmico", Color.MONSTRUO, 1, 20, 6, 1, [1,2,3], ["triangle"], [
    Ability("No forma escuadrones. Ataca solo. Al entrar, destruye todas tus otras cartas.", AbilityType.GENERAL, "permanent")
])

_c("Novicio del Saber", Color.SABIO, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar: scry 2", AbilityType.GENERAL, "on_enter")
])
_c("Investigador", Color.SABIO, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: mira las 3 primeras cartas de tu reserva", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Erudito del Nexo", Color.SABIO, 3, 2, 0, 2, [1], ["square","pentagon"], [
    Ability("En cuadrado: roba 1 carta extra al inicio del turno", AbilityType.FORMATION, "start_of_turn", formation_required="square")
])
_c("Archivero Supremo", Color.SABIO, 2, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Puedes jugar cartas del cementerio pagando 2 acciones extra", AbilityType.GENERAL, "permanent")
])
_c("Omnisciente", Color.SABIO, 1, 3, 0, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: mano enemiga revelada. Robas 3 cartas por turno.", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])
_c("Lingüista", Color.SABIO, 3, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar: nombra un color. Roba 1 por cada carta de ese color en tu mano.", AbilityType.GENERAL, "on_enter")
])
_c("Pronosticador", Color.SABIO, 2, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: nombra una carta. Si está en mano enemiga, la descarta.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Sabio Absoluto", Color.SABIO, 1, 3, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono: mano máxima 10 y no pierdes sellos por descartar", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Brote Silvestre", Color.NATURALEZA, 5, 1, 0, 1, [1], ["triangle","square","pentagon"], [
    Ability("Al entrar: +1 HP a una carta aliada", AbilityType.GENERAL, "on_enter")
])
_c("Vid Espinosa", Color.NATURALEZA, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Atacantes contra cartas en el escuadrón de ~ reciben 1 de daño", AbilityType.GENERAL, "permanent")
])
_c("Roble Ancestral", Color.NATURALEZA, 3, 5, 0, 3, [1], ["square","pentagon"], [
    Ability("No puede ascender. Regenera 2 HP al final del turno.", AbilityType.GENERAL, "end_of_turn")
])
_c("Bosque Protector", Color.NATURALEZA, 2, 4, 0, 4, [1], ["pentagon"], [
    Ability("En pentágono: todas las cartas en tu red ganan +2 HP", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])
_c("Madre Tierra", Color.NATURALEZA, 1, 8, 0, 5, [1], ["pentagon"], [
    Ability("En pentágono: al final del turno, resucita 1 carta de tu cementerio en L1", AbilityType.FORMATION, "end_of_turn", formation_required="pentagon")
])
_c("Hiedra Trepadora", Color.NATURALEZA, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("Al entrar: vincúlala inmediatamente con 1 carta adyacente sin costo", AbilityType.GENERAL, "on_enter")
])
_c("Jardín de Piedra", Color.NATURALEZA, 2, 3, 0, 2, [1], ["square"], [
    Ability("En cuadrado: cartas enemigas no pueden ascender", AbilityType.FORMATION, "permanent", formation_required="square")
])
_c("Yggdrasil", Color.NATURALEZA, 1, 12, 0, 6, [1], ["pentagon"], [
    Ability("Solo pentágono. Al final del turno, todas tus cartas ganan +1 HP permanente.", AbilityType.GENERAL, "end_of_turn")
])

_c("Enlace Básico", Color.LOGISTRON, 5, 1, 0, 2, [1,2,3], [], logistron=True)
_c("Conmutador", Color.LOGISTRON, 3, 2, 0, 4, [1,2,3], [], logistron=True, abilities=[
    Ability("Vínculos entre escuadrones conectados por ~ no cuestan acciones", AbilityType.GENERAL, "permanent")
])
_c("Distribuidor de Carga", Color.LOGISTRON, 2, 3, 0, 3, [1,2,3], [], logistron=True, abilities=[
    Ability("Escuadrones conectados comparten su potenciamiento equitativamente", AbilityType.GENERAL, "permanent")
])
_c("Hub Central", Color.LOGISTRON, 1, 8, 0, 12, [1,2,3], [], logistron=True, abilities=[
    Ability("Al morir: pierdes 5 sellos por cada vínculo que tenía", AbilityType.GENERAL, "on_kill")
])
_c("Nodo Fantasma", Color.LOGISTRON, 3, 2, 0, 3, [1,2,3], [], logistron=True, abilities=[
    Ability("No ocupa una celda (puede compartir celda con otra carta)", AbilityType.GENERAL, "permanent")
])

_c("Infiltrado Básico", Color.ESPIA, 5, 1, 0, 1, [], [], spy=True, abilities=[
    Ability("Inteligencia básica: 1 carta al azar al infiltrarse", AbilityType.GENERAL, "on_enter")
])
_c("Dormido", Color.ESPIA, 3, 2, 0, 1, [], [], spy=True, abilities=[
    Ability("3 turnos tras infiltrarse: destruye grimorio enemigo si tienes 5+ espías infiltrados", AbilityType.GENERAL, "permanent")
])
_c("Susurrador", Color.ESPIA, 2, 1, 0, 2, [], [], spy=True, abilities=[
    Ability("Infiltrado: [1] el dueño del escuadrón parasitado descarta 1 carta", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Agente Triple", Color.ESPIA, 1, 2, 1, 2, [], [], spy=True, abilities=[
    Ability("Puede infiltrarse/regresar sin límite. Cada infiltración roba 1 sello.", AbilityType.GENERAL, "permanent")
])
_c("Red de Inteligencia", Color.ESPIA, 1, 3, 0, 4, [], [], spy=True, abilities=[
    Ability("En frontera: todos tus espías +1 V. Ves mano enemiga completa.", AbilityType.GENERAL, "permanent")
])

_c("Peón", Color.INCOLORO, 5, 1, 0, 1, [1,2,3], ["triangle","square","pentagon"], [])
_c("Aventurero", Color.INCOLORO, 5, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Al entrar: muévete 1 meridiano", AbilityType.GENERAL, "on_enter")
])
_c("Forajido", Color.INCOLORO, 3, 2, 1, 1, [1,2,3], ["triangle","square"], [
    Ability("[1]: ataca un nodo enemigo con daño = su D. Una vez por turno.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Cazatesoros", Color.INCOLORO, 3, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Al entrar: si controlas cartas de 3 colores distintos, roba 2", AbilityType.GENERAL, "on_enter")
])
_c("Gladiador", Color.INCOLORO, 2, 4, 1, 1, [1,2], ["triangle"], [
    Ability("[1]: lucha contra un nodo enemigo. Ambos reciben 2 de daño.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Místico", Color.INCOLORO, 2, 2, 0, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("[1]: scry 3. Roba 1.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Señor de la Guerra", Color.INCOLORO, 1, 5, 2, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Todos tus escuadrones ganan +1 daño base", AbilityType.GENERAL, "permanent")
])
_c("Vagabundo", Color.INCOLORO, 3, 2, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Puede moverse libremente entre capas sin costo de ascenso", AbilityType.GENERAL, "permanent")
])
_c("Titiritero", Color.INCOLORO, 2, 2, 0, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En cuadrado: [1] toma control de un escuadrón enemigo este turno", AbilityType.FORMATION, "active", formation_required="square")
])
_c("El Arquitecto", Color.INCOLORO, 1, 10, 3, 6, [1,2,3], ["triangle","square","pentagon"], [
    Ability("Cuesta 3 acciones. Red sin límite de vínculos. Al morir, pierdes.", AbilityType.GENERAL, "permanent")
])

# ─── Wave 8 (301-330) — Refuerzos Político + Alquimista + Sabio ───

_c("Alcalde de Guerra", Color.POLITICO, 3, 2, 1, 2, [1,2], ["triangle","square"], [
    Ability("Al atacar: gasta 1 acción extra para duplicar su D este ataque", AbilityType.GENERAL, "on_attack")
])
_c("Recaudador de Impuestos", Color.POLITICO, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: el oponente pierde 2 sellos. Tú ganas 1 sello.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Señor de la Guerra Civil", Color.POLITICO, 2, 3, 2, 2, [1,2,3], ["triangle","square"], [
    Ability("En cuadrado: escuadrones enemigos no reciben potenciamiento este turno", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Alcaldesa del Pueblo", Color.POLITICO, 5, 2, 1, 2, [1,2], ["triangle","square"], [
    Ability("Cartas jugadas en el mismo meridiano que ~ cuestan 0 acciones", AbilityType.GENERAL, "permanent")
])
_c("Comisario Político", Color.POLITICO, 3, 2, 1, 2, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En triángulo: las cartas en tu escuadrón ganan +1 D", AbilityType.FORMATION, "permanent", formation_required="triangle")
])
_c("Presidente Vitalicio", Color.POLITICO, 1, 4, 1, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todos tus Políticos ganan +2 D y atacan 2 veces por turno", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])
_c("Diputado Belicoso", Color.POLITICO, 3, 3, 2, 1, [1,2], ["triangle"], [
    Ability("No puede ser objetivo de habilidades políticas enemigas", AbilityType.GENERAL, "permanent")
])
_c("Canciller de Guerra", Color.POLITICO, 2, 3, 1, 3, [1,2,3], ["square","pentagon"], [
    Ability("En cuadrado: intercambia D de tus cartas con D enemigo hasta final del turno", AbilityType.FORMATION, "active", formation_required="square")
])

_c("Rebelde Armado", Color.INCOLORO, 5, 2, 2, 1, [1,2,3], ["triangle"], [
    Ability("Si está en escuadrón con al menos 1 Político: +1 D adicional", AbilityType.GENERAL, "permanent")
])
_c("Guardaespaldas del Concejo", Color.INCOLORO, 3, 4, 1, 1, [1,2], ["triangle","square"], [
    Ability("Guardaespaldas: redirige daño dirigido a Políticos hacia ~", AbilityType.GENERAL, "permanent")
])
_c("Multitud Enfurecida", Color.INCOLORO, 3, 1, 1, 1, [1,2], ["triangle"], [
    Ability("Puedes jugar hasta 5 copias. Por cada copia en tu escuadrón: +1 D.", AbilityType.GENERAL, "permanent")
])
_c("Asesor Sombrío", Color.INCOLORO, 2, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: destruye un Político aliado. Inflige 5 de daño al grimorio enemigo.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Alquimista Acorazado", Color.ALQUIMISTA, 3, 4, 1, 2, [1,2], ["triangle","square"], [
    Ability("[1]: gana +3 de armadura hasta final del turno", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Golem Alquímico", Color.ALQUIMISTA, 2, 6, 2, 1, [1], ["triangle"], [
    Ability("No puede ascender. No puede vincularse con más de 2 cartas.", AbilityType.GENERAL, "permanent")
])
_c("Elixirista de Combate", Color.ALQUIMISTA, 3, 3, 1, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: al inicio del turno, +1 HP a todas las cartas del escuadrón", AbilityType.FORMATION, "start_of_turn", formation_required="triangle")
])
_c("Alquimista de Asedio", Color.ALQUIMISTA, 2, 3, 2, 2, [1,2,3], ["square"], [
    Ability("En Rojo: ignora Guardaespaldas. En Gris: +2 D al atacar nodos.", AbilityType.COLOR, "on_attack", color_required=Color.GUERRERO)
])
_c("Transmutador de Masas", Color.ALQUIMISTA, 2, 3, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("En cuadrado: intercambia HP de tu escuadrón con el del defensor", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Homúnculo de Batalla", Color.ALQUIMISTA, 3, 4, 2, 2, [1,2,3], ["triangle","square"], [
    Ability("Cuando recibe daño: gana +1 D permanentemente", AbilityType.GENERAL, "on_attack")
])
_c("Alquimista Supremo", Color.ALQUIMISTA, 1, 5, 2, 4, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: todas las cartas en tu red ganan +2 HP y +1 D", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])
_c("Crisálida Alquímica", Color.ALQUIMISTA, 3, 1, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[2]: destrúyete. Busca un Alquimista en tu reserva y ponlo en juego aquí.", AbilityType.ACTIVE, "active", action_cost=2)
])

_c("Estratega de Campo", Color.SABIO, 3, 2, 1, 2, [1,2], ["triangle","square"], [
    Ability("En triángulo: +1 daño base al escuadrón por cada carta en tu mano (máx +3)", AbilityType.FORMATION, "on_attack", formation_required="triangle")
])
_c("Vidente de la Tormenta", Color.SABIO, 2, 2, 0, 2, [1], ["triangle","square","pentagon"], [
    Ability("[1]: mira mano enemiga. Roba 1 por cada carta con D>=1 que veas.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Bibliotecario de Guerra", Color.SABIO, 3, 3, 1, 2, [1,2], ["square","pentagon"], [
    Ability("Al inicio del turno: descarta 1 para dar +1 D a un escuadrón este turno", AbilityType.GENERAL, "start_of_turn")
])
_c("Archimago del Nexo", Color.SABIO, 1, 4, 2, 3, [1,2,3], ["triangle","square","pentagon"], [
    Ability("En pentágono: roba 2. Inflige 1 de daño al grimorio enemigo por carta en tu mano.", AbilityType.FORMATION, "active", formation_required="pentagon")
])
_c("Profesor de Combate", Color.SABIO, 5, 2, 1, 2, [1,2], ["triangle","square"], [
    Ability("Otras cartas en tu escuadrón ganan +1 D", AbilityType.GENERAL, "permanent")
])
_c("Sabio Guerrero", Color.SABIO, 3, 3, 2, 1, [1,2], ["triangle"], [
    Ability("Puede atacar solo (sin escuadrón) con daño = su D", AbilityType.GENERAL, "permanent")
])
_c("Archivera de la Guerra", Color.SABIO, 2, 2, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En cuadrado: puedes jugar cartas de tu cementerio este turno. Luego exílialas.", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Mente Colmena", Color.SABIO, 3, 2, 0, 4, [1,2], ["triangle","square","pentagon"], [
    Ability("En triángulo: todos los Sabios en tu red comparten su D (usan el mayor)", AbilityType.FORMATION, "permanent", formation_required="triangle")
])

_c("Canalizador Arcano", Color.INCOLORO, 3, 2, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("Cuenta como Alquimista y Sabio para efectos de facción", AbilityType.GENERAL, "permanent")
])
_c("Gólem de Guerra", Color.INCOLORO, 2, 7, 3, 1, [1], ["triangle"], [
    Ability("Cuesta 3 acciones jugarlo. No puede vincularse.", AbilityType.GENERAL, "permanent")
])

# ─── Wave 9 (331-350) — Anclados L1/L2 ───

_c("Muro Viviente", Color.NATURALEZA, 3, 6, 0, 1, [1], ["triangle"], [
    Ability("Mientras esté en L1: tu grimorio no recibe daño de ataques directos. No puede ascender.", AbilityType.GENERAL, "permanent")
])
_c("Sumo Sacerdote", Color.SELLADOR, 1, 4, 0, 3, [1], ["triangle","square","pentagon"], [
    Ability("En cuadrado: tus cartas en L1 son indestructibles este turno.", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Reina Madre", Color.POLITICO, 1, 5, 0, 5, [1], ["triangle","square","pentagon"], [
    Ability("Mientras esté en L1: todas tus cartas en L1 ganan +2 HP y pueden vincularse sin acciones.", AbilityType.GENERAL, "permanent")
])
_c("Armero Real", Color.GUERRERO, 3, 3, 0, 2, [1], ["triangle","square"], [
    Ability("[1]: +2 D a una carta en L1 hasta final del turno.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Centinela de la Puerta", Color.MILITAR, 3, 4, 2, 2, [1], ["triangle"], [
    Ability("Mientras esté en L1: los espías enemigos no pueden infiltrarse en tu territorio.", AbilityType.GENERAL, "permanent")
])
_c("Sabio Ermitaño", Color.SABIO, 1, 3, 0, 4, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: al inicio de tu turno, roba 3 cartas. No puede ascender ni atacar.", AbilityType.FORMATION, "start_of_turn", formation_required="pentagon")
])
_c("Bestia de Guarida", Color.MONSTRUO, 2, 7, 3, 1, [1], ["triangle"], [
    Ability("No puede ascender. No puede ser objetivo de habilidades enemigas mientras esté en L1.", AbilityType.GENERAL, "permanent")
])
_c("Pregonero del Pueblo", Color.INCOLORO, 5, 2, 0, 2, [1], ["triangle","square"], [
    Ability("Mientras esté en L1: puedes jugar cartas en L1 sin acciones (máx 2/turno).", AbilityType.GENERAL, "permanent")
])

_c("Capitana de la Guardia", Color.MILITAR, 2, 4, 2, 3, [1,2], ["triangle","square"], [
    Ability("En cuadrado: tus cartas en L1 y L2 ganan +1 D este turno.", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Arquitecta de Fortalezas", Color.SELLADOR, 2, 5, 0, 4, [1,2], ["square","pentagon"], [
    Ability("Mientras esté en L1 o L2: tu grimorio gana 3 de armadura al inicio de cada turno.", AbilityType.GENERAL, "start_of_turn")
])
_c("Maestro de la Vanguardia", Color.SABIO, 2, 3, 1, 3, [1,2], ["triangle","square"], [
    Ability("En triángulo: tus cartas en L2 pueden vincularse con L1 sin distancia máxima.", AbilityType.FORMATION, "permanent", formation_required="triangle")
])
_c("Alquimista de Trinchera", Color.ALQUIMISTA, 3, 3, 1, 2, [1,2], ["triangle","square"], [
    Ability("[1]: intercambia la posición de 2 cartas aliadas en L1 o L2.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Estratega de la Defensa", Color.POLITICO, 2, 4, 1, 3, [1,2], ["square"], [
    Ability("Al inicio del turno: si tienes 5+ cartas en L1+L2, ganas 2 acciones extra.", AbilityType.GENERAL, "start_of_turn")
])
_c("Enredadera de Raíz Profunda", Color.NATURALEZA, 3, 5, 1, 3, [1,2], ["square","pentagon"], [
    Ability("Tus cartas en L1 y L2 regeneran 1 HP al inicio de tu turno.", AbilityType.GENERAL, "start_of_turn")
])
_c("Berserker de la Brecha", Color.GUERRERO, 3, 2, 3, 1, [1,2], ["triangle"], [
    Ability("Cuando ataca desde L2: daño del escuadrón duplicado si objetivo a distancia corta/media.", AbilityType.GENERAL, "on_attack")
])
_c("Místico del Nexo", Color.INCOLORO, 1, 3, 0, 5, [1,2], ["triangle","square","pentagon"], [
    Ability("En pentágono: tus cartas en L1/L2 forman pentágono como si estuvieran en L3.", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

_c("Enrutador de Retaguardia", Color.LOGISTRON, 3, 2, 0, 6, [1], [], logistron=True, abilities=[
    Ability("Solo vincula con L1. Reduce 1 acción jugar cartas en L1.", AbilityType.GENERAL, "permanent")
])
_c("Torre de Señal", Color.LOGISTRON, 2, 3, 0, 4, [1,2], [], logistron=True, abilities=[
    Ability("Cartas en L1/L2 vinculadas a ~ atacan con alcance máximo.", AbilityType.GENERAL, "permanent")
])
_c("Nodo Ancla", Color.LOGISTRON, 3, 4, 0, 5, [1], [], logistron=True, abilities=[
    Ability("Cartas vinculadas a ~ no ascienden pero ganan +2 HP.", AbilityType.GENERAL, "permanent")
])
_c("Conducto Subterráneo", Color.LOGISTRON, 2, 2, 0, 4, [1,2], [], logistron=True, abilities=[
    Ability("[1]: teletransporta aliado L1→L2 o L2→L1. No cuenta como ascenso.", AbilityType.ACTIVE, "active", action_cost=1)
])

# ─── Wave 10 (351-370) — Más Anclados L1/L2 ───

_c("Minero Subterráneo", Color.SABOTEADOR, 3, 3, 1, 2, [1,2], ["triangle"], [
    Ability("[1]: destruye un vínculo entre dos cartas en L1 o L2.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Envenenador de Suministros", Color.SABOTEADOR, 2, 2, 0, 2, [1], ["square"], [
    Ability("En cuadrado: cartas enemigas en L1 pierden 1 HP al final del turno.", AbilityType.FORMATION, "end_of_turn", formation_required="square")
])
_c("Saboteadora de Retaguardia", Color.SABOTEADOR, 3, 2, 1, 2, [1,2], ["triangle","square"], [
    Ability("Cuando destruye un vínculo: roba 1 carta.", AbilityType.GENERAL, "on_trigger")
])
_c("Cazador de Nodos", Color.SABOTEADOR, 2, 3, 2, 1, [1,2], ["triangle"], [
    Ability("Al atacar nodo en L1/L2: ignora vínculos defensivos del objetivo.", AbilityType.GENERAL, "on_attack")
])

_c("Bardo de la Retaguardia", Color.FESTIVO, 3, 2, 0, 3, [1], ["square","pentagon"], [
    Ability("Tus cartas en L1 ganan +1 V mientras esté en juego.", AbilityType.GENERAL, "permanent")
])
_c("Corista del Muro", Color.FESTIVO, 3, 2, 0, 2, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: cura 2 HP a una carta en L1 o L2.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Flautista de la Vanguardia", Color.FESTIVO, 3, 2, 1, 3, [1,2], ["triangle","square"], [
    Ability("En triángulo: cartas vinculadas a ~ no pueden ser objetivo de habilidades enemigas.", AbilityType.FORMATION, "permanent", formation_required="triangle")
])
_c("Tambor de Guerra", Color.FESTIVO, 2, 3, 0, 2, [1,2], ["square"], [
    Ability("En cuadrado: tus escuadrones en L1,L2 ganan +2 daño base este turno.", AbilityType.FORMATION, "active", formation_required="square")
])

_c("Espía de Trinchera", Color.SABOTEADOR, 2, 2, 0, 2, [1,2], ["triangle"], [
    Ability("Espía. Se infiltra a L1 o L2 enemigo. No asciende una vez infiltrado.", AbilityType.GENERAL, "permanent")
], spy=True)
_c("Agente Latente", Color.SABOTEADOR, 1, 3, 1, 3, [1,2], ["triangle","square"], [
    Ability("Espía. Al infiltrar: mira carta enemiga en L1/L2. Si es Logistrón, destrúyela.", AbilityType.GENERAL, "on_trigger")
], spy=True)

_c("Ingeniero de Retaguardia", Color.INCOLORO, 3, 3, 0, 3, [1,2], ["square","pentagon"], [
    Ability("[1]: repara 2 sellos. Solo en L1 o L2.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Mercenario Leal", Color.INCOLORO, 3, 3, 2, 1, [1,2], ["triangle"], [
    Ability("Mientras esté en L1/L2 vinculado a Logistrón: +2 D.", AbilityType.GENERAL, "permanent")
])
_c("Vagabundo del Páramo", Color.INCOLORO, 5, 2, 1, 2, [1,2], ["triangle"], [
    Ability("[1]: descarta 2. Busca en tu reserva una carta y ponla en tu mano.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Artillero de Retaguardia", Color.INCOLORO, 2, 2, 2, 1, [1,2], ["triangle"], [
    Ability("Al atacar desde L2: ignora 3 de armadura del objetivo.", AbilityType.GENERAL, "on_attack")
])
_c("Coloso Anclado", Color.INCOLORO, 2, 8, 3, 1, [1], ["triangle"], [
    Ability("No puede ascender ni ser movido. No puede ser objetivo de espías.", AbilityType.GENERAL, "permanent")
])
_c("Mensajero del Frente", Color.INCOLORO, 5, 1, 0, 3, [1,2], ["triangle","square","pentagon"], [
    Ability("[1]: intercambia ~ con aliado en L3. No cuenta como ascenso.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Abad del Voto Inquebrantable", Color.SELLADOR, 1, 5, 1, 3, [1], ["square","pentagon"], [
    Ability("En cuadrado: tus cartas en L1 ganan +2 HP permanentemente. No asciende.", AbilityType.FORMATION, "active", formation_required="square")
])
_c("Prior del Santuario", Color.SELLADOR, 2, 4, 0, 4, [1,2], ["square"], [
    Ability("[1]: destruye un vínculo enemigo hacia tu L1 o L2.", AbilityType.ACTIVE, "active", action_cost=1)
])

_c("Destiladora de Defensas", Color.ALQUIMISTA, 3, 3, 0, 2, [1,2], ["triangle","square"], [
    Ability("[1]: carta en L1/L2 gana +2 HP y +1 D este turno.", AbilityType.ACTIVE, "active", action_cost=1)
])
_c("Alquimista de la Forma", Color.ALQUIMISTA, 2, 2, 0, 4, [1], ["triangle","square","pentagon"], [
    Ability("En pentágono: tus cartas en L1 forman pentágonos sin restricción.", AbilityType.FORMATION, "permanent", formation_required="pentagon")
])

# Legacy alias
MINI_SET = ALL_CARDS

# ─── Vanguardia & Línea de fuego distribution ───
# Regla nueva: cartas entran por defecto en L1
# Vanguardia: permite entrada directa en L2 (~30% de cartas con L2)
# Línea de fuego: permite entrada directa en L3 (~30% de cartas con L3)
import random as _random
_random.seed(42)

_l2_cards = [c for c in ALL_CARDS if 2 in c.allowed_layers and not c.is_spy and not c.is_logistron]
_l3_cards = [c for c in ALL_CARDS if 3 in c.allowed_layers and not c.is_spy and not c.is_logistron]

_vg = _random.sample([c.name for c in _l2_cards], max(1, int(len(_l2_cards) * 0.30)))
_lf = _random.sample([c.name for c in _l3_cards], max(1, int(len(_l3_cards) * 0.30)))

_vg_set = set(_vg)
_lf_set = set(_lf)

for c in ALL_CARDS:
    if c.name in _vg_set:
        if not any("Vanguardia" in a.description for a in c.abilities):
            c.abilities.append(Ability("Vanguardia: puede entrar directamente en L2.", AbilityType.GENERAL, "on_enter"))
    if c.name in _lf_set:
        if not any("Línea de fuego" in a.description for a in c.abilities):
            c.abilities.append(Ability("Línea de fuego: puede entrar directamente en L3.", AbilityType.GENERAL, "on_enter"))

del _random, _l2_cards, _l3_cards, _vg, _lf, _vg_set, _lf_set
