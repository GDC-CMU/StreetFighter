"""
Generate the attract-mode preview frames the ArcadeLauncher's gallery
displays inside this game's card (see the launcher's preview contract).

This runs the real game headlessly under SDL's dummy video/audio drivers,
drives a short deterministic AI-vs-AI fight using the game's own built-in
attract-mode demo (the same code path used when the game itself sits idle
for 15 seconds), and captures a handful of small frames plus a manifest:

    assets/preview/manifest.json
    assets/preview/frame_000.png
    assets/preview/frame_001.png
    ...

Determinism: pygame.time.get_ticks() is replaced with a synthetic clock
driven by our own frame counter (not wall-clock time), and the two
random.randint() calls _start_attract_mode() uses to pick characters are
scripted to a fixed, known pairing. Combined with the fixed random seed
Game.__init__() already sets for its own visuals, this makes two runs of
this tool produce byte-identical output, so regenerating without changing
the game's art leaves `git status` clean.

Usage:
    python tools/generate_preview.py

Re-run this after changing character art, the HUD, or stage art, so the
preview stays representative of the current game.
"""
import json
import os
import random
import sys

# Must be set before pygame_compat (imported below) initializes pygame.
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pygame_compat  # noqa: E402 - env vars above must be set first
pygame = pygame_compat.pygame

# ----- Preview parameters -----
FRAME_WIDTH = 200
FRAME_HEIGHT = 150
FPS = 8
FRAME_COUNT = 16               # 16 frames @ 8fps = a 2 second loop
SIM_TICKS_PER_FRAME = 6        # game-simulation steps between captures
WARMUP_TICKS = 90              # let the fighters close in and trade hits
                                # before the loop starts capturing
PREVIEW_CHARACTER_PICK = [0, 2]  # index into config.CHARACTERS: KHALID, HASAN

OUT_DIR = os.path.join(REPO_ROOT, 'assets', 'preview')


class _DeterministicClock:
    """
    Stand-in for pygame.time.get_ticks(), advanced by a fixed amount per
    simulated game frame instead of real elapsed time. A lot of the game's
    combat cooldowns and HUD flicker/pulse effects key off get_ticks(), so
    without this, two runs of this tool - or the same run on a faster or
    slower machine - could capture different animation states and break
    the byte-identical output guarantee.
    """

    def __init__(self, ms_per_tick):
        self.ms_per_tick = ms_per_tick
        self.ms = 0.0

    def tick(self):
        self.ms += self.ms_per_tick

    def get_ticks(self):
        return int(self.ms)


def _scripted_randint(values):
    """
    Returns a random.randint(a, b) stand-in that ignores its arguments and
    yields the given values in order. Used to script _start_attract_mode()'s
    two character-selection calls to a fixed, known-good pairing, while
    still going through that exact same (real) code path.
    """
    it = iter(values)

    def _fake(a, b):
        return next(it)

    return _fake


def _clear_previous_frames():
    """Remove any previously generated frame_*.png so a shrinking
    FRAME_COUNT can never leave stale frames behind."""
    if not os.path.isdir(OUT_DIR):
        return
    for name in os.listdir(OUT_DIR):
        if name.startswith('frame_') and name.endswith('.png'):
            os.remove(os.path.join(OUT_DIR, name))


def main():
    import config as c
    from game import Game

    os.makedirs(OUT_DIR, exist_ok=True)
    _clear_previous_frames()

    clock = _DeterministicClock(ms_per_tick=1000.0 / c.FPS)
    pygame.time.get_ticks = clock.get_ticks

    # Game.__init__ seeds random.seed(42) itself (for consistent ground
    # texture); we rely on that same seed for everything else this script
    # touches, then temporarily script the character-selection rolls below.
    game = Game()

    real_randint = random.randint
    random.randint = _scripted_randint(PREVIEW_CHARACTER_PICK)
    try:
        game._start_attract_mode()
    finally:
        random.randint = real_randint

    # Skip the "ROUND 1" / "FIGHT!" title card (shown while round_timer > 96)
    # so captured frames show the actual fight, not a static banner.
    game.round_timer = 90
    game.last_timer_update = clock.get_ticks()

    # Let the fighters close the distance and start trading hits before
    # capturing, so the loop opens on visible action, not the post-spawn
    # standoff.
    for _ in range(WARMUP_TICKS):
        clock.tick()
        game._update_fight()

    frame_names = []
    for i in range(FRAME_COUNT):
        for _ in range(SIM_TICKS_PER_FRAME):
            clock.tick()
            game._update_fight()

        # Suppress the in-game "DEMO - PRESS ANY BUTTON TO PLAY" attract-mode
        # banner for the capture only: it's meant for the cabinet's own idle
        # screen, not a passive launcher card thumbnail, and eats into a
        # 200x150 frame. Restored immediately after so the next _update_fight()
        # call still drives the AI (which needs attract_mode set).
        game.attract_mode = False
        game.screen.fill(c.DARK_GRAY)
        game._draw_fight()
        game.attract_mode = True

        small = pygame.transform.scale(game.screen, (FRAME_WIDTH, FRAME_HEIGHT))
        frame_name = f"frame_{i:03d}.png"
        pygame.image.save(small, os.path.join(OUT_DIR, frame_name))
        frame_names.append(frame_name)

    manifest = {
        "version": 1,
        "fps": FPS,
        "frames": frame_names,
    }
    manifest_path = os.path.join(OUT_DIR, 'manifest.json')
    with open(manifest_path, 'w', newline='\n') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')

    total_bytes = sum(
        os.path.getsize(os.path.join(OUT_DIR, name))
        for name in os.listdir(OUT_DIR)
    )
    print(
        f"Wrote {len(frame_names)} frames ({FRAME_WIDTH}x{FRAME_HEIGHT} @ "
        f"{FPS}fps) to {OUT_DIR} ({total_bytes} bytes total)"
    )


if __name__ == '__main__':
    main()
