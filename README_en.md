# ok-LimbusCompanyTool

English | [中文](README.md)

A screen-recognition tool that automates **Limbus Company** dailies, built on [ok-script](https://github.com/ok-oldking/ok-script).
It only reads the screen and simulates mouse/keyboard input; it never reads or modifies game memory or files.

> Personal learning project. Automation tools may violate the game's terms of service. Use at your own risk.

## Tasks

| Task | What it does |
|---|---|
| Daily (一鍵日常) | Convert Enkephalin, Thread and EXP Luxcavation, then claim pass rewards |
| Enkephalin (換體力) | Convert all Enkephalin into Enkephalin Modules (never spends Lunacy) |
| Thread Luxcavation (打纺锤本) | Skip today's open Thread stage, 3 times by default, limited to the remaining daily bonus |
| EXP Luxcavation (打經驗本) | Skip Battle (default) or fight with the last-used team; runs and stage are configurable |
| Pass Rewards (領通行證獎勵) | Open LIMBUS PASS from home, claim daily / weekly missions, then Claim All (optional) |
| Mirror Dungeon (鏡像迷宮) | Enter the dungeon and pick a team by star reward; in-dungeon play is not done yet |
| Capture Template (擷取模板) | Save the reference images used for recognition from the current game screen |

## Requirements

- PC (Steam) version, **16:9**, 1920×1080 or 2560×1440 recommended
- Game language: English, or the LLC Simplified Chinese patch
- The game must stay in the foreground while tasks run
- Windows and Python 3.12 for development (see the Chinese README for setup commands)

## First run: create templates

Use the Capture Template task on: the home screen (`home_window`), the Enkephalin panel (`enk_max`),
and a team formation screen (`team_screen`). Luxcavation buttons are found with OCR and need no template.
Commit `assets/lc/*.png` afterwards.

## Release

Push a tag starting with `v` (for example `v0.1.0`); GitHub Actions builds the installer and creates a release.
