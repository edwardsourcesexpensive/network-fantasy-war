"""
Network Fantasy War — Preconstructed Decks
8 themed 50-card decks built from the 300-card pool.
"""
from .card import ALL_CARDS, CardDef

# Build a lookup by name
_CARD_BY_NAME: dict[str, CardDef] = {c.name: c for c in ALL_CARDS}


def _get(name: str, count: int) -> list[CardDef]:
    """Get `count` copies of a card by name."""
    card = _CARD_BY_NAME.get(name)
    if not card:
        raise KeyError(f"Card not found: {name}")
    return [card] * count


def build_deck(name: str) -> list[CardDef]:
    """Build a 50-card deck by name."""
    deck = DECKS.get(name)
    if not deck:
        raise KeyError(f"Deck not found: {name}. Available: {list(DECKS.keys())}")
    cards = []
    for card_def in deck:
        cards.append(card_def)
    return cards


# ═══════════════════════════════════════════════════════════
# Deck definitions (each returns 50 CardDefs)
# ═══════════════════════════════════════════════════════════

def _deck_muro() -> list[CardDef]:
    """Mazo 1: Muro Inquebrantable v5 (Sellador + Festivo + anclados)"""
    return [
        # Selladores clásicos
        *_get("Abadesa del Voto Eterno", 2),
        *_get("Monje del Sello Silente", 2),
        *_get("Arquitecta del Muro", 2),
        *_get("Baluarte Inamovible", 2),
        *_get("Defensora Abnegada", 2),
        # Selladores anclados L1/L2
        *_get("Sumo Sacerdote", 1),
        *_get("Abad del Voto Inquebrantable", 1),
        *_get("Prior del Santuario", 2),
        *_get("Arquitecta de Fortalezas", 2),
        # Templarios
        *_get("Campeón del Filo Carmesí", 2),
        *_get("Rompe-escudos", 2),
        # Festivos anclados
        *_get("Bardo de la Retaguardia", 2),
        *_get("Tambor de Guerra", 2),
        *_get("Corista del Muro", 2),
        # Incoloros anclados
        *_get("Coloso Anclado", 2),
        *_get("Ingeniero de Retaguardia", 2),
        *_get("Mercenario Leal", 2),
        *_get("Mercenario sin Bandera", 1),   # Fase E1: ignore_color test
        *_get("Conducto Primario", 1),        # Fase E1: logistron_multiplier test
        # Logistrones
        *_get("Núcleo de Enlace", 3),
        *_get("Nodo Ancla", 2),
        *_get("Enrutador de Retaguardia", 2),
        *_get("Conmutador", 2),
        *_get("Microenlace", 2),
        *_get("Enlace Básico", 2),
    ]


def _deck_filo() -> list[CardDef]:
    """Mazo 2: Filo Carmesí v5 (Guerrero + Militar + anclados)"""
    return [
        *_get("Campeón del Filo Carmesí", 3),
        *_get("Berserker del Filo", 3),
        *_get("Estandarte Carmesí", 2),
        *_get("Duelista de la Brecha", 2),
        *_get("Lancero de Vanguardia", 3),
        *_get("Espadachín Veloz", 3),
        *_get("Rompe-escudos", 2),
        # Guerreros anclados
        *_get("Berserker de la Brecha", 2),
        *_get("Armero Real", 2),
        # Militares
        *_get("Sargento de la Escala de Hierro", 3),
        *_get("Recluta de la Escala", 3),
        *_get("Instructor de Reclutas", 2),
        *_get("Francotirador de Élite", 2),
        *_get("Comandante de Teatro", 2),
        *_get("Cadete", 2),
        # Incoloros anclados
        *_get("Artillero de Retaguardia", 2),
        # Logistrones
        *_get("Núcleo de Enlace", 2),
        *_get("Retransmisor de Batalla", 2),
        *_get("Plataforma de Asedio", 2),
        *_get("Conducto Subterráneo", 2),
        *_get("Microenlace", 2),
    ]


def _deck_sombras() -> list[CardDef]:
    """Mazo 3: Red de Sombras (Saboteador + Espía + Monstruo)"""
    return [
        *_get("Agente del Silencio", 2),
        *_get("Sabueso del Nexo", 2),
        *_get("Anuladora de Enlaces", 2),
        *_get("Saboteadora de Capas", 2),
        *_get("Zapador de Trincheras", 2),
        *_get("Virus de Red", 1),
        *_get("Saboteador Novato", 2),
        *_get("Cortacircuitos", 2),
        *_get("Saboteadora de Formaciones", 2),
        *_get("Incendiaria de Archivos", 2),
        *_get("Sombra Infiltrada", 2),
        *_get("Eco de la Frontera", 2),
        *_get("Agente Durmiente", 1),
        *_get("Cazador de Secretos", 2),
        *_get("Doble Agente", 1),
        *_get("Topo Paciente", 1),
        *_get("Merodeador", 1),
        *_get("Observador", 1),
        *_get("Engendro del Vacío", 2),
        *_get("Acechador de las Sombras", 2),
        *_get("Cría Voraz", 2),
        *_get("Depredador Nocturno", 2),
        *_get("Bestia Callejera", 2),
        *_get("Saboteador de Campo", 2),
        *_get("Núcleo de Enlace", 2),
        # Saboteadores anclados Wave 9-10
        *_get("Minero Subterráneo", 2),
        *_get("Saboteadora de Retaguardia", 2),
        *_get("Cazador de Nodos", 2),
    ]


def _deck_colegio() -> list[CardDef]:
    """Mazo 4: Colegio Arcano (Alquimista + Sabio + Naturaleza)"""
    return [
        *_get("Transmutadora del Espectro", 2),
        *_get("Mutacromática", 2),
        *_get("Sintetista de Esencias", 2),
        *_get("Destiladora de Pigmentos", 2),
        *_get("Alquimista de Guerra", 2),
        *_get("Alquimista de Campo", 2),
        *_get("Aprendiz de Alquimia", 2),
        *_get("Archivera del Conocimiento Perdido", 2),
        *_get("Bibliotecaria de los Ecos", 2),
        *_get("Oráculo del Nexo", 1),
        *_get("Cartógrafa de la Red", 2),
        *_get("Cronista de Batallas", 2),
        *_get("Visionaria del Nexo", 2),
        *_get("Estudiante Aplicado", 2),
        *_get("Aprendiz de Biblioteca", 2),
        *_get("Guardián del Bosque de Raíces", 2),
        *_get("Enredadera Vincular", 2),
        *_get("Árbol Primigenio", 2),
        *_get("Espora Expansiva", 2),
        *_get("Raíz Madre", 2),
        *_get("Brote Temprano", 2),
        *_get("Manto de Hojas", 2),
        *_get("Núcleo de Enlace", 2),
        *_get("Enrutador de Batalla", 1),
        *_get("Elixirista", 1),
        # Anclados Wave 9-10
        *_get("Reina Madre", 1),
        *_get("Maestro de la Vanguardia", 2),
    ]
    


def _deck_asamblea() -> list[CardDef]:
    """Mazo 5: Asamblea Popular v4 (Políticos ofensivos + Incoloros)"""
    return [
        # Políticos ofensivos (Wave 8)
        *_get("Alcalde de Guerra", 2),
        *_get("Recaudador de Impuestos", 2),
        *_get("Señor de la Guerra Civil", 2),
        *_get("Alcaldesa del Pueblo", 2),
        *_get("Comisario Político", 2),
        *_get("Diputado Belicoso", 2),
        *_get("Canciller de Guerra", 2),
        # Políticos clásicos
        *_get("Estratega de los Cien Hilos", 2),
        *_get("Tejedor de Alianzas", 2),
        *_get("Virrey de la Frontera", 2),
        *_get("Canciller del Tesoro", 2),
        *_get("Ministro de Guerra", 2),
        # Incoloros sinérgicos
        *_get("Rebelde Armado", 3),
        *_get("Guardaespaldas del Concejo", 2),
        *_get("Multitud Enfurecida", 3),
        *_get("Asesor Sombrío", 2),
        *_get("Forajido", 2),
        *_get("Gladiador", 2),
        *_get("Señor de la Guerra", 1),
        # Logistrones
        *_get("Núcleo de Enlace", 3),
        *_get("Conmutador", 2),
        # Anclados Wave 9-10
        *_get("Estratega de la Defensa", 2),
        *_get("Ingeniero de Retaguardia", 2),
        *_get("Pregonero del Pueblo", 2),
    ]


def _deck_legion() -> list[CardDef]:
    """Mazo 6: Legión de Acero v3 (Militar ascenso + Guerrero daño)"""
    return [
        # Militares (ascensos y sinergia)
        *_get("Sargento de la Escala de Hierro", 2),
        *_get("Recluta de la Escala", 2),
        *_get("General de la Escala de Hierro", 1),
        *_get("Instructor de Reclutas", 2),
        *_get("Comandante de Teatro", 2),
        *_get("Recluta Fresco", 2),
        *_get("Teniente", 2),
        *_get("Coronel", 2),
        *_get("Mariscal Supremo", 1),
        *_get("Almirante Supremo", 1),
        *_get("Soldado Raso", 2),
        # Guerreros (daño puro)
        *_get("Campeón del Filo Carmesí", 2),
        *_get("Berserker del Filo", 2),
        *_get("Estandarte Carmesí", 2),
        *_get("Lancero de Vanguardia", 2),
        *_get("Espadachín Veloz", 2),
        *_get("Berserker del Norte", 2),
        *_get("Jefe de Guerra", 1),
        # Logistrones ofensivos
        *_get("Retransmisor de Batalla", 2),
        *_get("Plataforma de Asedio", 2),
        *_get("Conducto de Energía", 2),
        *_get("Núcleo de Enlace", 2),
        *_get("Microenlace", 1),
        # Incoloro
        *_get("Coloso de Guerra", 2),
        *_get("Señor de la Guerra", 1),
        # Anclados Wave 9-10
        *_get("Capitana de la Guardia", 2),
        *_get("Centinela de la Puerta", 2),
        *_get("Mensajero del Frente", 2),
    ]


def _deck_jardin() -> list[CardDef]:
    """Mazo 7: Jardín Salvaje (Naturaleza + Monstruo)"""
    return [
        *_get("Guardián del Bosque de Raíces", 2),
        *_get("Enredadera Vincular", 2),
        *_get("Árbol Primigenio", 2),
        *_get("Espora Expansiva", 2),
        *_get("Bosque Andante", 2),
        *_get("Raíz Madre", 2),
        *_get("Enredadera Estranguladora", 2),
        *_get("Polinizadora de Esencias", 2),
        *_get("Árbol del Fin de los Tiempos", 1),
        *_get("Brote Silvestre", 2),
        *_get("Vid Espinosa", 2),
        *_get("Roble Ancestral", 2),
        *_get("Bosque Protector", 1),
        *_get("Madre Tierra", 1),
        *_get("Hiedra Trepadora", 2),
        *_get("Jardín de Piedra", 2),
        *_get("Yggdrasil", 1),
        *_get("Engendro del Vacío", 2),
        *_get("Acechador de las Sombras", 2),
        *_get("Cría Voraz", 2),
        *_get("Hidra Regenerativa", 2),
        *_get("Gigante de Piedra", 2),
        *_get("Depredador Alfa", 1),
        *_get("Kaiju Primordial", 1),
        *_get("Núcleo de Enlace", 2),
        *_get("Enjambre de Enlace", 1),
        # Anclados Wave 9-10
        *_get("Muro Viviente", 1),
        *_get("Enredadera de Raíz Profunda", 2),
        *_get("Bestia de Guarida", 2),
    ]


def _deck_consejo() -> list[CardDef]:
    """Mazo 8: Consejo Arcano v5 (Alquimistas + Sabios + anclados)"""
    return [
        # Alquimistas tanque
        *_get("Alquimista Acorazado", 3),
        *_get("Golem Alquímico", 2),
        *_get("Homúnculo de Batalla", 2),
        # Alquimistas anclados
        *_get("Destiladora de Defensas", 2),
        *_get("Alquimista de la Forma", 1),
        *_get("Alquimista de Trinchera", 2),
        # Sabios batalla
        *_get("Estratega de Campo", 3),
        *_get("Profesor de Combate", 2),
        # Sabios anclados
        *_get("Sabio Ermitaño", 1),
        *_get("Maestro de la Vanguardia", 2),
        *_get("Mente Colmena", 2),
        # Naturaleza anclada
        *_get("Muro Viviente", 1),
        *_get("Enredadera de Raíz Profunda", 2),
        *_get("Guardián del Bosque de Raíces", 2),
        # Incoloros
        *_get("Canalizador Arcano", 2),
        *_get("Místico del Nexo", 1),
        *_get("Mensajero del Frente", 2),
        *_get("Coloso Anclado", 2),
        # Logistrones anclados
        *_get("Torre de Señal", 2),
        *_get("Conducto Subterráneo", 2),
        *_get("Núcleo de Enlace", 2),
        *_get("Nodo Ancla", 2),
        *_get("Enrutador de Batalla", 2),
    ]


# Registry — pad to 50 cards
DECKS: dict[str, list[CardDef]] = {}
for name, fn in [
    ("muro", _deck_muro), ("filo", _deck_filo), ("sombras", _deck_sombras),
    ("colegio", _deck_colegio), ("asamblea", _deck_asamblea), ("legion", _deck_legion),
    ("jardin", _deck_jardin), ("consejo", _deck_consejo),
]:
    deck = fn()
    # Pad to 50 with extra logistrones
    while len(deck) < 50:
        deck.append(_CARD_BY_NAME["Núcleo de Enlace"])
    if len(deck) > 50:
        # Never silently drop cards — surface the overflow loudly (deck lists
        # are authored as exactly 50; a >50 list means new cards were appended
        # without rebalancing and would otherwise be lost to the slice below).
        dropped = deck[50:]
        print(f"WARNING: deck '{name}' has {len(deck)} cards, truncating to 50 — DROPPED: "
              f"{[c.name for c in dropped]}")
    DECKS[name] = deck[:50]

DECK_NAMES: dict[str, str] = {
    "muro": "Muro Inquebrantable (Sellador + Festivo)",
    "filo": "Filo Carmesí (Guerrero + Militar)",
    "sombras": "Red de Sombras (Saboteador + Espía + Monstruo)",
    "colegio": "Colegio Arcano (Alquimista + Sabio + Naturaleza)",
    "asamblea": "Asamblea Popular (Político + Incoloro)",
    "legion": "Legión de Acero (Militar + Guerrero)",
    "jardin": "Jardín Salvaje (Naturaleza + Monstruo)",
    "consejo": "Consejo Arcano (Alquimista + Sabio)",
}
