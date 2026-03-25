from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Trait(str, Enum):
    BRUISER = "Bruiser"
    ARCANIST = "Arcanist"
    SNIPER = "Sniper"


class Item(str, Enum):
    BLADE = "Blade"
    ARMOR = "Armor"
    WAND = "Wand"
    CLOAK = "Cloak"
    GLOVES = "Gloves"
    DEATHBLADE = "Deathblade"
    TITANS_RESOLVE = "Titan's Resolve"
    RABADON = "Rabadon's Cap"
    BLOODTHIRSTER = "Bloodthirster"
    INFINITY_EDGE = "Infinity Edge"


class Augment(str, Enum):
    RICH_GET_RICHER = "Rich Get Richer"
    BATTLEFORGED = "Battleforged"
    CELESTIAL_LIGHT = "Celestial Light"
    CYBER_SHELL = "Cyber Shell"
    FINAL_ASCENT = "Final Ascent"


@dataclass
class Unit:
    uid: int
    key: str
    name: str
    trait: Trait
    star: int
    hp: int
    max_hp: int
    atk: int
    items: List[Item] = field(default_factory=list)

    def copy_for_battle(self) -> "Unit":
        return Unit(
            self.uid,
            self.key,
            self.name,
            self.trait,
            self.star,
            self.hp,
            self.max_hp,
            self.atk,
            list(self.items),
        )


@dataclass
class ChampTemplate:
    key: str
    name: str
    trait: Trait
    cost: int
    hp: int
    atk: int


TEMPLATES: Tuple[ChampTemplate, ...] = (
    ChampTemplate("b1", "Garen", Trait.BRUISER, 1, 500, 44),
    ChampTemplate("b2", "Darius", Trait.BRUISER, 2, 600, 53),
    ChampTemplate("b3", "Sett", Trait.BRUISER, 3, 760, 58),
    ChampTemplate("a1", "Lux", Trait.ARCANIST, 1, 420, 58),
    ChampTemplate("a2", "Veigar", Trait.ARCANIST, 2, 460, 65),
    ChampTemplate("a3", "Ahri", Trait.ARCANIST, 3, 520, 73),
    ChampTemplate("s1", "Ashe", Trait.SNIPER, 1, 430, 60),
    ChampTemplate("s2", "Jinx", Trait.SNIPER, 2, 470, 68),
    ChampTemplate("s3", "Caitlyn", Trait.SNIPER, 3, 510, 74),
)

SHOP_ODDS_BY_LEVEL: Dict[int, Dict[int, int]] = {
    3: {1: 75, 2: 25, 3: 0},
    4: {1: 55, 2: 35, 3: 10},
    5: {1: 35, 2: 45, 3: 20},
    6: {1: 20, 2: 45, 3: 35},
}


def template_by_key(key: str) -> ChampTemplate:
    for t in TEMPLATES:
        if t.key == key:
            return t
    return TEMPLATES[0]


def _next_uid(state: "GameState") -> int:
    state._uid_counter += 1
    return state._uid_counter


@dataclass
class GameState:
    round_index: int = 1
    hp: int = 100
    gold: int = 10
    shop: List[str] = field(default_factory=list)
    bench: List[Optional[Unit]] = field(default_factory=lambda: [None] * 9)
    board: List[Optional[Unit]] = field(default_factory=lambda: [None] * 6)
    item_bench: List[Optional[Item]] = field(default_factory=lambda: [None] * 6)
    survived_rounds: int = 0
    total_kills: int = 0
    game_over: bool = False
    last_battle_log: str = ""
    opponents: Dict[str, int] = field(default_factory=lambda: {"Bot_A": 100, "Bot_B": 100, "Bot_C": 100, "Bot_D": 100})
    last_enemy_name: str = "Bot_A"
    augments: List[Augment] = field(default_factory=list)
    pending_augment_choices: List[Augment] = field(default_factory=list)
    level: int = 3
    xp: int = 0
    win_streak: int = 0
    lose_streak: int = 0
    champion_pool: Dict[str, int] = field(default_factory=dict)
    last_income_breakdown: Dict[str, int] = field(default_factory=dict)
    _uid_counter: int = 0

    def board_count(self) -> int:
        return sum(1 for u in self.board if u is not None)

    def bench_count(self) -> int:
        return sum(1 for u in self.bench if u is not None)

    def max_units(self) -> int:
        return min(6, self.level)


def _all_units(state: GameState) -> List[Unit]:
    return [u for u in state.board + state.bench if u is not None]


def _initial_pool() -> Dict[str, int]:
    pool: Dict[str, int] = {}
    for t in TEMPLATES:
        pool[t.key] = 16 if t.cost == 1 else 12 if t.cost == 2 else 9
    return pool


def total_pool_remaining(state: GameState) -> int:
    return sum(max(0, x) for x in state.champion_pool.values())


def get_shop_odds(level: int) -> Dict[int, int]:
    return SHOP_ODDS_BY_LEVEL.get(level, SHOP_ODDS_BY_LEVEL[6]).copy()


def _weighted_choice(weights: Dict[int, int]) -> int:
    total = sum(max(0, w) for w in weights.values())
    if total <= 0:
        return 1
    x = random.randint(1, total)
    acc = 0
    for k in sorted(weights.keys()):
        acc += max(0, weights[k])
        if x <= acc:
            return k
    return 1


def roll_shop(state: GameState) -> None:
    odds = get_shop_odds(state.level)
    shop: List[str] = []
    for _ in range(5):
        picked = ""
        for _retry in range(8):
            tier = _weighted_choice(odds)
            candidates = [t for t in TEMPLATES if t.cost == tier and state.champion_pool.get(t.key, 0) > 0]
            if candidates:
                weighted: List[str] = []
                for t in candidates:
                    rem = state.champion_pool.get(t.key, 0)
                    weighted.extend([t.key] * min(rem, 6))
                picked = random.choice(weighted)
                break
        if not picked:
            fallback = [t.key for t in TEMPLATES if state.champion_pool.get(t.key, 0) > 0]
            picked = random.choice(fallback) if fallback else ""
        shop.append(picked)
    state.shop = shop


def interest(state: GameState) -> int:
    cap = 6 if Augment.RICH_GET_RICHER in state.augments else 5
    return min(cap, state.gold // 10)


def _star_multiplier(star: int) -> float:
    if star == 1:
        return 1.0
    if star == 2:
        return 1.8
    return 3.0


def _apply_item_stats(unit: Unit) -> None:
    for it in unit.items:
        if it == Item.BLADE:
            unit.atk += 10
        elif it == Item.ARMOR:
            unit.max_hp += 85
            unit.hp += 85
        elif it == Item.WAND:
            unit.atk += 14
        elif it == Item.CLOAK:
            unit.max_hp += 60
            unit.hp += 60
        elif it == Item.GLOVES:
            unit.atk += 8
            unit.max_hp += 35
            unit.hp += 35
        elif it == Item.DEATHBLADE:
            unit.atk += 28
        elif it == Item.TITANS_RESOLVE:
            unit.atk += 14
            unit.max_hp += 160
            unit.hp += 160
        elif it == Item.RABADON:
            unit.atk += 34
        elif it == Item.BLOODTHIRSTER:
            unit.atk += 20
            unit.max_hp += 90
            unit.hp += 90
        elif it == Item.INFINITY_EDGE:
            unit.atk += 26


def apply_synergy_bonus(units: List[Unit], augments: List[Augment]) -> List[Unit]:
    traits = [u.trait for u in units]
    bruiser_hp = 0
    arcanist_atk = 0
    sniper_atk = 0
    if traits.count(Trait.BRUISER) >= 2:
        bruiser_hp += 120
    if traits.count(Trait.BRUISER) >= 4:
        bruiser_hp += 130
    if traits.count(Trait.ARCANIST) >= 2:
        arcanist_atk += 18
    if traits.count(Trait.ARCANIST) >= 4:
        arcanist_atk += 18
    if traits.count(Trait.SNIPER) >= 2:
        sniper_atk += 15
    if traits.count(Trait.SNIPER) >= 4:
        sniper_atk += 18

    out: List[Unit] = []
    for u in units:
        nu = u.copy_for_battle()
        mult = _star_multiplier(nu.star)
        nu.max_hp = int(nu.max_hp * mult)
        nu.hp = int(nu.hp * mult)
        nu.atk = int(nu.atk * mult)
        _apply_item_stats(nu)
        if nu.trait == Trait.BRUISER:
            nu.max_hp += bruiser_hp
            nu.hp += bruiser_hp
        if nu.trait == Trait.ARCANIST:
            nu.atk += arcanist_atk
        if nu.trait == Trait.SNIPER:
            nu.atk += sniper_atk
        if Augment.BATTLEFORGED in augments:
            nu.atk += 10
        if Augment.CYBER_SHELL in augments and nu.items:
            nu.max_hp += 120
            nu.hp += 120
        out.append(nu)
    return out


def build_enemy_team(round_index: int, enemy_hp: int) -> List[Unit]:
    scale_hp = 240 + round_index * 75 + max(0, (100 - enemy_hp) * 2)
    scale_atk = 28 + round_index * 7
    count = 2 if round_index <= 3 else 3 if round_index <= 9 else 4
    names = ["Stone Golem", "Feral Wolf", "Iron Brute", "Arcane Shade"]
    team: List[Unit] = []
    for i in range(count):
        trait = Trait.BRUISER if i % 3 == 0 else Trait.ARCANIST if i % 3 == 1 else Trait.SNIPER
        team.append(
            Unit(
                uid=-100 - i,
                key=f"enemy_{i}",
                name=names[i % len(names)],
                trait=trait,
                star=1 + (1 if round_index > 8 and i == 0 else 0),
                hp=scale_hp,
                max_hp=scale_hp,
                atk=scale_atk,
                items=[],
            )
        )
    return team


def simulate_battle(player: List[Unit], enemy: List[Unit], augments: List[Augment]) -> Tuple[bool, int, str]:
    p = apply_synergy_bonus([u.copy_for_battle() for u in player], augments)
    e = apply_synergy_bonus([u.copy_for_battle() for u in enemy], [])
    log: List[str] = []
    turn = 0
    while any(u.hp > 0 for u in p) and any(u.hp > 0 for u in e):
        turn += 1
        if turn > 240:
            log.append("Timeout: defender wins.")
            return False, 0, "\n".join(log)

        for u in p:
            if u.hp <= 0:
                continue
            targets = [x for x in e if x.hp > 0]
            if not targets:
                break
            t = targets[0]
            t.hp = max(0, t.hp - u.atk)

        for u in e:
            if u.hp <= 0:
                continue
            targets = [x for x in p if x.hp > 0]
            if not targets:
                break
            t = targets[0]
            t.hp = max(0, t.hp - u.atk)

        if turn % 10 == 0:
            p_sum = sum(max(0, x.hp) for x in p)
            e_sum = sum(max(0, x.hp) for x in e)
            log.append(f"Turn {turn}: player={p_sum} enemy={e_sum}")

    player_alive = [u for u in p if u.hp > 0]
    enemy_alive = [u for u in e if u.hp > 0]
    if player_alive and not enemy_alive:
        survivors = len(player_alive)
        log.append("Result: WIN")
        return True, survivors, "\n".join(log[-8:])
    log.append("Result: LOSE")
    return False, 0, "\n".join(log[-8:])


def _resolve_star_up(state: GameState, key: str) -> None:
    while True:
        candidates: List[Tuple[str, int]] = []
        for i, u in enumerate(state.board):
            if u is not None and u.key == key and u.star < 3:
                candidates.append(("board", i))
        for i, u in enumerate(state.bench):
            if u is not None and u.key == key and u.star < 3:
                candidates.append(("bench", i))
        if len(candidates) < 3:
            break
        selected = candidates[:3]
        keeper_kind, keeper_idx = selected[0]
        for kind, idx in selected[1:]:
            if kind == "board":
                state.board[idx] = None
            else:
                state.bench[idx] = None
        keeper = state.board[keeper_idx] if keeper_kind == "board" else state.bench[keeper_idx]
        if keeper is None:
            break
        keeper.star += 1
        keeper.max_hp = int(keeper.max_hp * 1.25)
        keeper.hp = keeper.max_hp
        keeper.atk = int(keeper.atk * 1.2)
        if keeper.star >= 3:
            break


def buy_from_shop(state: GameState, shop_index: int) -> str:
    if state.game_over:
        return "Game over."
    if shop_index < 0 or shop_index >= len(state.shop):
        return "Invalid shop slot."
    key = state.shop[shop_index]
    if not key:
        return "Empty shop slot."
    tpl = template_by_key(key)
    if state.champion_pool.get(tpl.key, 0) <= 0:
        state.shop[shop_index] = ""
        return "Unit no longer available in pool."
    if state.gold < tpl.cost:
        return "Not enough gold."
    empty = next((i for i, u in enumerate(state.bench) if u is None), None)
    if empty is None:
        return "Bench is full."
    state.gold -= tpl.cost
    state.champion_pool[tpl.key] = max(0, state.champion_pool.get(tpl.key, 0) - 1)
    state.bench[empty] = Unit(
        uid=_next_uid(state),
        key=tpl.key,
        name=tpl.name,
        trait=tpl.trait,
        star=1,
        hp=tpl.hp,
        max_hp=tpl.hp,
        atk=tpl.atk,
        items=[],
    )
    state.shop[shop_index] = ""
    _resolve_star_up(state, tpl.key)
    return "OK"


def equip_item_to_unit(state: GameState, item_index: int, location: str, unit_index: int) -> str:
    if state.game_over:
        return "Game over."
    if item_index < 0 or item_index >= len(state.item_bench):
        return "Invalid item slot."
    item = state.item_bench[item_index]
    if item is None:
        return "Item slot is empty."
    if location == "board":
        target = state.board
    elif location == "bench":
        target = state.bench
    else:
        return "Invalid location."
    if unit_index < 0 or unit_index >= len(target):
        return "Invalid unit slot."
    unit = target[unit_index]
    if unit is None:
        return "No unit in selected slot."
    if len(unit.items) >= 3:
        return "Unit already has 3 items."
    combined = _try_combine_item(unit, item)
    if not combined:
        unit.items.append(item)
    state.item_bench[item_index] = None
    return "OK"


def _try_combine_item(unit: Unit, incoming: Item) -> bool:
    recipes = {
        frozenset([Item.BLADE, Item.BLADE]): Item.DEATHBLADE,
        frozenset([Item.BLADE, Item.ARMOR]): Item.TITANS_RESOLVE,
        frozenset([Item.WAND, Item.WAND]): Item.RABADON,
        frozenset([Item.BLADE, Item.CLOAK]): Item.BLOODTHIRSTER,
        frozenset([Item.BLADE, Item.GLOVES]): Item.INFINITY_EDGE,
    }
    for i, existing in enumerate(unit.items):
        key = frozenset([existing, incoming])
        if key in recipes:
            unit.items[i] = recipes[key]
            return True
    return False


def sell_unit(state: GameState, location: str, index: int) -> str:
    if state.game_over:
        return "Game over."
    target = state.bench if location == "bench" else state.board if location == "board" else None
    if target is None:
        return "Invalid location."
    if index < 0 or index >= len(target):
        return "Invalid index."
    unit = target[index]
    if unit is None:
        return "Slot is empty."
    refund = max(1, template_by_key(unit.key).cost - 1 + unit.star)
    state.gold += refund
    returned_copies = 1 if unit.star == 1 else 3 if unit.star == 2 else 9
    state.champion_pool[unit.key] = state.champion_pool.get(unit.key, 0) + returned_copies
    for it in unit.items:
        free_item_slot = next((i for i, x in enumerate(state.item_bench) if x is None), None)
        if free_item_slot is not None:
            state.item_bench[free_item_slot] = it
    target[index] = None
    return "OK"


def move_bench_to_board(state: GameState, bench_index: int, board_index: int) -> str:
    if state.game_over:
        return "Game over."
    if bench_index < 0 or bench_index >= len(state.bench):
        return "Invalid bench index."
    if board_index < 0 or board_index >= len(state.board):
        return "Invalid board index."
    unit = state.bench[bench_index]
    if unit is None:
        return "Empty bench slot."
    if state.board[board_index] is not None:
        return "Board slot occupied."
    if state.board_count() >= state.max_units():
        return f"Unit cap reached ({state.max_units()})."
    state.bench[bench_index] = None
    state.board[board_index] = unit
    return "OK"


def move_board_to_bench(state: GameState, board_index: int, bench_index: int) -> str:
    if state.game_over:
        return "Game over."
    if board_index < 0 or board_index >= len(state.board):
        return "Invalid board index."
    if bench_index < 0 or bench_index >= len(state.bench):
        return "Invalid bench index."
    unit = state.board[board_index]
    if unit is None:
        return "Empty board slot."
    if state.bench[bench_index] is not None:
        return "Bench slot occupied."
    state.board[board_index] = None
    state.bench[bench_index] = unit
    return "OK"


def reroll_shop(state: GameState) -> str:
    if state.game_over:
        return "Game over."
    if state.gold < 2:
        return "Not enough gold to reroll."
    state.gold -= 2
    roll_shop(state)
    return "OK"


def xp_to_next_level(level: int) -> int:
    table = {3: 4, 4: 8, 5: 12}
    return table.get(level, 99)


def buy_xp(state: GameState) -> str:
    if state.game_over:
        return "Game over."
    if state.level >= 6:
        return "Already max level."
    if state.gold < 4:
        return "Not enough gold for XP."
    state.gold -= 4
    state.xp += 4
    while state.level < 6:
        need = xp_to_next_level(state.level)
        if state.xp < need:
            break
        state.xp -= need
        state.level += 1
    return "OK"


def _maybe_drop_item(state: GameState) -> None:
    open_slot = next((i for i, x in enumerate(state.item_bench) if x is None), None)
    if open_slot is None:
        return
    if state.round_index % 2 == 0 or random.random() < 0.35:
        state.item_bench[open_slot] = random.choice(list(Item))


def _augment_round(round_index: int) -> bool:
    return round_index in {2, 5, 8}


def _roll_augment_choices(state: GameState) -> None:
    if state.pending_augment_choices:
        return
    pool = list(Augment)
    random.shuffle(pool)
    state.pending_augment_choices = pool[:3]


def choose_augment(state: GameState, choice_index: int) -> str:
    if not state.pending_augment_choices:
        return "No augment choice available."
    if choice_index < 0 or choice_index >= len(state.pending_augment_choices):
        return "Invalid augment choice."
    aug = state.pending_augment_choices[choice_index]
    state.pending_augment_choices = []
    state.augments.append(aug)
    if aug == Augment.RICH_GET_RICHER:
        state.gold += 10
    elif aug == Augment.CELESTIAL_LIGHT:
        state.hp = min(100, state.hp + 12)
    elif aug == Augment.FINAL_ASCENT:
        state.gold += 4
    return "OK"


def alive_opponents(state: GameState) -> List[str]:
    return [name for name, hp in state.opponents.items() if hp > 0]


def streak_bonus(state: GameState) -> int:
    streak = max(state.win_streak, state.lose_streak)
    if streak >= 6:
        return 3
    if streak >= 4:
        return 2
    if streak >= 2:
        return 1
    return 0


def start_new_run() -> GameState:
    state = GameState()
    state.champion_pool = _initial_pool()
    roll_shop(state)
    _maybe_drop_item(state)
    return state


def battle_round(state: GameState) -> str:
    if state.game_over:
        return "Game over."
    if state.pending_augment_choices:
        return "Select an augment first."
    team = [u for u in state.board if u is not None]
    if not team:
        return "Place at least one unit on the board."
    if not alive_opponents(state):
        state.game_over = True
        return "All opponents are defeated."

    enemy_name = random.choice(alive_opponents(state))
    enemy_hp = state.opponents[enemy_name]
    state.last_enemy_name = enemy_name
    enemy_team = build_enemy_team(state.round_index, enemy_hp)
    won, survivors, combat_log = simulate_battle(team, enemy_team, state.augments)

    base_income = 0
    streak_income = 0
    interest_income = 0
    augment_income = 0

    if won:
        state.survived_rounds += 1
        state.total_kills += len(enemy_team)
        state.win_streak += 1
        state.lose_streak = 0
        damage_to_enemy = 8 + survivors * 2 + state.round_index // 2
        state.opponents[enemy_name] = max(0, state.opponents[enemy_name] - damage_to_enemy)
        base_income = 5 + state.round_index
        state.gold += base_income
    else:
        state.lose_streak += 1
        state.win_streak = 0
        damage_to_player = 8 + state.round_index * 2
        if Augment.CELESTIAL_LIGHT in state.augments:
            damage_to_player = max(1, damage_to_player - 2)
        state.hp = max(0, state.hp - damage_to_player)
        base_income = 2
        state.gold += base_income
        if state.hp <= 0:
            state.game_over = True

    state.round_index += 1
    if state.level < 6:
        state.xp += 2
        while state.level < 6:
            need = xp_to_next_level(state.level)
            if state.xp < need:
                break
            state.xp -= need
            state.level += 1
    if Augment.FINAL_ASCENT in state.augments and state.round_index >= 10:
        augment_income += 2
        state.gold += 2
    if Augment.CELESTIAL_LIGHT in state.augments and not state.game_over:
        state.hp = min(100, state.hp + 1)
    if not state.game_over and not alive_opponents(state):
        state.game_over = True

    if not state.game_over:
        streak_income = streak_bonus(state)
        state.gold += streak_income
        interest_income = interest(state)
        state.gold += interest_income
        roll_shop(state)
        _maybe_drop_item(state)
        if _augment_round(state.round_index):
            _roll_augment_choices(state)

    state.last_income_breakdown = {
        "base": base_income,
        "streak": streak_income,
        "interest": interest_income,
        "augment": augment_income,
        "total": base_income + streak_income + interest_income + augment_income,
    }

    state.last_battle_log = (
        f"Opponent: {enemy_name}\n"
        + combat_log
        + f"\nPlayer HP: {state.hp} | Gold: {state.gold} | WinStreak: {state.win_streak} | LoseStreak: {state.lose_streak}\n"
        + "Opponents: "
        + ", ".join(f"{k}={v}" for k, v in state.opponents.items())
    )
    return "OK"


def compute_final_score(state: GameState) -> int:
    all_units = _all_units(state)
    unit_power = sum((u.star * 40) + (len(u.items) * 18) + (template_by_key(u.key).cost * 10) for u in all_units)
    dead_opponents = sum(1 for hp in state.opponents.values() if hp == 0)
    return int(
        state.survived_rounds * 280
        + state.round_index * 45
        + state.hp * 7
        + state.gold * 13
        + state.total_kills * 24
        + dead_opponents * 420
        + unit_power
        + len(state.augments) * 180
    )


def update_best_score(path: Path, score: int) -> bool:
    p = Path(path)
    data = {"best": 0}
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(raw.get("best"), int) and raw["best"] >= 0:
                data["best"] = raw["best"]
        except (OSError, json.JSONDecodeError):
            pass
    if score > data["best"]:
        data["best"] = score
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    return False


def load_best_score(path: Path) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(raw.get("best"), int) and raw["best"] >= 0:
            return raw["best"]
    except (OSError, json.JSONDecodeError):
        pass
    return 0
