"""
Network Fantasy War - Digital Prototype
Board: battlefield state, positioning, distance calculations.
"""
from dataclasses import dataclass, field
from typing import Optional
from .card import CardInstance


# Board dimensions
NUM_LAYERS = 3   # L1, L2, L3
NUM_MERIDIANS = 15  # expandable


@dataclass
class Board:
    """
    The complete battlefield. Two territories (players 0 and 1).
    
    Player 0's territory: layers 1-3 (L1=front-line near frontier, L3=back near player? 
    Actually per the design: L1 is retaguardia (closest to player), L3 is closest to frontier.
    Wait, let me re-check: the design says L1 = retaguardia, L2 = vanguardia, L3 = squad leaders.
    And "L3 de cada jugador está junto a la frontera".
    So for player 0: L3 is at the top (near frontier), L1 at bottom (near player).
    For player 1 (on the other side of frontier): L3 is at the bottom, L1 at top.
    
    But for simplicity in the model, each player's territory is: L1=0 (closest to player), L2=1, L3=2 (closest to frontier).
    Frontier is between the two L3 rows.
    """
    cells: list[list[list[Optional[int]]]] = field(default_factory=list)
    # cells[player][layer][meridian] = card_id or None
    frontier_cards: list[int] = field(default_factory=list)  # card_ids on the frontier
    next_card_id: int = 0

    def __post_init__(self):
        if not self.cells:
            self.cells = [
                [[None for _ in range(NUM_MERIDIANS)] for _ in range(NUM_LAYERS)],
                [[None for _ in range(NUM_MERIDIANS)] for _ in range(NUM_LAYERS)],
            ]

    def _player_layer_to_grid(self, player: int, layer: int) -> int:
        """Convert player-relative layer (L1=0, L2=1, L3=2) to internal index."""
        return layer - 1  # L1->0, L2->1, L3->2

    def place_card(self, player: int, card: CardInstance, layer: int, meridian: int):
        """Place a card at (player, layer, meridian). Returns True if successful."""
        li = self._player_layer_to_grid(player, layer)
        if self.cells[player][li][meridian] is not None:
            return False
        if not self._can_place_horizontal(player, li, meridian):
            return False
        self.cells[player][li][meridian] = card.card_id
        card.position = (player, layer, meridian)
        return True

    def place_spy_frontier(self, card: CardInstance):
        """Place a spy on the frontier."""
        self.frontier_cards.append(card.card_id)
        card.position = (-1, 0, 0)  # Special position for frontier

    def _can_place_horizontal(self, player: int, layer_idx: int, meridian: int) -> bool:
        """Check the rule: no card adjacent horizontally to another in the same layer."""
        if meridian > 0 and self.cells[player][layer_idx][meridian - 1] is not None:
            return False
        if meridian < NUM_MERIDIANS - 1 and self.cells[player][layer_idx][meridian + 1] is not None:
            return False
        return True

    def remove_card(self, card: CardInstance):
        """Remove a card from the board."""
        if card.position is None:
            return
        p, layer, meridian = card.position
        if p == -1:  # Frontier
            if card.card_id in self.frontier_cards:
                self.frontier_cards.remove(card.card_id)
        else:
            li = self._player_layer_to_grid(p, layer)
            self.cells[p][li][meridian] = None
        card.position = None

    def get_card_at(self, player: int, layer: int, meridian: int) -> Optional[int]:
        """Get card_id at position, or None."""
        li = self._player_layer_to_grid(player, layer)
        return self.cells[player][li][meridian]

    def find_empty_meridian(self, player: int, layer: int) -> Optional[int]:
        """Find a valid meridian to place a card in the given layer."""
        li = self._player_layer_to_grid(player, layer)
        for m in range(NUM_MERIDIANS):
            if self.cells[player][li][m] is None and self._can_place_horizontal(player, li, m):
                return m
        return None

    def swap_cards(self, card_a: CardInstance, card_b: CardInstance):
        """Swap the board positions of two cards. Bypasses adjacency checks."""
        pos_a = card_a.position
        pos_b = card_b.position
        if not pos_a or not pos_b or pos_a[0] == -1 or pos_b[0] == -1:
            return False
        p_a, l_a, m_a = pos_a
        p_b, l_b, m_b = pos_b
        li_a = l_a - 1
        li_b = l_b - 1
        
        # Swap cell contents
        self.cells[p_a][li_a][m_a] = card_b.card_id
        self.cells[p_b][li_b][m_b] = card_a.card_id
        
        # Update card positions
        card_a.position = (p_b, l_b, m_b)
        card_b.position = (p_a, l_a, m_a)
        return True

    def spatial_distance(self, pos1: tuple, pos2: tuple) -> Optional[str]:
        """
        Calculate spatial distance between two positions.
        Returns: 'corta', 'media', 'larga', or None (invalid).
        
        pos = (player, layer, meridian) or (-1, 0, 0) for frontier.
        """
        if pos1[0] == -1 or pos2[0] == -1:
            return None  # Frontier distance rules are special (handled elsewhere)

        p1, l1, m1 = pos1
        p2, l2, m2 = pos2

        if p1 != p2:
            return None  # Cross-territory (handled by spy rules)

        dv = abs(l1 - l2)  # Vertical distance (in layers, L1-L3 = 0-2 apart)
        dh = abs(m2 - m1)  # Horizontal distance in meridians

        if dv == 0 and dh == 2:
            return "corta"
        if dv == 1 and dh <= 1:
            return "corta"
        if dv == 0 and dh == 3:
            return "media"
        if dv == 1 and dh == 2:
            return "media"
        if dv == 2 and dh <= 1:
            return "larga"
        if dv == 1 and dh == 3:
            return "larga"
        return None

    def get_all_cards(self, player: int) -> list[int]:
        """Get all card IDs on a player's territory."""
        result = []
        for layer in range(NUM_LAYERS):
            for meridian in range(NUM_MERIDIANS):
                cid = self.cells[player][layer][meridian]
                if cid is not None:
                    result.append(cid)
        return result


def find_best_meridian(board: Board, player: int, layer: int) -> Optional[int]:
    """Find any valid meridian (respecting the adjacency rule)."""
    return board.find_empty_meridian(player, layer)
