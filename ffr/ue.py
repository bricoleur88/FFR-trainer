"""언리얼 엔진 5 런타임 리플렉션 리더.

고정 오프셋 대신 실행 중인 게임에서 FNamePool / GUObjectArray 를 찾아
클래스·프로퍼티 이름으로 오프셋을 구한다. 게임이 패치돼도 대부분 그대로 동작한다.
"""
import struct

from .i18n import _
from .mem import Process

EXE = "FFRS-Win64-Shipping.exe"


class Prop:
    __slots__ = ("name", "type", "offset", "size", "addr", "extra")

    def __init__(self, name, type_, offset, size, addr, extra=None):
        self.name, self.type, self.offset, self.size, self.addr, self.extra = \
            name, type_, offset, size, addr, extra

    def __repr__(self):
        return f"<{self.type} {self.name} @0x{self.offset:X}>"


class UE:
    def __init__(self, exe=EXE):
        self.p = Process(exe)
        self._names = {}
        self._props = {}
        self.hdr = {}          # obj addr -> (class, name_idx, name_num, outer)
        self._by_class = {}
        self._locate_globals()
        self.refresh()
        self._detect_layout()

    # ------------------------------------------------------------------ 전역 탐색
    def _locate_globals(self):
        p = self.p
        lo, hi = p.base, p.base + p.size
        self.name_blocks = None
        self.obj_array = None
        seen = set()
        for start, size in p.regions(lo, hi):
            data = p.read(start, size)
            if not data:
                continue
            n = len(data) // 8
            qs = struct.unpack_from(f"<{n}Q", data)
            for i, v in enumerate(qs):
                if v < 0x10000 or v > 0x7FFFFFFFFFFF or lo <= v < hi or v & 7:
                    continue
                addr = start + i * 8
                # GUObjectArray.ObjObjects: Objects**, PreAlloc, MaxElements, NumElements, MaxChunks, NumChunks
                if self.obj_array is None and i + 3 < n:
                    mx, num, mxc, nc = struct.unpack_from("<iiii", data, (i + 2) * 8)
                    if 0x10000 <= mx <= 0x4000000 and 1000 < num <= mx and 0 < nc <= mxc \
                            and nc == (num + 0xFFFF) // 0x10000:
                        if self._check_obj_array(addr):
                            self.obj_array = addr
                # FNamePool.Blocks[0] -> "None" 엔트리로 시작
                if self.name_blocks is None and v not in seen:
                    seen.add(v)
                    h = p.read(v, 22)
                    if h and h[2:6] == b"None" and h[8:20] == b"ByteProperty":
                        self.name_blocks = addr
            if self.name_blocks and self.obj_array:
                break
        if not self.name_blocks:
            raise RuntimeError(_("FNamePool 을 찾지 못했습니다."))
        if not self.obj_array:
            raise RuntimeError(_("GUObjectArray 를 찾지 못했습니다."))

    def _check_obj_array(self, addr):
        p = self.p
        chunk0 = p.u64(p.u64(addr))
        if not chunk0:
            return False
        for isz in (0x18, 0x10, 0x14, 0x20):
            ok = True
            for i in (1, 2, 5, 40):
                o = p.u64(chunk0 + i * isz)
                if not o or p.i32(o + 0xC) != i:
                    ok = False
                    break
            if ok:
                self.item_size = isz
                return True
        return False

    # ------------------------------------------------------------------ 이름
    def name(self, idx, number=0):
        s = self._names.get(idx)
        if s is None:
            p = self.p
            block = p.u64(self.name_blocks + (idx >> 16) * 8)
            ent = block + (idx & 0xFFFF) * 2
            hdr = p.u16(ent)
            ln = hdr >> 6
            if not block or ln == 0 or ln > 1023:
                s = ""
            elif hdr & 1:
                s = (p.read(ent + 2, ln * 2) or b"").decode("utf-16le", "replace")
            else:
                s = (p.read(ent + 2, ln) or b"").decode("latin-1")
            self._names[idx] = s
        return f"{s}_{number - 1}" if number else s

    def fname_at(self, addr):
        d = self.p.read(addr, 8)
        if not d:
            return ""
        i, n = struct.unpack("<II", d)
        return self.name(i, n)

    # ------------------------------------------------------------------ 오브젝트
    def refresh(self):
        """GUObjectArray 전체를 다시 읽는다."""
        p = self.p
        hdr = {}
        chunks = p.u64(self.obj_array)
        num = p.i32(self.obj_array + 0x14)
        isz = self.item_size
        for ci in range((num + 0xFFFF) // 0x10000):
            chunk = p.u64(chunks + ci * 8)
            cnt = min(0x10000, num - ci * 0x10000)
            data = p.read(chunk, cnt * isz)
            if not data:
                continue
            for i in range(cnt):
                o = struct.unpack_from("<Q", data, i * isz)[0]
                if not o:
                    continue
                h = p.read(o, 0x28)
                if not h:
                    continue
                _, _, _, cls, ni, nn, outer = struct.unpack("<QIiQIIQ", h)
                hdr[o] = (cls, ni, nn, outer)
        self.hdr = hdr
        self._by_class = {}

    def find_live(self, class_name):
        """class_name (하위 클래스 포함)의 인스턴스를 오브젝트 배열에서 바로 찾는다 (CDO 제외).

        refresh() 와 달리 self.hdr 를 건드리지 않아 백그라운드 스레드에서 써도 된다.
        """
        p = self.p
        target = self.find_struct(class_name)
        if not target:
            return []
        chunks = p.u64(self.obj_array)
        num = p.i32(self.obj_array + 0x14)
        isz = self.item_size
        ok, out = {}, []
        for ci in range((num + 0xFFFF) // 0x10000):
            cnt = min(0x10000, num - ci * 0x10000)
            data = p.read(p.u64(chunks + ci * 8), cnt * isz)
            if not data:
                continue
            for i in range(cnt):
                o = struct.unpack_from("<Q", data, i * isz)[0]
                if not o:
                    continue
                c = p.u64(o + 0x10)
                hit = ok.get(c)
                if hit is None:
                    hit = ok[c] = target in self.supers(c)
                if hit and not self.fname_at(o + 0x18).startswith("Default__"):
                    out.append(o)
        return out

    def is_live(self, o):
        """o 가 아직 오브젝트 배열에 등록된 같은 객체인지 확인한다."""
        p = self.p
        idx = p.i32(o + 0xC)
        if idx <= 0 or idx >= p.i32(self.obj_array + 0x14):
            return False
        chunk = p.u64(p.u64(self.obj_array) + (idx >> 16) * 8)
        return p.u64(chunk + (idx & 0xFFFF) * self.item_size) == o

    def obj_name(self, o):
        h = self.hdr.get(o)
        if h:
            return self.name(h[1], h[2])
        return self.fname_at(o + 0x18) if o else ""

    def obj_class(self, o):
        h = self.hdr.get(o)
        return h[0] if h else self.p.u64(o + 0x10)

    def class_name(self, o):
        return self.obj_name(self.obj_class(o))

    def path(self, o):
        parts = []
        while o and len(parts) < 16:
            parts.append(self.obj_name(o))
            h = self.hdr.get(o)
            o = h[3] if h else 0
        return ".".join(reversed(parts))

    def find_struct(self, name, kinds=("Class", "ScriptStruct", "BlueprintGeneratedClass",
                                       "WidgetBlueprintGeneratedClass", "AnimBlueprintGeneratedClass")):
        for o, h in self.hdr.items():
            if self.name(h[1], h[2]) == name and self.class_name(o) in kinds:
                return o
        return 0

    def supers(self, struct_addr):
        out = []
        s = struct_addr
        while s and len(out) < 64:
            out.append(s)
            s = self.p.u64(s + self.off_super)
        return out

    def is_a(self, o, class_addr):
        return class_addr in self.supers(self.obj_class(o))

    def instances(self, class_name, include_default=False, exact=False):
        """class_name (또는 그 하위 클래스)의 살아있는 인스턴스 목록."""
        target = self.find_struct(class_name)
        if not target:
            return []
        ok_cache = {}
        out = []
        for o, h in self.hdr.items():
            c = h[0]
            ok = ok_cache.get(c)
            if ok is None:
                ok = (c == target) if exact else (target in self.supers(c))
                ok_cache[c] = ok
            if ok:
                if not include_default and self.name(h[1]).startswith("Default__"):
                    continue
                out.append(o)
        return out

    # ------------------------------------------------------------------ 레이아웃 감지
    def _detect_layout(self):
        p = self.p
        actor = self.find_struct("Actor", ("Class",))
        vector = self.find_struct("Vector", ("ScriptStruct",))
        if not actor or not vector:
            raise RuntimeError(_("기본 엔진 클래스를 찾지 못했습니다 (게임 로딩이 끝난 뒤 다시 시도)."))
        self.off_super = None
        for off in range(0x30, 0x70, 8):
            if self.obj_name(p.u64(actor + off)) == "Object":
                self.off_super = off
                break
        if self.off_super is None:
            raise RuntimeError(_("UStruct 레이아웃을 인식하지 못했습니다."))
        self.off_children = self.off_super + 0x8
        self.off_childprops = self.off_super + 0x10
        self.off_propsize = self.off_super + 0x18

        first = p.u64(vector + self.off_childprops)
        self.ff_next = self.ff_name = None
        for nxt, nm in ((0x18, 0x20), (0x20, 0x28), (0x18, 0x28), (0x20, 0x20)):
            f, names = first, []
            while f and len(names) < 4:
                names.append(self.fname_at(f + nm))
                f = p.u64(f + nxt)
            if names[:3] == ["X", "Y", "Z"]:
                self.ff_next, self.ff_name = nxt, nm
                break
        if self.ff_next is None:
            raise RuntimeError(_("FField 레이아웃을 인식하지 못했습니다."))
        fx = first
        fy = p.u64(fx + self.ff_next)
        fz = p.u64(fy + self.ff_next)
        self.fp_offset = None
        for off in range(self.ff_name + 8, 0x70, 4):
            a, b, c = p.i32(fx + off), p.i32(fy + off), p.i32(fz + off)
            if a == 0 and b in (4, 8) and c == b * 2:
                self.fp_offset = off
                break
        if self.fp_offset is None:
            raise RuntimeError(_("FProperty 레이아웃을 인식하지 못했습니다."))
        self.fp_elemsize = self.fp_offset - 0x10
        self.fp_end = self.fp_offset + 0x2C

    # ------------------------------------------------------------------ 프로퍼티
    def _read_prop(self, f):
        p = self.p
        name = self.fname_at(f + self.ff_name)
        ftype = self.fname_at(p.u64(f + 8))
        offset = p.i32(f + self.fp_offset)
        size = p.i32(f + self.fp_elemsize)
        extra = None
        e = f + self.fp_end
        if ftype in ("ObjectProperty", "StructProperty", "ClassProperty", "ByteProperty",
                     "WeakObjectProperty", "SoftObjectProperty", "InterfaceProperty"):
            extra = p.u64(e)
        elif ftype in ("ArrayProperty", "SetProperty"):
            inner = p.u64(e)
            if not self.fname_at(p.u64(inner + 8)).endswith("Property"):
                inner = p.u64(e + 8)  # UE 5.4+: ArrayFlags 가 Inner 앞에 온다
            extra = self._read_prop(inner) if inner else None
        elif ftype == "MapProperty":
            k, v = p.u64(e), p.u64(e + 8)
            extra = (self._read_prop(k) if k else None, self._read_prop(v) if v else None)
        elif ftype == "EnumProperty":
            extra = p.u64(e + 8)
        elif ftype == "BoolProperty":
            d = p.read(e, 4) or b"\0\0\0\0"
            extra = (d[1], d[2])  # ByteOffset, ByteMask
        return Prop(name, ftype, offset, size, f, extra)

    def own_props(self, struct_addr):
        out = []
        f = self.p.u64(struct_addr + self.off_childprops)
        while f and len(out) < 4096:
            out.append(self._read_prop(f))
            f = self.p.u64(f + self.ff_next)
        return out

    def props(self, struct_addr):
        """상속 포함 {이름: Prop}."""
        d = self._props.get(struct_addr)
        if d is None:
            d = {}
            for s in reversed(self.supers(struct_addr)):
                for pr in self.own_props(s):
                    d[pr.name] = pr
            self._props[struct_addr] = d
        return d

    def struct_size(self, struct_addr):
        return self.p.i32(struct_addr + self.off_propsize)

    def type_str(self, pr):
        t = pr.type
        if t in ("ObjectProperty", "StructProperty", "ClassProperty", "WeakObjectProperty",
                 "SoftObjectProperty", "EnumProperty", "InterfaceProperty") and pr.extra:
            return f"{t}<{self.obj_name(pr.extra)}>"
        if t == "ByteProperty" and pr.extra:
            return f"ByteProperty<{self.obj_name(pr.extra)}>"
        if t in ("ArrayProperty", "SetProperty") and pr.extra:
            return f"{t}<{self.type_str(pr.extra)}>"
        if t == "MapProperty" and pr.extra and pr.extra[0] and pr.extra[1]:
            return f"MapProperty<{self.type_str(pr.extra[0])}, {self.type_str(pr.extra[1])}>"
        if t == "BoolProperty" and pr.extra:
            return f"BoolProperty(mask 0x{pr.extra[1]:02X})"
        return t

    # ------------------------------------------------------------------ 값 접근
    _FMT = {
        "IntProperty": ("<i", 4), "UInt32Property": ("<I", 4), "Int64Property": ("<q", 8),
        "UInt64Property": ("<Q", 8), "Int16Property": ("<h", 2), "UInt16Property": ("<H", 2),
        "Int8Property": ("<b", 1), "ByteProperty": ("<B", 1), "FloatProperty": ("<f", 4),
        "DoubleProperty": ("<d", 8), "ObjectProperty": ("<Q", 8), "ClassProperty": ("<Q", 8),
        "EnumProperty": ("<B", 1),
    }

    def get(self, base, pr):
        """base(오브젝트/구조체 주소)에서 프로퍼티 값을 읽는다."""
        p = self.p
        a = base + pr.offset
        if pr.type == "BoolProperty":
            bo, mask = pr.extra
            return bool(p.u8(a + bo) & mask)
        if pr.type == "NameProperty":
            return self.fname_at(a)
        if pr.type == "StrProperty":
            data, num = p.u64(a), p.i32(a + 8)
            if not data or num <= 0 or num > 4096:
                return ""
            return (p.read(data, num * 2) or b"").decode("utf-16le", "replace").rstrip("\0")
        if pr.type == "StructProperty":
            return a
        if pr.type == "ArrayProperty":
            return p.u64(a), p.i32(a + 8)  # (data, count)
        fmt = self._FMT.get(pr.type)
        if not fmt:
            return None
        d = p.read(a, fmt[1])
        return struct.unpack(fmt[0], d)[0] if d else None

    def set(self, base, pr, value):
        p = self.p
        a = base + pr.offset
        if pr.type == "BoolProperty":
            bo, mask = pr.extra
            cur = p.u8(a + bo)
            return p.write(a + bo, bytes([(cur | mask) if value else (cur & ~mask & 0xFF)]))
        fmt = self._FMT.get(pr.type)
        if not fmt or pr.type in ("ObjectProperty", "ClassProperty"):
            raise TypeError(_("{type} 은(는) 쓰기를 지원하지 않습니다.", type=pr.type))
        if fmt[0][1] in "fd":
            value = float(value)
        else:
            value = int(value)
        return p.write(a, struct.pack(fmt[0], value))

    def array_items(self, base, pr):
        """ArrayProperty 의 각 원소 주소를 돌려준다."""
        data, num = self.get(base, pr)
        if not data or num <= 0 or num > 100000 or not pr.extra:
            return []
        return [data + i * pr.extra.size for i in range(num)]
