# Professor Fighting Game 🥋

A vintage arcade-style fighting game featuring four unique professor characters, each with their own special abilities and fighting styles!

## 🎮 Characters

### Professor Khalid - "The Taekwondo Master"
- **Stats:** Health: 110 | Speed: 6 | Jump: -19
- **Special Move:** Spinning Kick - Multi-hit spinning attack that moves forward
- **Fighting Style:** Balanced, martial arts focused

### Professor Eduardo - "The Pizza Master"
- **Stats:** Health: 95 | Speed: 5 | Jump: -16
- **Special Move:** Pizza Throw - Launches 3 pizza slices in rapid succession
- **Fighting Style:** Projectile-based, ranged attacks

### Professor Hasan - "The Pyromancer"
- **Stats:** Health: 100 | Speed: 5 | Jump: -18
- **Special Move:** Fireball - Fast sine-wave projectile
- **Fighting Style:** Magic-based, unpredictable projectiles

### Professor Hammoud - "The Tech Wizard"
- **Stats:** Health: 85 | Speed: 7 | Jump: -20
- **Special Move:** Circuit Board - Slow but homing projectile
- **Fighting Style:** Tech-based, strategic

## 🎮 Controls

### Keyboard Controls

#### Player 1
- **Movement:** W/A/S/D
- **Light Punch:** J
- **Heavy Punch:** K
- **Light Kick:** L
- **Heavy Kick:** I
- **Special Move:** U
- **Dash:** Left Shift
- **Block:** Hold S (Down)
- **Parry:** O

#### Player 2
- **Movement:** Arrow Keys
- **Light Punch:** Numpad 1
- **Heavy Punch:** Numpad 2
- **Light Kick:** Numpad 3
- **Heavy Kick:** Numpad 4
- **Special Move:** Numpad 0
- **Dash:** Right Shift
- **Block:** Hold Down Arrow
- **Parry:** Numpad 5

### Arcade Box Controls (CMU Arcade Machine)

| Action | Button |
|--------|--------|
| Movement | Joystick |
| Light Punch | B (Button 0) |
| Heavy Punch | A (Button 1) |
| Light Kick | X (Button 2) |
| Heavy Kick | Y (Button 3) |
| Special Move | Insert (Button 4) |
| Dash | Select (Button 8) |
| Parry | Start (Button 9) |
| **BACK** | **P1 (Button 5)** |

**Note:** The P1 button (Button 5) always goes back one level: it ends the current fight and returns to character select while fighting, returns to the main menu from any other screen, and exits the game only from the main menu (mirrored by Esc on keyboard).

## 🖼️ Attract-mode preview (ArcadeLauncher)

`assets/preview/` holds a short, pre-rendered animation (`manifest.json` plus
`frame_NNN.png` files) that the ArcadeLauncher's gallery attract mode plays
inside this game's card while the cabinet is idle. It's not used by the game
itself and doesn't affect gameplay - the launcher can't run another game's
loop, so each game ships a small looping clip instead.

To regenerate it after changing character art, the HUD, or stage art:

```
python tools/generate_preview.py
```

This runs the real game headlessly (no window needed) and captures a short
AI-vs-AI demo fight, the same one the game itself shows after 15 seconds of
idle. It's deterministic - re-running it without changing the game's visuals
reproduces byte-identical files, so `git status` stays clean.

## 🎓 Credits

Created for CMU-Q Arena Fighting Game Project
Version 1.0 - 2026

---

**Enjoy the fight!** 🥊🔥
