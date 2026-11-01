# Slippy Penguin — Isometric Endless Runner

A voxel-style, isometric endless-runner inspired by Crossy Road's "Slippy Penguin."  
Slide across procedurally generated ice, dodge water gaps, and push your high score while ambient wind howls and snow drifts around you.

---

## Features

| Category  | Details |
|-----------|---------|
| Terrain   | Procedural ice path with random branches and turns; multi-layer isometric rendering via TMX. |
| Graphics  | 111 × 128-pixel voxel tiles, parallax background scroll, snow particle overlay. |
| Sprites   | Three penguin poses (forward, left, right) auto-scaled and depth-sorted. |
| Audio     | Looping wind, turn "swoosh," milestone chime (pitches up every 25 points), and lose stinger. |
| Gameplay  | Smooth camera follow, constant acceleration, high-score tracking, instant restart (R) or quit (Esc). |

---

## Project Structure

```
.
├── main.py                # Game source
├── graphics.tsx           # Isometric tileset definition
├── map.tmx                # Main map used by the game
├── forward.png, left.png, right.png
├── bg1.png, bg2.png       # Parallax backgrounds
├── wind.wav, turn.mp3, lose.mp3, milestone.wav
├── Tiled-main/            # Source Tiled project and additional assets
├── highscore.txt          # Auto-created/updated
└── README.md
```

---

## Requirements

```
python >= 3.10
pygame >= 2.4
pytmx   >= 3.32
numpy   >= 1.24
```

Install dependencies:

```bash
pip install pygame pytmx numpy
```

## Running the Game

```bash
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| ← / A | Turn left |
| → / D | Turn right |
| ↑ / W | Continue forward |
| R | Restart after death |
| Esc / Q | Quit |

Every 25-tile milestone plays an increasingly higher-pitched "ding." Falling off the path or leaving the map ends the run.

## Modding

* **Tileset** - edit the Tiled project under `Tiled-main/` and keep the game's asset paths in sync.
* **Backgrounds** - add additional `bg*.png` files; one is chosen randomly on start.
* **Audio** - replace the root-level WAV/MP3 files while keeping the milestone clip short and percussive.
* **Font** - the game prefers `8-BIT WONDER.TTF`; if absent, it falls back to the system font.
