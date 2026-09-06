"""Local presentation adapters. Combat and source drawing routines stay intact."""

from functools import lru_cache
from pygame_compat import pygame
import config as c
import drawing
from entities import Fighter, HitEffect
from ui_components import P2_ACCENT


class PresentedFighter(Fighter):
    """Observe resolved contacts; never substitute a combat result or timing."""

    def __init__(self, *args, on_contact, key_blocked, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_contact = on_contact
        self.key_blocked = key_blocked

    def take_damage(self, amount, knockback, stun, attacker_facing_right):
        # Match take_damage's existing precedence, including block over parry.
        kind = ("block" if self.is_blocking or self.blocking else
                "parry" if self.parrying and self.parry_window > 0 else "hit")
        position = self.rect.center
        result = super().take_damage(amount, knockback, stun, attacker_facing_right)
        self.on_contact(self, kind, position)
        return result

    def is_action_pressed(self, action):
        # Only keys carried across a menu boundary are gated. The other pad/
        # keyboard is still usable, and normal combat polling is unchanged.
        if action in self.controls and self.key_blocked(self.controls[action]):
            return bool(self.joy_input_getter and
                        self.joy_input_getter(action, int(self.is_p2)))
        return super().is_action_pressed(action)


class ContactEffect(HitEffect):
    """Existing impact burst for hits; shield shapes distinguish defense."""

    def __init__(self, x, y, kind, heavy=False):
        color = P2_ACCENT if kind == "block" else c.YELLOW if kind == "parry" else c.ORANGE
        super().__init__(x, y, 'heavy' if heavy else 'light', color)
        self.kind = kind
        self.text = {"hit": "HIT!", "block": "BLOCK", "parry": "PARRY!"}[kind]
        self.duration = 24 if kind != "hit" else 18

    def draw(self, surface, text_renderer):
        if not self.active:
            return
        if self.kind == "hit":
            drawing.draw_hit_effect(surface, int(self.x), int(self.y), self.effect_type,
                                    self.color, self.frame)
        else:
            # Shield expands once from contact, never a whole-screen flash.
            radius = 23 + min(self.frame, 10)
            rect = pygame.Rect(int(self.x) - radius, int(self.y) - 26, radius * 2, 52)
            pygame.draw.ellipse(surface, self.color, rect, 3 if self.kind == "parry" else 2)
            if self.kind == "parry":
                pygame.draw.ellipse(surface, self.color, rect.inflate(12, 12), 1)
        text = text_renderer.render_outlined(self.text, 'small', self.color, c.BLACK, 2)
        text.set_alpha(min(255, int(510 * (1 - self.frame / self.duration))))
        x = max(8, min(c.SCREEN_WIDTH - text.get_width() - 8,
                       int(self.x) - text.get_width() // 2))
        surface.blit(text, (x, max(124, int(self.y) - 56 - self.frame // 4)))


@lru_cache(maxsize=128)
def idle_portrait(index, phase, facing_right=True):
    """A bounded loop of the original idle art, at its original size."""
    surface = pygame.Surface((156, 148), pygame.SRCALPHA)
    draw = (drawing.draw_khalid, drawing.draw_eduardo,
            drawing.draw_hasan, drawing.draw_hammoud)[index]
    draw(surface, 78, 76, facing_right, 'idle', phase * 4)
    return surface


@lru_cache(maxsize=8)
def veil(width, height, color, alpha):
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((*color, alpha))
    return surface
