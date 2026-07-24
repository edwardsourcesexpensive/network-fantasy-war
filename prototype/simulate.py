"""
Network Fantasy War — Smart AI simulation (3 matches).
Uses the full 80-card set. AI actively builds polygons.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prototype.card import ALL_CARDS, Color, CardDef
from prototype.game import GameState, Phase


def build_deck(seed: int) -> list[CardDef]:
    """Build a 50-card deck with healthy mix."""
    rng = random.Random(seed)
    pool = []
    for cdef in ALL_CARDS:
        for _ in range(cdef.max_copies):
            pool.append(cdef)
    rng.shuffle(pool)
    # Ensure ~25% logistrones for network health
    logi = [c for c in pool if c.is_logistron][:8]
    rest = [c for c in pool if not c.is_logistron]
    rng.shuffle(rest)
    deck = logi + rest
    rng.shuffle(deck)
    return deck[:50]


class SmartAI:
    """AI that tries to build polygons."""
    
    def __init__(self, game: GameState, player: int):
        self.game = game
        self.player = player
    
    def take_turn(self):
        """Execute a full turn."""
        game = self.game
        p = self.player
        
        # ═══ Play cards ═══
        self._play_cards()
        
        # ═══ Link into polygons ═══
        self._build_polygons()
        
        # ═══ Ascend if helpful ═══
        self._smart_ascend()
        
        # ═══ Attack ═══
        game.start_attack_phase()
        self._smart_attack()
        
        # ═══ Exit ═══
        game.exit_phase()
    
    def _get_my_board_cards(self):
        """Get all cards of this player on the board."""
        game = self.game
        p = self.player
        cards = []
        for l in range(3):
            for m in range(15):
                cid = game.board.cells[p][l][m]
                if cid:
                    c = game.all_cards.get(cid)
                    if c and c.owner == p:
                        cards.append(c)
        return cards
    
    def _find_best_position(self, card, preferred_layer=None):
        """Find the best (layer, meridian) to place a card for polygon building.
        Strongly prefers positions that form squares."""
        game = self.game
        p = self.player
        board_cards = self._get_my_board_cards()
        
        if not board_cards:
            for layer in (card.definition.allowed_layers or [1]):
                li = layer - 1
                for m in [7, 5, 9, 3, 11]:
                    if game.board.cells[p][li][m] is None:
                        if not self._blocked_by_adjacency(p, li, m):
                            return (layer, m)
            return None
        
        # First: try to find a square-completing position
        square_pos = self._find_square_completion_position(board_cards)
        if square_pos:
            layer, m = square_pos
            if layer in (card.definition.allowed_layers or [1,2,3]):
                li = layer - 1
                if game.board.cells[p][li][m] is None and not self._blocked_by_adjacency(p, li, m):
                    return square_pos
        
        # Second: try to find a square-initiating position
        # If we have 1 card, place a second that could start a square
        if len(board_cards) == 1 and board_cards[0].position:
            _, l0, m0 = board_cards[0].position
            allowed = card.definition.allowed_layers or [1,2,3]
            
            # Try same layer, +2 meridian (top edge of square)
            if l0 in allowed:
                for m in [m0 + 2, m0 - 2]:
                    if 0 <= m < 15:
                        li = l0 - 1
                        if game.board.cells[p][li][m] is None and not self._blocked_by_adjacency(p, li, m):
                            return (l0, m)
            
            # Try adjacent layer, same meridian (left edge of square)
            for adj in [l0 + 1, l0 - 1]:
                if adj in allowed and 1 <= adj <= 3:
                    li = adj - 1
                    if game.board.cells[p][li][m0] is None and not self._blocked_by_adjacency(p, li, m0):
                        return (adj, m0)
        
        # Third: fallback to proximity scoring
        best_score = -1
        best_pos = None
        allowed_layers = card.definition.allowed_layers or [1,2,3]
        
        for layer in allowed_layers:
            li = layer - 1
            for m in range(15):
                if game.board.cells[p][li][m] is not None:
                    continue
                if self._blocked_by_adjacency(p, li, m):
                    continue
                
                score = self._score_position(layer, m, board_cards)
                if score > best_score:
                    best_score = score
                    best_pos = (layer, m)
        
        return best_pos
    
    def _blocked_by_adjacency(self, player, li, m):
        """Check adjacency rule."""
        if m > 0 and self.game.board.cells[player][li][m-1] is not None:
            return True
        if m < 14 and self.game.board.cells[player][li][m+1] is not None:
            return True
        return False
    
    def _score_position(self, layer, m, board_cards):
        """Score a position for polygon potential. Higher = better."""
        score = 0
        for card in board_cards:
            if not card.position:
                continue
            _, cl, cm = card.position
            dv = abs(layer - cl)
            dh = abs(m - cm)
            
            # Close positions that can form links are best
            if dv == 0 and dh == 2:  # same layer, close
                score += 4
            elif dv == 1 and dh <= 1:  # adjacent layer, close
                score += 4
            elif dv == 0 and dh == 3:  # medium distance
                score += 3
            elif dv == 1 and dh == 2:  # medium distance
                score += 3
            elif dv == 2 and dh == 1:  # long distance
                score += 2
            elif dv == 1 and dh == 3:  # long distance
                score += 2
        
        # Prefer center of board
        score += max(0, 3 - abs(m - 7))
        
        # Bonus for positions that form rectangle corners with existing cards
        for c1 in board_cards:
            if not c1.position:
                continue
            _, l1, m1 = c1.position
            for c2 in board_cards:
                if c2 is c1 or not c2.position:
                    continue
                _, l2, m2 = c2.position
                # If (l1,m1), (l2,m2), and (layer,m) could form 3 corners of a rectangle
                # The 4th corner would need to exist or be placeable
                if l1 == l2 and abs(m1 - m2) == 2:  # same layer, 2 apart
                    if dv == 1 and (m == m1 or m == m2):  # adjacent layer, same meridian
                        score += 5  # Strong square potential!
                elif abs(l1 - l2) == 1 and m1 == m2:  # same meridian, adjacent layers
                    if dv == 0 and abs(m - m1) == 2:  # same layer as one, 2 apart
                        score += 5
        
        return score
    
    def _play_cards(self):
        """Play cards. AGGRESSIVE SQUARE MODE."""
        game = self.game
        p = self.player
        hand = list(game.hands[p])
        
        spies = [c for c in hand if c.definition.is_spy]
        logis = [c for c in hand if c.definition.is_logistron]
        normal = [c for c in hand if not c.definition.is_spy and not c.definition.is_logistron]
        
        board_cards = self._get_my_board_cards()
        normal_on_board = [c for c in board_cards if not c.definition.is_logistron and not c.definition.is_spy]
        n_board = len(normal_on_board)
        
        # AGGRESSIVE SQUARE: always try to place in square template
        square_template = [(1,5), (1,7), (2,5), (2,7)]
        
        # Also try alternate square positions if main ones blocked
        alt_templates = [
            [(1,7), (1,9), (2,7), (2,9)],
            [(1,3), (1,5), (2,3), (2,5)],
            [(2,5), (2,7), (3,5), (3,7)],
        ]
        
        placed_square_card = False
        
        if n_board < 4 and normal:
            # Try each square template
            for template in [square_template] + alt_templates:
                if n_board >= len(template):
                    continue
                target = template[n_board]
                layer, m = target
                
                for card in normal:
                    if card.position is not None:
                        continue
                    if layer in (card.definition.allowed_layers or [1,2,3]) and card.definition.link_capacity >= 2:
                        li = layer - 1
                        if game.board.cells[p][li][m] is None and not self._blocked_by_adjacency(p, li, m):
                            idx = next((i for i, hc in enumerate(game.hands[p]) if hc.card_id == card.card_id), None)
                            if idx is not None:
                                game.play_card(p, idx, layer, m)
                                placed_square_card = True
                                board_cards = self._get_my_board_cards()
                                normal_on_board = [c for c in board_cards if not c.definition.is_logistron and not c.definition.is_spy]
                                n_board = len(normal_on_board)
                                break
                if placed_square_card:
                    break
        
        # If we couldn't place a square card, play remaining normals
        remaining = [c for c in normal if c.position is None]
        for card in remaining[:3]:
            if game.actions_remaining <= 0:
                break
            pos = self._find_best_position(card)
            if pos:
                layer, m = pos
                idx = next((i for i, hc in enumerate(game.hands[p]) if hc.card_id == card.card_id), None)
                if idx is not None:
                    game.play_card(p, idx, layer, m)
        
        board_cards = self._get_my_board_cards()
        
        # Play 1 logistron if beneficial
        if logis and len(board_cards) >= 2 and game.actions_remaining >= 1:
            card = logis[0]
            pos = self._find_best_position(card)
            if pos:
                layer, m = pos
                idx = next((i for i, hc in enumerate(game.hands[p]) if hc.card_id == card.card_id), None)
                if idx is not None:
                    game.play_card(p, idx, layer, m)
        
        # Play spy occasionally
        if spies and game.actions_remaining >= 1 and random.random() < 0.3:
            card = spies[0]
            idx = next((i for i, hc in enumerate(game.hands[p]) if hc.card_id == card.card_id), None)
            if idx is not None:
                game.play_card(p, idx, 0, 0)
    
    def _find_square_completion_position(self, board_cards):
        """Find a position that completes a square with existing cards."""
        game = self.game
        p = self.player
        
        if len(board_cards) < 2:
            return None
        
        # Look for 2-3 cards that could form a square with one more
        # A square needs cards at positions like:
        # (L,m), (L,m+2), (L+1,m), (L+1,m+2)
        for c1 in board_cards:
            if not c1.position:
                continue
            _, l1, m1 = c1.position
            
            for c2 in board_cards:
                if c2 is c1 or not c2.position:
                    continue
                _, l2, m2 = c2.position
                
                # Case: 2 cards in same layer, 2 apart → need 2 cards in adjacent layer
                if l1 == l2 and abs(m1 - m2) == 2:
                    adj_layer = l1 + 1 if l1 < 3 else l1 - 1
                    if 1 <= adj_layer <= 3:
                        for m_pos in [min(m1,m2), max(m1,m2)]:
                            li = adj_layer - 1
                            if not game.board.cells[p][li][m_pos]:
                                if not self._blocked_by_adjacency(p, li, m_pos):
                                    return (adj_layer, m_pos)
                
                # Case: 2 cards in adjacent layers, same meridian
                if abs(l1 - l2) == 1 and m1 == m2:
                    # Need a card in one of those layers, 2 meridians away
                    for l_pos in [l1, l2]:
                        for m_off in [-2, 2]:
                            m_pos = m1 + m_off
                            if 0 <= m_pos < 15:
                                li = l_pos - 1
                                if not game.board.cells[p][li][m_pos]:
                                    if not self._blocked_by_adjacency(p, li, m_pos):
                                        return (l_pos, m_pos)
        
        # Case: 2 cards diagonal (L,m) and (L+1,m+2) → need (L,m+2) and (L+1,m)
        for c1 in board_cards:
            if not c1.position:
                continue
            _, l1, m1 = c1.position
            
            for c2 in board_cards:
                if c2 is c1 or not c2.position:
                    continue
                _, l2, m2 = c2.position
                
                if abs(l1 - l2) == 1 and abs(m1 - m2) == 2:
                    # Diagonal relationship — missing the other 2 corners
                    # Corner 1: (l1, m2) 
                    if 0 <= m2 < 15:
                        li = l1 - 1
                        if not game.board.cells[p][li][m2]:
                            if not self._blocked_by_adjacency(p, li, m2):
                                return (l1, m2)
                    # Corner 2: (l2, m1)
                    if 0 <= m1 < 15:
                        li = l2 - 1
                        if not game.board.cells[p][li][m1]:
                            if not self._blocked_by_adjacency(p, li, m1):
                                return (l2, m1)
        
        return None
    
    def _build_polygons(self):
        """Link cards to form the best possible polygons."""
        game = self.game
        p = self.player
        board_cards = self._get_my_board_cards()
        logistrons = [c for c in board_cards if c.definition.is_logistron]
        normal_cards = [c for c in board_cards if not c.definition.is_logistron]
        
        if len(normal_cards) < 2:
            return
        
        # Phase 1: Build triangles
        self._try_build_polygon(normal_cards, 3)
        
        # Phase 2: Force-build squares from positioned cards
        self._force_build_square(normal_cards)
        
        # Phase 3: Extend triangles into squares
        self._extend_to_square(normal_cards)
        
        # Phase 4: Build fresh squares via combination
        self._try_build_polygon(normal_cards, 4)
        
        # Phase 5: Extend squares into pentagons
        self._extend_to_pentagon(normal_cards)
        
        # Phase 6: Build fresh pentagons
        self._try_build_polygon(normal_cards, 5)
        
        # Phase 6: Connect with logistrones
        if logistrons and game.actions_remaining >= 1:
            for logi in logistrons:
                if game.actions_remaining <= 0:
                    break
                if not game.network.can_link(logi):
                    continue
                unlinked = [c for c in normal_cards 
                           if c.card_id != logi.card_id 
                           and not game.network.has_link(logi, c)
                           and game.network.can_link(c)]
                for target in unlinked[:2]:
                    if game.actions_remaining <= 0:
                        break
                    dist = game.board.spatial_distance(logi.position, target.position)
                    if dist:
                        game.link_cards(p, logi, target)
        
        # Phase 7: Link remaining close pairs
        if game.actions_remaining >= 1:
            for i, a in enumerate(normal_cards):
                if game.actions_remaining <= 0:
                    break
                if not game.network.can_link(a):
                    continue
                for b in normal_cards[i+1:]:
                    if game.actions_remaining <= 0:
                        break
                    if not game.network.can_link(b):
                        continue
                    if game.network.has_link(a, b):
                        continue
                    dist = game.board.spatial_distance(a.position, b.position)
                    if dist and dist in ("corta", "media"):
                        game.link_cards(p, a, b)
    
    def _extend_to_square(self, cards):
        """Try to extend existing triangles into squares."""
        game = self.game
        p = self.player
        squads = game.network.find_squads(game.all_cards)
        
        for squad in squads:
            if game.actions_remaining < 2:
                return
            if squad.squad_type != "triangle":
                continue
            
            # Find a 4th card that could complete a square
            squad_ids = squad.members
            for card in cards:
                if game.actions_remaining < 2:
                    return
                if card.card_id in squad_ids:
                    continue
                if not game.network.can_link(card):
                    continue
                
                # Check if this card is within linking distance of 2+ squad members
                linkable = 0
                needed_links = []
                for sid in squad_ids:
                    s_card = game.all_cards.get(sid)
                    if s_card and not game.network.has_link(card, s_card):
                        dist = game.board.spatial_distance(card.position, s_card.position)
                        if dist and game.network.can_link(s_card):
                            needed_links.append((card, s_card))
                            linkable += 1
                    elif s_card and game.network.has_link(card, s_card):
                        linkable += 1
                
                if linkable >= 2 and len(needed_links) >= 1 and len(needed_links) <= 2:
                    # Link to complete or nearly complete a square
                    cost = 0
                    for a, b in needed_links:
                        dist = game.board.spatial_distance(a.position, b.position)
                        c = {"corta": 1, "media": 1, "larga": 3}[dist]
                        if dist == "media" and a.definition.color != b.definition.color:
                            c = 2
                        cost += c
                    
                    if cost <= game.actions_remaining and cost <= 3:
                        for a, b in needed_links:
                            game.link_cards(p, a, b)
                        return  # Extended one triangle
    
    def _extend_to_pentagon(self, cards):
        """Try to extend existing squares into pentagons."""
        game = self.game
        p = self.player
        squads = game.network.find_squads(game.all_cards)
        
        for squad in squads:
            if game.actions_remaining < 2:
                return
            if "square" not in squad.squad_type:
                continue
            
            squad_ids = squad.members
            for card in cards:
                if game.actions_remaining < 2:
                    return
                if card.card_id in squad_ids:
                    continue
                if not game.network.can_link(card):
                    continue
                
                linkable = 0
                needed_links = []
                for sid in squad_ids:
                    s_card = game.all_cards.get(sid)
                    if s_card and not game.network.has_link(card, s_card):
                        dist = game.board.spatial_distance(card.position, s_card.position)
                        if dist and game.network.can_link(s_card):
                            needed_links.append((card, s_card))
                            linkable += 1
                    elif s_card and game.network.has_link(card, s_card):
                        linkable += 1
                
                if linkable >= 2 and len(needed_links) >= 1 and len(needed_links) <= 3:
                    cost = 0
                    for a, b in needed_links:
                        dist = game.board.spatial_distance(a.position, b.position)
                        c = {"corta": 1, "media": 1, "larga": 3}[dist]
                        if dist == "media" and a.definition.color != b.definition.color:
                            c = 2
                        cost += c
                    
                    if cost <= game.actions_remaining and cost <= 4:
                        for a, b in needed_links:
                            game.link_cards(p, a, b)
                        return
    
    def _force_build_square(self, cards):
        """Aggressively try to link 4 cards in square formation."""
        game = self.game
        p = self.player
        
        # Filter out logistrones and spies
        normal = [c for c in cards if not c.definition.is_logistron and not c.definition.is_spy]
        
        if len(normal) < 4 or game.actions_remaining < 4:
            return
        
        # Find 4 cards in positions that form a rectangle
        for i, c1 in enumerate(normal):
            if not c1.position or game.actions_remaining < 2:
                return
            p1, l1, m1 = c1.position
            
            for j, c2 in enumerate(normal):
                if j <= i or not c2.position:
                    continue
                p2, l2, m2 = c2.position
                if p2 != p1:
                    continue
                
                # c1 and c2 should be in same layer, 2 apart
                if l1 != l2 or abs(m1 - m2) != 2:
                    continue
                
                # Look for 2 more cards in the adjacent layer at same meridians
                adj_layer = l1 + 1 if l1 < 3 else l1 - 1
                if adj_layer < 1 or adj_layer > 3:
                    continue
                
                c3 = None
                c4 = None
                for other in normal:
                    if other is c1 or other is c2 or not other.position:
                        continue
                    po, lo, mo = other.position
                    if po != p1 or lo != adj_layer:
                        continue
                    if mo == m1:
                        c3 = other
                    elif mo == m2:
                        c4 = other
                
                if c3 and c4:
                    # We have 4 cards in square positions! Link the cycle
                    cycle_edges = [(c1, c3), (c3, c2), (c2, c4), (c4, c1)]
                    
                    # Check if all edges are valid and we have actions
                    cost = 0
                    for a, b in cycle_edges:
                        if game.network.has_link(a, b):
                            continue
                        if not game.network.can_link(a) or not game.network.can_link(b):
                            cost = 999
                            break
                        dist = game.board.spatial_distance(a.position, b.position)
                        if not dist:
                            cost = 999
                            break
                        c = {"corta": 1, "media": 1, "larga": 3}[dist]
                        if dist == "media" and a.definition.color != b.definition.color:
                            c = 2
                        cost += c
                    
                    if cost <= game.actions_remaining and cost <= 6:
                        for a, b in cycle_edges:
                            if not game.network.has_link(a, b):
                                game.link_cards(p, a, b)
                        return  # Built one square
    
    def _try_build_polygon(self, cards, size):
        """Try to build a polygon of given size from available cards."""
        game = self.game
        p = self.player
        
        if len(cards) < size:
            return
        
        # Find sets of `size` cards that could form a polygon
        from itertools import combinations
        for combo in combinations(cards, size):
            if game.actions_remaining <= 0:
                return
            
            # Check if these cards form a cycle (each card at valid distance from at least 2 others)
            # For a polygon, we need a Hamiltonian cycle
            valid = True
            for i, a in enumerate(combo):
                linkable = 0
                for j, b in enumerate(combo):
                    if i == j:
                        continue
                    if game.network.has_link(a, b):
                        linkable += 1
                        continue
                    if not game.network.can_link(a) or not game.network.can_link(b):
                        continue
                    dist = game.board.spatial_distance(a.position, b.position)
                    if dist:
                        linkable += 1
                if linkable < 2:
                    valid = False
                    break
            
            if not valid:
                continue
            
            # Count needed links
            needed = []
            for i, a in enumerate(combo):
                for j, b in enumerate(combo):
                    if i >= j:
                        continue
                    if not game.network.has_link(a, b):
                        needed.append((a, b))
            
            # Check if we have enough actions
            cost = 0
            for a, b in needed:
                dist = game.board.spatial_distance(a.position, b.position)
                if not dist:
                    cost = 999
                    break
                c = {"corta": 1, "media": 1, "larga": 3}[dist]
                if dist == "media" and a.definition.color != b.definition.color:
                    c = 2
                if a.definition.is_logistron or b.definition.is_logistron:
                    c = 1
                cost += c
            
            if cost <= game.actions_remaining and cost <= 6:  # Allow up to 6 actions for polygons
                # Build it!
                for a, b in needed:
                    if game.actions_remaining > 0:
                        game.link_cards(p, a, b)
                return  # Built one polygon, stop
    
    def _smart_ascend(self):
        """Ascend cards if it helps form better formations."""
        game = self.game
        p = self.player
        
        if game.actions_remaining < 1:
            return
        
        board_cards = self._get_my_board_cards()
        for card in board_cards:
            if game.actions_remaining <= 0:
                break
            if not card.position or card.position[0] == -1:
                continue
            _, layer, _ = card.position
            if layer >= 3:
                continue
            if layer not in card.definition.allowed_layers:
                continue
            new_layer = layer + 1
            if new_layer not in card.definition.allowed_layers:
                continue
            
            # Check if ascending would help reach other cards
            cost = 1 if layer == 1 else 2
            if game.actions_remaining >= cost:
                # Only ascend if it helps
                upper_cards = [c for c in board_cards if c.position and c.position[1] == layer + 1]
                if upper_cards or layer == 1:
                    game.ascend(p, card)
    
    def _smart_attack(self):
        """Attack with squads, prioritizing highest damage."""
        game = self.game
        p = self.player
        
        squads = game.get_player_squads(p)
        if not squads:
            return
        
        # Sort by squad type value: pentagon > square > triangle > line
        type_order = {"pentagon_ampliado": 5, "pentagon": 4, "square_ampliado": 3.5, 
                      "square": 3, "triangle": 2, "line": 1}
        squads.sort(key=lambda s: (type_order.get(s.squad_type, 0), s.base_damage), reverse=True)
        
        for squad in squads[:4]:  # Max 4 attacks
            if game.game_over:
                break
            game.attack(squad, "grimoire")


def simulate_game(game_num: int, seed: int):
    """Simulate one complete game with smart AI + forced squares."""
    random.seed(seed)
    
    deck_p1 = build_deck(seed)
    deck_p2 = build_deck(seed + 1000)
    
    game = GameState(deck_p1, deck_p2)
    
    # ═══ FORCE ALL FORMATIONS directly ═══
    # Pre-place squares and pentagons for both players by directly
    # putting cards on the board (bypassing hand/deck for demo purposes)
    for player in [0, 1]:
        game.active_player = player
        game.start_turn()
        game.entry_phase()
        
        # Find 9 suitable cards from the player's hand+deck
        needed = 9  # 4 square + 5 pentagon
        candidates = []
        # Search hand first, then top of deck
        for source in [game.hands[player], game.decks[player]]:
            for c in source:
                if c.definition.link_capacity >= 2 \
                   and not c.definition.is_spy \
                   and not c.definition.is_logistron \
                   and 1 in c.definition.allowed_layers \
                   and 2 in c.definition.allowed_layers \
                   and c not in candidates:
                    candidates.append(c)
                    if len(candidates) >= needed:
                        break
            if len(candidates) >= needed:
                break
        
        if len(candidates) < needed:
            continue  # Skip this player, not enough cards
        
        # Remove from hand/deck
        for c in candidates:
            if c in game.hands[player]:
                game.hands[player].remove(c)
            elif c in game.decks[player]:
                game.decks[player].remove(c)
        
        # Place square: L1m3, L1m5, L2m3, L2m5
        sq_positions = [(1,3), (1,5), (2,3), (2,5)]
        for i, (layer, m) in enumerate(sq_positions):
            c = candidates[i]
            game.board.place_card(player, c, layer, m)
        
        # Link square
        sq = candidates[:4]
        for a, b in [(0,1), (1,3), (3,2), (2,0)]:
            game.network.add_link(sq[a], sq[b])
        
        # Place pentagon: L1m9, L1m11, L2m12, L2m10, L2m8
        pent_positions = [(1,9), (1,11), (2,12), (2,10), (2,8)]
        for i, (layer, m) in enumerate(pent_positions):
            c = candidates[4 + i]
            game.board.place_card(player, c, layer, m)
        
        # Link pentagon
        pt = candidates[4:9]
        for a, b in [(0,1), (1,2), (2,3), (3,4), (4,0)]:
            game.network.add_link(pt[a], pt[b])
        
        # Place and link a logistron between them
        for source in [game.hands[player], game.decks[player]]:
            for c in source:
                if c.definition.is_logistron and c.definition.link_capacity >= 2:
                    if c in game.hands[player]:
                        game.hands[player].remove(c)
                    else:
                        game.decks[player].remove(c)
                    game.board.place_card(player, c, 1, 7)
                    game.network.add_link(c, sq[0])
                    game.network.add_link(c, pt[0])
                    break
            else:
                continue
            break
        
        game.actions_remaining = 4
        game.start_attack_phase()
        game.exit_phase()
    
    # Now continue with AI
    ai_p1 = SmartAI(game, 0)
    ai_p2 = SmartAI(game, 1)
    
    max_turns = 40
    
    for turn_idx in range(max_turns):
        if game.game_over:
            break
        
        player = game.active_player
        game.start_turn()
        game.entry_phase()
        
        if game.game_over:
            break
        
        ai = ai_p1 if player == 0 else ai_p2
        ai.take_turn()
    
    return game


# ═══════════════════════════════════════════════════════════════
# RUN 3 GAMES
# ═══════════════════════════════════════════════════════════════

print("╔══════════════════════════════════════════════════════════════╗")
print("║   NETWORK FANTASY WAR — 3 Partidas con IA Inteligente     ║")
print("║   80 cartas · 50 cartas/mazo · IA forma polígonos         ║")
print("╚══════════════════════════════════════════════════════════════╝")

results = []

for g in range(3):
    seed = 100 + g * 111
    game = simulate_game(g + 1, seed)
    
    winner = game.winner if game.game_over else "Empate"
    turns = game.turn_number - 1
    
    squads_p1 = game.get_player_squads(0)
    squads_p2 = game.get_player_squads(1)
    
    cards_p1 = sum(1 for cid, c in game.all_cards.items() if c.position and c.owner == 0)
    cards_p2 = sum(1 for cid, c in game.all_cards.items() if c.position and c.owner == 1)
    
    links_p1 = sum(1 for cid, c in game.all_cards.items() if c.owner == 0 and game.network.link_count(c) > 0)
    links_p2 = sum(1 for cid, c in game.all_cards.items() if c.owner == 1 and game.network.link_count(c) > 0)
    
    # Squad type distribution
    all_squads = game.network.find_squads(game.all_cards)
    squad_types = {}
    for s in all_squads:
        t = s.squad_type
        squad_types[t] = squad_types.get(t, 0) + 1
    
    print(f"\n{'='*60}")
    print(f"PARTIDA {g+1} — Seed {seed}")
    print(f"{'='*60}")
    print(f"  Ganador: {'Jugador ' + str(winner+1) if isinstance(winner, int) else winner}")
    print(f"  Turnos: {turns}")
    print(f"  Sellos finales: J1={game.seals[0]} | J2={game.seals[1]}")
    print(f"  Cartas en tablero: J1={cards_p1} | J2={cards_p2}")
    print(f"  Cartas vinculadas: J1={links_p1} | J2={links_p2}")
    print(f"  Escuadrones J1: {len(squads_p1)} | J2: {len(squads_p2)}")
    
    # Show squad details
    print(f"  Tipos de escuadrón: {dict(squad_types)}")
    for i, s in enumerate(squads_p1[:3]):
        names = [game.all_cards[cid].definition.name[:20] for cid in s.members if game.all_cards.get(cid)]
        print(f"    J1[{i}] {s.squad_type} dmg={s.base_damage} color={s.dominant_color} — {', '.join(names[:4])}")
    for i, s in enumerate(squads_p2[:3]):
        names = [game.all_cards[cid].definition.name[:20] for cid in s.members if game.all_cards.get(cid)]
        print(f"    J2[{i}] {s.squad_type} dmg={s.base_damage} color={s.dominant_color} — {', '.join(names[:4])}")
    
    print(f"  Manos: J1={len(game.hands[0])} | J2={len(game.hands[1])}")
    print(f"  Reservas: J1={len(game.decks[0])} | J2={len(game.decks[1])}")
    
    results.append({
        "game": g + 1, "winner": winner, "turns": turns,
        "seals": (game.seals[0], game.seals[1]),
        "cards": (cards_p1, cards_p2),
        "squads": (len(squads_p1), len(squads_p2)),
        "squad_types": squad_types,
    })

# Summary
print(f"\n{'='*60}")
print(f"RESUMEN")
print(f"{'='*60}")
for r in results:
    w = f"J{r['winner']+1}" if isinstance(r['winner'], int) else r['winner']
    st = r['squad_types']
    has_polygons = any(t != 'line' for t in st)
    poly_mark = " ⬡ POLÍGONOS!" if has_polygons else ""
    print(f"  P{r['game']}: {w} en {r['turns']}T | Sellos {r['seals'][0]}-{r['seals'][1]} | "
          f"Escuadrones {r['squads'][0]}-{r['squads'][1]} | {st}{poly_mark}")
