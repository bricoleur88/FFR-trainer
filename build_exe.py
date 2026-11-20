# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 bricoleur88
"""배포용 실행 파일을 빌드하고 zip 으로 묶는다.

사용:  python build_exe.py                  빌드 + zip
       python build_exe.py --package-only   이미 빌드된 폴더로 zip 만 다시 만들기
필요:  pip install "flet[all]" pyinstaller

결과:  dist/FFR-Trainer/        빌드된 실행 파일 폴더
       dist/FFR-Trainer.zip     배포용 (실행 파일 + 세 언어 README + 라이선스). 화면 언어는 프로그램 안에서 고른다.
"""
import builtins
import os
import shutil
import sys
import zipfile

import flet_cli.__pyinstaller.win_utils as win_utils
import flet_cli.cli

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
APP = os.path.join(DIST, "FFR-Trainer")

DOCS = ("README.md", "README.ko.md", "README.ja.md", "LICENSE", "THIRD-PARTY-NOTICES.md")
# 실행하면서 생긴 파일과 예전 문서는 배포본에 넣지 않는다
RUNTIME_FILES = ("names_cache.json", "names_ko.json", "drop_defaults.json", "lang.txt", "사용법.md")
OLD_ZIPS = ("FFR-Trainer-ko.zip", "FFR-Trainer-en.zip", "FFR-Trainer-ja.zip")  # 언어별로 나누던 시절의 묶음


def _open(file, mode="r", *args, **kwargs):
    # flet-cli 1.1.2 는 exe 를 바이너리로 열면서 encoding 을 넘겨 오류가 난다. 그 인자만 걸러낸다.
    if "b" in mode:
        kwargs.pop("encoding", None)
    return builtins.open(file, mode, *args, **kwargs)


def build():
    win_utils.open = _open
    sys.argv = ["flet", "pack", "trainer.py", "-n", "FFR-Trainer", "-D", "-y", "--distpath", "dist"]
    os.chdir(ROOT)
    flet_cli.cli.main()


def package():
    for name in RUNTIME_FILES + DOCS:
        path = os.path.join(APP, name)
        if os.path.exists(path):
            os.remove(path)
    target = os.path.join(DIST, "FFR-Trainer.zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for folder, _dirs, files in os.walk(APP):
            for file in files:
                full = os.path.join(folder, file)
                z.write(full, os.path.join("FFR-Trainer", os.path.relpath(full, APP)))
        for doc in DOCS:
            z.write(os.path.join(ROOT, doc), f"FFR-Trainer/{doc}")
    print(f"{os.path.basename(target)}  {os.path.getsize(target) / 1048576:.1f} MB")
    for name in OLD_ZIPS:
        path = os.path.join(DIST, name)
        if os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    if "--package-only" not in sys.argv:
        if os.path.isdir(APP):
            shutil.rmtree(APP)
        build()
    package()
