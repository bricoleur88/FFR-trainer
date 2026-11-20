# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 bricoleur88
"""FINAL FANTASY RESONANCE (Steam) 트레이너 — flet GUI.

실행:  python trainer.py     (게임을 먼저 실행해 타이틀 화면 이후까지 진행)
필요:  pip install flet
(이전 tkinter 버전은 trainer_tk.py)
"""
import os
import threading
import time

import flet as ft

from ffr.game import ADDABLE, BATTLE_FIELDS, STAT_NAMES, Game
from ffr.i18n import LANG_NAMES, _, get_lang, set_lang

JOIN = {0: "합류", 1: "미합류", 2: "이탈", 3: "일시 이탈", 4: "로스트"}  # 화면에 낼 때 번역
DIFFICULTY = ["Easy", "Normal", "Expert"]
ITEM_FILTERS = ["보유 중", "전체", "소모품", "무기", "방어구", "악세서리", "중요품", "아티팩트"]
MAX_MONEY = 9_999_999
DIM = ft.Colors.OUTLINE


def to_int(text, lo=0, hi=2_000_000_000):
    v = int(str(text).replace(",", "").strip())
    return max(lo, min(hi, v))


def fmt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


BTN_STYLE = ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=14, vertical=0),
                           text_style=ft.TextStyle(size=13),
                           visual_density=ft.VisualDensity.COMPACT)
FIELD_PAD = ft.Padding.symmetric(horizontal=10, vertical=9)


def filled(text, **kw):
    return ft.FilledButton(text, style=BTN_STYLE, height=32, **kw)


def outlined(text, **kw):
    return ft.OutlinedButton(text, style=BTN_STYLE, height=32, **kw)


def num_field(value="", width=110, label=None, on_submit=None):
    return ft.TextField(value=str(value), width=width, label=label, dense=True,
                        text_size=13, content_padding=FIELD_PAD,
                        text_align=ft.TextAlign.RIGHT, on_submit=on_submit)


def labeled(text, field, width=None):
    """입력칸 앞에 이름표를 붙인다. width 를 주면 이름표 폭을 고정해 줄을 맞춘다."""
    return ft.Row([ft.Text(text, size=13, width=width), field], tight=True, spacing=6,
                  vertical_alignment=ft.CrossAxisAlignment.CENTER)


def hint(text):
    return ft.Text(text, size=12, color=DIM)


class SelectList:
    """머리글이 있는 선택 가능한 목록 (행을 클릭해 선택/해제)."""

    def __init__(self, columns, multi=True, on_select=None):
        self.columns = columns  # [(제목, 너비 또는 None=늘어남, 정렬)]
        self.multi = multi
        self.on_select = on_select
        self.rows = {}
        self.selected = set()
        self._ctl = {}
        self.lv = ft.ListView(expand=True, spacing=0, item_extent=34)
        head = ft.Container(
            ft.Row(self._cells([c[0] for c in columns], False, bold=True), spacing=8),
            padding=ft.Padding.symmetric(vertical=8, horizontal=12),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=6)
        self.control = ft.Column([head, self.lv], expand=True, spacing=2)

    def _cells(self, values, dim, bold=False):
        out = []
        for (_title, width, align), v in zip(self.columns, values):
            out.append(ft.Text(str(v), width=width, expand=width is None, no_wrap=True, size=13,
                               overflow=ft.TextOverflow.ELLIPSIS, text_align=align,
                               color=DIM if dim else None,
                               weight=ft.FontWeight.BOLD if bold else None))
        return out

    def set_rows(self, rows):
        """rows: {키: (값 목록, 흐리게 표시 여부)}"""
        if list(rows) == list(self.rows):
            for key, (values, dim) in rows.items():
                if self.rows[key] != (values, dim):
                    for t, v in zip(self._ctl[key][1], values):
                        t.value = str(v)
                        t.color = DIM if dim else None
        else:
            self.selected &= set(rows)
            self._ctl = {}
            controls = []
            for key, (values, dim) in rows.items():
                texts = self._cells(values, dim)
                box = ft.Container(ft.Row(texts, spacing=8), height=34, border_radius=4,
                                   padding=ft.Padding.symmetric(vertical=0, horizontal=12),
                                   bgcolor=ft.Colors.PRIMARY_CONTAINER if key in self.selected else None,
                                   on_click=lambda e, k=key: self._click(k))
                self._ctl[key] = (box, texts)
                controls.append(box)
            self.lv.controls = controls
        self.rows = dict(rows)

    def _click(self, key):
        if key in self.selected:
            self.selected.discard(key)
        else:
            if not self.multi:
                self.selected.clear()
            self.selected.add(key)
        for k, (box, _texts) in self._ctl.items():
            box.bgcolor = ft.Colors.PRIMARY_CONTAINER if k in self.selected else None
        self.lv.update()
        if self.on_select:
            self.on_select()

    def clear_selection(self):
        self.selected.clear()
        for box, _texts in self._ctl.values():
            box.bgcolor = None


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.game = None
        self.busy = threading.Lock()
        self.enc_rate = 100
        self.enc_active = False
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)
        page.padding = 14
        try:
            page.window.width, page.window.height = 920, 740
            page.window.min_width, page.window.min_height = 800, 560
        except Exception:  # noqa: BLE001  (웹 모드에는 창이 없다)
            pass

        self.build_ui()
        page.run_thread(self.connect)
        page.run_thread(self.loop)

    def build_ui(self):
        """현재 언어로 화면 전체를 만든다 (언어를 바꾸면 다시 호출된다)."""
        page = self.page
        page.title = _("FINAL FANTASY RESONANCE 트레이너")
        self.status = ft.Text(_("게임에 연결하는 중…"), size=13)
        self.lang_menu = ft.Dropdown(width=118, dense=True, text_size=13, content_padding=FIELD_PAD,
                                     value=get_lang(), on_select=self.change_lang,
                                     options=[ft.DropdownOption(key=k, text=v) for k, v in LANG_NAMES.items()])
        top = ft.Row([
            ft.Text(_("FFR 트레이너"), size=18, weight=ft.FontWeight.BOLD),
            ft.Container(self.status, expand=True, padding=ft.Padding.symmetric(horizontal=12, vertical=0)),
            self.lang_menu,
            outlined(_("이름 다시 읽기"), on_click=lambda e: self.bg(self.load_names, True)),
            outlined(_("새로고침"), on_click=lambda e: self.refresh_all()),
            filled(_("게임에 연결"), on_click=lambda e: self.bg(self.connect)),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        tabs = [(_("일반"), self.tab_general()), (_("캐릭터"), self.tab_units()), (_("아이템"), self.tab_items()),
                (_("비전"), self.tab_visions()), (_("전투"), self.tab_battle())]
        self.tabs = ft.Tabs(
            length=len(tabs), expand=True,
            content=ft.Column([
                ft.TabBar(tabs=[ft.Tab(label=t) for t, _c in tabs]),
                ft.TabBarView(expand=True, controls=[
                    ft.Container(c, padding=ft.Padding.only(top=14), expand=True) for _t, c in tabs]),
            ], expand=True, spacing=0))
        page.controls.clear()
        page.add(top, self.tabs)

    def change_lang(self, e=None):
        """언어를 바꾸고, 켜 둔 설정은 유지한 채 화면을 다시 그린다."""
        code = self.lang_menu.value
        if code not in LANG_NAMES or code == get_lang():
            return
        with self.busy:
            keep = {
                "tab": self.tabs.selected_index, "money": self.money.value, "lock": self.money_lock.value,
                "enc_off": self.enc_off.value, "enc": self.enc_slider.value,
                "filter": self.item_filter.value, "search": self.item_search.value,
                "num": self.item_num.value, "pt": self.vision_pt.value,
                "drop": {k: (s.value, a.value) for k, (s, _label, a) in self.drop.items()},
            }
            set_lang(code)
            self.build_ui()
            self.tabs.selected_index = keep["tab"]
            self.money.value, self.money_lock.value = keep["money"], keep["lock"]
            self.enc_off.value, self.enc_slider.value = keep["enc_off"], keep["enc"]
            self.enc_label.value = f"{self.enc_rate}%"
            self.item_filter.value, self.item_search.value = keep["filter"], keep["search"]
            self.item_num.value, self.vision_pt.value = keep["num"], keep["pt"]
            for k, (value, always) in keep["drop"].items():
                slider, label, switch = self.drop[k]
                slider.value, switch.value, label.value = value, always, f"×{float(value):g}"
            g = self.game
            if g and g.p.alive():
                g.apply_names()
                self.status.value = self.status_text()
                self.fill_battle()
                self.refresh_all()
            else:
                self.status.value = _("먼저 게임에 연결하세요.")
            self.page.update()

    # ------------------------------------------------------------------ 공통
    def bg(self, fn, *args):
        self.page.run_thread(fn, *args)

    def say(self, text):
        self.page.show_dialog(ft.SnackBar(ft.Text(text), duration=2500))

    def alert(self, text, title=_("트레이너")):
        dlg = ft.AlertDialog(title=ft.Text(title), content=ft.Text(text, width=440),
                             actions=[ft.TextButton(_("확인"), on_click=lambda e: self.page.pop_dialog())])
        self.page.show_dialog(dlg)

    def confirm(self, text, on_yes):
        def yes(e):
            self.page.pop_dialog()
            self.guard(on_yes)()

        dlg = ft.AlertDialog(modal=True, title=ft.Text(_("확인")), content=ft.Text(text, width=440), actions=[
            ft.TextButton(_("취소"), on_click=lambda e: self.page.pop_dialog()),
            filled(_("계속"), on_click=yes)])
        self.page.show_dialog(dlg)

    def ok(self):
        g = self.game
        if not g:
            self.alert(_("먼저 게임에 연결하세요."))
            return False
        if not g.p.alive():
            self.game = None
            self.set_status(_("게임이 종료되었습니다 — 다시 실행 후 '게임에 연결'"))
            return False
        if not g.save():
            self.alert(_("세이브 데이터가 아직 로드되지 않았습니다."))
            return False
        return True

    def guard(self, fn):
        """입력 오류를 대화상자로 보여주는 래퍼."""
        def run(*args):
            if not self.ok():
                return
            try:
                fn()
            except ValueError:
                self.alert(_("숫자를 올바르게 입력하세요."))
            except Exception as e:  # noqa: BLE001
                self.alert(str(e))
        return run

    def status_text(self):
        """연결 상태 문구. 화면 언어의 이름이 아직 없으면 그 사실을 덧붙인다."""
        g = self.game
        text = _("연결됨 (PID {pid})", pid=g.p.pid)
        shown = getattr(g, "names_lang", None)
        if shown and shown != get_lang():
            text += _(" — 이름은 {lang}(으)로 표시 (이 언어의 이름은 게임을 그 언어로 한 번 실행해 '이름 다시 읽기')",
                      lang=LANG_NAMES.get(shown, shown))
        return text

    def set_status(self, text):
        self.status.value = text
        self.status.update()

    # ------------------------------------------------------------------ 연결
    def connect(self):
        with self.busy:
            self.set_status(_("게임에 연결하는 중…"))
            try:
                if self.game:
                    self.game.p.close()
                self.game = None
                self.game = Game()
            except Exception as e:  # noqa: BLE001
                self.set_status(_("연결 실패: {error}", error=e))
                return
            self.fill_battle()
            self.refresh_all()
        self.load_names()

    def load_names(self, force=False):
        g = self.game
        if not g:
            return
        base = _("연결됨 (PID {pid})", pid=g.p.pid)
        with self.busy:
            if force or not g.has_name_cache():
                self.set_status(base + _(" — 한국어 이름 읽는 중… (몇 초 걸립니다)"))
            try:
                ok = g.load_names(force=force)
            except Exception:  # noqa: BLE001
                ok = False
            self.set_status(self.status_text() if ok else base + _(" — 한국어 이름을 찾지 못해 원문으로 표시"))
        self.refresh_all()

    # ------------------------------------------------------------------ 일반 탭
    def tab_general(self):
        self.money = num_field(width=140, on_submit=self.guard(self.apply_money))
        self.money_lock = ft.Checkbox(label=_("소지금 고정 (줄어들지 않음)"), value=False)
        self.diff = ft.Dropdown(width=140, dense=True, text_size=13, content_padding=FIELD_PAD,
                                options=[ft.DropdownOption(key=d, text=d) for d in DIFFICULTY])
        self.enc_off = ft.Switch(label=_("랜덤 인카운터 끄기"), value=False)
        self.enc_slider = ft.Slider(min=0, max=300, divisions=60, value=100, width=320,
                                    label="{value}%", on_change=self.on_rate)
        self.enc_label = ft.Text("100%", width=50, weight=ft.FontWeight.BOLD)
        self.enc_state = hint("")
        self.info = ft.Text("", size=13)

        def label(text):
            return ft.Text(text, width=150)

        return ft.Column([
            ft.Row([label(_("소지금 (길)")), self.money,
                    filled(_("적용"), on_click=self.guard(self.apply_money)),
                    outlined(_("최대"), on_click=self.guard(self.max_money)), self.money_lock]),
            ft.Row([label(_("난이도")), self.diff, filled(_("적용"), on_click=self.guard(self.apply_diff))]),
            ft.Divider(),
            ft.Row([label(_("랜덤 인카운터")), self.enc_off, self.enc_state]),
            ft.Row([label(_("인카운터 확률")), self.enc_slider, self.enc_label,
                    outlined(_("100%로"), on_click=self.reset_rate)]),
            ft.Row([label(""), hint(_("0% = 거의 안 만남 · 100% = 기본 · 300% = 3배 자주 (이동 거리 누적 배율)"))]),
            ft.Divider(),
            self.info,
            hint(_("· 값은 현재 로드된 세이브 데이터에 바로 반영됩니다. 메뉴를 닫았다 열면 표시가 갱신됩니다.\n"
                 "· 변경 내용을 유지하려면 게임 안에서 저장하세요. 만일을 위해 다른 슬롯에 저장하는 것을 권장합니다.")),
        ], spacing=14, scroll=ft.ScrollMode.AUTO)

    def apply_money(self):
        v = to_int(self.money.value, 0, MAX_MONEY)
        self.game.player_set("currentMoney", v)
        self.money.value = str(v)
        self.money.update()
        self.say(_("소지금을 {money} 길로 변경했습니다.", money=f"{v:,}"))

    def max_money(self):
        self.money.value = str(MAX_MONEY)
        self.apply_money()

    def apply_diff(self):
        if self.diff.value not in DIFFICULTY:
            raise RuntimeError(_("난이도를 선택하세요."))
        self.game.player_set("GameDifficulty", DIFFICULTY.index(self.diff.value))
        self.say(_("난이도를 {name}(으)로 변경했습니다.", name=self.diff.value))

    def on_rate(self, e=None):
        self.enc_rate = int(round(float(self.enc_slider.value) / 5.0)) * 5
        self.enc_label.value = f"{self.enc_rate}%"
        self.enc_label.update()

    def reset_rate(self, e=None):
        self.enc_slider.value = 100
        self.enc_slider.update()
        self.on_rate()

    # ------------------------------------------------------------------ 캐릭터 탭
    def tab_units(self):
        R, C = ft.TextAlign.RIGHT, ft.TextAlign.CENTER
        self.unit_list = SelectList(
            [(_("이름"), None, None), ("Lv", 50, R), (_("경험치"), 90, R), ("HP", 70, R), ("MP", 70, R), (_("상태"), 120, C)],
            multi=False, on_select=self.load_unit)
        self.u_title = ft.Text(_("캐릭터를 선택하세요"), weight=ft.FontWeight.BOLD)
        FW = 84  # 입력칸 폭
        self.u_level, self.u_exp, self.u_hp, self.u_mp = (num_field(width=FW) for _i in range(4))
        self.u_bonus = {idx: num_field(width=FW) for idx in STAT_NAMES}
        LW, GAP = 64, 20  # 이름표 폭, 칸 사이 간격

        def cell(text, field):
            return labeled(text, field, LW)

        def button(text, handler):
            # 입력칸 한 칸과 같은 폭의 자리에 넣어 세로 줄이 맞게 한다
            return ft.Container(filled(text, on_click=self.guard(handler)),
                                width=LW + 6 + FW, alignment=ft.Alignment(-1, 0))

        bonus = [cell(_(STAT_NAMES[idx]), f) for idx, f in self.u_bonus.items()]
        edit = ft.Column([
            self.u_title,
            ft.Row([cell(_("레벨"), self.u_level), button(_("레벨 적용"), self.apply_level),
                    cell(_("경험치"), self.u_exp), button(_("경험치 적용"), self.apply_exp)], spacing=GAP),
            ft.Row([cell(_("현재 HP"), self.u_hp), cell(_("현재 MP"), self.u_mp),
                    button(_("HP/MP 적용"), self.apply_hpmp)], spacing=GAP),
            ft.Container(height=4),
            ft.Text(_("스탯 영구 보너스"), size=13, weight=ft.FontWeight.BOLD),
            ft.Row(bonus[0:4], spacing=GAP),
            ft.Row(bonus[4:7] + [button(_("보너스 적용"), self.apply_bonus)], spacing=GAP),
            hint(_("레벨/경험치를 바꾼 뒤에는 저장 후 다시 로드하거나 전투를 한 번 치르면 능력치에 반영됩니다.")),
        ], spacing=10)
        return ft.Column([ft.Container(self.unit_list.control, height=320), ft.Divider(), edit],
                         spacing=8, scroll=ft.ScrollMode.AUTO)

    def selected_unit(self):
        if not self.unit_list.selected:
            raise RuntimeError(_("캐릭터를 먼저 선택하세요."))
        uid = next(iter(self.unit_list.selected))
        for u in self.game.units():
            if u["id"] == uid:
                return u
        raise RuntimeError(_("캐릭터를 찾을 수 없습니다. 새로고침 하세요."))

    def load_unit(self):
        g = self.game
        if not g or not self.unit_list.selected:
            return
        try:
            u = self.selected_unit()
        except RuntimeError:
            return
        self.u_title.value = _("{name} 편집", name=u["name"])
        self.u_level.value, self.u_exp.value = str(u["level"]), str(u["exp"])
        self.u_hp.value, self.u_mp.value = str(u["hp"]), str(u["mp"])
        for idx, field in self.u_bonus.items():
            field.value = str(u["bonus"].get(idx, 0))
        self.page.update()

    def apply_level(self):
        u = self.selected_unit()
        table = self.game.level_table(u["id"])
        if not table:
            raise RuntimeError(_("이 캐릭터의 레벨 테이블을 찾지 못했습니다."))
        lv = to_int(self.u_level.value, table[0][0], table[-1][0])
        self.game.unit_set(u["addr"], "Experience", self.game.exp_for(u["id"], lv))
        self.refresh_units()
        self.load_unit()
        self.say(_("{name}의 레벨을 {level}(으)로 맞췄습니다.", name=u["name"], level=lv))

    def apply_exp(self):
        u = self.selected_unit()
        self.game.unit_set(u["addr"], "Experience", to_int(self.u_exp.value, 0, 99_999_999))
        self.refresh_units()
        self.load_unit()
        self.say(_("{name}의 경험치를 변경했습니다.", name=u["name"]))

    def apply_hpmp(self):
        u = self.selected_unit()
        self.game.unit_set(u["addr"], "HitPoint", to_int(self.u_hp.value, 1, 99_999))
        self.game.unit_set(u["addr"], "MagicPoint", to_int(self.u_mp.value, 0, 99_999))
        self.refresh_units()
        self.page.update()
        self.say(_("{name}의 HP/MP를 변경했습니다.", name=u["name"]))

    def apply_bonus(self):
        u = self.selected_unit()
        for idx, field in self.u_bonus.items():
            self.game.unit_set_bonus(u["addr"], idx, to_int(field.value, 0, 99_999))
        self.refresh_units()
        self.page.update()
        self.say(_("{name}의 스탯 보너스를 변경했습니다.", name=u["name"]))

    # ------------------------------------------------------------------ 아이템 탭
    def tab_items(self):
        R, C = ft.TextAlign.RIGHT, ft.TextAlign.CENTER
        self.item_list = SelectList([("ID", 70, R), (_("이름"), None, None), (_("분류"), 100, C), (_("수량"), 60, R)])
        self.item_filter = ft.Dropdown(width=140, dense=True, text_size=13, content_padding=FIELD_PAD,
                                       value=ITEM_FILTERS[0],
                                       options=[ft.DropdownOption(key=f, text=_(f)) for f in ITEM_FILTERS],
                                       on_select=lambda e: self.refresh_items(update=True))
        self.item_search = ft.TextField(width=220, dense=True, text_size=13,
                                        content_padding=FIELD_PAD, hint_text=_("검색 (이름 또는 ID)"),
                                        on_change=lambda e: self.refresh_items(update=True))
        self.item_slack = hint("")
        self.item_num = num_field("99", width=80)
        return ft.Column([
            ft.Row([labeled(_("보기"), self.item_filter), self.item_search, ft.Container(expand=True),
                    self.item_slack]),
            self.item_list.control,
            ft.Row([labeled(_("수량"), self.item_num),
                    filled(_("선택 항목에 적용"), on_click=self.guard(self.apply_items)),
                    outlined(_("보유 소모품 전부 적용"), on_click=self.guard(self.apply_consumables)),
                    outlined(_("선택 해제"), on_click=lambda e: self.clear_items()),
                    ft.Container(expand=True), hint(_("흐린 글씨 = 미보유 (적용하면 새로 등록)"))]),
        ], spacing=10, expand=True)

    def clear_items(self):
        self.item_list.clear_selection()
        self.item_list.lv.update()

    def apply_items(self):
        g = self.game
        n = to_int(self.item_num.value, 1, 99)
        sel = list(self.item_list.selected)
        if not sel:
            raise RuntimeError(_("아이템을 먼저 선택하세요 (행을 클릭하면 여러 개 선택됩니다)."))
        owned = {it["id"]: it for it in g.inventory()}
        new_key = [i for i in sel if i not in owned and g.item_name(i)[1] == "중요품"]

        def run():
            no_slot = skipped = 0
            for iid in sel:
                cat = g.item_name(iid)[1]
                one = 1 if cat in ("중요품", "아티팩트") else n  # 하나만 존재하는 물건
                if iid in owned:
                    g.item_set(owned[iid]["addr"], one)
                elif cat not in ADDABLE:
                    skipped += 1
                elif not g.add_item(iid, one):
                    no_slot += 1
            self.refresh_items(update=True)
            msg = []
            if no_slot:
                msg.append(
                    _("인벤토리에 빈 슬롯이 없어 {count}개를 등록하지 못했습니다.\n\n"
                      "게임에서 '아직 갖고 있지 않은 종류'의 아이템을 하나 얻으면 (상점 구매, 보물상자 등) "
                      "게임이 인벤토리 공간을 넉넉히 늘려 빈 슬롯이 수십 개 생깁니다. 그 뒤에 다시 적용하세요.",
                      count=no_slot))
            if skipped:
                msg.append(_("{count}개는 인벤토리에 넣을 수 없는 분류라 건너뛰었습니다 (비전은 비전 탭에서).",
                             count=skipped))
            if msg:
                self.alert("\n\n".join(msg))
            else:
                self.say(_("아이템 {count}종에 적용했습니다.", count=len(sel)))

        if new_key:
            self.confirm(
                _("미보유 중요품 {count}개를 새로 등록합니다.\n\n"
                  "중요품은 스토리 진행 조건으로 쓰이는 경우가 있어, 미리 갖고 있으면 이벤트 순서가 꼬일 수 "
                  "있습니다. 적용 후에는 기존 세이브를 덮어쓰지 말고 새 슬롯에 저장하세요.",
                  count=len(new_key)), run)
        else:
            run()

    def apply_consumables(self):
        n = to_int(self.item_num.value, 1, 99)
        count = 0
        for it in self.game.inventory():
            if it["cat"] == "소모품":
                self.game.item_set(it["addr"], n)
                count += 1
        self.refresh_items(update=True)
        self.say(_("보유 소모품 {count}종을 {num}개로 맞췄습니다.", count=count, num=n))

    # ------------------------------------------------------------------ 비전 탭
    def tab_visions(self):
        R, C = ft.TextAlign.RIGHT, ft.TextAlign.CENTER
        self.vision_list = SelectList([("ID", 80, R), (_("이름"), None, None), (_("보유"), 70, C), (_("각성 포인트"), 110, R)])
        self.vision_slack = hint("")
        self.vision_pt = num_field("100", width=100)
        return ft.Column([
            ft.Row([hint(_("흐린 글씨 = 미보유")), ft.Container(expand=True), self.vision_slack]),
            self.vision_list.control,
            ft.Row([labeled(_("각성 포인트"), self.vision_pt),
                    filled(_("선택 항목에 적용"), on_click=self.guard(self.apply_visions)),
                    outlined(_("선택한 미보유 비전 획득"), on_click=self.guard(self.add_visions))]),
        ], spacing=10, expand=True)

    def apply_visions(self):
        n = to_int(self.vision_pt.value, 0, 999_999)
        sel = set(self.vision_list.selected)
        if not sel:
            raise RuntimeError(_("비전을 먼저 선택하세요."))
        done = 0
        for v in self.game.visions():
            if v["id"] in sel:
                self.game.vision_set(v["addr"], n)
                done += 1
        self.refresh_visions()
        self.page.update()
        if not done:
            raise RuntimeError(_("각성 포인트는 보유한 비전에만 적용됩니다."))
        self.say(_("비전 {count}개의 각성 포인트를 변경했습니다.", count=done))

    def add_visions(self):
        g = self.game
        owned = {v["id"] for v in g.visions()}
        want = [i for i in self.vision_list.selected if i not in owned]
        if not want:
            raise RuntimeError(_("미보유(흐린 글씨) 비전을 먼저 선택하세요."))

        def run():
            failed = sum(0 if g.add_vision(i) else 1 for i in want)
            self.refresh_visions()
            self.page.update()
            if failed:
                self.alert(
                    _("비전 목록에 빈 슬롯이 없어 {count}개를 등록하지 못했습니다.\n\n"
                      "게임에서 새 비전을 하나 정상적으로 획득하면 게임이 목록 공간을 늘려 빈 슬롯이 생깁니다. "
                      "그 뒤에 다시 시도하세요.", count=failed))
            else:
                self.say(_("비전 {count}개를 등록했습니다.", count=len(want)))

        self.confirm(
            _("비전 {count}개를 보유 목록에 등록합니다.\n\n"
              "게임이 직접 획득 처리한 것이 아니어서 싱크로 포인트 등은 비어 있는 상태로 들어갑니다. "
              "실험적인 기능이므로, 적용 후에는 기존 세이브를 덮어쓰지 말고 새 슬롯에 저장해 확인하세요.",
              count=len(want)), run)

    # ------------------------------------------------------------------ 전투 탭
    def tab_battle(self):
        self.drop = {}
        rows = []
        for key, title in (("normal", _("일반 드랍")), ("rare", _("레어 드랍"))):
            slider = ft.Slider(min=1, max=10, divisions=18, value=1, width=300,
                               on_change=lambda e, k=key: self.on_drop_slide(k),
                               on_change_end=lambda e: self.guard(self.apply_drop)())
            label = ft.Text("×1", width=50, weight=ft.FontWeight.BOLD)
            always = ft.Switch(label=_("항상 드랍 (100%)"), value=False,
                               on_change=lambda e: self.guard(self.apply_drop)())
            self.drop[key] = (slider, label, always)
            rows.append(ft.Row([ft.Text(title, width=120), slider, label, always]))
        self.drop_info = hint("")

        self.calc = {}
        grid = []
        for field, label in BATTLE_FIELDS:
            tf = num_field(width=110)
            default = hint("")
            self.calc[field] = (tf, default)
            grid.append(ft.Row([ft.Text(_(label), width=300, size=13), tf, default]))
        return ft.Column([
            ft.Text(_("전투 아이템 드랍 확률"), weight=ft.FontWeight.BOLD),
            *rows,
            ft.Row([outlined(_("드랍 확률 기본값으로"), on_click=self.guard(self.reset_drop)), self.drop_info]),
            hint(_("모든 적의 드랍 확률을 '원래 확률 × 배율'로 바꿉니다 (최대 100%). 드랍 아이템이 없는 적은 그대로입니다.")),
            ft.Divider(),
            ft.Text(_("전투 계산 수치"), weight=ft.FontWeight.BOLD),
            *grid,
            ft.Row([filled(_("적용"), on_click=self.guard(self.apply_calc)),
                    outlined(_("선제공격 100%"), on_click=self.guard(self.preset_preempt)),
                    outlined(_("기본값으로"), on_click=self.guard(self.reset_calc))]),
            hint(_("이 탭의 값은 게임의 데이터 테이블을 직접 바꿉니다. 게임을 끄면 원래 값으로 돌아갑니다 (세이브에 남지 않음).")),
        ], spacing=8, scroll=ft.ScrollMode.AUTO)

    def on_drop_slide(self, key):
        slider, label, _always = self.drop[key]
        label.value = f"×{float(slider.value):g}"
        label.update()

    def apply_drop(self):
        (ns, _l1, na), (rs, _l2, ra) = self.drop["normal"], self.drop["rare"]
        self.game.set_drop_rates(float(ns.value), bool(na.value), float(rs.value), bool(ra.value))
        self.show_drop()
        self.drop_info.update()

    def reset_drop(self):
        for slider, label, always in self.drop.values():
            slider.value, label.value, always.value = 1, "×1", False
        self.game.set_drop_rates()
        self.show_drop()
        self.page.update()

    def show_drop(self):
        n_avg, r_avg, n_cnt, r_cnt = self.game.drop_summary()
        self.drop_info.value = _("현재 평균 — 일반 {normal}% (적 {n_count}종) · 레어 {rare}% (적 {r_count}종)",
                                 normal=f"{n_avg:.1f}", n_count=n_cnt, rare=f"{r_avg:.1f}", r_count=r_cnt)

    def fill_battle(self):
        g = self.game
        for field, (tf, default) in self.calc.items():
            if field in g.calc_defaults:
                tf.value = fmt(g.calc_get(field))
                default.value = _("기본 {value}", value=fmt(g.calc_defaults[field]))
            else:
                tf.value, default.value = "", _("(없음)")
        self.show_drop()
        self.page.update()

    def apply_calc(self):
        g = self.game
        for field, (tf, _default) in self.calc.items():
            if field not in g.calc_defaults or not str(tf.value).strip():
                continue
            v = float(tf.value)
            if v < 0:
                raise ValueError
            g.calc_set(field, v)
        self.fill_battle()
        self.say(_("전투 계산 수치를 적용했습니다."))

    def preset_preempt(self):
        self.calc["friendliesPreemtiveRate"][0].value = "100"
        self.calc["enemiesPreemtiveRate"][0].value = "0"
        self.apply_calc()

    def reset_calc(self):
        for field, v in self.game.calc_defaults.items():
            self.game.calc_set(field, v)
        self.fill_battle()
        self.say(_("전투 계산 수치를 기본값으로 되돌렸습니다."))

    # ------------------------------------------------------------------ 갱신
    def refresh_units(self):
        g = self.game
        party = g.party_ids()
        rows = {}
        for u in g.units():
            state = _(JOIN.get(u["join"], "?")) + (_(" · 파티") if u["id"] in party else "")
            rows[u["id"]] = ((u["name"], u["level"], f'{u["exp"]:,}', u["hp"], u["mp"], state), False)
        self.unit_list.set_rows(rows)

    def refresh_items(self, update=False):
        g = self.game
        if not g or not g.save():
            return
        flt = self.item_filter.value or ITEM_FILTERS[0]
        key = (self.item_search.value or "").strip().lower()
        owned = {i["id"]: i["num"] for i in g.inventory()}
        if flt == "보유 중":
            ids = list(owned)
        else:
            ids = list(owned) + sorted(i for i in g.items if i not in owned)
            if flt == "전체":
                ids = [i for i in ids if g.item_name(i)[1] != "비전"]
            else:
                ids = [i for i in ids if g.item_name(i)[1] == flt]
        rows = {}
        for iid in ids:
            name, cat = g.item_name(iid)
            if key and key not in name.lower() and key != str(iid):
                continue
            rows[iid] = ((iid, name, _(cat), owned.get(iid, "-")), iid not in owned)
        self.item_list.set_rows(rows)
        self.item_slack.value = _("새로 등록 가능한 빈 슬롯: {count}개", count=g.inventory_slack())
        if update:
            self.page.update()

    def refresh_visions(self):
        g = self.game
        owned = {v["id"]: v for v in g.visions()}
        rows = {i: ((i, v["name"], _("보유"), v["awakening"]), False) for i, v in owned.items()}
        for i, name in sorted(g.all_visions().items()):
            rows.setdefault(i, ((i, name, "-", "-"), True))
        self.vision_list.set_rows(rows)
        self.vision_slack.value = _("새로 등록 가능한 빈 슬롯: {count}개", count=g.vision_slack())

    def refresh_all(self):
        g = self.game
        if not g or not g.p.alive() or not g.save():
            return
        self.money.value = str(g.player_get("currentMoney"))
        d = g.player_get("GameDifficulty")
        self.diff.value = DIFFICULTY[d] if d is not None and 0 <= d < 3 else None
        self.refresh_units()
        self.refresh_items()
        self.refresh_visions()
        self.page.update()

    # ------------------------------------------------------------------ 백그라운드
    def loop(self):
        """소지금 고정, 인카운터 제어, 상태 표시를 주기적으로 처리한다."""
        n = 0
        while True:
            time.sleep(0.3)
            n += 1
            g = self.game
            if not g or self.busy.locked():
                continue
            try:
                if not g.p.alive():
                    self.game = None
                    self.set_status(_("게임이 종료되었습니다 — 다시 실행 후 '게임에 연결'"))
                    continue
                # 인카운터
                want = bool(self.enc_off.value) or self.enc_rate != 100
                msg = ""
                if want:
                    ok = g.encounter_set(self.enc_rate / 100.0, bool(self.enc_off.value))
                    what = _("인카운터 없음") if self.enc_off.value else _("확률 {rate}%", rate=self.enc_rate)
                    msg = _("{what} 적용 중", what=what) if ok else _("필드 대기 중 (필드에 나가면 적용)")
                elif self.enc_active:
                    g.encounter_restore()
                self.enc_active = want
                if msg != self.enc_state.value:
                    self.enc_state.value = msg
                    self.enc_state.update()
                if n % 2:
                    continue
                # 소지금 고정 / 정보 표시
                if g.save():
                    cur = g.player_get("currentMoney")
                    if self.money_lock.value:
                        try:
                            want_money = to_int(self.money.value, 0, MAX_MONEY)
                            if cur is not None and cur < want_money:
                                g.player_set("currentMoney", want_money)
                                cur = want_money
                        except ValueError:
                            pass
                    t = int(g.player_get("PlayTime") or 0)
                    info = _("플레이 시간 {time}    전투 승리 {wins}회    현재 소지금 {money} 길",
                             time=f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}",
                             wins=g.player_get("WinNum"), money=f"{cur:,}")
                else:
                    info = _("세이브 데이터 대기 중…")
                if info != self.info.value:
                    self.info.value = info
                    self.info.update()
            except Exception:  # noqa: BLE001
                pass


def main(page: ft.Page):
    App(page)


if __name__ == "__main__":
    import sys

    # "python trainer.py --web 8550" 처럼 실행하면 창 대신 웹 서버로 띄운다 (화면 점검용)
    port = sys.argv[sys.argv.index("--web") + 1] if "--web" in sys.argv else os.environ.get("FFR_WEB_PORT")
    if port:
        os.environ["FLET_FORCE_WEB_SERVER"] = "true"  # 기본 브라우저를 열지 않고 서버만 띄운다
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=int(port))
    else:
        ft.run(main)
