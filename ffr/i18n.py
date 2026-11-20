"""화면 문구 번역. 소스의 한국어 문구를 키로 쓰고, 영어/일본어 번역을 여기서 찾는다.

언어 선택 순서:  실행 인자 `--lang en`  >  실행 파일(또는 프로젝트) 폴더의 lang.txt  >  Windows 표시 언어
화면의 언어 메뉴에서 바꾸면 set_lang() 이 lang.txt 에 저장해 다음 실행에도 유지된다.
"""
import os
import sys

LANGS = ("ko", "en", "ja")
LANG_NAMES = {"ko": "한국어", "en": "English", "ja": "日本語"}


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _detect():
    if "--lang" in sys.argv:
        i = sys.argv.index("--lang")
        if i + 1 < len(sys.argv) and sys.argv[i + 1] in LANGS:
            return sys.argv[i + 1]
    try:
        with open(os.path.join(_app_dir(), "lang.txt"), encoding="utf-8") as f:
            code = f.read().strip().lower()
        if code in LANGS:
            return code
    except OSError:
        pass
    return _system_lang()


def _system_lang():
    """Windows 표시 언어가 한국어/일본어면 그 언어, 아니면 영어."""
    try:
        import ctypes
        primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
        return {0x12: "ko", 0x11: "ja"}.get(primary, "en")
    except Exception:  # noqa: BLE001
        return "en"


def set_lang(code):
    """화면 언어를 바꾸고 lang.txt 에 저장한다."""
    global LANG
    if code not in LANGS:
        return
    LANG = code
    try:
        with open(os.path.join(_app_dir(), "lang.txt"), "w", encoding="utf-8") as f:
            f.write(code + "\n")
    except OSError:
        pass


def get_lang():
    return LANG


LANG = _detect()

# 한국어 문구 -> (영어, 일본어)
TR = {
    # 창 / 공통
    "FINAL FANTASY RESONANCE 트레이너": ("FINAL FANTASY RESONANCE Trainer", "FINAL FANTASY RESONANCE トレーナー"),
    "FFR 트레이너": ("FFR Trainer", "FFR トレーナー"),
    "트레이너": ("Trainer", "トレーナー"),
    "이름 다시 읽기": ("Reload names", "名前を再読込"),
    "새로고침": ("Refresh", "更新"),
    "게임에 연결": ("Connect to game", "ゲームに接続"),
    "확인": ("OK", "OK"),
    "취소": ("Cancel", "キャンセル"),
    "계속": ("Continue", "続行"),
    "적용": ("Apply", "適用"),
    "최대": ("Max", "最大"),
    "기본값으로": ("Reset to defaults", "初期値に戻す"),
    "숫자를 올바르게 입력하세요.": ("Please enter a valid number.", "数値を正しく入力してください。"),
    # 연결 상태
    "게임에 연결하는 중…": ("Connecting to the game…", "ゲームに接続中…"),
    "연결됨 (PID {pid})": ("Connected (PID {pid})", "接続済み (PID {pid})"),
    "연결 실패: {error}": ("Connection failed: {error}", "接続失敗: {error}"),
    " — 한국어 이름 읽는 중… (몇 초 걸립니다)": (" — reading names… (takes a few seconds)",
                                         " — 名前を読み込み中… (数秒かかります)"),
    " — 한국어 이름을 찾지 못해 원문으로 표시": (" — names not found, showing internal names",
                                      " — 名前が見つからないため内部名で表示"),
    "먼저 게임에 연결하세요.": ("Connect to the game first.", "先にゲームに接続してください。"),
    "게임이 종료되었습니다 — 다시 실행 후 '게임에 연결'": (
        "The game has closed — start it again, then press 'Connect to game'",
        "ゲームが終了しました — 再起動して「ゲームに接続」を押してください"),
    "세이브 데이터가 아직 로드되지 않았습니다.": ("Save data is not loaded yet.", "セーブデータがまだロードされていません。"),
    "세이브 데이터 대기 중…": ("Waiting for save data…", "セーブデータ待機中…"),
    # 탭
    "일반": ("General", "一般"),
    "캐릭터": ("Characters", "キャラクター"),
    "아이템": ("Items", "アイテム"),
    "비전": ("Visions", "ビジョン"),
    "전투": ("Battle", "バトル"),
    # 일반 탭
    "소지금 (길)": ("Gil", "所持金 (ギル)"),
    "소지금 고정 (줄어들지 않음)": ("Lock gil (never decreases)", "所持金を固定 (減らない)"),
    "난이도": ("Difficulty", "難易度"),
    "난이도를 선택하세요.": ("Select a difficulty.", "難易度を選択してください。"),
    "랜덤 인카운터": ("Random encounters", "ランダムエンカウント"),
    "랜덤 인카운터 끄기": ("Disable random encounters", "ランダムエンカウントを無効化"),
    "인카운터 확률": ("Encounter rate", "エンカウント率"),
    "100%로": ("Reset to 100%", "100%に戻す"),
    "0% = 거의 안 만남 · 100% = 기본 · 300% = 3배 자주 (이동 거리 누적 배율)": (
        "0% = almost never · 100% = default · 300% = 3× as often (multiplier on distance walked)",
        "0% = ほぼ遭遇しない · 100% = 標準 · 300% = 3倍の頻度 (移動距離の蓄積倍率)"),
    "· 값은 현재 로드된 세이브 데이터에 바로 반영됩니다. 메뉴를 닫았다 열면 표시가 갱신됩니다.\n"
    "· 변경 내용을 유지하려면 게임 안에서 저장하세요. 만일을 위해 다른 슬롯에 저장하는 것을 권장합니다.": (
        "· Values are written straight into the loaded save data. Close and reopen the in-game menu to see them.\n"
        "· Save inside the game to keep your changes. Saving to a different slot is recommended, just in case.",
        "· 値はロード中のセーブデータに即座に反映されます。メニューを開き直すと表示が更新されます。\n"
        "· 変更を残すにはゲーム内でセーブしてください。念のため別のスロットへのセーブをおすすめします。"),
    "소지금을 {money} 길로 변경했습니다.": ("Gil set to {money}.", "所持金を {money} ギルに変更しました。"),
    "난이도를 {name}(으)로 변경했습니다.": ("Difficulty set to {name}.", "難易度を {name} に変更しました。"),
    "인카운터 없음": ("No encounters", "エンカウントなし"),
    "확률 {rate}%": ("Rate {rate}%", "確率 {rate}%"),
    "{what} 적용 중": ("{what} — active", "{what} 適用中"),
    "필드 대기 중 (필드에 나가면 적용)": ("Waiting for the field (applies once you are on the field)",
                               "フィールド待機中 (フィールドに出ると適用)"),
    "플레이 시간 {time}    전투 승리 {wins}회    현재 소지금 {money} 길": (
        "Play time {time}    Battles won {wins}    Gil {money}",
        "プレイ時間 {time}    戦闘勝利 {wins}回    所持金 {money} ギル"),
    # 캐릭터 탭
    "이름": ("Name", "名前"),
    "경험치": ("EXP", "経験値"),
    "상태": ("Status", "状態"),
    "합류": ("Joined", "加入"),
    "미합류": ("Not joined", "未加入"),
    "이탈": ("Left", "離脱"),
    "일시 이탈": ("Away", "一時離脱"),
    "로스트": ("Lost", "ロスト"),
    " · 파티": (" · Party", " · パーティ"),
    "캐릭터를 선택하세요": ("Select a character", "キャラクターを選択してください"),
    "{name} 편집": ("Edit {name}", "{name} を編集"),
    "레벨": ("Level", "レベル"),
    "레벨 적용": ("Set level", "レベル適用"),
    "경험치 적용": ("Set EXP", "経験値適用"),
    "현재 HP": ("HP", "現在HP"),
    "현재 MP": ("MP", "現在MP"),
    "HP/MP 적용": ("Set HP/MP", "HP/MP適用"),
    "스탯 영구 보너스": ("Permanent stat bonuses", "ステータス永続ボーナス"),
    "보너스 적용": ("Set bonuses", "ボーナス適用"),
    "최대 HP": ("Max HP", "最大HP"),
    "최대 MP": ("Max MP", "最大MP"),
    "공격": ("ATK", "攻撃"),
    "방어": ("DEF", "防御"),
    "지능": ("INT", "知性"),
    "정신": ("MND", "精神"),
    "민첩": ("AGI", "素早さ"),
    "레벨/경험치를 바꾼 뒤에는 저장 후 다시 로드하거나 전투를 한 번 치르면 능력치에 반영됩니다.": (
        "After changing level/EXP, save and reload or finish one battle for the stats to update.",
        "レベル/経験値を変更した後は、セーブしてロードし直すか、戦闘を1回行うと能力値に反映されます。"),
    "캐릭터를 먼저 선택하세요.": ("Select a character first.", "先にキャラクターを選択してください。"),
    "캐릭터를 찾을 수 없습니다. 새로고침 하세요.": ("Character not found. Press Refresh.",
                                   "キャラクターが見つかりません。更新してください。"),
    "이 캐릭터의 레벨 테이블을 찾지 못했습니다.": ("No level table found for this character.",
                                 "このキャラクターのレベルテーブルが見つかりません。"),
    "{name}의 레벨을 {level}(으)로 맞췄습니다.": ("{name}: level set to {level}.", "{name} のレベルを {level} にしました。"),
    "{name}의 경험치를 변경했습니다.": ("{name}: EXP changed.", "{name} の経験値を変更しました。"),
    "{name}의 HP/MP를 변경했습니다.": ("{name}: HP/MP changed.", "{name} のHP/MPを変更しました。"),
    "{name}의 스탯 보너스를 변경했습니다.": ("{name}: stat bonuses changed.", "{name} のステータスボーナスを変更しました。"),
    # 아이템 탭
    "보기": ("Show", "表示"),
    "보유 중": ("Owned", "所持中"),
    "전체": ("All", "すべて"),
    "소모품": ("Consumables", "消耗品"),
    "무기": ("Weapons", "武器"),
    "방어구": ("Armor", "防具"),
    "악세서리": ("Accessories", "アクセサリー"),
    "중요품": ("Key items", "だいじなもの"),
    "아티팩트": ("Artifacts", "アーティファクト"),
    "장비": ("Equipment", "装備"),
    "검색 (이름 또는 ID)": ("Search (name or ID)", "検索 (名前またはID)"),
    "분류": ("Category", "分類"),
    "수량": ("Qty", "数量"),
    "새로 등록 가능한 빈 슬롯: {count}개": ("Free slots for new entries: {count}", "新規登録できる空きスロット: {count}"),
    "선택 항목에 적용": ("Apply to selected", "選択項目に適用"),
    "보유 소모품 전부 적용": ("Apply to all owned consumables", "所持中の消耗品すべてに適用"),
    "선택 해제": ("Clear selection", "選択解除"),
    "흐린 글씨 = 미보유 (적용하면 새로 등록)": ("Greyed out = not owned (applying adds it)",
                                   "薄い文字 = 未所持 (適用すると新規登録)"),
    "아이템을 먼저 선택하세요 (행을 클릭하면 여러 개 선택됩니다).": (
        "Select items first (click rows to select several).",
        "先にアイテムを選択してください (行をクリックすると複数選択できます)。"),
    "아이템 {count}종에 적용했습니다.": ("Applied to {count} item(s).", "アイテム {count} 種に適用しました。"),
    "보유 소모품 {count}종을 {num}개로 맞췄습니다.": ("Set {count} owned consumable(s) to {num}.",
                                       "所持中の消耗品 {count} 種を {num} 個にしました。"),
    "{count}개는 인벤토리에 넣을 수 없는 분류라 건너뛰었습니다 (비전은 비전 탭에서).": (
        "Skipped {count} item(s) that cannot go into the inventory (use the Visions tab for visions).",
        "{count} 個はインベントリに入れられない分類のためスキップしました (ビジョンはビジョンタブで)。"),
    "인벤토리에 빈 슬롯이 없어 {count}개를 등록하지 못했습니다.\n\n"
    "게임에서 '아직 갖고 있지 않은 종류'의 아이템을 하나 얻으면 (상점 구매, 보물상자 등) "
    "게임이 인벤토리 공간을 넉넉히 늘려 빈 슬롯이 수십 개 생깁니다. 그 뒤에 다시 적용하세요.": (
        "{count} item(s) could not be added because the inventory has no free slots.\n\n"
        "Obtain one item of a kind you do not own yet in the game (buy it in a shop, open a chest, etc.). "
        "The game then enlarges the inventory and a few dozen free slots appear. Apply again after that.",
        "インベントリに空きスロットがないため {count} 個を登録できませんでした。\n\n"
        "ゲーム内で「まだ持っていない種類」のアイテムを1つ入手すると (ショップで購入、宝箱など)、"
        "ゲームがインベントリを拡張して空きスロットが数十個できます。その後でもう一度適用してください。"),
    "미보유 중요품 {count}개를 새로 등록합니다.\n\n"
    "중요품은 스토리 진행 조건으로 쓰이는 경우가 있어, 미리 갖고 있으면 이벤트 순서가 꼬일 수 "
    "있습니다. 적용 후에는 기존 세이브를 덮어쓰지 말고 새 슬롯에 저장하세요.": (
        "This will add {count} key item(s) you do not own.\n\n"
        "Key items can be story progress conditions, so owning them early may break the order of events. "
        "Afterwards, save to a new slot instead of overwriting your existing save.",
        "未所持のだいじなものを {count} 個、新規登録します。\n\n"
        "だいじなものはストーリー進行の条件に使われることがあり、先に持っているとイベントの順序が"
        "おかしくなる可能性があります。適用後は既存のセーブを上書きせず、新しいスロットにセーブしてください。"),
    # 비전 탭
    "보유": ("Owned", "所持"),
    "각성 포인트": ("Awakening pts", "覚醒ポイント"),
    "흐린 글씨 = 미보유": ("Greyed out = not owned", "薄い文字 = 未所持"),
    "선택한 미보유 비전 획득": ("Obtain selected visions", "選択した未所持ビジョンを入手"),
    "비전을 먼저 선택하세요.": ("Select visions first.", "先にビジョンを選択してください。"),
    "각성 포인트는 보유한 비전에만 적용됩니다.": ("Awakening points only apply to visions you own.",
                                "覚醒ポイントは所持しているビジョンにのみ適用されます。"),
    "미보유(흐린 글씨) 비전을 먼저 선택하세요.": ("Select visions you do not own (greyed out) first.",
                                 "先に未所持 (薄い文字) のビジョンを選択してください。"),
    "비전 {count}개의 각성 포인트를 변경했습니다.": ("Awakening points changed for {count} vision(s).",
                                    "ビジョン {count} 体の覚醒ポイントを変更しました。"),
    "비전 {count}개를 등록했습니다.": ("Added {count} vision(s).", "ビジョン {count} 体を登録しました。"),
    "비전 {count}개를 보유 목록에 등록합니다.\n\n"
    "게임이 직접 획득 처리한 것이 아니어서 싱크로 포인트 등은 비어 있는 상태로 들어갑니다. "
    "실험적인 기능이므로, 적용 후에는 기존 세이브를 덮어쓰지 말고 새 슬롯에 저장해 확인하세요.": (
        "This will add {count} vision(s) to your owned list.\n\n"
        "Because the game did not grant them itself, synchro points and similar data start out empty. "
        "This feature is experimental: afterwards, save to a new slot instead of overwriting your existing save.",
        "ビジョン {count} 体を所持リストに登録します。\n\n"
        "ゲーム自身が入手処理をしたわけではないため、シンクロポイントなどは空の状態で入ります。"
        "実験的な機能なので、適用後は既存のセーブを上書きせず、新しいスロットにセーブして確認してください。"),
    "비전 목록에 빈 슬롯이 없어 {count}개를 등록하지 못했습니다.\n\n"
    "게임에서 새 비전을 하나 정상적으로 획득하면 게임이 목록 공간을 늘려 빈 슬롯이 생깁니다. "
    "그 뒤에 다시 시도하세요.": (
        "{count} vision(s) could not be added because the vision list has no free slots.\n\n"
        "Obtain one new vision normally in the game; the game then enlarges the list and free slots appear. "
        "Try again after that.",
        "ビジョンリストに空きスロットがないため {count} 体を登録できませんでした。\n\n"
        "ゲーム内で新しいビジョンを1体普通に入手すると、ゲームがリストを拡張して空きスロットができます。"
        "その後でもう一度試してください。"),
    # 전투 탭
    "전투 아이템 드랍 확률": ("Battle item drop rates", "戦闘アイテムドロップ率"),
    "일반 드랍": ("Normal drop", "通常ドロップ"),
    "레어 드랍": ("Rare drop", "レアドロップ"),
    "항상 드랍 (100%)": ("Always drop (100%)", "必ずドロップ (100%)"),
    "드랍 확률 기본값으로": ("Reset drop rates", "ドロップ率を初期値に戻す"),
    "현재 평균 — 일반 {normal}% (적 {n_count}종) · 레어 {rare}% (적 {r_count}종)": (
        "Current average — normal {normal}% ({n_count} enemies) · rare {rare}% ({r_count} enemies)",
        "現在の平均 — 通常 {normal}% (敵 {n_count} 種) · レア {rare}% (敵 {r_count} 種)"),
    "모든 적의 드랍 확률을 '원래 확률 × 배율'로 바꿉니다 (최대 100%). 드랍 아이템이 없는 적은 그대로입니다.": (
        "Sets every enemy's drop rate to 'original rate × multiplier' (capped at 100%). "
        "Enemies without a drop item are unchanged.",
        "すべての敵のドロップ率を「元の確率 × 倍率」に変更します (最大100%)。ドロップアイテムのない敵はそのままです。"),
    "전투 계산 수치": ("Battle calculation values", "戦闘計算の数値"),
    "기본 {value}": ("default {value}", "初期値 {value}"),
    "(없음)": ("(n/a)", "(なし)"),
    "선제공격 100%": ("Preemptive strike 100%", "先制攻撃 100%"),
    "이 탭의 값은 게임의 데이터 테이블을 직접 바꿉니다. 게임을 끄면 원래 값으로 돌아갑니다 (세이브에 남지 않음).": (
        "Values on this tab change the game's data tables directly. They revert when the game closes "
        "(nothing is stored in the save).",
        "このタブの値はゲームのデータテーブルを直接書き換えます。ゲームを終了すると元に戻ります (セーブには残りません)。"),
    "전투 계산 수치를 적용했습니다.": ("Battle values applied.", "戦闘計算の数値を適用しました。"),
    "전투 계산 수치를 기본값으로 되돌렸습니다.": ("Battle values reset to defaults.", "戦闘計算の数値を初期値に戻しました。"),
    "아군 선제공격 확률 (%)": ("Party preemptive strike chance (%)", "味方の先制攻撃率 (%)"),
    "적 선제공격 확률 (%)": ("Enemy preemptive strike chance (%)", "敵の先制攻撃率 (%)"),
    "도주 기본 확률 보정": ("Escape base chance modifier", "逃走の基本確率補正"),
    "훔치기 레어 아이템 확률 (%)": ("Steal: rare item chance (%)", "盗む: レアアイテム率 (%)"),
    "노 대미지 보너스 EXP 배율": ("No-damage bonus EXP multiplier", "ノーダメージボーナス EXP倍率"),
    "브레이크 피니시 보너스 길 배율": ("Break-finish bonus gil multiplier", "ブレイクフィニッシュボーナス ギル倍率"),
    "오버킬 보너스 AP 배율": ("Overkill bonus AP multiplier", "オーバーキルボーナス AP倍率"),
    "크리티컬 대미지 배율 (%)": ("Critical damage multiplier (%)", "クリティカルダメージ倍率 (%)"),
    "브레이크 대미지 배율 (%)": ("Break damage multiplier (%)", "ブレイクダメージ倍率 (%)"),
    "전체 대미지 계수 (아군·적 공통)": ("Overall damage factor (party and enemies)", "全体ダメージ係数 (味方・敵共通)"),
    "브레이크 시 리미트 게이지 증가": ("Limit gauge gain on break", "ブレイク時のリミットゲージ増加"),
    "피격 시 리미트 게이지 증가": ("Limit gauge gain when hit", "被ダメージ時のリミットゲージ増加"),
    "전투당 비전 소환 가능 횟수": ("Vision summons per battle", "1戦闘あたりのビジョン召喚回数"),
    # 연결 오류
    "{exe} 프로세스를 찾을 수 없습니다. 게임을 먼저 실행하세요.": (
        "Process {exe} not found. Start the game first.",
        "{exe} プロセスが見つかりません。先にゲームを起動してください。"),
    "프로세스를 열 수 없습니다 (오류 {code}). 관리자 권한으로 실행해 보세요.": (
        "Cannot open the process (error {code}). Try running as administrator.",
        "プロセスを開けません (エラー {code})。管理者として実行してみてください。"),
    "모듈 정보를 읽을 수 없습니다 (게임이 아직 로딩 중일 수 있음).": (
        "Cannot read module information (the game may still be loading).",
        "モジュール情報を読み取れません (ゲームがまだロード中の可能性があります)。"),
    "FNamePool 을 찾지 못했습니다.": ("FNamePool not found.", "FNamePool が見つかりません。"),
    "GUObjectArray 를 찾지 못했습니다.": ("GUObjectArray not found.", "GUObjectArray が見つかりません。"),
    "기본 엔진 클래스를 찾지 못했습니다 (게임 로딩이 끝난 뒤 다시 시도).": (
        "Core engine classes not found (try again once the game has finished loading).",
        "基本エンジンクラスが見つかりません (ゲームのロード完了後に再試行してください)。"),
    "UStruct 레이아웃을 인식하지 못했습니다.": ("Unrecognised UStruct layout.", "UStruct のレイアウトを認識できません。"),
    "FField 레이아웃을 인식하지 못했습니다.": ("Unrecognised FField layout.", "FField のレイアウトを認識できません。"),
    "FProperty 레이아웃을 인식하지 못했습니다.": ("Unrecognised FProperty layout.", "FProperty のレイアウトを認識できません。"),
    "{type} 은(는) 쓰기를 지원하지 않습니다.": ("Writing {type} is not supported.", "{type} の書き込みには対応していません。"),
    "세이브 매니저를 찾지 못했습니다. 타이틀 화면까지 로딩된 뒤 다시 시도하세요.": (
        "Save manager not found. Try again once the game has reached the title screen.",
        "セーブマネージャーが見つかりません。タイトル画面まで進んでから再試行してください。"),
}

_INDEX = {"en": 0, "ja": 1}


def _(text, **kwargs):
    """현재 언어로 번역한다. 번역이 없으면 원문을 그대로 쓴다."""
    if LANG != "ko":
        pair = TR.get(text)
        if pair:
            text = pair[_INDEX[LANG]]
    return text.format(**kwargs) if kwargs else text
