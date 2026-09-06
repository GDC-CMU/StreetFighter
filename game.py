"""
CMUQ Arena - Vintage Arcade Fighting Game
A professionally structured, maintainable fighting game with vintage arcade aesthetics

Game States:
- MAIN_MENU: Main menu with START, CONTROLS, ABOUT buttons
- CONTROLS: Display game controls
- ABOUT: Display game information
- CHARACTER_SELECT: Character selection screen
- FIGHT: Main fighting gameplay
- GAME_OVER: End game screen

Supports:
- Keyboard controls (Player 1: WASD + JKLIU, Player 2: Arrows + Numpad)
- Arcade Box joystick controls (CMU arcade-box compatible)
- PS4/PS5 and Nintendo Switch controllers

Author: Senior Game Developer
Date: 2026
"""

from pygame_compat import pygame
import sys
import random
import os
import config as c
from entities import Particle, SpinningKickEffect, HitEffect
from ui_components import (Button, VintageTextRenderer, ArcadeFrame, ScanlineEffect,
                           GradientBackground, draw_panel, draw_health_bar,
                           MENU_TOP, MENU_BOTTOM, PANEL, MUTED, RULE, P2_ACCENT)
from combat import CombatSystem
from presentation import PresentedFighter, ContactEffect, idle_portrait, veil
import drawing
import joystick


class Game:
    """
    Main game class - handles all game logic, rendering, and state management
    """
    
    # ==================== INITIALIZATION ====================
    
    def __init__(self):
        """Initialize game window, assets, and game state"""
        # Safe init for arcade box compatibility
        if hasattr(pygame, 'init'):
            pygame.init()
        
        # Initialize mixer for music/sound
        if hasattr(pygame, 'mixer'):
            pygame.mixer.init()
        
        # Display setup - fullscreen scaled for authentic arcade feel.
        # SCALED keeps the game at its logical 800x600 while SDL letterboxes it
        # onto whatever panel is fitted, so any laptop resolution works too.
        # STREETFIGHTER_WINDOWED=1 gives a window for development.
        flags = pygame.SCALED
        if not c.windowed_requested():
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(
            (c.SCREEN_WIDTH, c.SCREEN_HEIGHT),
            flags
        )
        pygame.display.set_caption("CMUQ Arena - Vintage Arcade Fighter")
        
        # Core game components
        self.clock = pygame.time.Clock()
        self.text_renderer = VintageTextRenderer()
        
        # Initialize joystick/arcade box support
        joystick.init()
        joystick.set_callbacks(
            on_press=self._on_joy_press,
            on_release=self._on_joy_release,
            on_hold=self._on_joy_button_hold,
            on_digital_axis=self._on_digital_joy_axis
        )
        
        # Track joystick input state for fighters
        self.joy_input_state = {
            0: {'buttons': set(), 'axis': set()},  # Player 1 joystick
            1: {'buttons': set(), 'axis': set()},  # Player 2 joystick
        }
        
        # Currently-held keyboard keys (tracked via KEYDOWN/KEYUP edges so
        # attract-mode/idle-timer checks don't depend on any(get_pressed()),
        # which some arcade-box pygame builds don't support reliably)
        self.keys_down = set()
        self.blocked_keys = set()
        self.blocked_buttons = {0: set(), 1: set()}
        self.blocked_axes = {0: set(), 1: set()}
        
        # Debouncing for menu/character select joystick scrolling (prevent too-fast scrolling)
        self.joy_menu_scroll_cooldown = 0
        self.joy_char_select_cooldown = {0: 0, 1: 0}  # Per-player cooldown
        
        # Music/Audio
        self.music_path = os.path.join(os.path.dirname(__file__), 'music.mp3')
        self.music_start_time = 0  # Track when music started
        self.music_loop_point = 180000  # Loop from 3 minutes (180 seconds) in milliseconds
        
        # Visual effects
        self.scanlines = ScanlineEffect(c.SCREEN_WIDTH, c.SCREEN_HEIGHT)
        self.screen_shake = 0
        self.screen_shake_offset = (0, 0)
        self.hit_effects = []  # Comic book hit effects
        self.ko_slowdown = False
        self.slowdown_timer = 0
        
        # Hit freeze effect (brief pause on heavy hits for impact)
        self.hit_freeze_frames = 0
        
        # Counter attack window (frames after successful parry where attacks do bonus damage)
        self.counter_attack_window = {'p1': 0, 'p2': 0}
        
        # Retain the gameplay seed; presentation has a separate stream.
        random.seed(42)
        # Cosmetic choices never advance the AI's RNG, including in draw.
        self.cosmetic_rng = random.Random(42)
        self.floor_texture = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT - c.FLOOR_Y))
        self.floor_texture.fill(c.DIRT_BROWN)
        texture_rng = random.Random(42)
        for _ in range(50):
            x = texture_rng.randint(0, c.SCREEN_WIDTH)
            y = texture_rng.randint(0, c.SCREEN_HEIGHT - c.FLOOR_Y)
            radius = texture_rng.randint(3, 8)
            pygame.draw.circle(self.floor_texture, tuple(int(v * .8) for v in c.DIRT_BROWN),
                               (x, y), radius)
        self.object_surface = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT), pygame.SRCALPHA)
        self.result_backdrop = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        drawing.draw_parallax_background(self.result_backdrop, 200, 550, 0)
        self.result_backdrop.blit(self.floor_texture, (0, c.FLOOR_Y))
        self.feedback = []
        self.ready_since = {'p1': None, 'p2': None}
        self.special_ready = {'p1': True, 'p2': True}
        
        # Game state management
        self.state = "MAIN_MENU"  # Current game state
        self.running = True
        
        # Initialize all game screens
        self._init_main_menu()
        self._init_controls_screen()
        self._init_about_screen()
        self._init_character_select()
        self._init_fight_screen()
        self.result_selected = 0
        self.result_buttons = [
            Button(250, 304 + i * 72, 300, 56, label, color)
            for i, (label, color) in enumerate((
                ("REMATCH", c.ORANGE), ("CHANGE FIGHTERS", c.BLUE), ("MAIN MENU", c.GREEN)))
        ]
        
    def _init_main_menu(self):
        """Initialize main menu UI elements"""
        # Menu title
        self.menu_title = "CMUQ ARENA"
        self.menu_subtitle = "VINTAGE ARCADE FIGHTER"
        self.ui_input = "joystick" if joystick.get_joystick_count() else "keyboard"
        
        # Create menu buttons (centered vertically)
        button_width = 300
        button_height = 56
        button_x = c.SCREEN_WIDTH // 2 - button_width // 2
        start_y = 266
        gap = 76
        
        self.menu_buttons = [
            Button(button_x, start_y, button_width, button_height, "START", c.ORANGE),
            Button(button_x, start_y + gap, button_width, button_height, "CONTROLS", c.BLUE),
            Button(button_x, start_y + gap * 2, button_width, button_height, "ABOUT", c.GREEN)
        ]
        self.menu_selected = 0  # Current selected button (for keyboard navigation)
        
    def _init_controls_screen(self):
        """Initialize controls screen UI"""
        # Back button
        self.controls_back_button = Button(
            c.SCREEN_WIDTH // 2 - 150, 494, 300, 52, "BACK", c.ORANGE
        )
        self.controls_back_button.selected = True
        
    def _init_about_screen(self):
        """Initialize about screen UI"""
        # Back button
        self.about_back_button = Button(
            c.SCREEN_WIDTH // 2 - 150, 494, 300, 52, "BACK", c.ORANGE
        )
        self.about_back_button.selected = True
        
    def _init_character_select(self):
        """Initialize character selection screen"""
        self.p1_cursor = 0
        self.p2_cursor = 1
        self.p1_selected = False
        self.p2_selected = False
        self.p2_coin_inserted = True  # Instant 2-player mode - no coin required
        self.selection_started = None
        
    def _init_fight_screen(self):
        """Initialize fight screen variables"""
        self.p1 = None
        self.p2 = None
        self.round_timer = 99
        self.last_timer_update = 0
        self.particles = []
        self.projectiles = []
        self.special_effects = []
        self.combat_system = CombatSystem()  # Combat system for tracking combos
        self.winner_sequence_active = False
        self.winner_sequence_frame = 0
        
        # Round system (Best of 3)
        self.p1_wins = 0
        self.p2_wins = 0
        self.current_round = 1
        self.round_over = False
        self.round_transition_timer = 0
        self.round_winner = None  # "p1" or "p2" or "draw"
        
        # Attract mode
        self.idle_timer = 0  # Frames since last input
        self.attract_mode = False
        self.ai_p1 = None  # AI controller for P1 in attract mode
        self.ai_p2 = None  # AI controller for P2 in attract mode
    
    # ==================== GAME LOOP ====================
    
    def run(self):
        """Main game loop - handles events, updates, and rendering"""
        # Start playing music at game start
        self._play_music()
        
        while self.running:
            # Limit to 60 FPS for consistent gameplay
            self.clock.tick(c.FPS)
            
            # Update music looping (handles loop point at 3 minutes)
            self._update_music()
            
            # Clear screen with arcade background
            self.screen.fill(c.DARK_GRAY)
            
            # Get mouse state
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False
            
            # ===== EVENT HANDLING =====
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mouse_clicked = True
                        mouse_pos = event.pos
                        self._focus_menu_pointer(event.pos)

                if event.type == pygame.MOUSEMOTION and event.rel != (0, 0):
                    self._focus_menu_pointer(event.pos)
                        
                if event.type == pygame.KEYDOWN:
                    if event.key not in self.keys_down:
                        self.keys_down.add(event.key)
                        self._handle_keypress(event.key)
                
                if event.type == pygame.KEYUP:
                    self.keys_down.discard(event.key)
                    self.blocked_keys.discard(event.key)
                
                # Handle joystick events
                joystick.handle_event(event)
            
            # Update joystick hold states
            joystick.update()
            
            # CRITICAL FIX: Clean up stale axis states
            # This is a safety check for arcade joysticks that might not send proper release events
            for joystick_id in list(self.joy_input_state.keys()):
                if joystick_id < pygame.joystick.get_count():
                    joy = pygame.joystick.Joystick(joystick_id)
                    # Check axis 0 (left/right)
                    axis0_val = joy.get_axis(0) if joy.get_numaxes() > 0 else 0
                    # Check axis 1 (up/down)
                    axis1_val = joy.get_axis(1) if joy.get_numaxes() > 1 else 0
                    
                    # If both axes are near center, clear axis state
                    if abs(axis0_val) < 0.3 and abs(axis1_val) < 0.3:
                        if self.joy_input_state[joystick_id]['axis']:
                            print(f"[CLEANUP] Joy {joystick_id} axes cleared (were: {self.joy_input_state[joystick_id]['axis']})")
                            self.joy_input_state[joystick_id]['axis'].clear()
            # Poll cleanup must release guards in this frame, before a stick
            # can be pressed in the same direction on the next frame.
            self._release_input_guards()
            
            # Decrement joystick menu scroll cooldown
            if self.joy_menu_scroll_cooldown > 0:
                self.joy_menu_scroll_cooldown -= 1
            for player_id in self.joy_char_select_cooldown:
                if self.joy_char_select_cooldown[player_id] > 0:
                    self.joy_char_select_cooldown[player_id] -= 1
            
            # ===== STATE-BASED UPDATE AND RENDERING =====
            if self.state == "MAIN_MENU":
                self._update_main_menu(mouse_pos, mouse_clicked)
                
            elif self.state == "CONTROLS":
                self._update_controls(mouse_pos, mouse_clicked)
                
            elif self.state == "ABOUT":
                self._update_about(mouse_pos, mouse_clicked)
                
            elif self.state == "CHARACTER_SELECT":
                self._update_character_select(mouse_pos, mouse_clicked)
                
            elif self.state == "FIGHT":
                self._update_fight()
                
            elif self.state == "GAME_OVER":
                self._update_game_over(mouse_pos, mouse_clicked)

            # A mouse action can change state during update (including tearing
            # down fighters). Draw the destination, not the departed screen.
            if self.state in ("FIGHT", "GAME_OVER"):
                self._finish_fight_frame()
            {
                "MAIN_MENU": self._draw_main_menu,
                "CONTROLS": self._draw_controls,
                "ABOUT": self._draw_about,
                "CHARACTER_SELECT": self._draw_character_select,
                "FIGHT": self._draw_fight,
                "GAME_OVER": self._draw_game_over,
            }[self.state]()
            
            # ===== VINTAGE ARCADE EFFECTS =====
            ArcadeFrame.draw(self.screen)
            self.scanlines.draw(self.screen)
            
            # Update display
            pygame.display.flip()
        
        # Cleanup
        joystick.quit()
        pygame.quit()
        sys.exit()
    
    # ==================== INPUT HANDLING ====================
    
    def _handle_keypress(self, key):
        """
        Handle keyboard input based on current game state
        
        Args:
            key: Pygame key constant
        """
        self.ui_input = "keyboard"
        if key in self.blocked_keys:
            return
        # Global: ESC mirrors the P1 arcade button - back one level,
        # or exit the process entirely from the main menu.
        if key == pygame.K_ESCAPE:
            self._go_back()
            return
                
        # Main menu keyboard navigation
        if self.state == "MAIN_MENU":
            if key == pygame.K_UP or key == pygame.K_w:
                self.menu_selected = (self.menu_selected - 1) % len(self.menu_buttons)
            elif key == pygame.K_DOWN or key == pygame.K_s:
                self.menu_selected = (self.menu_selected + 1) % len(self.menu_buttons)
            elif key == pygame.K_RETURN or key == pygame.K_SPACE:
                self._activate_menu_button(self.menu_selected)
                
        elif self.state in ("CONTROLS", "ABOUT"):
            if key == pygame.K_RETURN:
                self.state = "MAIN_MENU"

        # Character select keyboard controls
        elif self.state == "CHARACTER_SELECT":
            # P1 controls
            if not self.p1_selected:
                if key == pygame.K_a:
                    self.p1_cursor = (self.p1_cursor - 1) % len(c.CHARACTERS)
                elif key == pygame.K_d:
                    self.p1_cursor = (self.p1_cursor + 1) % len(c.CHARACTERS)
                elif key in (pygame.K_j, pygame.K_RETURN):
                    self.p1_selected = True
            
            # P2 controls - always available
            if not self.p2_selected:
                if key == pygame.K_LEFT:
                    self.p2_cursor = (self.p2_cursor - 1) % len(c.CHARACTERS)
                elif key == pygame.K_RIGHT:
                    self.p2_cursor = (self.p2_cursor + 1) % len(c.CHARACTERS)
                elif key in (pygame.K_KP1, pygame.K_KP_ENTER):
                    self.p2_selected = True
                    
        # Game over screen
        elif self.state == "GAME_OVER":
            if key in (pygame.K_UP, pygame.K_w):
                self.result_selected = (self.result_selected - 1) % len(self.result_buttons)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.result_selected = (self.result_selected + 1) % len(self.result_buttons)
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._activate_result()
    
    # ==================== UNIVERSAL BACK / EXIT ACTION ====================
    
    def _go_back(self):
        """
        Handle the universal "back / up one level" action, shared by the P1
        arcade button (button 5) and the Esc key so cabinet and desktop
        development behave identically.
        
        This steps the state machine up one level per press:
            FIGHT             -> CHARACTER_SELECT (abort the fight; or
                                  MAIN_MENU if this is just the attract-mode
                                  demo, matching how any other input wakes it)
            GAME_OVER         -> MAIN_MENU
            CHARACTER_SELECT  -> MAIN_MENU
            CONTROLS          -> MAIN_MENU
            ABOUT             -> MAIN_MENU
            MAIN_MENU         -> process exit via sys.exit(0)
        
        MAIN_MENU is the top of the stack - nothing sits above it, so a press
        there ends the process. This is how the arcade cabinet's outer menu
        and the launcher regain control, so it must always call sys.exit(0)
        and must never be changed to anything else.
        """
        self._consume_held_inputs()
        self.selection_started = None
        if self.state == "MAIN_MENU":
            print("Back button pressed at main menu - exiting game")
            joystick.quit()
            pygame.quit()
            sys.exit(0)
        elif self.state == "FIGHT":
            if self.attract_mode:
                # Just the screensaver demo - wake it the same way any other
                # input does, straight back to the main menu.
                self.attract_mode = False
                self.idle_timer = 0
                self.state = "MAIN_MENU"
            else:
                self._exit_fight_to_character_select()
        elif self.state == "GAME_OVER":
            self.p1_selected = False
            self.p2_selected = False
            self.p1_cursor = 0
            self.p2_cursor = 0
            self.p2_coin_inserted = True
            self.state = "MAIN_MENU"
        else:
            # CHARACTER_SELECT, CONTROLS, ABOUT
            self.state = "MAIN_MENU"
    
    # ==================== JOYSTICK INPUT HANDLING ====================
    
    def _on_joy_press(self, button, joystick_id):
        """
        Handle joystick button press events.
        Called when any button is pressed on any connected joystick.
        
        Args:
            button: String representing the button (e.g., '0', '1', 'H0')
            joystick_id: ID of the joystick that triggered the event
        """
        self.ui_input = "joystick"
        if joystick_id in self.joy_input_state:
            buttons = self.joy_input_state[joystick_id]['buttons']
            if button in buttons:
                return  # Repeated down events are not a second menu action.
            buttons.add(button)
        if button in self.blocked_buttons.get(joystick_id, ()):
            return
        # BACK BUTTON - P1 button (5) on any joystick backs out one level of
        # the state machine (see _go_back). This event only fires on the
        # JOYBUTTONDOWN edge, so a held button cannot re-trigger it.
        if button == c.ARCADE_RESET_BUTTON:
            self._go_back()
            return
        
        # Handle menu/character select navigation
        if self.state == "MAIN_MENU":
            # Light kick mirrors P1/Esc as back in main menu
            if button == '2':
                self._go_back()
            else:
                self._handle_joy_menu(button, joystick_id)
        elif self.state == "CONTROLS":
            # Light kick acts as back in controls screen
            if button == '2':
                self.state = "MAIN_MENU"
            elif button in ['0', '1', '9']:
                self.state = "MAIN_MENU"
        elif self.state == "ABOUT":
            # Light kick acts as back in about screen
            if button == '2':
                self.state = "MAIN_MENU"
            elif button in ['0', '1', '9']:
                self.state = "MAIN_MENU"
        elif self.state == "CHARACTER_SELECT":
            self._handle_joy_character_select(button, joystick_id)
        elif self.state == "GAME_OVER":
            if button == 'H0':
                self.result_selected = (self.result_selected - 1) % len(self.result_buttons)
            elif button == 'H2':
                self.result_selected = (self.result_selected + 1) % len(self.result_buttons)
            if button in ['0', '1', '9']:
                self._activate_result()
    
    def _on_joy_release(self, button, joystick_id):
        """
        Handle joystick button release events.
        
        Args:
            button: String representing the button
            joystick_id: ID of the joystick that triggered the event
        """
        # Remove from tracked state
        if joystick_id in self.joy_input_state:
            self.joy_input_state[joystick_id]['buttons'].discard(button)
            self.blocked_buttons[joystick_id].discard(button)
    
    def _on_joy_button_hold(self, buttons, joystick_id):
        """
        Handle joystick button hold events (called each frame while held).
        
        Args:
            buttons: List of button strings currently held
            joystick_id: ID of the joystick
        """
        # Update tracked state
        if joystick_id in self.joy_input_state:
            self.joy_input_state[joystick_id]['buttons'] = set(buttons)
    
    def _on_digital_joy_axis(self, results, joystick_id):
        """
        Handle digital joystick axis events.
        Results are tuples of (axis, direction) where:
        - axis 0: left/right, axis 1: up/down
        - direction -1: left/up, direction 1: right/down
        
        Args:
            results: List of (axis, direction) tuples for active movements
            joystick_id: ID of the joystick
        """
        if results:
            self.ui_input = "joystick"
        # Update tracked state - ALWAYS update to current active movements
        # Empty list means all axes are at neutral
        if joystick_id in self.joy_input_state:
            # Convert results to set - this ensures released axes are removed
            new_axis_state = set(results) if results else set()
            old_axis_state = self.joy_input_state[joystick_id]['axis']
            
            # Update the state
            self.joy_input_state[joystick_id]['axis'] = new_axis_state
            self.blocked_axes[joystick_id].intersection_update(new_axis_state)
            
            # Debug: Log axis state changes
            if new_axis_state != old_axis_state:
                print(f"[Joy {joystick_id}] Axis changed: {old_axis_state} -> {new_axis_state} (results={results})")
        
        results = [value for value in results
                   if value not in self.blocked_axes.get(joystick_id, ())]
        # Handle menu/character select navigation WITH DEBOUNCING
        # Only process menu scrolling every 8 frames to prevent too-fast scrolling
        if self.state == "MAIN_MENU":
            if self.joy_menu_scroll_cooldown <= 0 and results:
                for axis, direction in results:
                    if axis == 1:  # Up/Down
                        if direction == -1:  # Up
                            self.menu_selected = (self.menu_selected - 1) % len(self.menu_buttons)
                            self.joy_menu_scroll_cooldown = 8  # 8 frame cooldown
                        elif direction == 1:  # Down
                            self.menu_selected = (self.menu_selected + 1) % len(self.menu_buttons)
                            self.joy_menu_scroll_cooldown = 8  # 8 frame cooldown
        
        elif self.state == "GAME_OVER":
            if self.joy_menu_scroll_cooldown <= 0:
                for axis, direction in results:
                    if axis == 1:
                        self.result_selected = (self.result_selected + direction) % len(self.result_buttons)
                        self.joy_menu_scroll_cooldown = 8
        elif self.state == "CHARACTER_SELECT":
            # Determine which player based on joystick_id
            if joystick_id == 0 and self.joy_char_select_cooldown[0] <= 0:  # Player 1
                if not self.p1_selected and results:
                    for axis, direction in results:
                        if axis == 0:  # Left/Right
                            if direction == -1:  # Left
                                self.p1_cursor = (self.p1_cursor - 1) % len(c.CHARACTERS)
                                self.joy_char_select_cooldown[0] = 8
                            elif direction == 1:  # Right
                                self.p1_cursor = (self.p1_cursor + 1) % len(c.CHARACTERS)
                                self.joy_char_select_cooldown[0] = 8
            elif joystick_id == 1 and self.joy_char_select_cooldown[1] <= 0:  # Player 2
                if not self.p2_selected and results:
                    for axis, direction in results:
                        if axis == 0:  # Left/Right
                            if direction == -1:  # Left
                                self.p2_cursor = (self.p2_cursor - 1) % len(c.CHARACTERS)
                                self.joy_char_select_cooldown[1] = 8
                            elif direction == 1:  # Right
                                self.p2_cursor = (self.p2_cursor + 1) % len(c.CHARACTERS)
                                self.joy_char_select_cooldown[1] = 8
    
    def _handle_joy_menu(self, button, joystick_id):
        """Handle joystick input in main menu"""
        # Hat buttons for navigation
        if button == 'H0':  # Up
            self.menu_selected = (self.menu_selected - 1) % len(self.menu_buttons)
        elif button == 'H2':  # Down
            self.menu_selected = (self.menu_selected + 1) % len(self.menu_buttons)
        # Any action button to select
        elif button in ['0', '1', '9']:  # b, a, or Start
            self._activate_menu_button(self.menu_selected)
    
    def _handle_joy_character_select(self, button, joystick_id):
        """Handle joystick input in character selection"""
        # Determine which player based on joystick_id
        if joystick_id == 0:  # Player 1
            if not self.p1_selected:
                if button == 'H3':  # Left
                    self.p1_cursor = (self.p1_cursor - 1) % len(c.CHARACTERS)
                elif button == 'H1':  # Right
                    self.p1_cursor = (self.p1_cursor + 1) % len(c.CHARACTERS)
                elif button in ['0', '1', '9']:  # Menu-only confirm aliases
                    self.p1_selected = True
        elif joystick_id == 1:  # Player 2
            if not self.p2_selected:
                if button == 'H3':  # Left
                    self.p2_cursor = (self.p2_cursor - 1) % len(c.CHARACTERS)
                elif button == 'H1':  # Right
                    self.p2_cursor = (self.p2_cursor + 1) % len(c.CHARACTERS)
                elif button in ['0', '1', '9']:  # Menu-only confirm aliases
                    self.p2_selected = True
    
    def get_joy_action(self, action, joystick_id=0):
        """
        Check if a game action is active via joystick.
        Used by Fighter class for combat input.
        
        Args:
            action: Action name ('light_punch', 'jump', etc.)
            joystick_id: Which joystick to check (0 for P1, 1 for P2)
            
        Returns:
            True if the action is currently triggered via joystick
        """
        if joystick_id not in self.joy_input_state:
            return False
        
        state = self.joy_input_state[joystick_id]
        
        # Get button mappings based on player
        if joystick_id == 0:
            button_map = c.ARCADE_P1_BUTTONS
            axis_map = c.ARCADE_P1_AXIS
        else:
            button_map = c.ARCADE_P2_BUTTONS
            axis_map = c.ARCADE_P2_AXIS
        
        # Check button actions
        if action in button_map:
            button = button_map[action]
            if button in state['buttons'] and button not in self.blocked_buttons[joystick_id]:
                return True
        
        # Check axis actions (movement)
        if action in axis_map:
            axis, direction = axis_map[action]
            axis_tuple = (axis, direction)
            in_axis_state = axis_tuple in state['axis'] and axis_tuple not in self.blocked_axes[joystick_id]
            
            # Debug: log movement checks
            if action in ['left', 'right', 'jump', 'down']:
                if in_axis_state or (self.state == "FIGHT" and action in ['left', 'right']):
                    print(f"[Joy {joystick_id}] Check {action}: axis_tuple={axis_tuple}, in_state={in_axis_state}, state['axis']={state['axis']}")
            
            return in_axis_state
        
        # Check hat/dpad buttons
        for hat_button, hat_action in c.HAT_BUTTONS.items():
            if (hat_action == action and hat_button in state['buttons']
                    and hat_button not in self.blocked_buttons[joystick_id]):
                return True
        
        return False
    
    # ==================== MAIN MENU STATE ====================

    def _focus_menu_pointer(self, position):
        """Only real pointer motion/clicks take focus from keyboard or stick."""
        self.ui_input = "mouse"
        if self.state in ("MAIN_MENU", "GAME_OVER"):
            buttons = self.menu_buttons if self.state == "MAIN_MENU" else self.result_buttons
            for i, button in enumerate(buttons):
                if button.rect.collidepoint(position):
                    if self.state == "MAIN_MENU":
                        self.menu_selected = i
                    else:
                        self.result_selected = i
                    break

    def _center_text(self, text, y, size='small', color=c.WHITE, center=None):
        text_surface = self.text_renderer.render(text, size, color)
        center = c.SCREEN_WIDTH // 2 if center is None else center
        self.screen.blit(text_surface, (center - text_surface.get_width() // 2, y))

    def _menu_heading(self, text):
        GradientBackground.draw_vertical(self.screen, MENU_TOP, MENU_BOTTOM)
        self._center_text(text, 36, 'large', c.ORANGE)
        pygame.draw.line(self.screen, RULE, (40, 112), (760, 112))

    def _menu_hint(self, keyboard, arcade, mouse=None):
        if self.ui_input == "joystick":
            text = arcade
        elif self.ui_input == "mouse" and mouse:
            text = mouse
        else:
            text = keyboard
        self._center_text(text, 558, color=MUTED)
    
    def _update_main_menu(self, mouse_pos, mouse_clicked):
        """
        Update main menu logic
        
        Args:
            mouse_pos: Current mouse position tuple (x, y)
            mouse_clicked: Boolean indicating if mouse was clicked
        """
        # Track idle time for attract mode. Genuine visitor input is any
        # held key, any joystick button, or a stick pushed past its
        # deadzone - NOT raw analog noise. Digital axis state is already
        # debounced by the joystick module (only set once an axis crosses
        # its threshold, cleared once it settles back near center), so a
        # noisy/drifting stick at rest can't keep resetting this forever.
        any_input = (
            mouse_clicked or
            bool(self.keys_down) or
            any(self.joy_input_state[0]['buttons']) or
            any(self.joy_input_state[1]['buttons']) or
            bool(self.joy_input_state[0]['axis']) or
            bool(self.joy_input_state[1]['axis'])
        )
        
        if any_input:
            self.idle_timer = 0
            if self.attract_mode:
                # Exit attract mode on any input
                self.attract_mode = False
                self.state = "MAIN_MENU"
                return
        else:
            self.idle_timer += 1
        
        # Start attract mode after timeout
        if self.idle_timer >= c.ATTRACT_MODE_TIMEOUT and not self.attract_mode:
            self._start_attract_mode()
            return
        
        # Update all buttons with mouse position
        for i, button in enumerate(self.menu_buttons):
            button.update(mouse_pos)
            button.selected = (i == self.menu_selected)
            
            # Check for button clicks
            if button.is_clicked(mouse_pos, mouse_clicked):
                self.menu_selected = i
                self.ui_input = "mouse"
                self._activate_menu_button(i)
    
    def _activate_menu_button(self, index):
        """
        Activate menu button by index
        
        Args:
            index: Button index (0=START, 1=CONTROLS, 2=ABOUT)
        """
        if index == 0:  # START
            self._consume_held_inputs()
            self.selection_started = None
            self.state = "CHARACTER_SELECT"
            self.p1_selected = False
            self.p2_selected = False
        elif index == 1:  # CONTROLS
            self.state = "CONTROLS"
        elif index == 2:  # ABOUT
            self.state = "ABOUT"
    
    def _play_music(self):
        """Start playing background music"""
        try:
            if os.path.exists(self.music_path):
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.play(-1)  # -1 means loop infinitely (we'll handle the custom loop point)
                self.music_start_time = pygame.time.get_ticks()
                print(f"Music loaded and playing: {self.music_path}")
            else:
                print(f"Warning: Music file not found at {self.music_path}")
        except Exception as e:
            print(f"Error loading music: {e}")
    
    def _update_music(self):
        """Handle music looping from minute 3 when it ends"""
        try:
            # Check if music is playing
            if not pygame.mixer.music.get_busy():
                # Music ended, restart from loop point (3 minutes = 180 seconds)
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.play(-1)
                # Note: pygame doesn't support starting from a specific position,
                # so we restart from the beginning. For a perfect loop from 3:00,
                # you would need to edit the music file to start at that point.
                print("Music restarting...")
        except Exception as e:
            print(f"Error updating music: {e}")
    
    def _draw_main_menu(self):
        """Render main menu screen with vintage arcade styling"""
        GradientBackground.draw_vertical(self.screen, MENU_TOP, MENU_BOTTOM)
        self._center_text(self.menu_title, 76, 'xlarge', c.ORANGE)
        self._center_text(self.menu_subtitle, 170, 'medium')
        pygame.draw.line(self.screen, RULE, (100, 226), (700, 226))
        phase = (pygame.time.get_ticks() // 80) % 16
        for index, x, facing in ((self.p1_cursor, 52, True), (self.p2_cursor, 592, False)):
            self.screen.blit(idle_portrait(index, phase, facing), (x, 294))

        for i, button in enumerate(self.menu_buttons):
            button.selected = i == self.menu_selected
            button.draw(self.screen, self.text_renderer)
        self._menu_hint("UP/DOWN: CHOOSE  |  ENTER: SELECT  |  ESC: EXIT",
                        "STICK: CHOOSE  |  START: SELECT  |  P1: EXIT",
                        "CLICK: SELECT  |  ESC: EXIT")
    
    # ==================== CONTROLS SCREEN STATE ====================
    
    def _update_controls(self, mouse_pos, mouse_clicked):
        """Update controls screen logic"""
        self.controls_back_button.update(mouse_pos)
        
        if self.controls_back_button.is_clicked(mouse_pos, mouse_clicked):
            self.state = "MAIN_MENU"
    
    def _draw_controls(self):
        """Render controls screen with keyboard and arcade box controls"""
        self._menu_heading("GAME CONTROLS")
        columns = (40, 280, 480, 620)
        headers = ("IN FIGHT", "ARCADE", "P1 KEYS", "P2 KEYS")
        for x, label in zip(columns, headers):
            self.screen.blit(self.text_renderer.render(label, 'small', c.ORANGE), (x, 124))

        rows = (
            ("Move / jump", "Stick", "W/A/S/D", "Arrows"),
            ("Light punch", "B", "J", "Num 1"),
            ("Heavy punch", "A", "K", "Num 2"),
            ("Light kick", "X", "L", "Num 3"),
            ("Heavy kick", "Y", "I", "Num 4"),
            ("Special", "Insert", "U", "Num 0"),
            ("Dash", "Select", "L Shift", "R Shift"),
            ("Parry", "Start", "O", "Num 5"),
        )
        for i, row in enumerate(rows):
            y = 156 + i * 28
            for x, label in zip(columns, row):
                self.screen.blit(self.text_renderer.render(label, 'small', c.WHITE), (x, y))
        pygame.draw.line(self.screen, RULE, (40, 384), (760, 384))
        for i, line in enumerate((
                "BLOCK: HOLD DOWN",
                "SUPER: SPECIAL + HEAVY PUNCH WHEN METER IS FULL",
                "ESC / P1: FIGHT TO SELECT; EXIT AT MAIN MENU")):
            self.screen.blit(self.text_renderer.render(line, 'small', MUTED),
                             (40, 394 + i * 28))
        self.controls_back_button.draw(self.screen, self.text_renderer)
        self._menu_hint("ENTER: MAIN MENU  |  ESC: BACK",
                        "START: MAIN MENU  |  P1: BACK",
                        "CLICK BACK: MAIN MENU  |  ESC: BACK")
    
    # ==================== ABOUT SCREEN STATE ====================
    
    def _update_about(self, mouse_pos, mouse_clicked):
        """Update about screen logic"""
        self.about_back_button.update(mouse_pos)
        
        if self.about_back_button.is_clicked(mouse_pos, mouse_clicked):
            self.state = "MAIN_MENU"
    
    def _draw_about(self):
        """Render about screen"""
        self._menu_heading("ABOUT CMUQ ARENA")
        self._center_text("CMUQ ARENA", 158, 'medium', c.ORANGE)
        self._center_text("ULTIMATE FIGHTING CHAMPIONSHIP", 200, 'small', c.ORANGE)
        self._center_text("Made by Game Dev Club with Love", 272)
        self._center_text("Yousef Hussein - Class of 2029", 308)
        self._center_text("Version 1.0 - Tarnival 2026", 344)
        self._center_text("SUPPORTS PS4/PS5 AND SWITCH CONTROLLERS", 416, color=MUTED)
        self.about_back_button.draw(self.screen, self.text_renderer)
        self._menu_hint("ENTER: MAIN MENU  |  ESC: BACK",
                        "START: MAIN MENU  |  P1: BACK",
                        "CLICK BACK: MAIN MENU  |  ESC: BACK")
    
    # ==================== CHARACTER SELECT STATE ====================
    
    def _update_character_select(self, mouse_pos, mouse_clicked):
        """Present both locked picks for 500 ms without blocking input/events."""
        if self.p1_selected and self.p2_selected:
            now = pygame.time.get_ticks()
            if self.selection_started is None:
                self.selection_started = now
            elif now - self.selection_started >= 500:
                self._start_fight()
        else:
            self.selection_started = None
    
    def _draw_character_select(self):
        """Fixed roster slots and separate P1/P2 markers, even on mirror picks."""
        self._menu_heading("CHOOSE YOUR FIGHTER")
        for i, char in enumerate(c.CHARACTERS):
            x = 52 + i * 180
            rect = pygame.Rect(x, 184, 156, 148)
            active = i in (self.p1_cursor, self.p2_cursor)
            draw_panel(self.screen, rect, PANEL, c.ORANGE if active else RULE,
                       border_width=1, shadow=False)
            phase = (pygame.time.get_ticks() // 80) % 16 if active else 0
            self.screen.blit(idle_portrait(i, phase), rect.topleft)
            self._center_text(char['name'], 340, center=rect.centerx)

            for player, cursor, locked, y, color in (
                    ("P1", self.p1_cursor, self.p1_selected, 150, c.RED),
                    ("P2", self.p2_cursor, self.p2_selected, 378, P2_ACCENT)):
                if cursor == i:
                    label = f"{player}: {'LOCKED' if locked else 'SELECT'}"
                    self._center_text(label, y, color=c.YELLOW if locked else color,
                                      center=rect.centerx)
                    pygame.draw.line(self.screen, color, (x, y + 26),
                                     (x + rect.width, y + 26), 2)

        pygame.draw.line(self.screen, RULE, (40, 424), (760, 424))
        for player, cursor, locked, other_locked, center, color in (
                ("P1", self.p1_cursor, self.p1_selected, self.p2_selected, 220, c.RED),
                ("P2", self.p2_cursor, self.p2_selected, self.p1_selected, 580, P2_ACCENT)):
            self._center_text(f"{player}: {c.CHARACTERS[cursor]['name']}",
                              438, 'medium', color, center)
            if locked:
                waiting = "READY" if other_locked else f"WAITING FOR {'P2' if player == 'P1' else 'P1'}"
                self._center_text(f"LOCKED - {waiting}", 486, color=c.YELLOW, center=center)
            else:
                if self.ui_input == "joystick":
                    move, confirm = "STICK: CHOOSE", "START: LOCK IN"
                elif player == "P1":
                    move, confirm = "A/D: CHOOSE", "J / ENTER: LOCK IN"
                else:
                    move, confirm = "LEFT/RIGHT: CHOOSE", "NUM 1 / NUM ENTER: LOCK IN"
                self._center_text(move, 486, color=MUTED, center=center)
                self._center_text(confirm, 516, center=center)
        if self.selection_started is not None:
            progress = min(1, (pygame.time.get_ticks() - self.selection_started) / 500)
            width = int(360 * progress)
            pygame.draw.line(self.screen, c.YELLOW, (400 - width, 424), (400 + width, 424), 2)
            self._center_text("MATCH READY", 516, color=c.YELLOW)
        self._menu_hint("ESC: MAIN MENU", "P1: MAIN MENU")
    
    # ==================== FIGHT STATE ====================
    
    def _start_fight(self):
        """Initialize a new fight with selected characters"""
        self._consume_held_inputs()
        self._reset_match_presentation()
        self.combat_system = CombatSystem()
        # Use control configuration from config
        controls_p1 = c.DEFAULT_P1_CONTROLS
        controls_p2 = c.DEFAULT_P2_CONTROLS
        
        # Create fighters at proper ground positions
        stats_p1 = c.CHARACTERS[self.p1_cursor]
        stats_p2 = c.CHARACTERS[self.p2_cursor]
        
        # Spawn fighters on the ground (FLOOR_Y - P_HEIGHT)
        spawn_y = c.FLOOR_Y - c.P_HEIGHT
        self.p1 = self._new_fighter(200, spawn_y, stats_p1, controls_p1, is_p2=False,
                         combat_system=self.combat_system, fighter_id="p1",
                         joy_input_getter=self.get_joy_action)
        self.p2 = self._new_fighter(550, spawn_y, stats_p2, controls_p2, is_p2=True,
                         combat_system=self.combat_system, fighter_id="p2",
                         joy_input_getter=self.get_joy_action)
        
        # Register fighters with combat system for combo tracking
        self.combat_system.register_fighter("p1")
        self.combat_system.register_fighter("p2")
        
        # Reset round system for new match
        self.p1_wins = 0
        self.p2_wins = 0
        self.current_round = 1
        self.round_over = False
        self.round_transition_timer = 0
        self.round_winner = None
        
        # Reset ALL fight variables and clear leftover effects
        self.round_timer = 99
        self.particles = []
        self.projectiles = []
        self.special_effects = []
        self.hit_effects = []  # Clear hit effects from previous game
        self.screen_shake = 0  # Reset screen shake
        self.ko_slowdown = False
        self.slowdown_timer = 0
        self.winner_sequence_active = False
        self.winner_sequence_frame = 0
        
        self.state = "FIGHT"
        self.last_timer_update = pygame.time.get_ticks()
    
    def _exit_fight_to_character_select(self):
        """
        Abort the current fight (triggered by the P1/Esc back action) and
        return to character select. Tears down every piece of fight-only
        state - fighters, projectiles/effects, combat system, round and
        score counters - so a fight started afterwards never inherits
        leftover state from the one that was backed out of.
        """
        self.p1 = None
        self.p2 = None
        self._reset_match_presentation()
        self.particles = []
        self.projectiles = []
        self.special_effects = []
        self.hit_effects = []
        self.combat_system = CombatSystem()
        
        self.p1_wins = 0
        self.p2_wins = 0
        self.current_round = 1
        self.round_over = False
        self.round_transition_timer = 0
        self.round_winner = None
        self.winner_sequence_active = False
        self.winner_sequence_frame = 0
        
        self.round_timer = 99
        self.screen_shake = 0
        self.screen_shake_offset = (0, 0)
        self.hit_freeze_frames = 0
        self.ko_slowdown = False
        self.slowdown_timer = 0
        self.counter_attack_window = {'p1': 0, 'p2': 0}
        
        # Both players choose again for the next fight
        self.p1_selected = False
        self.p2_selected = False
        
        self.state = "CHARACTER_SELECT"
    
    def _start_attract_mode(self):
        """Start AI vs AI attract mode demo - exciting showcase of gameplay!"""
        self._reset_match_presentation()
        self.combat_system = CombatSystem()
        self.attract_mode = True
        
        # Select random characters
        self.p1_cursor = random.randint(0, len(c.CHARACTERS) - 1)
        self.p2_cursor = random.randint(0, len(c.CHARACTERS) - 1)
        while self.p2_cursor == self.p1_cursor:
            self.p2_cursor = random.randint(0, len(c.CHARACTERS) - 1)
        
        # Start fight with AI control
        controls_p1 = c.DEFAULT_P1_CONTROLS
        controls_p2 = c.DEFAULT_P2_CONTROLS
        
        stats_p1 = c.CHARACTERS[self.p1_cursor]
        stats_p2 = c.CHARACTERS[self.p2_cursor]
        
        spawn_y = c.FLOOR_Y - c.P_HEIGHT
        self.p1 = self._new_fighter(200, spawn_y, stats_p1, controls_p1, is_p2=False,
                         combat_system=self.combat_system, fighter_id="p1",
                         joy_input_getter=self.get_joy_action)
        self.p2 = self._new_fighter(550, spawn_y, stats_p2, controls_p2, is_p2=True,
                         combat_system=self.combat_system, fighter_id="p2",
                         joy_input_getter=self.get_joy_action)
        
        # Start with some super meter for exciting ultimates early on!
        self.p1.super_meter = 50
        self.p2.super_meter = 70  # P2 gets more to show ultimate sooner
        
        self.combat_system.register_fighter("p1")
        self.combat_system.register_fighter("p2")
        
        # Reset round system
        self.p1_wins = 0
        self.p2_wins = 0
        self.current_round = 1
        self.round_over = False
        self.round_transition_timer = 0
        
        # Reset fight variables
        self.round_timer = 99
        self.particles = []
        self.projectiles = []
        self.special_effects = []
        self.hit_effects = []
        self.screen_shake = 0
        self.winner_sequence_active = False
        
        self.state = "FIGHT"
        self.last_timer_update = pygame.time.get_ticks()
    
    def _reset_round(self):
        """Reset positions and health for new round (keep super meter)"""
        self.feedback.clear()
        self.ready_since = {'p1': None, 'p2': None}
        spawn_y = c.FLOOR_Y - c.P_HEIGHT
        
        # Store super meter
        p1_meter = getattr(self.p1, 'super_meter', 0)
        p2_meter = getattr(self.p2, 'super_meter', 0)
        
        # Reset positions
        self.p1.rect.x = 200
        self.p1.rect.y = spawn_y
        self.p2.rect.x = 550
        self.p2.rect.y = spawn_y
        
        # Reset health
        self.p1.health = self.p1.max_health
        self.p2.health = self.p2.max_health
        self.p1.alive = True
        self.p2.alive = True
        
        # Restore super meter
        self.p1.super_meter = p1_meter
        self.p2.super_meter = p2_meter
        
        # Reset states
        self.p1.attacking = False
        self.p1.hit_stun = 0
        self.p1.blocking = False
        self.p1.block_stun = 0
        self.p2.attacking = False
        self.p2.hit_stun = 0
        self.p2.blocking = False
        self.p2.block_stun = 0
        
        # Reset fight variables
        self.round_timer = 99
        self.particles = []
        self.projectiles = []
        self.special_effects = []
        self.hit_effects = []
        self.screen_shake = 0
        self.round_over = False
        self.round_transition_timer = 0
        self.round_winner = None
        self.winner_sequence_active = False
        self.winner_sequence_frame = 0
        self.last_timer_update = pygame.time.get_ticks()
        self.current_round += 1
    
    def _update_fight(self):
        """Update fight logic"""
        # Check for input during attract mode
        if self.attract_mode:
            # Genuine visitor input immediately cancels the demo: any held
            # key, any joystick button, or a stick pushed past its deadzone
            # (already debounced by the joystick module).
            any_input = (
                bool(self.keys_down) or
                any(self.joy_input_state[0]['buttons']) or
                any(self.joy_input_state[1]['buttons']) or
                bool(self.joy_input_state[0]['axis']) or
                bool(self.joy_input_state[1]['axis'])
            )
            if any_input:
                self.attract_mode = False
                self.idle_timer = 0
                self.state = "MAIN_MENU"
                return
            
            # Run simple AI for both fighters
            self._update_ai_fighter(self.p1, self.p2)
            self._update_ai_fighter(self.p2, self.p1)
        
        # Handle round transition
        if self.round_over:
            self.round_transition_timer += 1
            
            # Show "K.O." for first 60 frames
            if self.round_transition_timer >= c.ROUND_TRANSITION_TIME:
                # Check if match is over
                if self.p1_wins >= c.WINS_REQUIRED or self.p2_wins >= c.WINS_REQUIRED:
                    self._enter_results()
                else:
                    # Start next round
                    self._reset_round()
            return
        
        # Handle hit freeze (brief pause on heavy hits for impact)
        if self.hit_freeze_frames > 0:
            self.hit_freeze_frames -= 1
            return  # Skip update during hit freeze
        
        # Update counter attack windows
        for player in ['p1', 'p2']:
            if self.counter_attack_window[player] > 0:
                self.counter_attack_window[player] -= 1
        
        # Update timer
        if pygame.time.get_ticks() - self.last_timer_update > 1000:
            self.round_timer -= 1
            self.last_timer_update = pygame.time.get_ticks()
        
        # ATTRACT MODE: Keep fighters alive for continuous demo
        if self.attract_mode:
            # Regenerate health when low to prevent death
            if self.p1.health < 50:
                self.p1.health = min(self.p1.max_health, self.p1.health + 2)
            if self.p2.health < 50:
                self.p2.health = min(self.p2.max_health, self.p2.health + 2)
            # Reset timer to prevent timeout
            if self.round_timer < 30:
                self.round_timer = 99
        
        # Check win conditions (round over, not game over)
        if self.p1.health <= 0 or self.p2.health <= 0 or self.round_timer <= 0:
            if not self.round_over:
                self.round_over = True
                self.round_transition_timer = 0
                
                # Determine round winner
                if self.p1.health <= 0 and self.p2.health <= 0:
                    self.round_winner = "draw"
                elif self.p1.health <= 0:
                    self.round_winner = "p2"
                    self.p2_wins += 1
                    self.hit_effects.append(HitEffect(self.p1.rect.centerx, self.p1.rect.centery - 50, 'ko', c.RED))
                elif self.p2.health <= 0:
                    self.round_winner = "p1"
                    self.p1_wins += 1
                    self.hit_effects.append(HitEffect(self.p2.rect.centerx, self.p2.rect.centery - 50, 'ko', c.BLUE))
                else:
                    # Time out - higher health wins
                    if self.p1.health > self.p2.health:
                        self.round_winner = "p1"
                        self.p1_wins += 1
                    elif self.p2.health > self.p1.health:
                        self.round_winner = "p2"
                        self.p2_wins += 1
                    else:
                        self.round_winner = "draw"
                
                # Trigger winner sequence if match is over
                if self.p1_wins >= c.WINS_REQUIRED or self.p2_wins >= c.WINS_REQUIRED:
                    self.winner_sequence_active = True
                    self.winner_sequence_frame = 0
            return
        
        # Winner sequence animation - exactly 3 seconds (180 frames at 60fps)
        if self.winner_sequence_active:
            self.winner_sequence_frame += 1
            
            # Slow motion effect: Skip update on even frames for first 30 frames
            # This creates a slow-mo effect by updating game state at half speed
            is_in_slowmo_window = self.winner_sequence_frame <= 30
            is_even_frame = self.winner_sequence_frame % 2 == 0
            if is_in_slowmo_window and is_even_frame:
                return  # Skip this update to create slow motion
            
            if self.winner_sequence_frame >= 180:  # Exactly 3 seconds
                self._enter_results()
                self.winner_sequence_active = False
                self.winner_sequence_frame = 0
            return  # Don't update fight during winner sequence
        
        # Update screen shake
        if self.screen_shake > 0:
            self.screen_shake -= 1
            shake_amount = min(self.screen_shake, 5)
            self.screen_shake_offset = (
                self.cosmetic_rng.randint(-shake_amount, shake_amount),
                self.cosmetic_rng.randint(-shake_amount, shake_amount)
            )
        else:
            self.screen_shake_offset = (0, 0)
        
        # Update fighters and handle special moves
        result1 = self.p1.move(self.p2, c.SCREEN_WIDTH, c.SCREEN_HEIGHT)
        result2 = self.p2.move(self.p1, c.SCREEN_WIDTH, c.SCREEN_HEIGHT)
        
        # Handle special move results
        for result in [result1, result2]:
            if result is not None:
                if isinstance(result, list):
                    # Multiple projectiles (pizza throw)
                    self.projectiles.extend(result)
                elif isinstance(result, SpinningKickEffect):
                    # Special effect (spinning kick)
                    self.special_effects.append(result)
                elif hasattr(result, 'active') and not isinstance(result, SpinningKickEffect):
                    # Single projectile (make sure it's not a SpinningKickEffect)
                    self.projectiles.append(result)
        
        self.p1.update()
        self.p2.update()
        
        # Update and handle projectiles
        for proj in self.projectiles[:]:
            proj.update()
            if not proj.active:
                self.projectiles.remove(proj)
                continue
            
            # Check collision with fighters
            proj_rect = proj.get_rect()
            if proj.owner == self.p1 and proj_rect.colliderect(self.p2.rect):
                # Check if p2 is parrying
                if self.p2.parrying and self.p2.parry_window > 0:
                    # Successful parry - reflect projectile
                    proj.vel_x = -proj.vel_x  # Reverse horizontal velocity
                    proj.owner = self.p2  # Change ownership to p2
                    self.p2.parry_success = True
                    self.p2.color_flash = 10
                    self._contact_feedback(self.p2, 'parry', self.p2.rect.center)
                    # Grant counter attack window (60 frames = 1 second)
                    self.counter_attack_window['p2'] = 60
                    self.hit_freeze_frames = 5  # Brief freeze for impact
                else:
                    # Apply combo damage scaling
                    damage = proj.damage
                    if self.p1.combat_system and self.p1.fighter_id:
                        combo_info = self.p1.combat_system.record_hit(self.p1.fighter_id, damage, 'special')
                        damage *= combo_info['multiplier']
                    
                    # Check for counter attack bonus
                    if self.counter_attack_window['p1'] > 0:
                        damage *= 1.5  # 50% bonus damage on counter
                    
                    self.p2.take_damage(damage, 10, 15, self.p1.facing_right)
                    self.screen_shake = 8
                    self.hit_freeze_frames = 4  # Brief freeze on heavy hits
                    proj.active = False
            elif proj.owner == self.p2 and proj_rect.colliderect(self.p1.rect):
                # Check if p1 is parrying
                if self.p1.parrying and self.p1.parry_window > 0:
                    # Successful parry - reflect projectile
                    proj.vel_x = -proj.vel_x  # Reverse horizontal velocity
                    proj.owner = self.p1  # Change ownership to p1
                    self.p1.parry_success = True
                    self.p1.color_flash = 10
                    self._contact_feedback(self.p1, 'parry', self.p1.rect.center)
                    # Grant counter attack window (60 frames = 1 second)
                    self.counter_attack_window['p1'] = 60
                    self.hit_freeze_frames = 5  # Brief freeze for impact
                else:
                    # Apply combo damage scaling
                    damage = proj.damage
                    if self.p2.combat_system and self.p2.fighter_id:
                        combo_info = self.p2.combat_system.record_hit(self.p2.fighter_id, damage, 'special')
                        damage *= combo_info['multiplier']
                    
                    # Check for counter attack bonus
                    if self.counter_attack_window['p2'] > 0:
                        damage *= 1.5  # 50% bonus damage on counter
                    
                    self.p1.take_damage(damage, 10, 15, self.p2.facing_right)
                    self.screen_shake = 8
                    self.hit_freeze_frames = 4  # Brief freeze on heavy hits
                    proj.active = False
        
        # Update special effects
        for effect in self.special_effects[:]:
            effect.update()
            if not effect.active:
                self.special_effects.remove(effect)
                continue
            
            # Check for spinning kick hits
            if isinstance(effect, SpinningKickEffect) and effect.can_hit():
                target = self.p2 if effect.fighter == self.p1 else self.p1
                attacker = effect.fighter
                kick_rect = pygame.Rect(attacker.rect.x - 30, attacker.rect.y - 30, 
                                       attacker.rect.width + 60, attacker.rect.height + 60)
                if kick_rect.colliderect(target.rect):
                    # Apply combo damage scaling
                    damage = 8
                    if attacker.combat_system and attacker.fighter_id:
                        attacker.combat_system.increment_combo(attacker.fighter_id)
                        combo_multiplier = attacker.combat_system.get_combo_damage_multiplier(attacker.fighter_id)
                        damage *= combo_multiplier
                    
                    target.take_damage(damage, 15, 10, attacker.facing_right)
                    effect.register_hit()
                    self.screen_shake = 10
        
        # Update particles
        for p in self.particles[:]:
            p.update()
            if p.timer <= 0:
                self.particles.remove(p)
        
        # Update hit effects
        for effect in self.hit_effects[:]:
            effect.update()
            if not effect.active:
                self.hit_effects.remove(effect)
    
    def _draw_fight(self):
        """Render fight screen with vintage arcade HUD"""
        # Apply screen shake offset
        shake_x, shake_y = self.screen_shake_offset
        
        # Get current frame for animations
        current_frame = pygame.time.get_ticks() // 16  # ~60fps
        
        # Draw parallax background with CMU-Q pillars
        drawing.draw_parallax_background(self.screen, self.p1.rect.centerx, self.p2.rect.centerx, current_frame)
        
        self.screen.blit(self.floor_texture, (shake_x, c.FLOOR_Y + shake_y))
        
        # Floor line
        pygame.draw.line(self.screen, (100, 60, 25), (0 + shake_x, c.FLOOR_Y + shake_y), 
                        (c.SCREEN_WIDTH + shake_x, c.FLOOR_Y + shake_y), 3)
        
        # Create shaken surface for game objects
        if self.screen_shake > 0:
            # Draw everything to a temporary surface then blit with offset
            game_surface = self.object_surface
            game_surface.fill((0, 0, 0, 0))
        else:
            game_surface = self.screen
            shake_x, shake_y = 0, 0
        
        # Draw fighters (or winner sequence)
        if self.winner_sequence_active:
            # Determine winner and loser
            if self.p1.health <= 0:
                winner = self.p2
                loser = self.p1
            else:
                winner = self.p1
                loser = self.p2
            
            # Draw blood puddle at loser's position
            drawing.draw_blood_puddle(game_surface, loser.rect.centerx, c.FLOOR_Y, 80)
            
            # Use epic beatdown animation!
            drawing.draw_victory_beatdown(
                game_surface,
                winner.rect.centerx, winner.rect.bottom,
                loser.rect.centerx, c.FLOOR_Y,
                winner.stats['name'], winner.stats['skin'], winner.stats['color'],
                loser.stats['name'], loser.stats['skin'], loser.stats['color'],
                self.winner_sequence_frame
            )
            
        else:
            self.p1.draw(game_surface)
            self.p2.draw(game_surface)
        
        # Draw projectiles
        for proj in self.projectiles:
            proj.draw(game_surface)
        
        # Draw special effects (spinning kick rotation)
        for effect in self.special_effects:
            if isinstance(effect, SpinningKickEffect):
                # Draw rotation effect
                angle = effect.get_rotation_angle()
                # Visual feedback - could draw motion lines
                pass
        
        # Draw particles
        for p in self.particles:
            p.draw(game_surface)
        
        # Draw hit effects
        for effect in self.hit_effects:
            effect.draw(game_surface, self.text_renderer)
        for effect in self.feedback:
            effect.draw(game_surface, self.text_renderer)
        
        # Blit shaken surface if needed
        if self.screen_shake > 0:
            self.screen.blit(game_surface, (shake_x, shake_y))
        
        # Draw HUD (not affected by shake)
        self._draw_fight_hud()
    
    def _draw_fight_hud(self):
        """Draw vintage arcade-style HUD with segmented health bars"""
        pygame.draw.rect(self.screen, MENU_BOTTOM, (0, 0, c.SCREEN_WIDTH, 120))
        current_time = pygame.time.get_ticks()
        for player, fighter, x, color in (("P1", self.p1, 20, c.RED),
                                          ("P2", self.p2, 480, c.BLUE)):
            name = self.text_renderer.render(f"{player} {fighter.stats['name']}", 'small', c.WHITE)
            self.screen.blit(name, (x, 12))
            ratio = fighter.health / fighter.max_health
            draw_health_bar(self.screen, x, 44, 300, 24, ratio, color)

            # Display the existing Fighter.attack special gate (4000ms),
            # not the move's shorter recovery. No cooldown/state is changed.
            elapsed = current_time - fighter.last_special_time
            power_ratio = max(0.0, min(1.0, elapsed / 4000))
            ready = power_ratio >= 1.0
            status = "READY" if ready else f"{max(0, 4000 - elapsed) / 1000:.1f}s"
            label = self.text_renderer.render("SPECIAL", 'small', MUTED)
            self.screen.blit(label, (x, 78))
            status_text = self.text_renderer.render(status, 'small', c.YELLOW if ready else c.WHITE)
            self.screen.blit(status_text, (x + 300 - status_text.get_width(), 78))
            draw_health_bar(self.screen, x, 106, 300, 10, power_ratio,
                            c.YELLOW if ready else c.ORANGE, show_segments=False)
            since = self.ready_since[fighter.fighter_id]
            if ready and since is not None and current_time - since < 650:
                # One edge cue on recovery; the READY label never blinks off.
                inset = int(12 * min(1, (current_time - since) / 650))
                pygame.draw.rect(self.screen, c.YELLOW, (x - 2, 76, 304, 42), 1)
                pygame.draw.line(self.screen, c.WHITE, (x + inset, 111), (x + 298 - inset, 111))

        t_color = c.WHITE if self.round_timer > 10 else c.RED
        pygame.draw.rect(self.screen, c.ORANGE, (344, 10, 112, 64), 1)
        self._center_text(str(max(0, self.round_timer)), 8, 'large', t_color)
        self._center_text(f"ROUND {self.current_round}", 82, color=MUTED)

        # Combat housekeeping runs once after update, never from rendering.
        self._draw_combo_display()
        self._draw_round_wins()
        self._draw_super_meters()

        # The existing 99/98/97 windows are unchanged, with no new delay.
        if self.round_timer > 96 and not self.round_over and self.state == "FIGHT":
            if self.round_timer > 97:
                self._round_banner(f"ROUND {self.current_round}",
                                   f"FIRST TO {c.WINS_REQUIRED} ROUNDS", c.WHITE)
            else:
                self._round_banner("FIGHT!", "", c.YELLOW)

        if self.round_over and self.state == "FIGHT":
            self._draw_round_transition()

        if self.attract_mode:
            banner = self.text_renderer.render_outlined("DEMO - PRESS ANY BUTTON TO PLAY", 'small', c.YELLOW, c.BLACK, 2)
            banner_x = c.SCREEN_WIDTH // 2 - banner.get_width() // 2
            self.screen.blit(banner, (banner_x, 502))
    
    def _draw_round_wins(self):
        """Draw round win indicators (circles/gems)"""
        gem_radius = 8
        gem_y = 24
        
        # P1 wins (left side)
        for i in range(c.WINS_REQUIRED):
            gem_x = 280 + i * 26
            if i < self.p1_wins:
                # Won round - filled yellow
                pygame.draw.circle(self.screen, c.YELLOW, (gem_x, gem_y), gem_radius)
            else:
                # Not won yet - empty
                pygame.draw.circle(self.screen, c.DARK_GRAY, (gem_x, gem_y), gem_radius)
            pygame.draw.circle(self.screen, c.WHITE, (gem_x, gem_y), gem_radius, 2)
        
        # P2 wins (right side)
        p2_start_x = 740
        for i in range(c.WINS_REQUIRED):
            gem_x = p2_start_x + i * 26
            if i < self.p2_wins:
                # Won round - filled yellow
                pygame.draw.circle(self.screen, c.YELLOW, (gem_x, gem_y), gem_radius)
            else:
                # Not won yet - empty
                pygame.draw.circle(self.screen, c.DARK_GRAY, (gem_x, gem_y), gem_radius)
            pygame.draw.circle(self.screen, c.WHITE, (gem_x, gem_y), gem_radius, 2)
    
    def _draw_super_meters(self):
        """Draw super meter bars at bottom of screen"""
        for fighter, x in ((self.p1, 20), (self.p2, 500)):
            ratio = max(0.0, min(1.0, fighter.super_meter / c.SUPER_METER_MAX))
            ready = ratio >= 1.0
            pygame.draw.rect(self.screen, MENU_BOTTOM, (x - 4, 534, 288, 46))
            label = "SUPER READY" if ready else "SUPER"
            text = self.text_renderer.render(label, 'small', c.YELLOW if ready else c.WHITE)
            self.screen.blit(text, (x, 536))
            # Full remains visibly full; no pulsing down to black.
            draw_health_bar(self.screen, x, 564, 280, 14, ratio,
                            c.YELLOW if ready else c.PURPLE, show_segments=False)

    def _round_banner(self, title, detail, color):
        """One quiet, centered stage shared by the existing round windows."""
        self.screen.blit(veil(c.SCREEN_WIDTH, 126, MENU_BOTTOM, 210), (0, 238))
        pygame.draw.line(self.screen, c.ORANGE, (280, 238), (520, 238), 2)
        self._center_text(title, 250, 'large', color)
        if detail:
            self._center_text(detail, 324, color=MUTED)

    def _draw_round_transition(self):
        """Draw round over transition screen"""
        # Semi-transparent overlay
        # Keep the HUD fully readable. Only the arena recedes.
        self.screen.blit(veil(c.SCREEN_WIDTH, 410, c.BLACK, 150), (0, 120))
        
        # Same 60-frame KO window, including an accurate timeout label.
        if self.round_transition_timer < 60:
            if self.p1.health <= 0 and self.p2.health <= 0:
                title = "DOUBLE K.O.!"
            elif self.p1.health > 0 and self.p2.health > 0:
                title = "TIME UP"
            else:
                title = "K.O.!"
            self._round_banner(title, f"ROUND {self.current_round}", c.ORANGE)
        else:
            if self.round_winner == "p1":
                winner_text = f"P1 {self.p1.stats['name']} WINS!"
                color = c.RED
            elif self.round_winner == "p2":
                winner_text = f"P2 {self.p2.stats['name']} WINS!"
                color = P2_ACCENT
            else:
                winner_text = "ROUND DRAW"
                color = c.YELLOW
            detail = f"ROUND {self.current_round}  |  P1 {self.p1_wins} - {self.p2_wins} P2"
            self._round_banner(winner_text, detail, color)
    
    def _draw_combo_display(self):
        """Draw combo counter and announcements"""
        current_time = pygame.time.get_ticks()
        
        # Do not stack old fight announcements under the match winner's title.
        if self.state == "GAME_OVER":
            return
        
        # Draw P1 combo counter
        p1_combo = self.combat_system.get_combo_count("p1")
        if p1_combo >= 2:
            combo_text = self.text_renderer.render_outlined(f"{p1_combo} HITS", 'medium', c.YELLOW, c.BLACK, 2)
            self.screen.blit(combo_text, (20, 130))
        
        # Draw P2 combo counter
        p2_combo = self.combat_system.get_combo_count("p2")
        if p2_combo >= 2:
            combo_text = self.text_renderer.render_outlined(f"{p2_combo} HITS", 'medium', c.YELLOW, c.BLACK, 2)
            self.screen.blit(combo_text, (c.SCREEN_WIDTH - combo_text.get_width() - 20, 130))
        
        # Keep the existing counter window, without rapidly flashing the cue.
        if self.counter_attack_window['p1'] > 0:
            counter_text = self.text_renderer.render_outlined("COUNTER!", 'small', c.GREEN, c.BLACK, 1)
            self.screen.blit(counter_text, (20, 168))
        
        if self.counter_attack_window['p2'] > 0:
            counter_text = self.text_renderer.render_outlined("COUNTER!", 'small', c.GREEN, c.BLACK, 1)
            self.screen.blit(counter_text, (c.SCREEN_WIDTH - counter_text.get_width() - 20, 168))
        
        # Draw combo announcements
        # Latest message per player, in separate lanes. The underlying combo
        # history/lifetime is untouched; simultaneous messages no longer stack.
        latest = {}
        for announcement in self.combat_system.get_announcements():
            latest[announcement['fighter_id']] = announcement
        for announcement in latest.values():
            age = current_time - announcement['time']
            if age < 2000:  # Show for 2 seconds
                # Calculate animation
                alpha = int(255 * (1 - age / 2000))
                
                text = announcement['text']
                is_p1 = announcement['fighter_id'] == "p1"
                color = c.RED if is_p1 else P2_ACCENT
                
                # Render announcement text
                ann_text = self.text_renderer.render_outlined(text, 'small', color, c.BLACK, 1)
                
                # Position based on which player
                if is_p1:
                    x = 20
                else:
                    x = c.SCREEN_WIDTH - ann_text.get_width() - 20
                
                y = 202
                
                # Apply fade
                ann_text.set_alpha(alpha)
                self.screen.blit(ann_text, (x, y))
    
    # ==================== GAME OVER STATE ====================
    
    def _update_game_over(self, mouse_pos, mouse_clicked):
        """Update game over logic"""
        for i, button in enumerate(self.result_buttons):
            button.update(mouse_pos)
            if button.is_clicked(mouse_pos, mouse_clicked):
                self.result_selected = i
                self._activate_result()
                return
    
    def _draw_game_over(self):
        """Same arena, without stale HUD or contact effects behind the choices."""
        self.screen.blit(self.result_backdrop, (0, 0))
        
        # Dark overlay with gradient effect
        self.screen.blit(veil(c.SCREEN_WIDTH, c.SCREEN_HEIGHT, MENU_BOTTOM, 225), (0, 0))
        
        # Determine winner
        if self.p1_wins > self.p2_wins:
            winner_text = f"P1 {self.p1.stats['name']} WINS!"
            color = c.RED
        elif self.p2_wins > self.p1_wins:
            winner_text = f"P2 {self.p2.stats['name']} WINS!"
            color = P2_ACCENT
        else:
            winner_text = "MATCH DRAW"
            color = c.YELLOW
        
        self._center_text(winner_text, 72, 'large', color)
        self._center_text("GAME OVER", 150, 'medium')
        self._center_text(f"ROUNDS   P1 {self.p1_wins} - {self.p2_wins} P2",
                          202, 'medium')
        pygame.draw.line(self.screen, RULE, (40, 266), (760, 266))
        for player, cursor, center, facing in (("P1", self.p1_cursor, 136, True),
                                               ("P2", self.p2_cursor, 664, False)):
            self.screen.blit(idle_portrait(cursor, 0, facing), (center - 78, 300))
            self._center_text(player, 450, color=c.RED if facing else P2_ACCENT, center=center)
            self._center_text(c.CHARACTERS[cursor]['name'], 482, center=center)
        for i, button in enumerate(self.result_buttons):
            button.selected = i == self.result_selected
            button.draw(self.screen, self.text_renderer)
        self._menu_hint("UP/DOWN: CHOOSE  |  ENTER: SELECT  |  ESC: MENU",
                        "STICK: CHOOSE  |  START: SELECT  |  P1: MENU",
                        "CLICK: SELECT  |  ESC: MENU")
    
    # ==================== HELPER METHODS ====================

    def _consume_held_inputs(self):
        """Keep raw device state; mask carried inputs until their own release."""
        self.blocked_keys.update(self.keys_down)
        pressed = pygame.key.get_pressed()
        for key in set(c.DEFAULT_P1_CONTROLS.values()) | set(c.DEFAULT_P2_CONTROLS.values()):
            if pressed[key]:
                self.blocked_keys.add(key)
        for player, state in self.joy_input_state.items():
            self.blocked_buttons[player].update(state['buttons'])
            self.blocked_axes[player].update(state['axis'])
        self.joy_menu_scroll_cooldown = 0
        self.joy_char_select_cooldown = {0: 0, 1: 0}

    def _release_input_guards(self):
        pressed = pygame.key.get_pressed()
        self.blocked_keys.intersection_update(
            key for key in self.blocked_keys if key in self.keys_down or pressed[key])
        for player, state in self.joy_input_state.items():
            self.blocked_buttons[player].intersection_update(state['buttons'])
            self.blocked_axes[player].intersection_update(state['axis'])

    def _reset_match_presentation(self):
        self.selection_started = None
        self.feedback.clear()
        self.special_ready = {'p1': True, 'p2': True}
        self.ready_since = {'p1': None, 'p2': None}
        self.hit_freeze_frames = 0
        self.counter_attack_window = {'p1': 0, 'p2': 0}
        self.screen_shake_offset = (0, 0)
        self.attract_mode = False
        self.idle_timer = 0
        self.ai_p1 = self.ai_p2 = None

    def _new_fighter(self, *args, **kwargs):
        return PresentedFighter(*args, on_contact=self._contact_feedback,
                                key_blocked=self.blocked_keys.__contains__, **kwargs)

    def _contact_feedback(self, defender, kind, position):
        attacker = self.p1 if defender is self.p2 else self.p2
        heavy = bool(attacker and 'heavy' in (attacker.attack_type or ''))
        effect = ContactEffect(*position, kind, heavy)
        # Latest contact per defender, maximum two labels even in barrages.
        effect.fighter_id = defender.fighter_id
        self.feedback = [old for old in self.feedback if old.fighter_id != defender.fighter_id]
        self.feedback.append(effect)
        self._spawn_particles(*position, effect.color)
        if kind == 'hit' and heavy:
            self.screen_shake = max(self.screen_shake, 6)

    def _finish_fight_frame(self):
        """Once per display tick, including hit-stop/round/result windows.

        Combo housekeeping retains its old post-update timing. Cosmetic age
        advances here, so drawing a screenshot can never change a fight.
        """
        now = pygame.time.get_ticks()
        self.combat_system.update(now)
        for effect in self.feedback:
            effect.update()
        self.feedback = [effect for effect in self.feedback if effect.active]
        for fighter in (self.p1, self.p2):
            if fighter is None:
                continue
            ready = now - fighter.last_special_time >= 4000
            if ready and not self.special_ready[fighter.fighter_id]:
                self.ready_since[fighter.fighter_id] = now
            self.special_ready[fighter.fighter_id] = ready

    def _enter_results(self):
        self.state = "GAME_OVER"
        self.result_selected = 0
        self._consume_held_inputs()
        self.screen_shake = 0
        self.screen_shake_offset = (0, 0)
        self.feedback.clear()

    def _activate_result(self):
        self._consume_held_inputs()
        if self.result_selected == 0:
            self._start_fight()
        elif self.result_selected == 1:
            self._exit_fight_to_character_select()
        else:
            self._go_back()
    
    def _spawn_particles(self, x, y, color):
        """Spawn particle effects at position"""
        for _ in range(5):
            vx = self.cosmetic_rng.uniform(-5, 5)
            vy = self.cosmetic_rng.uniform(-5, -2)
            self.particles.append(Particle(x, y, color, (vx, vy)))
        del self.particles[:-96]
    
    def _update_ai_fighter(self, ai_fighter, target):
        """
        Enhanced AI logic for attract mode - aggressive fighting with specials and ultimates.
        Makes the demo exciting to watch!
        """
        current_time = pygame.time.get_ticks()
        dx = target.rect.centerx - ai_fighter.rect.centerx
        distance = abs(dx)
        
        # Face the opponent
        ai_fighter.facing_right = dx > 0
        
        # Random action selection with weighted probabilities
        rand = random.random()
        
        # ===== ULTIMATE MOVE - Use when meter is full! =====
        if ai_fighter.super_meter >= c.SUPER_METER_MAX:
            # High chance to use ultimate when available (exciting for demo!)
            if rand < 0.15 and distance < 300:
                # Move toward target first if needed
                if distance > 100:
                    if dx > 0:
                        ai_fighter.rect.x += ai_fighter.speed
                    else:
                        ai_fighter.rect.x -= ai_fighter.speed
                else:
                    # Execute ultimate!
                    result = ai_fighter.attack(target, 'ultimate')
                    if result is not None:
                        # Handle projectiles from ultimate
                        if isinstance(result, list):
                            self.projectiles.extend(result)
                        elif hasattr(result, 'active'):
                            if hasattr(result, 'fighter'):  # SpinningKickEffect
                                self.special_effects.append(result)
                            else:
                                self.projectiles.append(result)
                        # Screen flash for ultimate
                        self.screen_shake = 15
                        self.hit_freeze_frames = 8
        
        # ===== SPECIAL MOVES - Use frequently for demo =====
        elif rand < 0.08 and distance < 250:
            if current_time - ai_fighter.last_special_time >= 3000:  # Faster cooldown for demo
                result = ai_fighter.attack(target, 'special')
                if result is not None:
                    if isinstance(result, list):
                        self.projectiles.extend(result)
                    elif hasattr(result, 'active'):
                        if hasattr(result, 'fighter'):
                            self.special_effects.append(result)
                        else:
                            self.projectiles.append(result)
        
        # ===== MOVEMENT & COMBAT =====
        elif distance > 200:
            # Move toward target aggressively
            move_speed = ai_fighter.speed * 0.9
            if dx > 0:
                ai_fighter.rect.x += move_speed
            else:
                ai_fighter.rect.x -= move_speed
            
            # Jump toward opponent sometimes
            if rand < 0.04 and not ai_fighter.jumping:
                ai_fighter.vel_y = ai_fighter.jump_force
                ai_fighter.jumping = True
        
        elif distance < 120:
            # In attack range - be aggressive!
            if rand < 0.15:
                # Combo attacks - favor variety
                attacks = ['light_punch', 'heavy_punch', 'light_kick', 'heavy_kick']
                # Weight toward heavy attacks for more impact
                if random.random() < 0.4:
                    attack = random.choice(['heavy_punch', 'heavy_kick'])
                else:
                    attack = random.choice(attacks)
                ai_fighter.attack(target, attack)
                
            elif rand < 0.20:
                # Jump and attack
                if not ai_fighter.jumping:
                    ai_fighter.vel_y = ai_fighter.jump_force
                    ai_fighter.jumping = True
                    # Queue an attack
                    ai_fighter.attack(target, 'heavy_kick')
                    
            elif rand < 0.22:
                # Occasionally block
                ai_fighter.blocking = True
                ai_fighter.is_blocking = True
                
            elif rand < 0.25:
                # Dash back then attack
                if dx > 0:
                    ai_fighter.rect.x -= ai_fighter.speed * 2
                else:
                    ai_fighter.rect.x += ai_fighter.speed * 2
        
        # Medium range - approach with attacks
        else:
            if rand < 0.06:
                # Dash in
                if dx > 0:
                    ai_fighter.rect.x += ai_fighter.speed * 2
                else:
                    ai_fighter.rect.x -= ai_fighter.speed * 2
            elif rand < 0.10:
                # Jump in
                if not ai_fighter.jumping:
                    ai_fighter.vel_y = ai_fighter.jump_force
                    ai_fighter.jumping = True
            else:
                # Walk toward
                if dx > 0:
                    ai_fighter.rect.x += ai_fighter.speed * 0.5
                else:
                    ai_fighter.rect.x -= ai_fighter.speed * 0.5
        
        # Stop blocking randomly
        if ai_fighter.blocking and random.random() < 0.15:
            ai_fighter.blocking = False
            ai_fighter.is_blocking = False
        
        # ===== PHYSICS =====
        ai_fighter.vel_y += c.GRAVITY
        ai_fighter.rect.y += ai_fighter.vel_y
        
        # Floor collision
        if ai_fighter.rect.bottom > c.FLOOR_Y:
            ai_fighter.rect.bottom = c.FLOOR_Y
            ai_fighter.vel_y = 0
            ai_fighter.jumping = False
        
        # Screen bounds
        if ai_fighter.rect.left < 0:
            ai_fighter.rect.left = 0
        if ai_fighter.rect.right > c.SCREEN_WIDTH:
            ai_fighter.rect.right = c.SCREEN_WIDTH
        
        # ===== SUPER METER BOOST FOR DEMO =====
        # Give AI fighters extra meter so they use ultimates more often
        if self.attract_mode:
            ai_fighter.super_meter = min(c.SUPER_METER_MAX, ai_fighter.super_meter + 0.5)
    
    def _spawn_dust_particles(self, x, y):
        """Spawn dust particles for landing/jumping effects"""
        for _ in range(8):
            vx = self.cosmetic_rng.uniform(-3, 3)
            vy = self.cosmetic_rng.uniform(-1, -0.5)
            color = (139, 90, 43)  # Dirt brown
            self.particles.append(Particle(x, y, color, (vx, vy)))
        del self.particles[:-96]
