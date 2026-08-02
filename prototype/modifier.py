"""Modifier dataclass for the NFW passive ability dispatch system.

A Modifier is a data object registered by a card on the board.
When a card enters, its passive/trigger abilities are parsed into
Modifier objects and registered under the relevant hooks.
When the card leaves, its modifiers are removed.
"""

from dataclasses import dataclass, field


@dataclass
class Modifier:
    """A passive modifier registered by a card on the board.

    Attributes:
        source_card_id: which card created this modifier
        hook: which hook does this fire on (e.g. 'modify_squad')
        effect_type: what kind of effect (e.g. 'color_override', 'ignore_color')
        params: effect-specific parameters
        layer: scope — 'self', 'squad', 'network', 'global'
        priority: lower fires first (default 100)
        is_temporary: if True, cleaned in exit_phase (for temp buffs/colors)
    """
    source_card_id: int
    hook: str
    effect_type: str
    params: dict = field(default_factory=dict)
    layer: str = "self"
    priority: int = 100
    is_temporary: bool = False
