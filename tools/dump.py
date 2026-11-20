"""실행 중인 게임의 클래스/구조체 정의와 인스턴스 수를 덤프한다 (분석용).

사용: python tools/dump.py [출력폴더]
"""
import collections
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ffr.ue import UE  # noqa: E402

KINDS = ("Class", "ScriptStruct", "BlueprintGeneratedClass", "WidgetBlueprintGeneratedClass")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "dump"
    os.makedirs(out, exist_ok=True)
    t = time.time()
    ue = UE()
    print(f"pid={ue.p.pid} base=0x{ue.p.base:X} names=0x{ue.name_blocks:X} "
          f"objects=0x{ue.obj_array:X} item=0x{ue.item_size:X} count={len(ue.hdr)}")
    print(f"layout: super=0x{ue.off_super:X} ff_next=0x{ue.ff_next:X} ff_name=0x{ue.ff_name:X} "
          f"fp_offset=0x{ue.fp_offset:X}  ({time.time() - t:.1f}s)")

    counts = collections.Counter(h[0] for h in ue.hdr.values())
    with open(os.path.join(out, "classes.txt"), "w", encoding="utf-8") as f:
        for o, h in ue.hdr.items():
            kind = ue.class_name(o)
            if kind not in KINDS:
                continue
            path = ue.path(o)
            if path.startswith(("/Script/Engine.", "/Script/CoreUObject.", "/Script/UMG.",
                                "/Script/Slate", "/Script/Niagara", "/Script/MovieScene",
                                "/Script/Chaos", "/Script/Landscape", "/Script/AudioMixer")) \
                    and "--all" not in sys.argv:
                continue
            sup = ue.obj_name(ue.p.u64(o + ue.off_super))
            f.write(f"{kind} {path} : {sup}  size=0x{ue.struct_size(o):X}  instances={counts.get(o, 0)}\n")
            for pr in ue.own_props(o):
                f.write(f"    +0x{pr.offset:04X} {pr.name} : {ue.type_str(pr)}\n")
    with open(os.path.join(out, "instances.txt"), "w", encoding="utf-8") as f:
        for c, n in counts.most_common():
            f.write(f"{n:7d} {ue.path(c)}\n")
    print(f"완료: {out}  ({time.time() - t:.1f}s)")


if __name__ == "__main__":
    main()
