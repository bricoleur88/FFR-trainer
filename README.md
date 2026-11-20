# FINAL FANTASY RESONANCE Trainer

**English** | [한국어](README.ko.md) | [日本語](README.ja.md)

A trainer for the Steam version of FINAL FANTASY RESONANCE (single-player). It reads and writes save data and data-table values in the memory of the running game. It does not touch game files or executable code.

## Requirements

| | |
|---|---|
| OS | Windows 10 / 11, **64-bit (x64)** — tested on Windows 11 |
| Game | **FINAL FANTASY RESONANCE, Steam version** (single-player) |
| Extra software | None for `FFR-Trainer.exe`. Python is only needed when running from source. |

- Other platforms and other store versions of the game are not supported.
- 32-bit Windows and Windows on ARM are not supported.
- The game must be running with a save loaded before the trainer can connect.

## Getting started

1. Start the game and **load a save** (get past the title screen).
2. Run `FFR-Trainer.exe`.
3. When the top of the window shows `Connected (PID …)`, you are ready.
   - The first run takes a few seconds while item and character names are read. Later runs are instant.
   - If you started the trainer before the game, start the game and press **Connect to game**.

| Top button | What it does |
|---|---|
| Connect to game | Finds the game again and connects. Use it after restarting the game. |
| Refresh | Re-reads the values shown from the game. |
| Reload names | Re-reads item and character names from the game. Use it if names look wrong after a patch or after changing the game language. |
| Language menu | Switches the interface between 한국어 / English / 日本語. Applies immediately and is remembered. |

Names follow the interface language where available — see [Interface language](#interface-language).

## Things to know first

- **Save inside the game** to keep your changes. To be safe, **save to a different slot** rather than overwriting an existing save.
- If a change does not show up in the game right away, **close and reopen the in-game menu**.
- Values on the `Battle` tab (drop rates, battle calculation values) are not stored in the save. They **revert when the game closes**, so apply them again each session.
- In lists, **click a row to select it and click again to deselect**. Click several rows to select several.

## Tabs

### General

| Item | Description |
|---|---|
| Gil | Enter a value and press **Apply**. **Max** sets 9,999,999. |
| Lock gil | While ticked, gil never drops below the value entered. |
| Difficulty | Choose Easy / Normal / Expert and press **Apply**. |
| Disable random encounters | While on, you do not run into enemies on the field. |
| Encounter rate | Slider from 0% to 300%. 100% is the default, 300% is three times as often. **Reset to 100%** restores it. |

- Encounter features only apply **while you are on the field**. The status next to the switch shows `active` or `Waiting for the field`.
- Story battles and boss battles do not appear to be blocked.
- "Disable" takes priority over the slider.

### Characters

Click a character in the list to load their current values into the edit fields.

| Item | Description |
|---|---|
| Level | Sets EXP to the amount required for the level entered. |
| EXP | Sets EXP directly. |
| HP / MP | Changes current HP and MP. |
| Permanent stat bonuses | Permanent bonuses added to Max HP, Max MP, ATK, DEF, INT, MND and AGI. |

- After changing level or EXP, **save and reload, or finish one battle**, for the stats to update.

### Items

- **Show**: Owned / All / Consumables / Weapons / Armor / Accessories / Key items / Artifacts
- **Search**: by part of the name or by ID.
- **Apply to selected**: sets the quantity of the selected items to the value entered (1–99).
- **Apply to all owned consumables**: sets every consumable you own in one go.

**Adding items you do not own** — greyed-out items are ones you do not own. Selecting and applying them adds them, with one condition:

- You can only add as many as the **"Free slots for new entries"** count shown at the top right.
- Right after loading a save this is usually **0**.
- To create free slots, obtain **one item of a kind you do not own yet** in the game (buy it in a shop, for example). The game then enlarges the inventory and a few dozen free slots appear.
- Key items and artifacts are always added with a quantity of 1.
- **Key items** can be story progress conditions, so a confirmation appears before adding them. Owning them early may break the order of events.

### Visions

- Every vision is listed as owned or not owned.
- **Apply to selected**: changes the awakening points of visions you own.
- **Obtain selected visions**: adds visions you do not own to your owned list. **This feature is experimental.**
  - As with items, free slots are required. They appear once you obtain a new vision normally in the game.
  - Synchro points start out empty. Always save to a new slot afterwards and check the result.

### Battle

**Battle item drop rates** — applied to every enemy at once.

| Item | Description |
|---|---|
| Multiplier sliders | ×1 to ×10 for normal and rare drops separately. The rate becomes "original rate × multiplier", capped at 100%. |
| Always drop (100%) | Every enemy that has a drop item gets a 100% rate. |
| Reset drop rates | Restores the original rates. |

**Battle calculation values** — enter values and press **Apply**. The default is shown next to each field.

- Party / enemy preemptive strike chance, escape chance modifier, steal rare item chance
- No-damage bonus EXP multiplier, break-finish bonus gil multiplier, overkill bonus AP multiplier
- Critical / break damage multipliers, overall damage factor (party and enemies alike)
- Limit gauge gains, vision summons per battle
- **Preemptive strike 100%**: sets party to 100% and enemy to 0% in one click.
- **Reset to defaults**: restores every value.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection failed: Process … not found` | Start the game, then press **Connect to game**. |
| `Cannot open the process` | Try running the trainer **as administrator**. |
| `Save data is not loaded yet` | Load a save in the game and try again. |
| Names look wrong or are in another language | Press **Reload names**. |
| Stopped working after restarting the game | Press **Connect to game** again. |
| Antivirus blocks the executable | The tool reads and writes another program's memory, so it can be flagged as a false positive. Add an exception or run from source. |
| Connection fails after a game patch | Locations are found by name at runtime, so it usually keeps working, but a large structural change would need an update. |

## Files created next to the executable

These can be deleted; they are recreated on the next run.

| File | Contents |
|---|---|
| `names_cache.json` | Names read from the game, stored per language |
| `drop_defaults.json` | Original drop rates (used to restore defaults) |
| `lang.txt` | The interface language you chose (`ko`, `en` or `ja`) |

## Interface language

- Pick 한국어 / English / 日本語 from the **language menu** at the top of the window. It switches immediately and keeps the options you have turned on (encounters, drop rates and so on).
- On first run the language follows the Windows display language (English unless it is Korean or Japanese).
- Item and character names follow the interface language too. However, the trainer can only read names in **the language the game is running in** and in **Japanese (the original text)**.
  - Japanese names are always available, whatever language the game is in.
  - For any other language (for example the game in Korean but the interface in English), run the game once in that language and press **Reload names**. The names are then stored and shown from then on, whatever language the game is in.
  - Until names for the interface language exist, names are shown in the game's language and the status line at the top says so.

## Running from source (optional)

Requires Python 3.10 or later.

```
pip install "flet[all]"
python trainer.py
```

To build the executable yourself: `pip install pyinstaller`, then `python build_exe.py`.

## Limitations

- The effect of some features in actual play has not been thoroughly tested.
- New items and visions can only be added while free slots exist (see above).
- There is no in-battle invincibility or one-hit kill.
- In Korean, some names have no Korean text in the game and are machine-translated, so they may differ from the in-game wording.
- For the Steam single-player version only.

## Disclaimer

This is an unofficial fan-made tool. It is not affiliated with, endorsed by or supported by SQUARE ENIX CO., LTD. FINAL FANTASY and all related names, marks and game content are the property of their respective owners. The license below covers only the code in this repository, not the game.

The software is provided without any warranty. Use it at your own risk and keep backups of your save data.

## License

Copyright (C) 2026 bricoleur88

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License, version 3, as published by the Free Software Foundation. It is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See [LICENSE](LICENSE) for the full text.

The distributable build bundles third-party components under their own licenses; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
