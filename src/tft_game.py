import sys
from collections import Counter
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tft_engine import (
    Item,
    Trait,
    battle_round,
    buy_from_shop,
    choose_augment,
    compute_final_score,
    buy_xp,
    equip_item_to_unit,
    get_shop_odds,
    load_best_score,
    move_bench_to_board,
    move_board_to_bench,
    reroll_shop,
    sell_unit,
    start_new_run,
    total_pool_remaining,
    template_by_key,
    update_best_score,
    xp_to_next_level,
)

HIGH_PATH = _ROOT / "data" / "tft_highscores.json"
COST_COLORS = {1: "#f0f0f0", 2: "#7CFC9A", 3: "#73B9FF"}
ITEM_ABBR = {
    Item.BLADE: "Bd",
    Item.ARMOR: "Ar",
    Item.WAND: "Wd",
    Item.CLOAK: "Cl",
    Item.GLOVES: "Gl",
    Item.DEATHBLADE: "DB",
    Item.TITANS_RESOLVE: "TR",
    Item.RABADON: "RC",
    Item.BLOODTHIRSTER: "BT",
    Item.INFINITY_EDGE: "IE",
}


class TFTApp:
    def __init__(self) -> None:
        self.state = start_new_run()
        self.selected: tuple[str, int] | None = None
        self.selected_item: int | None = None
        self.phase = "Planning"
        self.phase_total_seconds = 20
        self.phase_seconds_left = 20
        self._phase_after_id: str | None = None

        self.root = tk.Tk()
        self.root.title("COMP2116 — TFT Style Auto-Battler")
        self.root.configure(bg="#0b1220")

        top = tk.Frame(self.root, bg="#0b1220")
        top.pack(fill=tk.X, padx=10, pady=8)

        self.lbl_hp = tk.Label(top, text="", fg="#eaeaea", bg="#0b1220", font=("Helvetica", 13, "bold"))
        self.lbl_hp.pack(side=tk.LEFT, padx=6)
        self.lbl_gold = tk.Label(top, text="", fg="#f8d93b", bg="#0b1220", font=("Helvetica", 13, "bold"))
        self.lbl_gold.pack(side=tk.LEFT, padx=6)
        self.lbl_level = tk.Label(top, text="", fg="#ffd39b", bg="#0b1220", font=("Helvetica", 13, "bold"))
        self.lbl_level.pack(side=tk.LEFT, padx=6)
        self.lbl_round = tk.Label(top, text="", fg="#9be7ff", bg="#0b1220", font=("Helvetica", 13, "bold"))
        self.lbl_round.pack(side=tk.LEFT, padx=6)
        self.lbl_best = tk.Label(top, text="", fg="#7CFFB2", bg="#0b1220", font=("Helvetica", 13, "bold"))
        self.lbl_best.pack(side=tk.LEFT, padx=6)
        self.lbl_streak = tk.Label(top, text="", fg="#ffb7c5", bg="#0b1220", font=("Helvetica", 13, "bold"))
        self.lbl_streak.pack(side=tk.LEFT, padx=6)

        self.syn_label = tk.Label(self.root, text="", fg="#bbbbbb", bg="#0b1220", font=("Helvetica", 11))
        self.syn_label.pack(fill=tk.X, padx=12)

        ctrl = tk.Frame(self.root, bg="#0b1220")
        ctrl.pack(fill=tk.X, padx=10)
        tk.Button(ctrl, text="New run", command=self._new_run, width=10).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Reroll (2g)", command=self._do_reroll, width=12).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Buy XP (4g)", command=self._do_buy_xp, width=12).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Battle!", command=self._do_battle, width=10).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="Sell selected", command=self._do_sell, width=12).pack(side=tk.LEFT, padx=4)

        shop_fr = tk.LabelFrame(self.root, text="Shop", fg="#eaeaea", bg="#111a2e", labelanchor="n")
        shop_fr.pack(fill=tk.X, padx=10, pady=6)
        self.shop_btns: list[tk.Button] = []
        for i in range(5):
            b = tk.Button(shop_fr, text="", width=22, command=lambda idx=i: self._buy(idx))
            b.grid(row=0, column=i, padx=4, pady=6)
            self.shop_btns.append(b)

        board_fr = tk.LabelFrame(
            self.root,
            text="Board (max 6) — bench→board to place | board→bench to return",
            fg="#eaeaea",
            bg="#111a2e",
        )
        board_fr.pack(fill=tk.X, padx=10, pady=6)
        self.board_btns: list[tk.Button] = []
        for r in range(2):
            for c in range(3):
                idx = r * 3 + c
                b = tk.Button(board_fr, text=f"-", width=18, height=4, command=lambda i=idx: self._click_board(i))
                b.grid(row=r, column=c, padx=4, pady=4)
                self.board_btns.append(b)

        bench_fr = tk.LabelFrame(self.root, text="Bench", fg="#eaeaea", bg="#111a2e")
        bench_fr.pack(fill=tk.X, padx=10, pady=6)
        self.bench_btns: list[tk.Button] = []
        for i in range(9):
            b = tk.Button(bench_fr, text="-", width=14, command=lambda idx=i: self._click_bench(idx))
            b.grid(row=i // 3, column=i % 3, padx=4, pady=4)
            self.bench_btns.append(b)

        item_fr = tk.LabelFrame(self.root, text="Item Bench (click item, then click a unit)", fg="#eaeaea", bg="#111a2e")
        item_fr.pack(fill=tk.X, padx=10, pady=6)
        self.item_btns: list[tk.Button] = []
        for i in range(6):
            b = tk.Button(item_fr, text="-", width=12, command=lambda idx=i: self._click_item(idx))
            b.grid(row=0, column=i, padx=4, pady=4)
            self.item_btns.append(b)

        aug_fr = tk.LabelFrame(self.root, text="Augments", fg="#eaeaea", bg="#111a2e")
        aug_fr.pack(fill=tk.X, padx=10, pady=6)
        self.aug_choice_btns: list[tk.Button] = []
        for i in range(3):
            b = tk.Button(aug_fr, text=f"Choice {i+1}", width=28, command=lambda idx=i: self._choose_augment(idx))
            b.grid(row=0, column=i, padx=4, pady=4)
            self.aug_choice_btns.append(b)

        self.players_label = tk.Label(self.root, text="", fg="#d9f1ff", bg="#0b1220", font=("Helvetica", 11))
        self.players_label.pack(fill=tk.X, padx=12)
        self.players_canvas = tk.Canvas(self.root, width=560, height=70, bg="#101a33", highlightthickness=0)
        self.players_canvas.pack(padx=12, pady=(2, 6), anchor=tk.W)
        self.odds_label = tk.Label(self.root, text="", fg="#ffd7a8", bg="#0b1220", font=("Helvetica", 11))
        self.odds_label.pack(fill=tk.X, padx=12)
        self.income_label = tk.Label(self.root, text="", fg="#c7ffd8", bg="#0b1220", font=("Helvetica", 11))
        self.income_label.pack(fill=tk.X, padx=12)
        self.phase_label = tk.Label(self.root, text="", fg="#d3d3ff", bg="#0b1220", font=("Helvetica", 11, "bold"))
        self.phase_label.pack(fill=tk.X, padx=12)
        self.phase_bar = tk.Canvas(self.root, width=560, height=12, bg="#1b2642", highlightthickness=0)
        self.phase_bar.pack(padx=12, pady=(2, 6), anchor=tk.W)

        self.log = tk.Text(self.root, height=10, width=110, bg="#0a1020", fg="#cfe9ff")
        self.log.pack(padx=10, pady=8)

        self._bind_keys()
        self._refresh_all()
        self._start_phase_cycle()

    def _do_buy_xp(self) -> None:
        msg = buy_xp(self.state)
        if msg != "OK":
            messagebox.showinfo("XP", msg)
        self._refresh_all()

    def _bind_keys(self) -> None:
        self.root.bind("<Escape>", lambda e: self.root.quit())
        self.root.bind("<F1>", lambda e: self._demo_boost())
        self.root.bind("<F2>", lambda e: self._demo_next_phase())
        self.root.bind("<F3>", lambda e: self._demo_auto_script())

    def _new_run(self) -> None:
        self.state = start_new_run()
        self.selected = None
        self.selected_item = None
        self.phase = "Planning"
        self.phase_total_seconds = 20
        self.phase_seconds_left = 20
        self._start_phase_cycle()
        self._refresh_all()

    def _demo_boost(self) -> None:
        if self.state.game_over:
            return
        # Teacher demo helper: quickly reaches visible milestones.
        self.state.gold += 30
        self.state.xp += 12
        while self.state.level < 6:
            need = xp_to_next_level(self.state.level)
            if self.state.xp < need:
                break
            self.state.xp -= need
            self.state.level += 1
        # Ensure item bench has visible demo items.
        preset = [Item.BLADE, Item.WAND, Item.ARMOR, Item.CLOAK, Item.GLOVES, Item.BLADE]
        for i in range(min(6, len(self.state.item_bench))):
            if self.state.item_bench[i] is None:
                self.state.item_bench[i] = preset[i]
        # Offer augment choices if none are currently offered/selected.
        if not self.state.pending_augment_choices and len(self.state.augments) < 3:
            from tft_engine import Augment

            self.state.pending_augment_choices = [
                Augment.BATTLEFORGED,
                Augment.CYBER_SHELL,
                Augment.RICH_GET_RICHER,
            ]
        self.log.delete("1.0", tk.END)
        self.log.insert(
            tk.END,
            "Demo Boost activated (F1): +30 gold, XP boost, demo items, and augment choices (if available).\n",
        )
        self._refresh_all()

    def _demo_next_phase(self) -> None:
        if self.state.game_over:
            return
        # Teacher demo helper: quickly advance phase timer.
        self.phase_seconds_left = 1
        self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, "Demo Next Phase activated (F2): timer will switch phase on next tick.\n")
        self._refresh_all()

    def _demo_auto_script(self) -> None:
        if self.state.game_over:
            return
        self._demo_boost()
        notes: list[str] = ["Demo Auto Script (F3) started."]

        # 1) Buy up to 3 affordable units from shop.
        buys = 0
        for i in range(len(self.state.shop)):
            if buys >= 3:
                break
            key = self.state.shop[i]
            if not key:
                continue
            tpl = template_by_key(key)
            if self.state.gold >= tpl.cost:
                msg = buy_from_shop(self.state, i)
                if msg == "OK":
                    buys += 1
        notes.append(f"Bought units: {buys}")

        # 2) Move bench units to board up to unit cap.
        moved = 0
        for bi in range(len(self.state.bench)):
            if self.state.board_count() >= self.state.max_units():
                break
            if self.state.bench[bi] is None:
                continue
            empty_board = next((j for j, u in enumerate(self.state.board) if u is None), None)
            if empty_board is None:
                break
            if move_bench_to_board(self.state, bi, empty_board) == "OK":
                moved += 1
        notes.append(f"Placed units on board: {moved}")

        # 3) Equip first available items to board units.
        equips = 0
        for item_i in range(len(self.state.item_bench)):
            if self.state.item_bench[item_i] is None:
                continue
            target = next(
                (j for j, u in enumerate(self.state.board) if u is not None and len(u.items) < 3),
                None,
            )
            if target is None:
                break
            if equip_item_to_unit(self.state, item_i, "board", target) == "OK":
                equips += 1
        notes.append(f"Equipped items: {equips}")

        # 4) Pick augment if choices exist.
        if self.state.pending_augment_choices:
            choose_augment(self.state, 0)
            notes.append("Picked augment choice #1.")

        # 5) Trigger a battle immediately (from planning only).
        if self.phase == "Planning":
            if self._resolve_combat():
                if self.state.game_over:
                    self._finish_run()
                    self._cancel_phase_cycle()
                else:
                    self._set_phase("Combat", 8)
                    self._start_phase_cycle()
                notes.append("Battle started successfully.")
            else:
                notes.append("Battle could not start (likely no valid board yet).")
        else:
            notes.append("Skipped battle start (not in Planning phase).")

        self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, "\n".join(notes) + "\n")
        self._refresh_all()

    def _choose_augment(self, idx: int) -> None:
        msg = choose_augment(self.state, idx)
        if msg != "OK":
            messagebox.showinfo("Augment", msg)
        self._refresh_all()

    def _do_reroll(self) -> None:
        msg = reroll_shop(self.state)
        if msg != "OK":
            messagebox.showinfo("Shop", msg)
        self._refresh_all()

    def _do_battle(self) -> None:
        if self.phase != "Planning":
            messagebox.showinfo("Battle", "You can only start battle during Planning phase.")
            return
        if not self._resolve_combat():
            self._refresh_all()
            return
        if self.state.game_over:
            self._finish_run()
            self._cancel_phase_cycle()
        else:
            self._set_phase("Combat", 8)
            self._start_phase_cycle()
        self._refresh_all()

    def _finish_run(self) -> None:
        score = compute_final_score(self.state)
        best = load_best_score(HIGH_PATH)
        newb = update_best_score(HIGH_PATH, score)
        extra = "\n\nNew best score!" if newb else ""
        messagebox.showinfo(
            "Run finished",
            f"Final score: {score}\nPrevious best: {best}{extra}",
        )

    def _buy(self, idx: int) -> None:
        msg = buy_from_shop(self.state, idx)
        if msg != "OK":
            messagebox.showinfo("Shop", msg)
        self._refresh_all()

    def _click_item(self, idx: int) -> None:
        if self.state.item_bench[idx] is None:
            return
        self.selected_item = None if self.selected_item == idx else idx
        self._refresh_all()

    def _try_equip_to(self, location: str, idx: int) -> bool:
        if self.selected_item is None:
            return False
        msg = equip_item_to_unit(self.state, self.selected_item, location, idx)
        if msg != "OK":
            messagebox.showinfo("Item", msg)
        else:
            self.selected_item = None
        self._refresh_all()
        return True

    def _click_bench(self, idx: int) -> None:
        if self.state.game_over:
            return
        if self._try_equip_to("bench", idx):
            return
        if self.selected is not None and self.selected[0] == "board":
            bi = self.selected[1]
            msg = move_board_to_bench(self.state, bi, idx)
            if msg != "OK":
                messagebox.showinfo("Move", msg)
            self.selected = None
            self._refresh_all()
            return
        self.selected = ("bench", idx)
        self._refresh_all()

    def _click_board(self, idx: int) -> None:
        if self.state.game_over:
            return
        if self._try_equip_to("board", idx):
            return
        if self.selected is not None and self.selected[0] == "board" and self.selected[1] == idx:
            self.selected = None
            self._refresh_all()
            return
        if self.selected is None:
            self.selected = ("board", idx)
            self._refresh_all()
            return
        kind, i = self.selected
        if kind == "bench":
            msg = move_bench_to_board(self.state, i, idx)
            if msg != "OK":
                messagebox.showinfo("Place", msg)
            self.selected = None
        self._refresh_all()

    def _do_sell(self) -> None:
        if self.selected is None:
            messagebox.showinfo("Sell", "Select bench or board first.")
            return
        kind, idx = self.selected
        msg = sell_unit(self.state, kind, idx)
        if msg != "OK":
            messagebox.showinfo("Sell", msg)
        self.selected = None
        self._refresh_all()

    def _synergy_text(self) -> str:
        units = [u for u in self.state.board if u is not None]
        if not units:
            return "Synergy: —"
        c = Counter(u.trait for u in units)
        parts = []
        for t in (Trait.BRUISER, Trait.ARCANIST, Trait.SNIPER):
            n = c.get(t, 0)
            if n:
                parts.append(f"{t.value}×{n}")
        bonus = []
        if c.get(Trait.BRUISER, 0) >= 2:
            bonus.append("Bruiser(2): +HP")
        if c.get(Trait.ARCANIST, 0) >= 2:
            bonus.append("Arcanist(2): +ATK")
        if c.get(Trait.SNIPER, 0) >= 2:
            bonus.append("Sniper(2): +ATK")
        btxt = " | ".join(bonus) if bonus else "no synergy yet"
        return "Synergy: " + ", ".join(parts) + " — " + btxt

    def _refresh_all(self) -> None:
        st = self.state
        best = load_best_score(HIGH_PATH)
        self.lbl_hp.config(text=f"HP: {st.hp}")
        self.lbl_gold.config(text=f"Gold: {st.gold} (next interest +{min(5, st.gold // 10)})")
        if st.level < 6:
            need = xp_to_next_level(st.level)
            self.lbl_level.config(text=f"Level: {st.level} ({st.xp}/{need} XP)")
        else:
            self.lbl_level.config(text=f"Level: {st.level} (MAX)")
        self.lbl_round.config(
            text=(
                f"Round: {st.round_index} | Wins: {st.survived_rounds} | Kills: {st.total_kills} | "
                f"Unit cap: {st.max_units()} | Last enemy: {st.last_enemy_name}"
            )
        )
        self.lbl_best.config(text=f"Best score: {best}")
        self.lbl_streak.config(text=f"Streak W:{st.win_streak} L:{st.lose_streak}")

        for i, b in enumerate(self.shop_btns):
            key = st.shop[i] if i < len(st.shop) else ""
            if not key:
                b.config(text="(empty)", state=tk.DISABLED, bg="#2c344d", fg="#d0d0d0")
            else:
                tpl = template_by_key(key)
                b.config(
                    text=f"{tpl.name}\n{tpl.trait.value} | {tpl.cost}g",
                    state=tk.NORMAL if not st.game_over else tk.DISABLED,
                    bg=COST_COLORS.get(tpl.cost, "#f0f0f0"),
                    fg="#111111",
                )

        for i, b in enumerate(self.bench_btns):
            u = st.bench[i]
            item_text = "" if u is None or not u.items else "[" + " ".join(ITEM_ABBR.get(it, "?") for it in u.items) + "]"
            label = "-" if u is None else f"{u.name} ★{u.star}\n{u.trait.value} {item_text}"
            bg = "#1c2744"
            if self.selected == ("bench", i):
                bg = "#2b3b63"
            b.config(text=label, bg=bg, state=tk.NORMAL if not st.game_over else tk.DISABLED)

        for i, b in enumerate(self.board_btns):
            u = st.board[i]
            item_text = "" if u is None or not u.items else "[" + " ".join(ITEM_ABBR.get(it, "?") for it in u.items) + "]"
            label = "-" if u is None else f"{u.name} ★{u.star}\n{u.trait.value} {item_text}"
            bg = "#1c2744"
            if self.selected == ("board", i):
                bg = "#2b3b63"
            b.config(text=label, bg=bg, state=tk.NORMAL if not st.game_over else tk.DISABLED)

        for i, b in enumerate(self.item_btns):
            item = st.item_bench[i]
            txt = "-" if item is None else item.value
            bg = "#1c2744" if self.selected_item != i else "#35528a"
            b.config(text=txt, bg=bg, state=tk.NORMAL if not st.game_over else tk.DISABLED)

        for i, b in enumerate(self.aug_choice_btns):
            if i < len(st.pending_augment_choices):
                b.config(text=st.pending_augment_choices[i].value, state=tk.NORMAL if not st.game_over else tk.DISABLED)
            else:
                b.config(text="(none)", state=tk.DISABLED)

        augment_text = ", ".join(a.value for a in st.augments) if st.augments else "-"
        opponents_text = " | ".join(f"{name}:{hp}" for name, hp in st.opponents.items())
        self.players_label.config(
            text=(
                f"Opponents HP -> {opponents_text}    ||    Active augments: {augment_text}    ||    "
                f"Pool remaining: {total_pool_remaining(st)}"
            )
        )
        self._draw_opponent_bars()
        odds = get_shop_odds(st.level)
        self.odds_label.config(
            text=f"Shop odds by cost -> 1-cost: {odds[1]}% | 2-cost: {odds[2]}% | 3-cost: {odds[3]}%"
        )
        income = st.last_income_breakdown
        if income:
            self.income_label.config(
                text=(
                    f"Last income -> base:{income.get('base', 0)} | streak:{income.get('streak', 0)} | "
                    f"interest:{income.get('interest', 0)} | augment:{income.get('augment', 0)} | total:+{income.get('total', 0)}"
                )
            )
        else:
            self.income_label.config(text="Last income -> (no combat yet)")
        self._draw_phase_bar()

        self.syn_label.config(text=self._synergy_text())

        self.root.update_idletasks()

    def _cancel_phase_cycle(self) -> None:
        if self._phase_after_id is not None:
            self.root.after_cancel(self._phase_after_id)
            self._phase_after_id = None

    def _set_phase(self, phase: str, seconds: int) -> None:
        self.phase = phase
        self.phase_total_seconds = max(1, seconds)
        self.phase_seconds_left = max(0, seconds)

    def _start_phase_cycle(self) -> None:
        self._cancel_phase_cycle()
        self._phase_after_id = self.root.after(1000, self._tick_phase)

    def _tick_phase(self) -> None:
        if self.state.game_over:
            self._cancel_phase_cycle()
            return
        self.phase_seconds_left = max(0, self.phase_seconds_left - 1)
        if self.phase == "Planning" and self.phase_seconds_left == 0:
            if self._resolve_combat():
                if self.state.game_over:
                    self._finish_run()
                    self._cancel_phase_cycle()
                    self._refresh_all()
                    return
                self._set_phase("Combat", 8)
            else:
                # If combat cannot start (e.g. no units), give a short extra planning window.
                self._set_phase("Planning", 8)
        elif self.phase == "Combat" and self.phase_seconds_left == 0:
            self._set_phase("Planning", 20)
        self._refresh_all()
        self._phase_after_id = self.root.after(1000, self._tick_phase)

    def _draw_phase_bar(self) -> None:
        self.phase_label.config(
            text=f"Phase: {self.phase} | {self.phase_seconds_left}s | F1 Demo Boost | F2 Next Phase | F3 Auto Demo"
        )
        self.phase_bar.delete("all")
        width = 560
        ratio = self.phase_seconds_left / self.phase_total_seconds if self.phase_total_seconds else 0
        fill_w = max(0, int(width * ratio))
        color = "#53e7a2" if self.phase == "Planning" else "#f6b26b"
        self.phase_bar.create_rectangle(0, 0, width, 12, fill="#1b2642", outline="")
        self.phase_bar.create_rectangle(0, 0, fill_w, 12, fill=color, outline="")

    def _resolve_combat(self) -> bool:
        msg = battle_round(self.state)
        if msg != "OK":
            messagebox.showinfo("Battle", msg)
            return False
        self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, self.state.last_battle_log + "\n")
        return True

    def _draw_opponent_bars(self) -> None:
        self.players_canvas.delete("all")
        x0 = 10
        y0 = 10
        bar_w = 120
        bar_h = 12
        gap = 12
        for i, (name, hp) in enumerate(self.state.opponents.items()):
            x = x0 + i * (bar_w + gap)
            ratio = max(0.0, min(1.0, hp / 100.0))
            fill_w = int(bar_w * ratio)
            alive = hp > 0
            self.players_canvas.create_text(x, y0 - 2, anchor="nw", text=name, fill="#d9f1ff", font=("Helvetica", 10, "bold"))
            self.players_canvas.create_rectangle(x, y0 + 14, x + bar_w, y0 + 14 + bar_h, fill="#22355f", outline="")
            color = "#66e6a8" if alive else "#666666"
            self.players_canvas.create_rectangle(x, y0 + 14, x + fill_w, y0 + 14 + bar_h, fill=color, outline="")
            hp_text = f"{hp} HP" if alive else "KO"
            hp_color = "#f7f7f7" if alive else "#ff7777"
            self.players_canvas.create_text(x + bar_w / 2, y0 + 33, text=hp_text, fill=hp_color, font=("Helvetica", 9))

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    TFTApp().run()


if __name__ == "__main__":
    main()
