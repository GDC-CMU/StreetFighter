"""
UI Components for CMUQ Arena - Vintage Arcade Fighter
Contains reusable UI elements like buttons, text renderers, and visual effects
"""

from pygame_compat import pygame
import config as c

class Button:
    """
    A vintage arcade-style button that supports both mouse and keyboard interaction
    Features: hover effects, click detection, visual feedback
    """
    def __init__(self, x, y, width, height, text, color=c.ORANGE, text_color=c.WHITE):
        """
        Initialize a button with position, size, and styling
        
        Args:
            x, y: Top-left position of button
            width, height: Button dimensions
            text: Button label text
            color: Button background color
            text_color: Text color
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hover = False
        self.selected = False
        
        # Vintage arcade colors
        self.border_color = c.YELLOW
        self.shadow_color = c.BLACK
        self.hover_color = c.YELLOW
        
    def update(self, mouse_pos):
        """Update hover state based on mouse position"""
        self.hover = self.rect.collidepoint(mouse_pos)
        
    def draw(self, surface, text_renderer):
        """
        Draw the button with vintage arcade styling
        
        Args:
            surface: Pygame surface to draw on
            text_renderer: Text renderer instance for drawing text
        """
        # Shadow effect for depth
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(surface, self.shadow_color, shadow_rect)
        
        # Determine button color based on state
        if self.hover or self.selected:
            btn_color = self.hover_color
            current_text_color = c.BLACK
            border_width = 5
        else:
            btn_color = self.color
            current_text_color = self.text_color
            border_width = 3
            
        # Draw button background
        pygame.draw.rect(surface, btn_color, self.rect)
        
        # Draw double border for vintage arcade look
        pygame.draw.rect(surface, self.border_color, self.rect, border_width)
        inner_rect = self.rect.inflate(-10, -10)
        pygame.draw.rect(surface, c.WHITE, inner_rect, 2)
        
        # Draw centered text
        text_surf = text_renderer.render(self.text, 'medium', current_text_color)
        text_x = self.rect.centerx - text_surf.get_width() // 2
        text_y = self.rect.centery - text_surf.get_height() // 2
        surface.blit(text_surf, (text_x, text_y))
        
    def is_clicked(self, mouse_pos, mouse_clicked):
        """Check if button was clicked"""
        return self.rect.collidepoint(mouse_pos) and mouse_clicked


class VintageTextRenderer:
    """
    Cross-platform text renderer with vintage arcade styling
    Uses pygame's font system which works on all platforms
    """
    def __init__(self):
        pygame.font.init()
        
        # Font size mappings
        self.font_sizes = {
            'small': 20,
            'medium': 28,
            'large': 56,
            'xlarge': 72
        }
        
        # Try to find a good cross-platform font
        self.fonts = {}
        available_fonts = pygame.font.get_fonts()
        
        # Preferred fonts in order (arcade/retro style first)
        preferred_fonts = [
            'couriernew', 'courier', 'consolas', 'lucidaconsole',
            'monaco', 'dejavusansmono', 'liberationmono',
            'arial', 'helvetica', 'freesans', 'dejavusans'
        ]
        
        # Find the first available preferred font
        selected_font = None
        for pref in preferred_fonts:
            if pref in available_fonts:
                selected_font = pref
                break
        
        # Load fonts for each size
        for size_name, size_val in self.font_sizes.items():
            try:
                if selected_font:
                    self.fonts[size_name] = pygame.font.SysFont(selected_font, size_val, bold=True)
                else:
                    # Fallback to default pygame font
                    self.fonts[size_name] = pygame.font.Font(None, size_val)
            except:
                self.fonts[size_name] = pygame.font.Font(None, size_val)
    
    def render(self, text, size='medium', color=(255, 255, 255)):
        """
        Render text and return a pygame surface
        
        Args:
            text: String to render
            size: 'small', 'medium', 'large', or 'xlarge'
            color: RGB tuple for text color
            
        Returns:
            Pygame surface with rendered text
        """
        if size not in self.fonts:
            size = 'medium'
        
        font = self.fonts[size]
        
        # Render with anti-aliasing for smooth text
        text_surface = font.render(str(text), True, color)
        
        return text_surface
    
    def render_outlined(self, text, size='medium', color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=2):
        """
        Render text with an outline for better visibility
        
        Args:
            text: String to render
            size: 'small', 'medium', 'large', or 'xlarge'
            color: RGB tuple for text color
            outline_color: RGB tuple for outline color
            outline_width: Width of outline in pixels
            
        Returns:
            Pygame surface with outlined text
        """
        if size not in self.fonts:
            size = 'medium'
        
        font = self.fonts[size]
        
        # Render the main text
        text_surface = font.render(str(text), True, color)
        
        # Create a larger surface for outline
        w, h = text_surface.get_size()
        outline_surface = pygame.Surface((w + outline_width * 2, h + outline_width * 2), pygame.SRCALPHA)
        
        # Render outline by drawing text at offsets
        outline_text = font.render(str(text), True, outline_color)
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    outline_surface.blit(outline_text, (outline_width + dx, outline_width + dy))
        
        # Render main text on top
        outline_surface.blit(text_surface, (outline_width, outline_width))
        
        return outline_surface


class ArcadeFrame:
    """Draws a vintage arcade cabinet frame around the game area"""
    
    @staticmethod
    def draw(surface):
        """
        Draw arcade cabinet decorations
        
        Args:
            surface: Pygame surface to draw on
        """
        width = surface.get_width()
        height = surface.get_height()
        
        # Top arcade marquee
        pygame.draw.rect(surface, c.BLACK, (0, 0, width, 8))
        pygame.draw.rect(surface, c.ORANGE, (0, 0, width, 4))
        pygame.draw.rect(surface, c.YELLOW, (0, 4, width, 2))
        
        # Bottom cabinet base
        pygame.draw.rect(surface, c.BLACK, (0, height - 8, width, 8))
        pygame.draw.rect(surface, c.YELLOW, (0, height - 6, width, 2))
        pygame.draw.rect(surface, c.ORANGE, (0, height - 4, width, 4))
        
        # Side panels
        pygame.draw.rect(surface, c.BLACK, (0, 0, 4, height))
        pygame.draw.rect(surface, c.BLACK, (width - 4, 0, 4, height))
        
        # Corner decorations
        corner_size = 20
        # Top-left
        pygame.draw.circle(surface, c.ORANGE, (corner_size, corner_size), 8)
        # Top-right
        pygame.draw.circle(surface, c.ORANGE, (width - corner_size, corner_size), 8)
        # Bottom-left
        pygame.draw.circle(surface, c.ORANGE, (corner_size, height - corner_size), 8)
        # Bottom-right
        pygame.draw.circle(surface, c.ORANGE, (width - corner_size, height - corner_size), 8)


class ScanlineEffect:
    """Creates vintage CRT scanline effect"""
    
    def __init__(self, width, height):
        """Initialize scanline surface"""
        self.surface = pygame.Surface((width, height))
        self.surface.set_colorkey(c.BLACK)
        self.surface.set_alpha(30)  # Reduced alpha for better visibility
        
        # Draw horizontal scanlines with more spacing
        for y in range(0, height, 4):
            pygame.draw.line(self.surface, (0, 0, 0), (0, y), (width, y), 1)
    
    def draw(self, surface):
        """Apply scanline effect to surface"""
        surface.blit(self.surface, (0, 0))


class GradientBackground:
    """Creates smooth gradient backgrounds for menus"""
    
    @staticmethod
    def draw_vertical(surface, color_top, color_bottom, rect=None):
        """
        Draw a vertical gradient.
        
        Args:
            surface: Pygame surface to draw on
            color_top: RGB tuple for top color
            color_bottom: RGB tuple for bottom color
            rect: Optional rect to limit gradient area
        """
        if rect is None:
            rect = pygame.Rect(0, 0, surface.get_width(), surface.get_height())
        
        for y in range(rect.height):
            # Linear interpolation between colors
            ratio = y / rect.height
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            pygame.draw.line(surface, (r, g, b), 
                           (rect.x, rect.y + y), 
                           (rect.x + rect.width, rect.y + y))
    
    @staticmethod
    def draw_radial(surface, center, radius, color_center, color_edge):
        """
        Draw a radial gradient (simplified - concentric circles).
        
        Args:
            surface: Pygame surface to draw on
            center: (x, y) center point
            radius: Maximum radius
            color_center: RGB tuple for center color
            color_edge: RGB tuple for edge color
        """
        for r in range(radius, 0, -2):
            ratio = 1 - (r / radius)
            cr = int(color_edge[0] + (color_center[0] - color_edge[0]) * ratio)
            cg = int(color_edge[1] + (color_center[1] - color_edge[1]) * ratio)
            cb = int(color_edge[2] + (color_center[2] - color_edge[2]) * ratio)
            pygame.draw.circle(surface, (cr, cg, cb), center, r)


class AnimatedText:
    """Animated text effects for dynamic UI elements"""
    
    def __init__(self, text, size, color, x, y):
        self.text = text
        self.size = size
        self.color = color
        self.x = x
        self.y = y
        self.frame = 0
        self.scale = 1.0
        self.alpha = 255
    
    def update(self):
        """Update animation frame"""
        self.frame += 1
    
    def draw_pulsing(self, surface, text_renderer):
        """Draw text with pulsing scale effect"""
        import math
        scale_offset = math.sin(self.frame * 0.1) * 0.1
        current_scale = 1.0 + scale_offset
        
        text_surf = text_renderer.render(self.text, self.size, self.color)
        
        # Scale the surface
        new_width = int(text_surf.get_width() * current_scale)
        new_height = int(text_surf.get_height() * current_scale)
        if new_width > 0 and new_height > 0:
            scaled = pygame.transform.scale(text_surf, (new_width, new_height))
            x = self.x - scaled.get_width() // 2
            y = self.y - scaled.get_height() // 2
            surface.blit(scaled, (x, y))
    
    def draw_floating(self, surface, text_renderer):
        """Draw text with floating up/down effect"""
        import math
        y_offset = math.sin(self.frame * 0.05) * 5
        
        text_surf = text_renderer.render(self.text, self.size, self.color)
        x = self.x - text_surf.get_width() // 2
        y = self.y - text_surf.get_height() // 2 + y_offset
        surface.blit(text_surf, (x, int(y)))


def draw_panel(surface, rect, bg_color, border_color, border_width=3, shadow=True):
    """
    Draw a styled panel with optional shadow.
    
    Args:
        surface: Pygame surface to draw on
        rect: pygame.Rect for panel bounds
        bg_color: Background color
        border_color: Border color
        border_width: Border thickness
        shadow: Whether to draw drop shadow
    """
    if shadow:
        shadow_rect = rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(surface, c.BLACK, shadow_rect)
    
    pygame.draw.rect(surface, bg_color, rect)
    pygame.draw.rect(surface, border_color, rect, border_width)
    
    # Inner highlight
    inner_rect = rect.inflate(-10, -10)
    pygame.draw.rect(surface, c.WHITE, inner_rect, 1)


def draw_health_bar(surface, x, y, width, height, ratio, color, show_segments=True):
    """
    Draw a styled health bar.
    
    Args:
        surface: Pygame surface to draw on
        x, y: Position
        width, height: Dimensions
        ratio: Health ratio (0.0 to 1.0)
        color: Bar color
        show_segments: Whether to show segmented style
    """
    # Background
    pygame.draw.rect(surface, c.BLACK, (x - 2, y - 2, width + 4, height + 4))
    pygame.draw.rect(surface, c.DARK_GRAY, (x, y, width, height))
    
    if show_segments:
        num_segments = 10
        gap = 2
        segment_width = (width - (num_segments - 1) * gap) / num_segments
        
        for i in range(num_segments):
            segment_x = x + i * (segment_width + gap)
            segment_threshold = (i + 1) / num_segments
            
            if ratio >= segment_threshold or ratio > (i / num_segments):
                # Flash on low health
                if ratio < 0.3:
                    flash_color = c.YELLOW if pygame.time.get_ticks() % 500 < 250 else color
                else:
                    flash_color = color
                pygame.draw.rect(surface, flash_color, (segment_x, y, segment_width, height))
    else:
        # Simple bar
        filled_width = int(width * ratio)
        if filled_width > 0:
            pygame.draw.rect(surface, color, (x, y, filled_width, height))
    
    # Border
    pygame.draw.rect(surface, c.WHITE, (x, y, width, height), 2)

