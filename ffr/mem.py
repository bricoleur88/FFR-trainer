"""Windows 프로세스 메모리 읽기/쓰기 (ctypes, 외부 의존성 없음)."""
import ctypes
import struct
from ctypes import wintypes as wt

from .i18n import _

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
WRITABLE = 0x04 | 0x08 | 0x40 | 0x80  # RW, WC, XRW, XWC


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", wt.LONG), ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_uint64), ("AllocationBase", ctypes.c_uint64),
        ("AllocationProtect", wt.DWORD), ("PartitionId", wt.WORD),
        ("RegionSize", ctypes.c_uint64), ("State", wt.DWORD),
        ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]


class MODULEINFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p), ("SizeOfImage", wt.DWORD),
                ("EntryPoint", ctypes.c_void_p)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_uint64, ctypes.POINTER(MBI), ctypes.c_size_t]
psapi.EnumProcessModules.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p), wt.DWORD,
                                     ctypes.POINTER(wt.DWORD)]
psapi.GetModuleInformation.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MODULEINFO),
                                       wt.DWORD]


def find_pid(exe_name):
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    pe = PROCESSENTRY32W()
    pe.dwSize = ctypes.sizeof(pe)
    pid = None
    ok = k32.Process32FirstW(snap, ctypes.byref(pe))
    while ok:
        if pe.szExeFile.lower() == exe_name.lower():
            pid = pe.th32ProcessID
            break
        ok = k32.Process32NextW(snap, ctypes.byref(pe))
    k32.CloseHandle(snap)
    return pid


class Process:
    def __init__(self, exe_name):
        self.pid = find_pid(exe_name)
        if not self.pid:
            raise RuntimeError(_("{exe} 프로세스를 찾을 수 없습니다. 게임을 먼저 실행하세요.", exe=exe_name))
        self.h = k32.OpenProcess(
            PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION,
            False, self.pid)
        if not self.h:
            raise RuntimeError(_("프로세스를 열 수 없습니다 (오류 {code}). 관리자 권한으로 실행해 보세요.",
                                 code=ctypes.get_last_error()))
        mod = ctypes.c_void_p()
        need = wt.DWORD()
        if not psapi.EnumProcessModules(self.h, ctypes.byref(mod), 8, ctypes.byref(need)):
            raise RuntimeError(_("모듈 정보를 읽을 수 없습니다 (게임이 아직 로딩 중일 수 있음)."))
        mi = MODULEINFO()
        psapi.GetModuleInformation(self.h, mod, ctypes.byref(mi), ctypes.sizeof(mi))
        self.base = mi.lpBaseOfDll
        self.size = mi.SizeOfImage

    def alive(self):
        code = wt.DWORD()
        k32.GetExitCodeProcess(self.h, ctypes.byref(code))
        return code.value == 259

    def close(self):
        if self.h:
            k32.CloseHandle(self.h)
            self.h = None

    # ---- 읽기 ----
    def read(self, addr, size):
        if addr < 0x10000 or addr > 0x7FFFFFFFFFFF:
            return None
        buf = ctypes.create_string_buffer(size)
        n = ctypes.c_size_t()
        if not k32.ReadProcessMemory(self.h, addr, buf, size, ctypes.byref(n)) or n.value != size:
            return None
        return buf.raw

    def _un(self, addr, fmt, size, default=0):
        d = self.read(addr, size)
        return struct.unpack(fmt, d)[0] if d else default

    def u8(self, a): return self._un(a, "<B", 1)
    def u16(self, a): return self._un(a, "<H", 2)
    def i32(self, a): return self._un(a, "<i", 4)
    def u32(self, a): return self._un(a, "<I", 4)
    def i64(self, a): return self._un(a, "<q", 8)
    def u64(self, a): return self._un(a, "<Q", 8)
    def f32(self, a): return self._un(a, "<f", 4, 0.0)
    def f64(self, a): return self._un(a, "<d", 8, 0.0)

    # ---- 쓰기 ----
    def write(self, addr, data):
        n = ctypes.c_size_t()
        return bool(k32.WriteProcessMemory(self.h, addr, data, len(data), ctypes.byref(n))) \
            and n.value == len(data)

    def w(self, addr, fmt, value):
        return self.write(addr, struct.pack(fmt, value))

    # ---- 영역 ----
    def regions(self, start=0x10000, end=0x7FFFFFFF0000, writable_only=True):
        mbi = MBI()
        a = start
        while a < end:
            if not k32.VirtualQueryEx(self.h, a, ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            nxt = mbi.BaseAddress + mbi.RegionSize
            if mbi.State == MEM_COMMIT and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS)):
                if not writable_only or (mbi.Protect & WRITABLE):
                    lo = max(mbi.BaseAddress, start)
                    yield lo, min(nxt, end) - lo
            if nxt <= a:
                break
            a = nxt
