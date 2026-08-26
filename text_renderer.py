from pygame_compat import pygame

class SimpleTextRenderer:
    """
    Cross-platform text renderer using pygame's font system.
    Works on Windows, Mac, and Linux without external dependencies.
    """
    def __init__(self):
        pygame.font.init()
        
        # Font size mappings
        self.font_sizes = {
            'small': 24,
            'medium': 32,
            'large': 72
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
                    self.fonts[size_name] = pygame.font.Font(None, size_val)
            except:
                self.fonts[size_name] = pygame.font.Font(None, size_val)
    
    def render(self, text, size='medium', color=(255, 255, 255)):
        """
        Render text and return a pygame surface.
        
        Args:
            text: String to render
            size: 'small', 'medium', or 'large'
            color: RGB tuple for text color
            
        Returns:
            Pygame surface with rendered text
        """
        if size not in self.fonts:
            size = 'medium'
        
        font = self.fonts[size]
        text_surface = font.render(str(text), True, color)
        
        return text_surface

