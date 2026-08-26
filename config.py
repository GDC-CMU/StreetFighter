# Use compatibility layer for arcade machine support
from pygame_compat import pygame

# --- CONFIGURATION & CONSTANTS ---
# Internal logic resolution (scales up to fullscreen automatically)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
BLUE = (50, 50, 255)
YELLOW = (255, 255, 0)
GREEN = (50, 255, 50)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GRAY = (100, 100, 100)
DARK_GRAY = (40, 40, 40)

# Skin tones
KHALID_SKIN = (181, 135, 99)  # Light brown
EDUARDO_SKIN = (210, 180, 140)  # Tan
HASAN_SKIN = (194, 140, 80)  # Medium brown
HAMMOUD_SKIN = (220, 190, 150)  # Light tan

# Outfit colors
KHALID_GI = (255, 165, 0)  # Orange
EDUARDO_APRON = (220, 20, 60)  # Red
EDUARDO_HAT = (255, 255, 255)  # White
HASAN_ROBE = (255, 215, 0)  # Gold/yellow
HAMMOUD_COAT = (34, 139, 34)  # Green

# Effect colors
COMIC_TEXT = (255, 255, 0)  # Yellow for "POW!"
COMIC_OUTLINE = (0, 0, 0)  # Black outline
DIRT_BROWN = (139, 90, 43)  # Dirt brown ground 

# Physics Defaults
GRAVITY = 0.8
FLOOR_Y = SCREEN_HEIGHT - 100
P_WIDTH = 50
P_HEIGHT = 100

# Character Definitions
# Global damage scaling (reduce all damage by this factor for longer fights)
GLOBAL_DAMAGE_MULT = 0.6  # 60% of original damage

CHARACTERS = [
    {
        'name': 'KHALID', 
        'color': KHALID_GI,
        'skin': KHALID_SKIN,
        'speed': 6, 
        'jump': -19, 
        'health': 300,  # ~3x health for longer fights
        'dmg_mult': 1.0, 
    
        'desc': 'TAEKWONDO MASTER',
        'special': 'spinning_kick'
    },
    {
        'name': 'EDUARDO', 
        'color': EDUARDO_APRON,
        'skin': EDUARDO_SKIN,
        'speed': 5, 
        'jump': -16, 
        'health': 280,  # ~3x health for longer fights
        'dmg_mult': 0.9, 
        'desc': 'PIZZA MASTER',
        'special': 'pizza_throw'
    },
    {
        'name': 'HASAN', 
        'color': HASAN_ROBE,
        'skin': HASAN_SKIN,
        'speed': 5, 
        'jump': -18, 
        'health': 300,  # ~3x health for longer fights
        'dmg_mult': 1.1, 
        'desc': 'PYROMANCER',
        'special': 'fireball'
    },
    {
        'name': 'HAMMOUD', 
        'color': HAMMOUD_COAT,
        'skin': HAMMOUD_SKIN,
        'speed': 7, 
        'jump': -20, 
        'health': 260,  # ~3x health for longer fights
        'dmg_mult': 0.85, 
        'desc': 'TECH WIZARD',
        'special': 'circuit_board'
    },
]

# ===== ROUND SYSTEM =====
WINS_REQUIRED = 2  # Best of 3 rounds
ROUND_TRANSITION_TIME = 180  # 3 seconds at 60fps

# ===== BLOCKING & CHIP DAMAGE =====
CHIP_DAMAGE_PERCENT = 0.15  # 15% damage through block
BLOCK_STUN_FRAMES = 12  # Frames defender can't act after blocking
PUSHBLOCK_DISTANCE = 30  # Pixels pushed back on block

# ===== SUPER METER =====
SUPER_METER_MAX = 100
SUPER_GAIN_ON_HIT = 8  # Meter gained when landing a hit
SUPER_GAIN_ON_DAMAGE = 4  # Meter gained when taking damage
ULTIMATE_DAMAGE = 80  # Ultimate move damage (before global scaling)

# ===== MOTION INPUT BUFFER =====
INPUT_BUFFER_FRAMES = 60  # Store 1 second of inputs at 60fps
MOTION_INPUT_WINDOW = 20  # Frames to complete motion input

# ===== ATTRACT MODE =====
ATTRACT_MODE_TIMEOUT = 1800  # 30 seconds at 60fps

# Attack Frame Data
FRAME_DATA = {
    'light_punch': {'startup': 3, 'active': 2, 'recovery': 5, 'total': 10, 'can_move_early': True},
    'heavy_punch': {'startup': 8, 'active': 4, 'recovery': 15, 'total': 27, 'can_move_early': False},
    'light_kick': {'startup': 4, 'active': 3, 'recovery': 6, 'total': 13, 'can_move_early': True},
    'heavy_kick': {'startup': 10, 'active': 5, 'recovery': 18, 'total': 33, 'can_move_early': False},
    'special': {'startup': 12, 'active': 10, 'recovery': 20, 'total': 42, 'can_move_early': False},
    'ultimate': {'startup': 20, 'active': 15, 'recovery': 30, 'total': 65, 'can_move_early': False},
    # NOTE: Block and dash below are reserved for future implementation
    'block': {'startup': 5, 'active': -1, 'recovery': 3, 'total': -1, 'can_move_early': True},
    'dash': {'startup': 2, 'active': 8, 'recovery': 5, 'total': 15, 'can_move_early': True},
}

# Motion Input Patterns (for Hadouken-style inputs)
# Stored as list of directional states: 'down', 'down_forward', 'forward'
MOTION_INPUTS = {
    'quarter_circle_forward': ['down', 'down_forward', 'forward'],  # QCF: ↓↘→
    'quarter_circle_back': ['down', 'down_back', 'back'],           # QCB: ↓↙←
    'dragon_punch': ['forward', 'down', 'down_forward'],            # DP: →↓↘
}

# Combo System
MAX_COMBO_HITS = 5
COMBO_DAMAGE_SCALING = {
    1: 1.0,  # First hit
    2: 1.0,  # Second hit
    3: 1.0,  # Third hit
    4: 0.8,  # Fourth hit - 80% damage
    5: 0.8,  # Fifth hit - 80% damage
}

# Block System Configuration
# Block effectiveness degrades with usage to prevent spam
BLOCK_EFFECTIVENESS_LEVELS = [1.0, 0.5, 0.25, 0.0]  # 100% -> 50% -> 25% -> 0%
BLOCK_DURATION_MS = 3000  # Maximum block duration: 3 seconds

# Parry System Configuration  
PARRY_COOLDOWN_FRAMES = 300  # 5 seconds at 60fps
PARRY_WINDOW_FRAMES = 6  # 6-frame parry window

# Control Mapping System
# This makes it easy to add arcade machine controls later
# Just update the mapping dictionary without changing game logic

# Action names (internal game actions)
ACTIONS = [
    'left', 'right', 'jump', 'down',
    'light_punch', 'heavy_punch', 
    'light_kick', 'heavy_kick', 
    'special', 'dash', 'parry'
]

# Default keyboard controls for Player 1
DEFAULT_P1_CONTROLS = {
    'left': pygame.K_a,
    'right': pygame.K_d,
    'jump': pygame.K_w,
    'down': pygame.K_s,
    'light_punch': pygame.K_j,
    'heavy_punch': pygame.K_k,
    'light_kick': pygame.K_l,
    'heavy_kick': pygame.K_i,
    'special': pygame.K_u,
    'dash': pygame.K_LSHIFT,
    'parry': pygame.K_o
}

# Default keyboard controls for Player 2
DEFAULT_P2_CONTROLS = {
    'left': pygame.K_LEFT,
    'right': pygame.K_RIGHT,
    'jump': pygame.K_UP,
    'down': pygame.K_DOWN,
    'light_punch': pygame.K_KP1,
    'heavy_punch': pygame.K_KP2,
    'light_kick': pygame.K_KP3,
    'heavy_kick': pygame.K_KP4,
    'special': pygame.K_KP0,
    'dash': pygame.K_RSHIFT,
    'parry': pygame.K_KP5
}

# Arcade Box Control Mapping
# Based on the CMU arcade-box-startercode Key-Map:
# | Key          | Button |
# |--------------|--------|
# | b            | 0      |
# | a            | 1      |
# | x            | 2      |
# | y            | 3      |
# | Insert money | 4      |
# | p1 (RESET)   | 5      |
# | Select       | 8      |
# | Start        | 9      |
#
# Joystick Axis:
# - Axis 0: Left/Right (-1 left, 1 right)
# - Axis 1: Up/Down (-1 up, 1 down)

# Arcade button string mappings for Player 1 (joystick 0)
ARCADE_P1_BUTTONS = {
    'light_punch': '0',   # b button
    'heavy_punch': '1',   # a button
    'light_kick': '2',    # x button
    'heavy_kick': '3',    # y button
    'special': '4',       # Insert money button
    'dash': '8',          # Select button
    'parry': '9',         # Start button
}

# Arcade axis mappings (axis_id, direction)
ARCADE_P1_AXIS = {
    'left': (0, -1),      # Axis 0, negative = left
    'right': (0, 1),      # Axis 0, positive = right  
    'jump': (1, -1),      # Axis 1, negative = up (jump)
    'down': (1, 1),       # Axis 1, positive = down
}

# Arcade button string mappings for Player 2 (joystick 1)
# Same button layout but on second joystick
ARCADE_P2_BUTTONS = {
    'light_punch': '0',
    'heavy_punch': '1',
    'light_kick': '2',
    'heavy_kick': '3',
    'special': '4',
    'dash': '8',
    'parry': '9',
}

ARCADE_P2_AXIS = {
    'left': (0, -1),
    'right': (0, 1),
    'jump': (1, -1),
    'down': (1, 1),
}

# Reset button - P1 button (5) on any joystick quits the game
ARCADE_RESET_BUTTON = '5'

# Hat/DPAD button mappings (for PS4/Switch controllers)
HAT_BUTTONS = {
    'H0': 'jump',   # Hat up = jump
    'H1': 'right',  # Hat right = move right
    'H2': 'down',   # Hat down = crouch/block
    'H3': 'left',   # Hat left = move left
}