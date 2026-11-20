# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 bricoleur88
"""FINAL FANTASY RESONANCE 게임 데이터 모델 (세이브 데이터 / 데이터 테이블)."""
import json
import os
import struct
import sys

from .i18n import _
from .loc import Localizer
from .ue import UE

def _app_dir():
    """저장 파일을 둘 폴더: 배포용 실행 파일이면 exe 옆, 소스 실행이면 프로젝트 폴더."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CACHE = os.path.join(_app_dir(), "names_cache.json")
DROP_CACHE = os.path.join(_app_dir(), "drop_defaults.json")

# 게임의 한국어 데이터에 번역이 들어 있지 않은 항목 (일본어 표시명 -> 직접 번역)
FALLBACK_KO = {
    "賢者の書": "현자의 서", "エクソダス": "엑소더스", "チョコボの鞍": "초코보의 안장",
    "イカサマコイン": "속임수 코인", "ソーサリーマント": "소서리 망토", "ヒールチョーカー": "힐 초커",
    "ブラックカード": "블랙 카드", "トランスポーター": "트랜스포터", "魂の勾玉": "영혼의 곡옥",
    "ルーンの腕輪": "룬의 팔찌", "盗賊のカフス": "도적의 커프스",
    "チョコボサドル：バイク": "초코보 새들: 바이크", "ダッシューズ": "대시 슈즈",
    "飛空艇スキン": "비공정 스킨", "EXP抑制装置": "EXP 억제 장치", "怒りの指輪": "분노의 반지",
    "てきよせ": "적 유인", "呪いの指輪": "저주의 반지", "賢者の巻物": "현자의 두루마리",
    "黒輝石": "흑휘석", "魔道書": "마도서", "地下隧道の鍵": "지하 터널의 열쇠",
    "牢屋の鍵": "감옥 열쇠", "オールドウィップ": "올드 윕",
}


def _has_hangul(s):
    return bool(s) and any("가" <= c <= "힣" for c in s)

# eUnitParameterType 중 baseParameterList(영구 보너스)로 의미 있는 항목
STAT_NAMES = {1: "최대 HP", 2: "최대 MP", 5: "공격", 6: "방어", 7: "지능", 8: "정신", 9: "민첩"}

ITEM_TABLES = [
    ("DT_ConsumablesItemData", "소모품"),
    ("DT_EquipmentItemData", "장비"),
    ("DT_ValuableItemData", "중요품"),
    ("DT_ArtifactItemData", "아티팩트"),
    ("DT_VisionItemData", "비전"),
]

EQUIP_TYPES = {1: "무기", 2: "방어구", 3: "악세서리", 4: "비전"}
# 인벤토리에 새로 등록할 수 있는 분류 (비전은 별도 목록으로 관리된다)
ADDABLE = ("소모품", "무기", "방어구", "악세서리", "중요품", "아티팩트")
ENCOUNT_OFF_DISTANCE = 1.0e9

# DT_UnitParameterCalc 에서 노출할 항목: (필드, 설명)
BATTLE_FIELDS = [
    ("friendliesPreemtiveRate", "아군 선제공격 확률 (%)"),
    ("enemiesPreemtiveRate", "적 선제공격 확률 (%)"),
    ("escapeFixRate", "도주 기본 확률 보정"),
    ("stealRareItemRate", "훔치기 레어 아이템 확률 (%)"),
    ("noDamageBonusExpMultiplier", "노 대미지 보너스 EXP 배율"),
    ("breakFinishBonusMoneyMultiplier", "브레이크 피니시 보너스 길 배율"),
    ("overKillBonusApMultiplier", "오버킬 보너스 AP 배율"),
    ("criticalDamageMagnification", "크리티컬 대미지 배율 (%)"),
    ("breakDamageMagnification", "브레이크 대미지 배율 (%)"),
    ("allDamageMagnification", "전체 대미지 계수 (아군·적 공통)"),
    ("breakLBIncrease", "브레이크 시 리미트 게이지 증가"),
    ("damagedLBIncrease", "피격 시 리미트 게이지 증가"),
    ("summonableVisionNum", "전투당 비전 소환 가능 횟수"),
]


class Game:
    def __init__(self):
        self.ue = UE()
        self.p = self.ue.p
        ue = self.ue
        mgrs = ue.instances("CPP_MuchaSaveDataManager")
        if not mgrs:
            raise RuntimeError(_("세이브 매니저를 찾지 못했습니다. 타이틀 화면까지 로딩된 뒤 다시 시도하세요."))
        self.mgr = mgrs[0]
        self.mgr_p = ue.props(ue.obj_class(self.mgr))
        self.S = ue.props(ue.find_struct("CPP_MuchaGameSaveData"))
        self.PL = ue.props(ue.find_struct("SaveData_Player"))
        self.UP = ue.props(ue.find_struct("SaveData_UnitParameter"))
        self.INV = ue.props(ue.find_struct("SaveData_Inventory"))
        self.VIS = ue.props(ue.find_struct("SaveData_Vision"))
        self.PARTY = ue.props(ue.find_struct("SaveData_Party"))
        self.tables = {ue.obj_name(o): o for o in ue.instances("DataTable")}
        self._load_tables()

    # ------------------------------------------------------------------ 테이블
    def rows(self, table):
        """DataTable 의 (행 이름, 행 주소, 프로퍼티) 목록."""
        p, ue = self.p, self.ue
        t = self.tables.get(table) if isinstance(table, str) else table
        if not t:
            return []
        P = ue.props(p.u64(t + 0x28))
        data, num = p.u64(t + 0x30), p.i32(t + 0x38)
        raw = p.read(data, num * 0x18) if data and 0 < num < 100000 else None
        out = []
        if raw:
            for i in range(num):
                ni, nn, ptr = struct.unpack_from("<IIQ", raw, i * 0x18)
                if ptr:
                    out.append((ue.name(ni, nn), ptr, P))
        return out

    def _load_tables(self):
        ue = self.ue
        self.items = {}  # id -> (이름, 분류)
        self._item_text = {}  # id -> 이름 FText 주소
        self._unit_text = {}
        for tname, cat in ITEM_TABLES:
            for name, r, P in self.rows(tname):
                if "ID" in P and ue.get(r, P["ID"]) not in self.items:
                    iid = ue.get(r, P["ID"])
                    if "EquipmentType" in P:
                        cat = EQUIP_TYPES.get(ue.get(r, P["EquipmentType"]), cat)
                    self.items[iid] = (name, cat)
                    if "Name" in P:
                        self._item_text[iid] = r + P["Name"].offset
        # 레벨 테이블: LevelParamId -> [(level, 누적 필요 경험치)]
        level_tables = {}
        for _, r, P in self.rows("DT_UnitLevelParameterList"):
            level_tables[ue.get(r, P["ID"])] = ue.get(r, P["DataTable"])
        self.unit_names = {}
        self.unit_levels = {}
        self._level_cache = {}
        for name, r, P in self.rows("DT_UnitParameter"):
            uid = ue.get(r, P["ID"])
            lp = level_tables.get(ue.get(r, P["LevelParamId"]))
            self.unit_names[uid] = name
            self.unit_levels[uid] = lp
            if "Name" in P:
                self._unit_text[uid] = r + P["Name"].offset
        calc = self.rows("DT_UnitParameterCalc")
        self.calc_row, self.calc_p = (calc[0][1], calc[0][2]) if calc else (0, {})
        self.calc_defaults = {f: self.calc_get(f) for f, _ in BATTLE_FIELDS if f in self.calc_p}
        self._load_drops()

    # ------------------------------------------------------------------ 드랍 확률
    def _load_drops(self):
        """적별 드랍 확률(%) 원본을 읽는다. 원본은 파일에 남겨 두어, 값을 바꾼 채
        트레이너를 다시 켜도 기본값을 알 수 있게 한다."""
        ue = self.ue
        self.drop_rows = []  # (적 ID, 행 주소)
        self.drop_p = {}
        current = {}
        for _, r, P in self.rows("DT_UnitParameter"):
            if "DropNormalItemRate" not in P:
                return
            self.drop_p = P
            uid = ue.get(r, P["ID"])
            self.drop_rows.append((uid, r))
            current[str(uid)] = [ue.get(r, P["DropNormalItemRate"]), ue.get(r, P["DropRareItemRate"])]
        saved = None
        try:
            with open(DROP_CACHE, encoding="utf-8") as f:
                saved = json.load(f)
        except (OSError, ValueError):
            pass
        if not saved or set(saved) != set(current):
            saved = current
            try:
                with open(DROP_CACHE, "w", encoding="utf-8") as f:
                    json.dump(saved, f)
            except OSError:
                pass
        self.drop_defaults = saved

    def set_drop_rates(self, normal_mult=1.0, normal_always=False, rare_mult=1.0, rare_always=False):
        """모든 적의 일반/레어 드랍 확률을 원본 × 배율로 바꾼다 (최대 100%).

        always 면 드랍 아이템이 설정된 적은 100%로 고정한다. 바꾼 적의 수를 돌려준다.
        """
        ue, P = self.ue, self.drop_p
        changed = 0
        for uid, r in self.drop_rows:
            base = self.drop_defaults.get(str(uid))
            if not base:
                continue
            for i, (item_f, rate_f, mult, always) in enumerate((
                    ("DropNormalItem", "DropNormalItemRate", normal_mult, normal_always),
                    ("DropRareItem", "DropRareItemRate", rare_mult, rare_always))):
                if (ue.get(r, P[item_f]) or -1) <= 0:
                    continue  # 드랍 아이템이 없는 적
                new = 100 if always else max(0, min(100, round(base[i] * mult)))
                if ue.get(r, P[rate_f]) != new:
                    ue.set(r, P[rate_f], new)
                    changed += 1
        return changed

    def drop_summary(self):
        """현재 드랍 확률 분포 요약: (일반 평균, 레어 평균, 대상 적 수)."""
        ue, P = self.ue, self.drop_p
        n_sum = n_cnt = r_sum = r_cnt = 0
        for _, r in self.drop_rows:
            if (ue.get(r, P["DropNormalItem"]) or -1) > 0:
                n_sum += ue.get(r, P["DropNormalItemRate"])
                n_cnt += 1
            if (ue.get(r, P["DropRareItem"]) or -1) > 0:
                r_sum += ue.get(r, P["DropRareItemRate"])
                r_cnt += 1
        return (n_sum / n_cnt if n_cnt else 0, r_sum / r_cnt if r_cnt else 0, n_cnt, r_cnt)

    # ------------------------------------------------------------------ 한국어 이름
    def has_name_cache(self):
        return os.path.exists(CACHE)

    def load_korean_names(self, force=False):
        """아이템·캐릭터 이름을 게임의 한국어 텍스트로 바꾼다.

        처음에는 게임 메모리를 훑느라 몇 초 걸리고, 결과는 names_ko.json 에 저장해 재사용한다.
        """
        data = None
        if not force and os.path.exists(CACHE):
            try:
                with open(CACHE, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = None
        if data is None:
            loc = Localizer(self.ue)
            sample = next((loc.text_id(a) for a in self._item_text.values() if loc.text_id(a)), None)
            if not sample or not loc.locate(sample):
                return False
            data = {"items": {}, "units": {}}
            for kind, texts in (("items", self._item_text), ("units", self._unit_text)):
                for key, addr in texts.items():
                    s = loc.resolve(addr)
                    if s:
                        data[kind][str(key)] = s
            # 게임 언어가 한국어일 때만, 게임에 번역이 없어 일본어로 남은 이름을 직접 번역으로 채운다
            names = [n for kind in data.values() for n in kind.values()]
            if names and sum(_has_hangul(n) for n in names) > len(names) / 2:
                for kind in data.values():
                    for key, s in kind.items():
                        if not _has_hangul(s):
                            kind[key] = FALLBACK_KO.get(s, s)
            try:
                with open(CACHE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=0)
            except OSError:
                pass
        for key, s in data.get("items", {}).items():
            iid = int(key)
            if iid in self.items:
                self.items[iid] = (s, self.items[iid][1])
        for key, s in data.get("units", {}).items():
            self.unit_names[int(key)] = s
        return True

    def level_table(self, uid):
        t = self.unit_levels.get(uid)
        if not t:
            return []
        if t not in self._level_cache:
            ue = self.ue
            self._level_cache[t] = sorted(
                (ue.get(r, P["Level"]), ue.get(r, P["RequiredExperience"])) for _, r, P in self.rows(t))
        return self._level_cache[t]

    def level_of(self, uid, exp):
        lv = 1
        for level, need in self.level_table(uid):
            if exp >= need:
                lv = level
        return lv

    def exp_for(self, uid, level):
        for lv, need in self.level_table(uid):
            if lv == level:
                return need
        return None

    def item_name(self, item_id):
        return self.items.get(item_id, (f"#{item_id}", "?"))

    # ------------------------------------------------------------------ 세이브
    def save(self):
        return self.ue.get(self.mgr, self.mgr_p["m_pGameSaveData"])

    def _player(self):
        sv = self.save()
        return sv + self.S["Player"].offset if sv else 0

    def player_get(self, field):
        b = self._player()
        return self.ue.get(b, self.PL[field]) if b else None

    def player_set(self, field, value):
        b = self._player()
        return bool(b) and self.ue.set(b, self.PL[field], value)

    def party_ids(self):
        sv = self.save()
        if not sv:
            return []
        base = sv + self.S["Party"].offset
        return [self.p.i32(a) for a in self.ue.array_items(base, self.PARTY["partyList"])]

    def units(self):
        sv = self.save()
        if not sv:
            return []
        ue, UP = self.ue, self.UP
        out = []
        for a in ue.array_items(sv, self.S["unitParameterList"]):
            uid = ue.get(a, UP["UnitId"])
            exp = ue.get(a, UP["Experience"])
            out.append({
                "addr": a, "id": uid, "name": self.unit_names.get(uid, f"#{uid}"),
                "exp": exp, "level": self.level_of(uid, exp),
                "hp": ue.get(a, UP["HitPoint"]), "mp": ue.get(a, UP["MagicPoint"]),
                "join": ue.get(a, UP["JoinStatus"]),
                "bonus": self.unit_bonus(a),
            })
        return out

    def unit_bonus(self, unit_addr):
        addrs = self.ue.array_items(unit_addr, self.UP["baseParameterList"])
        return {i: self.p.i32(addrs[i]) for i in STAT_NAMES if i < len(addrs)}

    def unit_set(self, unit_addr, field, value):
        return self.ue.set(unit_addr, self.UP[field], value)

    def unit_set_bonus(self, unit_addr, index, value):
        addrs = self.ue.array_items(unit_addr, self.UP["baseParameterList"])
        return index < len(addrs) and self.p.w(addrs[index], "<i", int(value))

    def inventory(self):
        sv = self.save()
        if not sv:
            return []
        ue = self.ue
        out = []
        for a in ue.array_items(sv, self.S["inventory"]):
            iid = ue.get(a, self.INV["ItemId"])
            name, cat = self.item_name(iid)
            out.append({"addr": a, "id": iid, "name": name, "cat": cat, "num": ue.get(a, self.INV["Num"])})
        return out

    def item_set(self, item_addr, num):
        return self.ue.set(item_addr, self.INV["Num"], num)

    def inventory_slack(self):
        """인벤토리 배열에 재할당 없이 더 넣을 수 있는 칸 수."""
        return self._slack("inventory")

    def _append(self, array_name, elem):
        """세이브의 배열 끝에 원소 하나를 써 넣는다. 여유 칸이 없으면 False.

        게임 쪽 메모리 할당자를 건드릴 수 없으므로 배열에 이미 확보된 여유 칸만 사용한다.
        """
        sv = self.save()
        if not sv:
            return False
        p = self.p
        pr = self.S[array_name]
        a = sv + pr.offset
        raw = p.read(a, 16)
        if not raw or len(elem) != pr.extra.size:
            return False
        data, count, cap = struct.unpack("<Qii", raw)
        if not data or count < 0 or count >= cap or cap > 100000:
            return False
        if not p.write(data + count * len(elem), bytes(elem)):
            return False
        # 원소를 먼저 쓰고 개수를 마지막에 늘린다. 그 사이 게임이 배열을 바꿨으면 취소.
        if p.read(a, 16) != raw:
            return False
        return p.w(a + 8, "<i", count + 1)

    def _slack(self, array_name):
        sv = self.save()
        if not sv:
            return 0
        a = sv + self.S[array_name].offset
        return max(0, self.p.i32(a + 12) - self.p.i32(a + 8))

    def add_item(self, item_id, num):
        """보유하지 않은 아이템을 인벤토리 끝에 등록한다. 빈 칸이 없으면 False."""
        elem = bytearray(self.S["inventory"].extra.size)
        struct.pack_into("<i", elem, self.INV["ItemId"].offset, int(item_id))
        struct.pack_into("<i", elem, self.INV["Num"].offset, int(num))
        return self._append("inventory", elem)

    # ------------------------------------------------------------------ 비전
    def all_visions(self):
        """게임에 존재하는 모든 비전 {id: 이름}."""
        return {i: n for i, (n, cat) in self.items.items() if cat == "비전"}

    def vision_slack(self):
        return self._slack("visionList")

    def add_vision(self, vision_id):
        """미보유 비전을 등록한다 (싱크로 포인트는 빈 상태). 빈 칸이 없으면 False."""
        if any(v["id"] == vision_id for v in self.visions()):
            return True
        size = self.S["visionList"].extra.size
        sync = self.VIS["synchroPoints"]
        if size - sync.offset != 0x50:
            return False  # 예상한 구조가 아니면 건드리지 않는다
        elem = bytearray(size)
        struct.pack_into("<i", elem, self.VIS["ID"].offset, int(vision_id))
        # 비어 있는 TMap: 비트 배열 용량 0x80, 빈 칸 목록 없음(-1)
        struct.pack_into("<ii", elem, sync.offset + 0x28, 0, 0x80)
        struct.pack_into("<ii", elem, sync.offset + 0x30, -1, 0)
        return self._append("visionList", elem)

    # ------------------------------------------------------------------ 랜덤 인카운터
    def player_unit(self):
        """필드의 플레이어 캐릭터 객체 (없으면 0)."""
        ue = self.ue
        cur = getattr(self, "_player_unit", 0)
        if cur and ue.is_live(cur) and ue.p.u64(cur + 0x10) == self._player_unit_cls:
            return cur
        found = ue.find_live("CPP_MapUnit_Playable")
        self._player_unit = found[0] if found else 0
        self._player_unit_cls = ue.p.u64(self._player_unit + 0x10) if found else 0
        return self._player_unit

    def encounter_set(self, ratio, block):
        """인카운트 누적 배율을 고정한다 (주기적으로 호출). block 이면 완전히 막는다.

        필드에 플레이어가 있으면 True.
        """
        pl = self.player_unit()
        if not pl:
            return False
        ue = self.ue
        P = ue.props(self._player_unit_cls)
        thr = P["m_EncountThresholdDistance"]
        ue.set(pl, P["m_OverwriteEncountRatio"], 0.0 if block else float(ratio))
        if block:
            ue.set(pl, thr, ENCOUNT_OFF_DISTANCE)
        elif (ue.get(pl, thr) or 0) >= ENCOUNT_OFF_DISTANCE / 10:
            ue.set(pl, thr, self._encounter_default("m_EncountThresholdDistance", 4.0))
        return True

    def _encounter_default(self, field, fallback):
        ue = self.ue
        off = self._cdo_offset()
        cdo = ue.p.u64(self._player_unit_cls + off) if off else 0
        v = ue.get(cdo, ue.props(self._player_unit_cls)[field]) if cdo else None
        return v if v is not None and 0 < v < 1.0e6 else fallback

    def encounter_restore(self):
        """인카운터 관련 값을 클래스 기본값으로 되돌린다."""
        pl = self.player_unit()
        if not pl:
            return False
        ue = self.ue
        P = ue.props(self._player_unit_cls)
        cdo = ue.p.u64(self._player_unit_cls + self._cdo_offset()) if self._cdo_offset() else 0
        for field, fallback in (("m_OverwriteEncountRatio", 1.0), ("m_EncountThresholdDistance", 4.0)):
            v = ue.get(cdo, P[field]) if cdo else None
            if v is None or not (0 < v < 1.0e6):
                v = fallback
            ue.set(pl, P[field], v)
        return True

    def _cdo_offset(self):
        """UClass 안에서 ClassDefaultObject 포인터의 위치를 찾는다."""
        if not hasattr(self, "_cdo_off"):
            ue = self.ue
            cls = ue.find_struct("CPP_MapUnit_Playable")
            self._cdo_off = 0
            for off in range(0x60, 0x200, 8):
                o = ue.p.u64(cls + off)
                if o and ue.p.u64(o + 0x10) == cls and ue.fname_at(o + 0x18).startswith("Default__"):
                    self._cdo_off = off
                    break
        return self._cdo_off

    def visions(self):
        sv = self.save()
        if not sv:
            return []
        ue = self.ue
        out = []
        for a in ue.array_items(sv, self.S["visionList"]):
            vid = ue.get(a, self.VIS["ID"])
            out.append({"addr": a, "id": vid, "name": self.item_name(vid)[0],
                        "awakening": ue.get(a, self.VIS["awakeningPoint"])})
        return out

    def vision_set(self, addr, value):
        return self.ue.set(addr, self.VIS["awakeningPoint"], value)

    # ------------------------------------------------------------------ 전투 계산 테이블
    def calc_get(self, field):
        return self.ue.get(self.calc_row, self.calc_p[field])

    def calc_set(self, field, value):
        return self.ue.set(self.calc_row, self.calc_p[field], value)
