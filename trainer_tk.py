# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 bricoleur88
"""FINAL FANTASY RESONANCE (Steam) 트레이너.

실행:  python trainer.py     (게임을 먼저 실행해 타이틀 화면 이후까지 진행)
"""
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from ffr.game import ADDABLE, BATTLE_FIELDS, STAT_NAMES, Game

JOIN = {0: "합류", 1: "미합류", 2: "이탈", 3: "일시 이탈", 4: "로스트"}
DIFFICULTY = ["Easy", "Normal", "Expert"]
ITEM_FILTERS = ["보유 중", "전체", "소모품", "무기", "방어구", "악세서리", "중요품", "아티팩트"]
MAX_MONEY = 9_999_999


def to_int(text, lo=0, hi=2_000_000_000):
    v = int(str(text).replace(",", "").strip())
    return max(lo, min(hi, v))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FINAL FANTASY RESONANCE 트레이너")
        self.geometry("760x560")
        self.minsize(700, 500)
        self.game = None
        self.encount_msg = ""
        self.encount_on = False
        self.encount_rate = 100
        self.encount_running = False
        self.unit_rows = {}
        self.item_rows = {}
        self.vision_rows = {}

        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        self.status = tk.StringVar(value="게임에 연결되지 않음")
        ttk.Label(top, textvariable=self.status).pack(side="left")
        ttk.Button(top, text="새로고침", command=self.refresh_all).pack(side="right")
        ttk.Button(top, text="이름 다시 읽기", command=lambda: self.load_names(force=True)).pack(side="right", padx=6)
        ttk.Button(top, text="게임에 연결", command=self.connect).pack(side="right", padx=6)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._tab_general(nb)
        self._tab_units(nb)
        self._tab_items(nb)
        self._tab_visions(nb)
        self._tab_battle(nb)

        self.after(200, self.connect)
        self.after(500, self.tick)

    # ------------------------------------------------------------------ 연결
    def connect(self):
        try:
            if self.game:
                self.game.p.close()
            self.game = None
            self.game = Game()
        except Exception as e:  # noqa: BLE001
            self.status.set(f"연결 실패: {e}")
            return
        self._fill_battle()
        self.refresh_all()
        self.load_names()

    def load_names(self, force=False):
        """한국어 이름을 읽어 온다 (처음 한 번은 몇 초 걸려서 백그라운드로 처리)."""
        g = self.game
        if not g:
            return
        base = f"연결됨 (PID {g.p.pid})"
        if g.has_name_cache() and not force:
            g.load_korean_names()
            self.status.set(base)
            self.refresh_all()
            return
        self.status.set(base + " — 한국어 이름 읽는 중…")
        result = {}

        def work():
            try:
                result["ok"] = g.load_korean_names(force=True)
            except Exception:  # noqa: BLE001
                result["ok"] = False

        def poll():
            if "ok" not in result:
                self.after(200, poll)
                return
            if self.game is g:
                self.status.set(base if result["ok"] else base + " — 한국어 이름을 찾지 못해 원문으로 표시")
                self.refresh_all()

        threading.Thread(target=work, daemon=True).start()
        self.after(200, poll)

    def ok(self):
        if not self.game:
            messagebox.showwarning("트레이너", "먼저 게임에 연결하세요.")
            return False
        if not self.game.p.alive():
            self.game = None
            self.status.set("게임이 종료되었습니다")
            return False
        if not self.game.save():
            messagebox.showwarning("트레이너", "세이브 데이터가 아직 로드되지 않았습니다.")
            return False
        return True

    def guard(self, fn):
        """입력 오류를 메시지로 보여주는 래퍼."""
        def run(*_):
            if not self.ok():
                return
            try:
                fn()
            except ValueError:
                messagebox.showerror("트레이너", "숫자를 올바르게 입력하세요.")
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("트레이너", str(e))
        return run

    # ------------------------------------------------------------------ 일반 탭
    def _tab_general(self, nb):
        f = ttk.Frame(nb, padding=14)
        nb.add(f, text="일반")
        self.money = tk.StringVar()
        self.money_lock = tk.BooleanVar()
        self.diff = tk.StringVar()
        self.info = tk.StringVar()

        ttk.Label(f, text="소지금 (길)").grid(row=0, column=0, sticky="w", pady=6)
        e = ttk.Entry(f, textvariable=self.money, width=14)
        e.grid(row=0, column=1, padx=8)
        e.bind("<Return>", self.guard(self.apply_money))
        ttk.Button(f, text="적용", command=self.guard(self.apply_money)).grid(row=0, column=2)
        ttk.Button(f, text="최대", command=self.guard(lambda: (self.money.set(MAX_MONEY), self.apply_money()))
                   ).grid(row=0, column=3, padx=6)
        ttk.Checkbutton(f, text="소지금 고정 (줄어들지 않음)", variable=self.money_lock
                        ).grid(row=1, column=1, columnspan=3, sticky="w")

        ttk.Label(f, text="난이도").grid(row=2, column=0, sticky="w", pady=(18, 6))
        cb = ttk.Combobox(f, textvariable=self.diff, values=DIFFICULTY, state="readonly", width=12)
        cb.grid(row=2, column=1, padx=8, pady=(18, 6))
        ttk.Button(f, text="적용", command=self.guard(self.apply_diff)).grid(row=2, column=2, pady=(18, 6))

        self.no_encount = tk.BooleanVar()
        self.encount_state = tk.StringVar()
        ttk.Label(f, text="랜덤 인카운터").grid(row=3, column=0, sticky="w", pady=(18, 6))
        ttk.Checkbutton(f, text="끄기 (필드에서 적과 마주치지 않음)", variable=self.no_encount,
                        command=self.toggle_encount).grid(row=3, column=1, columnspan=3, sticky="w", pady=(18, 6))
        ttk.Label(f, textvariable=self.encount_state, foreground="#666"
                  ).grid(row=3, column=4, sticky="w", padx=8, pady=(18, 6))
        self.rate_var = tk.DoubleVar(value=100)
        self.rate_label = tk.StringVar(value="100%")
        ttk.Label(f, text="인카운터 확률").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Scale(f, from_=0, to=300, variable=self.rate_var, command=self.on_rate, length=240
                  ).grid(row=4, column=1, columnspan=2, sticky="w", padx=8)
        ttk.Label(f, textvariable=self.rate_label, width=6).grid(row=4, column=3, sticky="w")
        ttk.Button(f, text="100%로", command=self.reset_rate).grid(row=4, column=4, sticky="w", padx=8)
        ttk.Label(f, foreground="#666", text="0% = 거의 안 만남 · 100% = 기본 · 300% = 3배 자주 (이동 거리 누적 배율)"
                  ).grid(row=5, column=1, columnspan=4, sticky="w", padx=8)

        ttk.Separator(f).grid(row=6, column=0, columnspan=5, sticky="ew", pady=14)
        ttk.Label(f, textvariable=self.info, justify="left").grid(row=7, column=0, columnspan=5, sticky="w")
        ttk.Label(f, justify="left", foreground="#666", text=(
            "· 값은 현재 로드된 세이브 데이터에 바로 반영됩니다. 메뉴를 닫았다 열면 표시가 갱신됩니다.\n"
            "· 변경 내용을 유지하려면 게임 안에서 저장하세요. 만일을 위해 다른 슬롯에 저장하는 것을 권장합니다."
        )).grid(row=8, column=0, columnspan=5, sticky="w", pady=(14, 0))

    def on_rate(self, value=None):
        self.encount_rate = int(round(self.rate_var.get() / 5.0)) * 5
        self.rate_label.set(f"{self.encount_rate}%")
        self.toggle_encount()

    def reset_rate(self):
        self.rate_var.set(100)
        self.on_rate()

    def toggle_encount(self):
        """끄기 또는 확률 조절이 켜져 있는 동안 백그라운드에서 값을 계속 고정한다."""
        self.encount_on = self.no_encount.get()
        if not (self.encount_on or self.encount_rate != 100) or self.encount_running:
            return  # 실행 중인 스레드가 새 설정을 반영하거나, 복원하고 끝난다
        g = self.game
        if not g:
            self.no_encount.set(False)
            self.encount_on = False
            messagebox.showwarning("트레이너", "먼저 게임에 연결하세요.")
            return
        self.encount_running = True

        def work():
            try:
                while (self.encount_on or self.encount_rate != 100) and self.game is g and g.p.alive():
                    try:
                        ok = g.encounter_set(self.encount_rate / 100.0, self.encount_on)
                        what = "인카운터 없음" if self.encount_on else f"확률 {self.encount_rate}%"
                        self.encount_msg = f"{what} 적용 중" if ok else "필드 대기 중 (필드에 나가면 적용)"
                    except Exception:  # noqa: BLE001
                        self.encount_msg = "값을 쓰지 못했습니다"
                    time.sleep(0.3)
                try:
                    if self.game is g and g.p.alive():
                        g.encounter_restore()
                except Exception:  # noqa: BLE001
                    pass
            finally:
                self.encount_msg = ""
                self.encount_running = False

        threading.Thread(target=work, daemon=True).start()

    def apply_money(self):
        v = to_int(self.money.get(), 0, MAX_MONEY)
        self.game.player_set("currentMoney", v)
        self.money.set(v)

    def apply_diff(self):
        self.game.player_set("GameDifficulty", DIFFICULTY.index(self.diff.get()))

    # ------------------------------------------------------------------ 캐릭터 탭
    def _tab_units(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="캐릭터")
        cols = ("name", "lv", "exp", "hp", "mp", "state")
        heads = ("이름", "Lv", "경험치", "HP", "MP", "상태")
        widths = (220, 50, 90, 70, 70, 110)
        self.unit_tree = ttk.Treeview(f, columns=cols, show="headings", height=9, selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.unit_tree.heading(c, text=h)
            self.unit_tree.column(c, width=w, anchor="w" if c == "name" else "center")
        self.unit_tree.pack(fill="x")
        self.unit_tree.bind("<<TreeviewSelect>>", lambda _: self.load_unit())

        ed = ttk.LabelFrame(f, text="선택한 캐릭터 편집", padding=10)
        ed.pack(fill="both", expand=True, pady=(10, 0))
        self.u_level, self.u_exp, self.u_hp, self.u_mp = (tk.StringVar() for _ in range(4))
        for i, (label, var, cmd) in enumerate((
                ("레벨", self.u_level, self.apply_level), ("경험치", self.u_exp, self.apply_exp),
                ("현재 HP", self.u_hp, lambda: self.apply_unit_field("HitPoint", self.u_hp)),
                ("현재 MP", self.u_mp, lambda: self.apply_unit_field("MagicPoint", self.u_mp)))):
            ttk.Label(ed, text=label).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Entry(ed, textvariable=var, width=10).grid(row=i, column=1, padx=6)
            ttk.Button(ed, text="적용", width=6, command=self.guard(cmd)).grid(row=i, column=2)

        ttk.Label(ed, text="스탯 영구 보너스").grid(row=0, column=3, columnspan=4, sticky="w", padx=(30, 0))
        self.u_bonus = {}
        for n, (idx, label) in enumerate(STAT_NAMES.items()):
            r, c = 1 + n // 2, 3 + (n % 2) * 2
            ttk.Label(ed, text=label).grid(row=r, column=c, sticky="e", padx=(30, 4))
            var = tk.StringVar()
            self.u_bonus[idx] = var
            ttk.Entry(ed, textvariable=var, width=7).grid(row=r, column=c + 1)
        ttk.Button(ed, text="보너스 적용", command=self.guard(self.apply_bonus)
                   ).grid(row=5, column=5, columnspan=2, sticky="e", pady=(6, 0))
        ttk.Label(ed, foreground="#666", justify="left", text=(
            "레벨/경험치를 바꾼 뒤에는 저장 후 다시 로드하거나 전투를 한 번 치르면 능력치에 반영됩니다."
        )).grid(row=6, column=0, columnspan=7, sticky="w", pady=(10, 0))

    def selected_unit(self):
        sel = self.unit_tree.selection()
        if not sel:
            raise RuntimeError("캐릭터를 먼저 선택하세요.")
        uid = int(sel[0])
        for u in self.game.units():
            if u["id"] == uid:
                return u
        raise RuntimeError("캐릭터를 찾을 수 없습니다. 새로고침 하세요.")

    def load_unit(self):
        if not self.game or not self.unit_tree.selection():
            return
        try:
            u = self.selected_unit()
        except RuntimeError:
            return
        self.u_level.set(u["level"])
        self.u_exp.set(u["exp"])
        self.u_hp.set(u["hp"])
        self.u_mp.set(u["mp"])
        for idx, var in self.u_bonus.items():
            var.set(u["bonus"].get(idx, 0))

    def apply_level(self):
        u = self.selected_unit()
        table = self.game.level_table(u["id"])
        if not table:
            raise RuntimeError("이 캐릭터의 레벨 테이블을 찾지 못했습니다.")
        lv = to_int(self.u_level.get(), table[0][0], table[-1][0])
        self.game.unit_set(u["addr"], "Experience", self.game.exp_for(u["id"], lv))
        self.refresh_units()

    def apply_exp(self):
        u = self.selected_unit()
        self.game.unit_set(u["addr"], "Experience", to_int(self.u_exp.get(), 0, 99_999_999))
        self.refresh_units()

    def apply_unit_field(self, field, var):
        u = self.selected_unit()
        self.game.unit_set(u["addr"], field, to_int(var.get(), 1 if field == "HitPoint" else 0, 99_999))
        self.refresh_units()

    def apply_bonus(self):
        u = self.selected_unit()
        for idx, var in self.u_bonus.items():
            self.game.unit_set_bonus(u["addr"], idx, to_int(var.get(), 0, 99_999))
        self.refresh_units()

    # ------------------------------------------------------------------ 아이템 탭
    def _tab_items(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="아이템")
        top = ttk.Frame(f)
        top.pack(side="top", fill="x", pady=(0, 8))
        self.item_filter = tk.StringVar(value=ITEM_FILTERS[0])
        self.item_search = tk.StringVar()
        self.item_slack = tk.StringVar()
        ttk.Label(top, text="보기").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.item_filter, values=ITEM_FILTERS, state="readonly", width=10)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda _: self.refresh_items(rebuild=True))
        ttk.Label(top, text="검색").pack(side="left", padx=(10, 0))
        e = ttk.Entry(top, textvariable=self.item_search, width=18)
        e.pack(side="left", padx=6)
        e.bind("<KeyRelease>", lambda _: self.refresh_items(rebuild=True))
        ttk.Label(top, textvariable=self.item_slack, foreground="#666").pack(side="right")

        bar = ttk.Frame(f)
        bar.pack(side="bottom", fill="x", pady=(8, 0))
        cols = ("id", "name", "cat", "num")
        self.item_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c, h, w in zip(cols, ("ID", "이름", "분류", "수량"), (70, 300, 100, 70)):
            self.item_tree.heading(c, text=h)
            self.item_tree.column(c, width=w, anchor="w" if c == "name" else "center")
        self.item_tree.tag_configure("none", foreground="#999")
        sb = ttk.Scrollbar(f, orient="vertical", command=self.item_tree.yview)
        self.item_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.item_tree.pack(fill="both", expand=True)

        self.item_num = tk.StringVar(value="99")
        ttk.Label(bar, text="수량").pack(side="left")
        ttk.Entry(bar, textvariable=self.item_num, width=6).pack(side="left", padx=6)
        ttk.Button(bar, text="선택 항목에 적용", command=self.guard(self.apply_items)).pack(side="left")
        ttk.Button(bar, text="보유 소모품 전부 적용", command=self.guard(self.apply_consumables)
                   ).pack(side="left", padx=6)
        ttk.Label(bar, foreground="#666", text="회색 = 미보유 (적용하면 새로 등록)").pack(side="right")

    def apply_items(self):
        g = self.game
        n = to_int(self.item_num.get(), 1, 99)
        sel = [int(i) for i in self.item_tree.selection()]
        if not sel:
            raise RuntimeError("아이템을 먼저 선택하세요 (Ctrl/Shift 로 여러 개 선택).")
        owned = {it["id"]: it for it in g.inventory()}
        new_key = [i for i in sel if i not in owned and g.item_name(i)[1] == "중요품"]
        if new_key and not messagebox.askyesno("트레이너", (
                f"미보유 중요품 {len(new_key)}개를 새로 등록합니다.\n\n"
                "중요품은 스토리 진행 조건으로 쓰이는 경우가 있어, 미리 갖고 있으면 이벤트 순서가 "
                "꼬일 수 있습니다. 적용 후에는 기존 세이브를 덮어쓰지 말고 새 슬롯에 저장하세요.\n\n"
                "계속할까요?")):
            return
        no_slot, blocked = 0, 0
        for iid in sel:
            cat = g.item_name(iid)[1]
            one = 1 if cat == "아티팩트" else n  # 하나만 존재하는 물건
            if iid in owned:
                g.item_set(owned[iid]["addr"], one)
            elif cat not in ADDABLE:
                blocked += 1
            elif not g.add_item(iid, one):
                no_slot += 1
        self.refresh_items()
        msg = []
        if no_slot:
            msg.append(
                f"인벤토리에 빈 슬롯이 없어 {no_slot}개를 등록하지 못했습니다.\n\n"
                "게임에서 '아직 갖고 있지 않은 종류'의 아이템을 하나 얻으면 (상점 구매, 보물상자 등) "
                "게임이 인벤토리 공간을 넉넉히 늘려 빈 슬롯이 수십 개 생깁니다. 그 뒤에 다시 적용하세요.")
        if blocked:
            msg.append(f"{blocked}개는 인벤토리에 넣을 수 없는 분류라 건너뛰었습니다 (비전은 비전 탭에서).")
        if msg:
            messagebox.showinfo("트레이너", "\n\n".join(msg))

    def apply_consumables(self):
        n = to_int(self.item_num.get(), 1, 99)
        for it in self.game.inventory():
            if it["cat"] == "소모품":
                self.game.item_set(it["addr"], n)
        self.refresh_items()

    # ------------------------------------------------------------------ 비전 탭
    def _tab_visions(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="비전")
        top = ttk.Frame(f)
        top.pack(side="top", fill="x", pady=(0, 8))
        self.vision_slack = tk.StringVar()
        ttk.Label(top, foreground="#666", text="회색 = 미보유").pack(side="left")
        ttk.Label(top, textvariable=self.vision_slack, foreground="#666").pack(side="right")
        cols = ("id", "name", "own", "awk")
        self.vision_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="extended")
        for c, h, w in zip(cols, ("ID", "이름", "보유", "각성 포인트"), (80, 280, 70, 110)):
            self.vision_tree.heading(c, text=h)
            self.vision_tree.column(c, width=w, anchor="w" if c == "name" else "center")
        self.vision_tree.tag_configure("none", foreground="#999")
        bar = ttk.Frame(f)
        bar.pack(side="bottom", fill="x", pady=(8, 0))
        self.vision_tree.pack(fill="both", expand=True)
        self.vision_pt = tk.StringVar(value="100")
        ttk.Label(bar, text="각성 포인트").pack(side="left")
        ttk.Entry(bar, textvariable=self.vision_pt, width=8).pack(side="left", padx=6)
        ttk.Button(bar, text="선택 항목에 적용", command=self.guard(self.apply_visions)).pack(side="left")
        ttk.Button(bar, text="선택한 미보유 비전 획득", command=self.guard(self.add_visions)
                   ).pack(side="left", padx=6)

    def apply_visions(self):
        n = to_int(self.vision_pt.get(), 0, 999_999)
        sel = {int(i) for i in self.vision_tree.selection()}
        if not sel:
            raise RuntimeError("비전을 먼저 선택하세요.")
        done = 0
        for v in self.game.visions():
            if v["id"] in sel:
                self.game.vision_set(v["addr"], n)
                done += 1
        self.refresh_visions()
        if not done:
            raise RuntimeError("각성 포인트는 보유한 비전에만 적용됩니다.")

    def add_visions(self):
        g = self.game
        owned = {v["id"] for v in g.visions()}
        want = [int(i) for i in self.vision_tree.selection() if int(i) not in owned]
        if not want:
            raise RuntimeError("미보유(회색) 비전을 먼저 선택하세요.")
        if not messagebox.askyesno("트레이너", (
                f"비전 {len(want)}개를 보유 목록에 등록합니다.\n\n"
                "게임이 직접 획득 처리한 것이 아니어서 싱크로 포인트 등은 비어 있는 상태로 들어갑니다. "
                "실험적인 기능이므로, 적용 후에는 기존 세이브를 덮어쓰지 말고 새 슬롯에 저장해 확인하세요.\n\n"
                "계속할까요?")):
            return
        failed = sum(0 if g.add_vision(i) else 1 for i in want)
        self.refresh_visions()
        if failed:
            messagebox.showinfo("트레이너", (
                f"비전 목록에 빈 슬롯이 없어 {failed}개를 등록하지 못했습니다.\n\n"
                "게임에서 새 비전을 하나 정상적으로 획득하면 게임이 목록 공간을 늘려 빈 슬롯이 생깁니다. "
                "그 뒤에 다시 시도하세요."))

    # ------------------------------------------------------------------ 전투 탭
    def _tab_battle(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="전투 수치")
        ttk.Label(f, foreground="#666", justify="left", text=(
            "게임의 전투 계산 테이블 값을 직접 바꿉니다. 게임을 끄면 원래 값으로 돌아갑니다 (세이브에 남지 않음)."
        )).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        self.calc_vars = {}
        self.calc_default_lbl = {}
        for i, (field, label) in enumerate(BATTLE_FIELDS, start=1):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            self.calc_vars[field] = var
            ttk.Entry(f, textvariable=var, width=10).grid(row=i, column=1, padx=8)
            lbl = ttk.Label(f, foreground="#666")
            lbl.grid(row=i, column=2, sticky="w")
            self.calc_default_lbl[field] = lbl
        r = len(BATTLE_FIELDS) + 1
        bar = ttk.Frame(f)
        bar.grid(row=r, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Button(bar, text="적용", command=self.guard(self.apply_calc)).pack(side="left")
        ttk.Button(bar, text="선제공격 100%", command=self.guard(self.preset_preempt)).pack(side="left", padx=6)
        ttk.Button(bar, text="기본값으로", command=self.guard(self.reset_calc)).pack(side="left")

    def _fill_battle(self):
        g = self.game
        for field, var in self.calc_vars.items():
            if field in g.calc_defaults:
                var.set(self._fmt(g.calc_get(field)))
                self.calc_default_lbl[field].config(text=f"기본 {self._fmt(g.calc_defaults[field])}")
            else:
                var.set("")
                self.calc_default_lbl[field].config(text="(없음)")

    @staticmethod
    def _fmt(v):
        return f"{v:g}" if isinstance(v, float) else str(v)

    def apply_calc(self):
        g = self.game
        for field, var in self.calc_vars.items():
            if field not in g.calc_defaults or not var.get().strip():
                continue
            v = float(var.get())
            if v < 0:
                raise ValueError
            g.calc_set(field, v)
        self._fill_battle()

    def preset_preempt(self):
        self.calc_vars["friendliesPreemtiveRate"].set("100")
        self.calc_vars["enemiesPreemtiveRate"].set("0")
        self.apply_calc()

    def reset_calc(self):
        for field, v in self.game.calc_defaults.items():
            self.game.calc_set(field, v)
        self._fill_battle()

    # ------------------------------------------------------------------ 갱신
    @staticmethod
    def _sync(tree, rows):
        """Treeview 내용을 rows({iid: values}) 로 맞춘다 (선택 유지)."""
        for iid in tree.get_children():
            if iid not in rows:
                tree.delete(iid)
        for iid, values in rows.items():
            if tree.exists(iid):
                tree.item(iid, values=values)
            else:
                tree.insert("", "end", iid=iid, values=values)

    def refresh_units(self):
        party = self.game.party_ids()
        rows = {}
        for u in self.game.units():
            state = JOIN.get(u["join"], "?") + (" · 파티" if u["id"] in party else "")
            rows[str(u["id"])] = (u["name"], u["level"], f'{u["exp"]:,}', u["hp"], u["mp"], state)
        self._sync(self.unit_tree, rows)

    def refresh_items(self, rebuild=False):
        g = self.game
        if not g or not g.save():
            return
        flt = self.item_filter.get()
        key = self.item_search.get().strip().lower()
        owned = {i["id"]: i["num"] for i in g.inventory()}
        if flt == "보유 중":
            ids = list(owned)
        else:
            ids = list(owned) + sorted(i for i in g.items if i not in owned)
            if flt != "전체":
                ids = [i for i in ids if g.item_name(i)[1] == flt]
            else:
                ids = [i for i in ids if g.item_name(i)[1] != "비전"]
        rows = {}
        for iid in ids:
            name, cat = g.item_name(iid)
            if key and key not in name.lower() and key != str(iid):
                continue
            rows[str(iid)] = (iid, name, cat, owned.get(iid, "-"))
        tree = self.item_tree
        if rebuild or list(rows) != list(tree.get_children()):
            sel = set(tree.selection())
            tree.delete(*tree.get_children())
            for iid, values in rows.items():
                tree.insert("", "end", iid=iid, values=values)
            keep = [i for i in rows if i in sel]
            if keep:
                tree.selection_set(keep)
        for iid, values in rows.items():
            tree.item(iid, values=values, tags=() if int(iid) in owned else ("none",))
        self.item_slack.set(f"새로 등록 가능한 빈 슬롯: {g.inventory_slack()}개")

    def refresh_visions(self):
        g = self.game
        owned = {v["id"]: v for v in g.visions()}
        rows = {str(i): (i, v["name"], "보유", v["awakening"]) for i, v in owned.items()}
        for i, name in sorted(g.all_visions().items()):
            rows.setdefault(str(i), (i, name, "-", "-"))
        self._sync(self.vision_tree, rows)
        for iid in rows:
            self.vision_tree.item(iid, tags=() if int(iid) in owned else ("none",))
        self.vision_slack.set(f"새로 등록 가능한 빈 슬롯: {g.vision_slack()}개")

    def refresh_all(self):
        g = self.game
        if not g or not g.p.alive() or not g.save():
            return
        self.money.set(g.player_get("currentMoney"))
        d = g.player_get("GameDifficulty")
        self.diff.set(DIFFICULTY[d] if d is not None and 0 <= d < 3 else "")
        self.refresh_units()
        self.refresh_items()
        self.refresh_visions()
        self.load_unit()

    def tick(self):
        g = self.game
        self.encount_on = self.no_encount.get()  # 스레드는 tk 변수 대신 이 값을 본다
        if (self.encount_on or self.encount_rate != 100) and not self.encount_running and g:
            self.toggle_encount()  # 게임에 다시 연결한 뒤에도 설정을 이어서 적용
        self.encount_state.set(self.encount_msg)
        try:
            if g and g.p.alive():
                if g.save():
                    cur = g.player_get("currentMoney")
                    if self.money_lock.get():
                        try:
                            want = to_int(self.money.get(), 0, MAX_MONEY)
                            if cur is not None and cur < want:
                                g.player_set("currentMoney", want)
                        except ValueError:
                            pass
                    t = int(g.player_get("PlayTime") or 0)
                    self.info.set(f"플레이 시간 {t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}    "
                                  f"전투 승리 {g.player_get('WinNum')}회    현재 소지금 {cur:,} 길")
                else:
                    self.info.set("세이브 데이터 대기 중…")
            elif g:
                self.game = None
                self.status.set("게임이 종료되었습니다 — 다시 실행 후 '게임에 연결'")
        except Exception:  # noqa: BLE001
            pass
        self.after(500, self.tick)


if __name__ == "__main__":
    App().mainloop()
