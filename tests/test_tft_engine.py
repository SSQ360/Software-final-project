from pathlib import Path

from src.tft_engine import (
    Augment,
    Item,
    GameState,
    battle_round,
    buy_from_shop,
    buy_xp,
    choose_augment,
    compute_final_score,
    equip_item_to_unit,
    get_shop_odds,
    load_best_score,
    move_bench_to_board,
    roll_shop,
    sell_unit,
    streak_bonus,
    start_new_run,
    total_pool_remaining,
    update_best_score,
    xp_to_next_level,
)


def test_buy_and_place() -> None:
    st = start_new_run()
    st.shop = ["b1", "a1", "s1", "b2", "a2"]
    assert buy_from_shop(st, 0) == "OK"
    assert st.bench[0] is not None
    assert move_bench_to_board(st, 0, 0) == "OK"
    assert st.board[0] is not None


def test_battle_requires_unit() -> None:
    st = start_new_run()
    msg = battle_round(st)
    assert msg != "OK"
    assert "board" in msg.lower()


def test_final_score_and_best(tmp_path: Path) -> None:
    st = GameState()
    st.survived_rounds = 3
    st.round_index = 4
    st.hp = 50
    st.gold = 20
    st.total_kills = 5
    s = compute_final_score(st)
    assert s > 0

    p = tmp_path / "t.json"
    assert update_best_score(p, s) is True
    assert load_best_score(p) == s
    assert update_best_score(p, s - 1) is False


def test_item_equip_and_augment_gate() -> None:
    st = start_new_run()
    st.shop = ["b1", "a1", "s1", "b2", "a2"]
    assert buy_from_shop(st, 0) == "OK"
    assert move_bench_to_board(st, 0, 0) == "OK"
    st.item_bench[0] = Item.BLADE
    assert st.item_bench[0] is not None
    assert equip_item_to_unit(st, 0, "board", 0) == "OK"
    assert st.board[0] is not None and len(st.board[0].items) == 1

    # force augment round and verify battle is blocked until chosen
    st.round_index = 2
    st.pending_augment_choices = [Augment.BATTLEFORGED, Augment.CELESTIAL_LIGHT, Augment.CYBER_SHELL]
    assert battle_round(st) == "Select an augment first."
    assert choose_augment(st, 0) == "OK"


def test_item_recipe_and_level_cap() -> None:
    st = start_new_run()
    st.shop = ["b1", "b1", "b1", "a1", "s1"]
    assert buy_from_shop(st, 0) == "OK"
    assert move_bench_to_board(st, 0, 0) == "OK"
    st.item_bench[0] = Item.BLADE
    st.item_bench[1] = Item.BLADE
    assert equip_item_to_unit(st, 0, "board", 0) == "OK"
    assert equip_item_to_unit(st, 1, "board", 0) == "OK"
    assert st.board[0] is not None
    assert Item.DEATHBLADE in st.board[0].items

    # Level and cap
    st.level = 3
    st.xp = xp_to_next_level(3) - 1
    st.gold = 20
    assert buy_xp(st) == "OK"
    assert st.level >= 4


def test_pool_depletion_and_return() -> None:
    st = start_new_run()
    before = st.champion_pool["b1"]
    st.shop = ["b1", "a1", "s1", "b2", "a2"]
    assert buy_from_shop(st, 0) == "OK"
    assert st.champion_pool["b1"] == before - 1
    assert sell_unit(st, "bench", 0) == "OK"
    assert st.champion_pool["b1"] == before
    assert total_pool_remaining(st) > 0


def test_streak_bonus_curve() -> None:
    st = start_new_run()
    assert streak_bonus(st) == 0
    st.win_streak = 2
    assert streak_bonus(st) == 1
    st.win_streak = 4
    assert streak_bonus(st) == 2
    st.win_streak = 6
    assert streak_bonus(st) == 3


def test_shop_odds_table() -> None:
    o3 = get_shop_odds(3)
    o6 = get_shop_odds(6)
    assert o3 == {1: 75, 2: 25, 3: 0}
    assert o6 == {1: 20, 2: 45, 3: 35}


def test_roll_shop_respects_remaining_pool() -> None:
    st = start_new_run()
    for k in list(st.champion_pool.keys()):
        st.champion_pool[k] = 0
    st.champion_pool["b1"] = 3
    st.level = 6
    roll_shop(st)
    assert all(x in ("b1", "") for x in st.shop)
