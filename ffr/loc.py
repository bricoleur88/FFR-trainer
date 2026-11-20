"""게임이 현재 언어(한국어)로 표시하는 문자열을 메모리에서 읽는다.

데이터 테이블의 이름(FText)은 문자열 테이블의 (네임스페이스, 키) ID 만 들고 있고,
실제 표시 문자열은 엔진 현지화 매니저의 맵에 있다. 그 맵의 원소 배열을 한 번 찾아서
ID -> 문자열 주소 사전을 만든다.
"""
import ctypes
import struct

from .mem import MBI, k32

ELEM = 0x20  # 맵 원소 크기: {ns u32, key u32, 표시문자열*, ...}


class Localizer:
    def __init__(self, ue):
        self.ue = ue
        self.p = ue.p
        self._ns = {}       # 문자열 테이블 경로 -> 네임스페이스 ID
        self._tables = None
        self.lookup = None  # (ns, key) -> 표시 문자열 객체 주소

    # ------------------------------------------------------------------ FText -> ID
    def _table_ns(self, table_path):
        if self._tables is None:
            ue = self.ue
            self._tables = {ue.path(o): o for o in ue.hdr if ue.class_name(o) == "StringTable"}
        if table_path not in self._ns:
            st = self._tables.get(table_path)
            inner = self.p.u64(st + 0x28) if st else 0
            self._ns[table_path] = self.p.u32(inner + 0x1C) if inner else None
        return self._ns[table_path]

    def text_id(self, ftext_addr):
        """FText 가 문자열 테이블 항목이면 (ns, key) 를, 아니면 None 을 돌려준다."""
        p = self.p
        data = p.u64(ftext_addr)
        hist = p.u64(data + 0x18) if data else 0
        raw = p.read(hist + 0x10, 12) if hist else None
        if not raw:
            return None
        name_idx, name_num, key = struct.unpack("<III", raw)
        table = self.ue.name(name_idx, name_num)
        if not table.startswith("/"):
            return None
        ns = self._table_ns(table)
        return (ns, key) if ns is not None else None

    # ------------------------------------------------------------------ 표시 문자열
    def _display(self, obj):
        p = self.p
        raw = p.read(obj + 8, 16) if obj else None
        if not raw:
            return None
        data, num, cap = struct.unpack("<Qii", raw)
        if not (0 < num <= 2048 and num <= cap):
            return None
        s = p.read(data, num * 2)
        if not s:
            return None
        return s.decode("utf-16le", "replace").rstrip("\0")

    def locate(self, sample_id):
        """sample_id 가 들어 있는 맵 원소 배열을 찾아 사전을 만든다. 성공하면 True."""
        p = self.p
        pat = struct.pack("<II", *sample_id)
        lo, hi = p.base, p.base + p.size
        for start, size in p.regions():
            if lo <= start < hi or size < 0x10000:
                continue
            off = 0
            while off < size:
                n = min(size - off, 1 << 25)
                d = p.read(start + off, n)
                i = d.find(pat) if d else -1
                while i >= 0:
                    hit = start + off + i
                    if hit % 8 == 0 and self._display(p.u64(hit + 8)) is not None:
                        self._build(hit)
                        return True
                    i = d.find(pat, i + 1)
                off += n
        return False

    def _build(self, hit):
        p = self.p
        mbi = MBI()
        k32.VirtualQueryEx(p.h, hit, ctypes.byref(mbi), ctypes.sizeof(mbi))
        alloc = mbi.AllocationBase
        lookup = {}
        for start, size in p.regions(alloc, alloc + (1 << 30)):
            k32.VirtualQueryEx(p.h, start, ctypes.byref(mbi), ctypes.sizeof(mbi))
            if mbi.AllocationBase != alloc:
                break
            d = p.read(start, size)
            if not d:
                continue
            first = (hit - start) % ELEM
            for o in range(first, len(d) - ELEM + 1, ELEM):
                ns, key, ptr = struct.unpack_from("<IIQ", d, o)
                if 0x10000 < ptr < 0x7FFFFFFFFFFF and not ptr & 7:
                    lookup[(ns, key)] = ptr
        self.lookup = lookup

    def resolve(self, ftext_addr):
        """FText 의 현재 언어 표시 문자열 (못 찾으면 None)."""
        if not self.lookup:
            return None
        tid = self.text_id(ftext_addr)
        obj = self.lookup.get(tid) if tid else None
        return self._display(obj) if obj else None
