"""
Network Fantasy War - Digital Prototype
Network: links between cards, squad detection, potenciamiento calculation.
"""
from collections import defaultdict, deque
from typing import Optional
import itertools
from .card import CardInstance, Color


class Network:
    """
    Manages links between cards and computes squad formations + potenciamiento.
    Links are stored as adjacency list: {card_id: set(linked_card_ids)}
    """
    def __init__(self):
        self.links: dict[int, set[int]] = defaultdict(set)
        self.link_armor: dict[tuple, int] = defaultdict(int)

    def add_link(self, card_a: CardInstance, card_b: CardInstance):
        a, b = card_a.card_id, card_b.card_id
        self.links[a].add(b)
        self.links[b].add(a)

    def remove_link(self, card_a: CardInstance, card_b: CardInstance):
        a, b = card_a.card_id, card_b.card_id
        self.links[a].discard(b)
        self.links[b].discard(a)
        key = tuple(sorted((a, b)))
        self.link_armor.pop(key, None)

    def has_link(self, card_a: CardInstance, card_b: CardInstance) -> bool:
        return card_b.card_id in self.links[card_a.card_id]

    def get_links(self, card: CardInstance) -> set[int]:
        return self.links.get(card.card_id, set())

    def link_count(self, card: CardInstance) -> int:
        return len(self.links.get(card.card_id, set()))

    def can_link(self, card: CardInstance) -> bool:
        return self.link_count(card) < card.definition.link_capacity

    def remove_all_links(self, card: CardInstance):
        cid = card.card_id
        for neighbor in list(self.links.get(cid, set())):
            self.links[neighbor].discard(cid)
            key = tuple(sorted((cid, neighbor)))
            self.link_armor.pop(key, None)
        self.links.pop(cid, None)

    def break_all_squad_links(self, squad: "Squad"):
        """Remove all links belonging to members of a squad."""
        all_pairs = set()
        for cid in squad.members:
            for neighbor in list(self.links.get(cid, set())):
                pair = tuple(sorted((cid, neighbor)))
                all_pairs.add(pair)
        for a, b in all_pairs:
            self.links[a].discard(b)
            self.links[b].discard(a)
            self.link_armor.pop((a, b), None)

    def network_distance(self, card_a: CardInstance, card_b: CardInstance) -> Optional[int]:
        a, b = card_a.card_id, card_b.card_id
        if a == b:
            return 0
        if a not in self.links:
            return None
        visited = {a}
        queue = deque([(a, 0)])
        while queue:
            node, dist = queue.popleft()
            for neighbor in self.links.get(node, set()):
                if neighbor == b:
                    return dist + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))
        return None

    def connected_component(self, card: CardInstance) -> set[int]:
        start = card.card_id
        if start not in self.links:
            return {start}
        visited = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in self.links.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def find_squads(self, cards: dict[int, CardInstance]) -> list["Squad"]:
        """
        Find all squad formations in the network.
        
        Uses cycle detection: for each connected component of normal cards,
        check if it forms an n-cycle (polygon). Internal nodes connected to
        3+ members of the cycle indicate an "ampliado" formation.
        """
        squads = []
        processed = set()

        # Build subgraph of normal cards (non-logi, non-spy)
        normal_ids = {
            cid for cid, c in cards.items()
            if not c.definition.is_logistron and not c.definition.is_spy
        }

        # Squads are single-owner: split each connected component by owner so a
        # card linked to an ENEMY card (spy infiltration, frontier↔L3, etc.)
        # never merges both players into one squad. We compute components over
        # same-owner links only.
        def _owner(cid):
            c = cards.get(cid)
            return c.owner if c is not None else None

        # Find all connected components in the normal subgraph (same owner)
        visited_components = set()
        for cid in normal_ids:
            if cid in visited_components or cid not in self.links:
                if cid not in visited_components and cid not in processed:
                    # Isolated card - no squad
                    processed.add(cid)
                continue

            # BFS to find the component (only traverse same-owner links)
            component = set()
            queue = deque([cid])
            seed_owner = _owner(cid)
            while queue:
                node = queue.popleft()
                if node in visited_components:
                    continue
                visited_components.add(node)
                if node in normal_ids and _owner(node) == seed_owner:
                    component.add(node)
                    for neighbor in self.links.get(node, set()):
                        if (neighbor in normal_ids and neighbor not in visited_components
                                and _owner(neighbor) == seed_owner):
                            queue.append(neighbor)

            if len(component) < 2:
                for n in component:
                    processed.add(n)
                continue

            # Find cycles in this component
            component_squads = self._find_cycles_in_component(component, cards)
            squads.extend(component_squads)
            for s in component_squads:
                processed.update(s.members)

        # Detect lines: greedily pair remaining linked normal cards
        # Build the subgraph of remaining unprocessed cards
        remaining_ids = {cid for cid in normal_ids if cid not in processed and cid in self.links}
        if remaining_ids:
            # BFS to find connected components, then form lines from each
            # (same-owner only, so cross-owner links don't fuse lines)
            visited = set()
            for cid in remaining_ids:
                if cid in visited:
                    continue
                # BFS to get this component (same owner as the seed)
                component = set()
                queue = [cid]
                seed_owner = _owner(cid)
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    if _owner(node) != seed_owner:
                        continue
                    component.add(node)
                    for neighbor in self.links.get(node, set()):
                        if (neighbor in remaining_ids and neighbor not in visited
                                and _owner(neighbor) == seed_owner):
                            queue.append(neighbor)
                
                # Form maximal disjoint lines: each line is exactly 2 linked cards.
                # A card may belong to only ONE line (attack once per turn rule).
                # In a path A-B-C, we get line {A,B} and C stays unpaired.
                # In a path A-B-C-D, we get lines {A,B} and {C,D}.
                paired = set()
                # Sort for determinism; process nodes in order
                for a in sorted(component):
                    if a in paired:
                        continue
                    # Find the first unpaired neighbor in this component
                    for b in sorted(self.links.get(a, set())):
                        if b in component and b not in paired and b > a:
                            squads.append(Squad(
                                members={a, b},
                                squad_type="line",
                                cards=cards,
                                internal_nodes=0,
                            ))
                            paired.add(a)
                            paired.add(b)
                            break  # a is now used; move to next unpaired node
                
                # Remaining unpaired cards in this component
                for c in component - paired:
                    processed.add(c)
        
        # Handle any remaining cards as singletons
        for cid in normal_ids:
            if cid not in processed:
                processed.add(cid)

        return squads

    def _find_cycles_in_component(self, component: set[int],
                                   cards: dict[int, CardInstance]) -> list["Squad"]:
        """Find polygon cycles in a connected component."""
        squads = []
        remaining = set(component)

        # First, look for cycles using only cycle-degree nodes (degree 2 in subgraph)
        # Try from largest to smallest (pentagon > square > triangle)
        for target_size in [5, 4, 3]:
            while True:
                cycle = self._find_cycle_of_size(remaining, target_size, cards)
                if not cycle:
                    break

                # Check for internal nodes (ampliado)
                internals = self._find_internal_nodes(cycle, remaining, cards)
                all_members = cycle | internals

                type_map = {
                    3: "triangle",
                    4: "square",
                    5: "pentagon",
                }
                base_type = type_map[target_size]
                if internals:
                    base_type += "_ampliado"

                squad = Squad(
                    members=all_members,
                    squad_type=base_type,
                    cards=cards,
                    internal_nodes=len(internals)
                )
                squads.append(squad)
                remaining -= all_members

        # Post-process: reclassify pentagons that contain a 4-cycle as square_ampliado
        squads = self._reclassify_pentagons_as_ampliado(squads, cards)

        return squads

    def _reclassify_pentagons_as_ampliado(self, squads: list["Squad"],
                                           cards: dict[int, CardInstance]) -> list["Squad"]:
        """If a pentagon contains a 4-cycle, reclassify as square_ampliado."""
        result = []
        for squad in squads:
            if squad.squad_type not in ("pentagon", "pentagon_ampliado"):
                result.append(squad)
                continue
            # Skip if already ampliado — it has proper internal detection
            if squad.squad_type == "pentagon_ampliado":
                result.append(squad)
                continue
            if len(squad.members) < 5:
                result.append(squad)
                continue

            # Try all 4-node subsets to find a square cycle
            members_list = list(squad.members)
            best_square = None
            best_internal_count = -1
            best_result = None
            
            for subset in itertools.combinations(members_list, 4):
                subset_set = set(subset)
                cycle = self._find_cycle_of_size(subset_set, 4, cards)
                if not cycle:
                    continue
                
                # Score this 4-cycle: count how many remaining nodes are
                # connected to 3+ members of the cycle (these are internals)
                remaining = squad.members - cycle
                internals = set()
                for node in remaining:
                    links = self.links.get(node, set())
                    conns = sum(1 for m in cycle if m in links)
                    if conns >= 3:
                        internals.add(node)
                
                # Prefer the cycle that has the most internal nodes
                if len(internals) > best_internal_count:
                    best_internal_count = len(internals)
                    best_square = cycle
                    best_result = (cycle, internals, remaining - internals)
            
            if best_square:
                found_square, all_internals, other_remaining = best_result
                total_internal = len(all_internals)
                # Non-internal remaining nodes also stay in the squad
                # (they might be connected to 1-2 square members)
                
                result.append(Squad(
                    members=found_square | all_internals | other_remaining,
                    squad_type="square_ampliado" if total_internal > 0 else "square",
                    cards=cards,
                    internal_nodes=total_internal
                ))
            else:
                result.append(squad)

        return result

    def _find_cycle_of_size(self, nodes: set[int], size: int,
                            cards: dict[int, CardInstance]) -> Optional[set[int]]:
        """
        Find a simple cycle of exactly `size` nodes within `nodes`.
        Uses DFS with backtracking.
        Returns the set of nodes in the cycle, or None.
        """
        if len(nodes) < size:
            return None

        nodes_list = list(nodes)

        for start in nodes_list:
            path = [start]
            visited = {start}
            result = self._dfs_cycle(start, start, path, visited, size, nodes)
            if result:
                return set(result)
        return None

    def _dfs_cycle(self, start: int, current: int, path: list[int],
                   visited: set[int], target_size: int,
                   valid_nodes: set[int]) -> Optional[list[int]]:
        """DFS to find a cycle of target_size."""
        if len(path) == target_size:
            # Check if last node connects back to start
            if start in self.links.get(current, set()):
                return path
            return None

        if len(path) > target_size:
            return None

        for neighbor in self.links.get(current, set()):
            if neighbor not in valid_nodes:
                continue
            if neighbor in visited:
                continue
            # Prune: can't form a cycle if we can't reach start in remaining steps
            # (simple optimization - skip for now)

            path.append(neighbor)
            visited.add(neighbor)
            result = self._dfs_cycle(start, neighbor, path, visited, target_size, valid_nodes)
            if result:
                return result
            visited.discard(neighbor)
            path.pop()

        return None

    def _find_internal_nodes(self, cycle: set[int], remaining: set[int],
                             cards: dict[int, CardInstance]) -> set[int]:
        """Find nodes connected to 3+ members of the cycle (internal nodes)."""
        internal = set()
        for cid in remaining - cycle:
            if cid not in self.links:
                continue
            card = cards.get(cid)
            if card and card.definition.is_logistron:
                continue
            connections = sum(1 for m in cycle if m in self.links.get(cid, set()))
            if connections >= 3:
                internal.add(cid)
        return internal


class Squad:
    """A squad formation detected in the network."""
    def __init__(self, members: set[int], squad_type: str,
                 cards: dict[int, CardInstance], internal_nodes: int = 0):
        self.members = members
        self.squad_type = squad_type
        self.cards = cards
        self.internal_nodes = internal_nodes
        self.ignored_color_cards: set[int] = set()  # cards excluded from color majority

    @property
    def base_damage(self) -> int:
        table = {
            "line": 1,
            "triangle": 2,
            "square": 3,
            "square_ampliado": 3 + self.internal_nodes,
            "pentagon": 4,
            "pentagon_ampliado": 4 + (self.internal_nodes * 2),
        }
        return table.get(self.squad_type, 1)

    @property
    def empowerment(self) -> int:
        table = {
            "line": 1,
            "triangle": 3,
            "square": 5,
            "square_ampliado": 5 + self.internal_nodes,
            "pentagon": 7,
            "pentagon_ampliado": 7 + (self.internal_nodes * 2),
        }
        return table.get(self.squad_type, 0)

    @property
    def empowerment_range(self) -> int:
        table = {
            "line": 2,
            "triangle": 2,
            "square": 2,
            "square_ampliado": 2,
            "pentagon": 999,
            "pentagon_ampliado": 999,
        }
        return table.get(self.squad_type, 1)

    @property
    def dominant_color(self) -> Optional[Color]:
        return self.get_dominant_color({})

    def get_dominant_color(self, color_overrides: dict[int, Color]) -> Optional[Color]:
        color_counts = defaultdict(int)
        total = 0
        for cid in self.members:
            if cid in self.ignored_color_cards:
                continue
            card = self.cards.get(cid)
            if card and not card.definition.is_logistron:
                effective_color = color_overrides.get(cid, card.definition.color)
                color_counts[effective_color] += 1
                total += 1
        for color, count in color_counts.items():
            if count > total / 2:
                return color
        return None

    def contains_card(self, card_id: int) -> bool:
        return card_id in self.members

    def __repr__(self):
        internal_str = f" +{self.internal_nodes} int" if self.internal_nodes else ""
        return f"Squad({self.squad_type}{internal_str}, {len(self.members)} members, dmg={self.base_damage})"


def calculate_potenciamiento(attacking_squad: Squad, all_squads: list[Squad],
                              network: Network, cards: dict[int, CardInstance],
                              flat: bool = False) -> int:
    """Calculate total potenciamiento an attacking squad receives from friendly squads."""
    def _owner_of(cid):
        c = cards.get(cid)
        return c.owner if c is not None else None

    def _is_alive(cid):
        c = cards.get(cid)
        return c is not None and c.current_hp > 0

    attacking_owner = next(
        (_owner_of(m) for m in attacking_squad.members if _owner_of(m) is not None),
        None,
    )

    total = 0
    atk_ids = set(attacking_squad.members)
    for squad in all_squads:
        # Skip self by IDENTITY — find_squads() recomputes fresh Squad objects on
        # every call, so `squad is attacking_squad` is never True when the caller
        # passes a squad from a different find_squads() invocation.
        if set(squad.members) == atk_ids:
            continue
        # Only FRIENDLY squads contribute potenciamiento (same owner), and only
        # if they still have a living member — a wiped squad donates nothing.
        squad_owner = next(
            (_owner_of(m) for m in squad.members if _owner_of(m) is not None),
            None,
        )
        if attacking_owner is not None and squad_owner != attacking_owner:
            continue
        if not any(_is_alive(m) for m in squad.members):
            continue
        connected = False
        min_distance = float('inf')
        for a_member in attacking_squad.members:
            for b_member in squad.members:
                dist = network.network_distance(
                    CardInstance(a_member, None, 0),
                    CardInstance(b_member, None, 0)
                )
                if dist is not None and dist < min_distance:
                    min_distance = dist
                    connected = True

        if connected and min_distance <= squad.empowerment_range:
            total += 1 if flat else squad.empowerment

    return total
