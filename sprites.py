from pygame_compat import pygame

class SpriteSheet:
    def __init__(self, filename):
        try:
            self.sheet = pygame.image.load(filename).convert_alpha()
        except pygame.error as e:
            print(f"Unable to load spritesheet image: {filename}")
            raise SystemExit(e)

    def image_at(self, rectangle, colorkey=None):
        """Loads a specific image from a specific rectangle"""
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size).convert()
        image.blit(self.sheet, (0, 0), rect)
        if colorkey is not None:
            if colorkey == -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image

    def load_strip(self, rect, image_count, colorkey=None):
        """Loads a strip of images and returns them as a list"""
        tups = [(rect[0] + rect[2] * x, rect[1], rect[2], rect[3])
                for x in range(image_count)]
        return [self.image_at(rect, colorkey) for rect in tups]

class AnimationManager:
    def __init__(self, sprite_sheet, scale=4):
        self.sheet = sprite_sheet
        self.scale = scale
        self.animations = {}
        # Assuming 64x64 pixel frames in the grid
        self.frame_width = 64
        self.frame_height = 64
        self.colorkey = (0, 0, 0) # Black background in spritesheet to be transparent

    def load_animation(self, name, row_index, frame_count):
        # row_index starts at 0
        rect = (0, row_index * self.frame_height, self.frame_width, self.frame_height)
        frames = self.sheet.load_strip(rect, frame_count, self.colorkey)
        
        # Scale up for retro pixel look
        scaled_frames = []
        for frame in frames:
            scaled_frames.append(pygame.transform.scale(
                frame, (self.frame_width * self.scale, self.frame_height * self.scale)))
        
        self.animations[name] = scaled_frames

    def get_frame(self, action, frame_index, flip=False):
        if action not in self.animations:
            return None # Fallback or error
        
        # Loop animation safely
        frames = self.animations[action]
        current_frame = frames[frame_index % len(frames)]
        
        if flip:
            return pygame.transform.flip(current_frame, True, False)
        return current_frame