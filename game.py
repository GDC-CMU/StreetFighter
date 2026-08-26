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
from entities import Fighter, Particle, SpinningKickEffect, HitEffect, Projectile
from ui_components import (Button, VintageTextRenderer, ArcadeFrame, ScanlineEffect,
                           GradientBackground, draw_panel, draw_health_bar)
from combat import CombatSystem
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
        
        # Display setup - fullscreen scaled for authentic arcade feel
        self.screen = pygame.display.set_mode(
            (c.SCREEN_WIDTH, c.SCREEN_HEIGHT),
            pygame.SCALED | pygame.FULLSCREEN
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
        
        # Set random seed for consistent ground texture
        random.seed(42)
        
        # Game state management
        self.state = "MAIN_MENU"  # Current game state
        self.running = True
        
        # Initialize all game screens
        self._init_main_menu()
        self._init_controls_screen()
        self._init_about_screen()
        self._init_character_select()
        self._init_fight_screen()
        
    def _init_main_menu(self):
        """Initialize main menu UI elements"""
        # Menu title
        self.menu_title = "CMUQ ARENA"
        self.menu_subtitle = "VINTAGE ARCADE FIGHTER"
        
        # Create menu buttons (centered vertically)
        button_width = 300
        button_height = 60
        button_x = c.SCREEN_WIDTH // 2 - button_width // 2
        start_y = 280
        gap = 80
        
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
            c.SCREEN_WIDTH // 2 - 150, 500, 300, 60, "BACK", c.ORANGE
        )
        
    def _init_about_screen(self):
        """Initialize about screen UI"""
        # Back button
        self.about_back_button = Button(
            c.SCREEN_WIDTH // 2 - 150, 500, 300, 60, "BACK", c.ORANGE
        )
        
    def _init_character_select(self):
        """Initialize character selection screen"""
        self.p1_cursor = 0
        self.p2_cursor = 1
        self.p1_selected = False
        self.p2_selected = False
        self.p2_coin_inserted = True  # Instant 2-player mode - no coin required
        
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
                        
                if event.type == pygame.KEYDOWN:
                    self._handle_keypress(event.key)
                
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
            
            # Decrement joystick menu scroll cooldown
            if self.joy_menu_scroll_cooldown > 0:
                self.joy_menu_scroll_cooldown -= 1
            for player_id in self.joy_char_select_cooldown:
                if self.joy_char_select_cooldown[player_id] > 0:
                    self.joy_char_select_cooldown[player_id] -= 1
            
            # ===== STATE-BASED UPDATE AND RENDERING =====
            if self.state == "MAIN_MENU":
                self._update_main_menu(mouse_pos, mouse_clicked)
                self._draw_main_menu()
                
            elif self.state == "CONTROLS":
                self._update_controls(mouse_pos, mouse_clicked)
                self._draw_controls()
                
            elif self.state == "ABOUT":
                self._update_about(mouse_pos, mouse_clicked)
                self._draw_about()
                
            elif self.state == "CHARACTER_SELECT":
                self._update_character_select(mouse_pos, mouse_clicked)
                self._draw_character_select()
                
            elif self.state == "FIGHT":
                self._update_fight()
                self._draw_fight()
                
            elif self.state == "GAME_OVER":
                self._update_game_over(mouse_pos, mouse_clicked)
                self._draw_game_over()
            
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
        # Global: ESC to go back/quit
        if key == pygame.K_ESCAPE:
            if self.state == "MAIN_MENU":
                self.running = False
            else:
                self.state = "MAIN_MENU"
                
        # Main menu keyboard navigation
        if self.state == "MAIN_MENU":
            if key == pygame.K_UP or key == pygame.K_w:
                self.menu_selected = (self.menu_selected - 1) % len(self.menu_buttons)
            elif key == pygame.K_DOWN or key == pygame.K_s:
                self.menu_selected = (self.menu_selected + 1) % len(self.menu_buttons)
            elif key == pygame.K_RETURN or key == pygame.K_SPACE:
                self._activate_menu_button(self.menu_selected)
                
        # Character select keyboard controls
        elif self.state == "CHARACTER_SELECT":
            # P1 controls
            if not self.p1_selected:
                if key == pygame.K_a:
                    self.p1_cursor = (self.p1_cursor - 1) % len(c.CHARACTERS)
                elif key == pygame.K_d:
                    self.p1_cursor = (self.p1_cursor + 1) % len(c.CHARACTERS)
                elif key == pygame.K_j:
                    self.p1_selected = True
            
            # P2 controls - always available
            if not self.p2_selected:
                if key == pygame.K_LEFT:
                    self.p2_cursor = (self.p2_cursor - 1) % len(c.CHARACTERS)
                elif key == pygame.K_RIGHT:
                    self.p2_cursor = (self.p2_cursor + 1) % len(c.CHARACTERS)
                elif key == pygame.K_KP1:
                    self.p2_selected = True
                    
        # Game over screen
        elif self.state == "GAME_OVER":
            if key == pygame.K_RETURN:
                # Reset character selection for next game
                self.p1_selected = False
                self.p2_selected = False
                self.p1_cursor = 0
                self.p2_cursor = 0
                self.p2_coin_inserted = True  # Keep 2-player mode enabled
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
        # RESET BUTTON - P1 button (5) quits the game on any joystick
        if button == c.ARCADE_RESET_BUTTON:
            print("Reset button pressed - exiting game")
            joystick.quit()
            pygame.quit()
            sys.exit(0)
        
        # Track button state
        if joystick_id in self.joy_input_state:
            self.joy_input_state[joystick_id]['buttons'].add(button)
        
        # Handle menu/character select navigation
        if self.state == "MAIN_MENU":
            # Light kick acts as back in main menu
            if button == '2':
                self.running = False
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
            # Any button to continue
            if button in ['0', '1', '9']:
                self.p1_selected = False
                self.p2_selected = False
                self.p1_cursor = 0
                self.p2_cursor = 0
                self.p2_coin_inserted = True
                self.state = "MAIN_MENU"
    
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
        # Update tracked state - ALWAYS update to current active movements
        # Empty list means all axes are at neutral
        if joystick_id in self.joy_input_state:
            # Convert results to set - this ensures released axes are removed
            new_axis_state = set(results) if results else set()
            old_axis_state = self.joy_input_state[joystick_id]['axis']
            
            # Update the state
            self.joy_input_state[joystick_id]['axis'] = new_axis_state
            
            # Debug: Log axis state changes
            if new_axis_state != old_axis_state:
                print(f"[Joy {joystick_id}] Axis changed: {old_axis_state} -> {new_axis_state} (results={results})")
        
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
                elif button in ['0', '1']:  # b or a to select
                    self.p1_selected = True
        elif joystick_id == 1:  # Player 2
            if not self.p2_selected:
                if button == 'H3':  # Left
                    self.p2_cursor = (self.p2_cursor - 1) % len(c.CHARACTERS)
                elif button == 'H1':  # Right
                    self.p2_cursor = (self.p2_cursor + 1) % len(c.CHARACTERS)
                elif button in ['0', '1']:  # b or a to select
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
            if button in state['buttons']:
                return True
        
        # Check axis actions (movement)
        if action in axis_map:
            axis, direction = axis_map[action]
            axis_tuple = (axis, direction)
            in_axis_state = axis_tuple in state['axis']
            
            # Debug: log movement checks
            if action in ['left', 'right', 'jump', 'down']:
                if in_axis_state or (self.state == "FIGHT" and action in ['left', 'right']):
                    print(f"[Joy {joystick_id}] Check {action}: axis_tuple={axis_tuple}, in_state={in_axis_state}, state['axis']={state['axis']}")
            
            return in_axis_state
        
        # Check hat/dpad buttons
        for hat_button, hat_action in c.HAT_BUTTONS.items():
            if hat_action == action and hat_button in state['buttons']:
                return True
        
        return False
    
    # ==================== MAIN MENU STATE ====================
    
    def _update_main_menu(self, mouse_pos, mouse_clicked):
        """
        Update main menu logic
        
        Args:
            mouse_pos: Current mouse position tuple (x, y)
            mouse_clicked: Boolean indicating if mouse was clicked
        """
        # Track idle time for attract mode
        keys = pygame.key.get_pressed()
        
        # Check for start keys instead of any(keys) - pygame-ce doesn't support iterating all keys
        # Only check the keys that matter: Space, Enter, Z, X (common arcade buttons)
        start_keys_pressed = (
            keys[pygame.K_SPACE] or 
            keys[pygame.K_RETURN] or 
            keys[pygame.K_z] or 
            keys[pygame.K_x]
        )
        
        any_input = (
            mouse_clicked or 
            start_keys_pressed or 
            any(self.joy_input_state[0]['buttons']) or 
            any(self.joy_input_state[1]['buttons'])
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
                self._activate_menu_button(i)
    
    def _activate_menu_button(self, index):
        """
        Activate menu button by index
        
        Args:
            index: Button index (0=START, 1=CONTROLS, 2=ABOUT)
        """
        if index == 0:  # START
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
        # Draw gradient background for polish
        GradientBackground.draw_vertical(self.screen, (20, 20, 40), (5, 5, 15))
        
        # Title section with background panel
        title = self.text_renderer.render_outlined(self.menu_title, 'large', c.ORANGE, c.BLACK, 3)
        title_x = c.SCREEN_WIDTH // 2 - title.get_width() // 2
        title_y = 80
        
        # Title background panel with enhanced styling
        title_panel = pygame.Rect(title_x - 40, title_y - 20, title.get_width() + 80, title.get_height() + 40)
        draw_panel(self.screen, title_panel, (30, 30, 50), c.ORANGE, 4, shadow=True)
        
        self.screen.blit(title, (title_x, title_y))
        
        # Subtitle with outline for better visibility
        subtitle = self.text_renderer.render_outlined(self.menu_subtitle, 'medium', c.WHITE, c.BLACK, 2)
        subtitle_x = c.SCREEN_WIDTH // 2 - subtitle.get_width() // 2
        self.screen.blit(subtitle, (subtitle_x, 170))
        
        # Draw all menu buttons
        for button in self.menu_buttons:
            button.draw(self.screen, self.text_renderer)
        
        # Decorative line
        pygame.draw.line(self.screen, c.ORANGE, (100, 230), (c.SCREEN_WIDTH - 100, 230), 2)
        pygame.draw.line(self.screen, c.ORANGE, (100, 520), (c.SCREEN_WIDTH - 100, 520), 2)
        
        # Footer text
        footer = self.text_renderer.render("USE ARROW KEYS OR MOUSE  |  JOYSTICK SUPPORTED", 'small', c.GRAY)
        footer_x = c.SCREEN_WIDTH // 2 - footer.get_width() // 2
        self.screen.blit(footer, (footer_x, 545))
        
        # Version info
        version = self.text_renderer.render("v1.0", 'small', c.DARK_GRAY)
        self.screen.blit(version, (c.SCREEN_WIDTH - version.get_width() - 10, c.SCREEN_HEIGHT - 25))
    
    # ==================== CONTROLS SCREEN STATE ====================
    
    def _update_controls(self, mouse_pos, mouse_clicked):
        """Update controls screen logic"""
        self.controls_back_button.update(mouse_pos)
        
        if self.controls_back_button.is_clicked(mouse_pos, mouse_clicked):
            self.state = "MAIN_MENU"
    
    def _draw_controls(self):
        """Render controls screen with keyboard and arcade box controls"""
        # Title
        title = self.text_renderer.render("GAME CONTROLS", 'large', c.ORANGE)
        title_x = c.SCREEN_WIDTH // 2 - title.get_width() // 2
        self.screen.blit(title, (title_x, 30))
        
        # Controls panel
        panel_rect = pygame.Rect(20, 80, c.SCREEN_WIDTH - 40, 400)
        pygame.draw.rect(self.screen, c.BLACK, panel_rect)
        pygame.draw.rect(self.screen, c.ORANGE, panel_rect, 3)
        
        # ===== KEYBOARD CONTROLS =====
        kbd_title = self.text_renderer.render("KEYBOARD", 'medium', c.GREEN)
        self.screen.blit(kbd_title, (40, 90))
        
        # Player 1 keyboard
        y_offset = 115
        p1_title = self.text_renderer.render("P1:", 'small', c.RED)
        self.screen.blit(p1_title, (40, y_offset))
        
        y_offset += 18
        controls_p1 = [
            ("MOVE: W/A/S/D", "PUNCH: J/K"),
            ("KICK: L/I", "SPECIAL: U"),
            ("DASH: LSHIFT", "PARRY: O"),
        ]
        
        for left, right in controls_p1:
            left_surf = self.text_renderer.render(left, 'small', c.WHITE)
            right_surf = self.text_renderer.render(right, 'small', c.WHITE)
            self.screen.blit(left_surf, (40, y_offset))
            self.screen.blit(right_surf, (200, y_offset))
            y_offset += 16
        
        # Player 2 keyboard
        y_offset += 8
        p2_title = self.text_renderer.render("P2:", 'small', c.BLUE)
        self.screen.blit(p2_title, (40, y_offset))
        
        y_offset += 18
        controls_p2 = [
            ("MOVE: ARROWS", "PUNCH: NUM1/2"),
            ("KICK: NUM3/4", "SPECIAL: NUM0"),
            ("DASH: RSHIFT", "PARRY: NUM5"),
        ]
        
        for left, right in controls_p2:
            left_surf = self.text_renderer.render(left, 'small', c.WHITE)
            right_surf = self.text_renderer.render(right, 'small', c.WHITE)
            self.screen.blit(left_surf, (40, y_offset))
            self.screen.blit(right_surf, (200, y_offset))
            y_offset += 16
        
        # ===== ARCADE BOX CONTROLS =====
        arcade_title = self.text_renderer.render("ARCADE BOX", 'medium', c.GREEN)
        self.screen.blit(arcade_title, (420, 90))
        
        y_offset = 115
        arcade_info = [
            ("JOYSTICK: MOVE", ""),
            ("B BUTTON: LIGHT PUNCH", ""),
            ("A BUTTON: HEAVY PUNCH", ""),
            ("X BUTTON: LIGHT KICK", ""),
            ("Y BUTTON: HEAVY KICK", ""),
            ("INSERT: SPECIAL MOVE", ""),
            ("SELECT: DASH", ""),
            ("START: PARRY", ""),
            ("", ""),
            ("P1 BUTTON: EXIT GAME", "(RESET)"),
        ]
        
        for label, note in arcade_info:
            if label:
                label_surf = self.text_renderer.render(label, 'small', c.WHITE)
                self.screen.blit(label_surf, (420, y_offset))
            if note:
                note_surf = self.text_renderer.render(note, 'small', c.RED)
                self.screen.blit(note_surf, (620, y_offset))
            y_offset += 16
        
        # ===== GENERAL INFO =====
        info_y = 340
        pygame.draw.line(self.screen, c.ORANGE, (30, info_y), (c.SCREEN_WIDTH - 30, info_y), 2)
        
        info_y += 10
        info_lines = [
            "BLOCK: HOLD DOWN TO BLOCK ATTACKS",
            "ESC: RETURN TO MENU / EXIT",
            "SUPPORTS PS4/PS5 AND SWITCH CONTROLLERS",
        ]
        
        for line in info_lines:
            info_surf = self.text_renderer.render(line, 'small', c.YELLOW)
            self.screen.blit(info_surf, (40, info_y))
            info_y += 18
        
        # Joystick status
        joy_count = joystick.get_joystick_count()
        status_text = f"JOYSTICKS CONNECTED: {joy_count}"
        status_color = c.GREEN if joy_count > 0 else c.GRAY
        status_surf = self.text_renderer.render(status_text, 'small', status_color)
        self.screen.blit(status_surf, (420, info_y - 18))
        
        # Back button
        self.controls_back_button.draw(self.screen, self.text_renderer)
    
    # ==================== ABOUT SCREEN STATE ====================
    
    def _update_about(self, mouse_pos, mouse_clicked):
        """Update about screen logic"""
        self.about_back_button.update(mouse_pos)
        
        if self.about_back_button.is_clicked(mouse_pos, mouse_clicked):
            self.state = "MAIN_MENU"
    
    def _draw_about(self):
        """Render about screen"""
        # Title
        title = self.text_renderer.render("ABOUT CMUQ ARENA", 'large', c.ORANGE)
        title_x = c.SCREEN_WIDTH // 2 - title.get_width() // 2
        self.screen.blit(title, (title_x, 50))
        
        # Info panel
        panel_rect = pygame.Rect(100, 150, c.SCREEN_WIDTH - 200, 320)
        pygame.draw.rect(self.screen, c.BLACK, panel_rect)
        pygame.draw.rect(self.screen, c.ORANGE, panel_rect, 3)
        
        # Game information
        y_offset = 180
        info_lines = [
            "CMUQ ARENA",
            "ULTIMATE FIGHTING CHAMPIONSHIP",
            "",
            "Made by Game Dev Club with Love",
            "Yousef Hussein - Class of 2029",
            "Version 1.0 - Tarnival 2026"
        ]
        
        for i, line in enumerate(info_lines):
            color = c.ORANGE if i < 2 else c.WHITE
            size = 'medium' if i < 2 else 'small'
            text = self.text_renderer.render(line, size, color)
            text_x = c.SCREEN_WIDTH // 2 - text.get_width() // 2
            self.screen.blit(text, (text_x, y_offset + i * 25))
        
        # Back button
        self.about_back_button.draw(self.screen, self.text_renderer)
    
    # ==================== CHARACTER SELECT STATE ====================
    
    def _update_character_select(self, mouse_pos, mouse_clicked):
        """Update character selection logic"""
        # Check if both players are ready
        if self.p1_selected and self.p2_selected:
            pygame.time.delay(500)
            self._start_fight()
    
    def _draw_character_select(self):
        """Render character selection screen with perfect alignment"""
        # Draw gradient background
        GradientBackground.draw_vertical(self.screen, (30, 15, 40), (10, 5, 20))
        
        # Title with outline
        title = self.text_renderer.render_outlined("CHOOSE YOUR FIGHTER", 'large', c.WHITE, c.BLACK, 3)
        title_x = c.SCREEN_WIDTH // 2 - title.get_width() // 2
        title_bg = pygame.Rect(title_x - 30, 35, title.get_width() + 60, 70)
        draw_panel(self.screen, title_bg, (40, 20, 50), c.ORANGE, 4)
        self.screen.blit(title, (title_x, 50))
        
        # Character grid - perfectly centered
        num_chars = len(c.CHARACTERS)
        box_width = 120
        box_height = 140
        gap = 30
        total_width = num_chars * box_width + (num_chars - 1) * gap
        start_x = (c.SCREEN_WIDTH - total_width) // 2
        start_y = 180
        
        for i, char in enumerate(c.CHARACTERS):
            x = start_x + i * (box_width + gap)
            y = start_y
            
            # Character box with shadow and gradient effect
            char_rect = pygame.Rect(x, y, box_width, box_height)
            draw_panel(self.screen, char_rect, (50, 50, 60), c.WHITE, 3)
            
            # Inner gradient for depth
            inner_rect = pygame.Rect(x + 5, y + 5, box_width - 10, box_height - 10)
            GradientBackground.draw_vertical(self.screen, (60, 60, 70), (30, 30, 40), inner_rect)
            
            # Draw character portrait (head only, centered in box)
            portrait_x = x + box_width // 2
            portrait_y = y + box_height // 2
            char_name = char['name']
            if 'KHALID' in char_name:
                drawing.draw_khalid(self.screen, portrait_x, portrait_y + 30, True, 'idle', 0)
            elif 'EDUARDO' in char_name:
                drawing.draw_eduardo(self.screen, portrait_x, portrait_y + 30, True, 'idle', 0)
            elif 'HASAN' in char_name:
                drawing.draw_hasan(self.screen, portrait_x, portrait_y + 30, True, 'idle', 0)
            elif 'HAMMOUD' in char_name:
                drawing.draw_hammoud(self.screen, portrait_x, portrait_y + 30, True, 'idle', 0)
            
            # Character name - centered with outline
            name = self.text_renderer.render_outlined(char['name'], 'small', c.WHITE, c.BLACK, 1)
            name_x = x + box_width // 2 - name.get_width() // 2
            self.screen.blit(name, (name_x, y + box_height + 8))
            
            # P1 selection indicator
            if i == self.p1_cursor:
                color = c.YELLOW if self.p1_selected else c.RED
                pygame.draw.rect(self.screen, color, char_rect.inflate(10, 10), 5)
                
                p1_label = self.text_renderer.render("P1", 'small', c.RED)
                label_x = x + box_width // 2 - p1_label.get_width() // 2
                self.screen.blit(p1_label, (label_x, y - 30))
                
                if self.p1_selected:
                    ready = self.text_renderer.render("READY!", 'small', c.YELLOW)
                    ready_x = x + box_width // 2 - ready.get_width() // 2
                    self.screen.blit(ready, (ready_x, y + box_height + 60))
            
            # P2 selection indicator
            if i == self.p2_cursor:
                # Calculate offset if P1 and P2 are selecting the same character
                offset = 6 if i == self.p1_cursor else 0
                
                # P2 human player indicator
                color = c.YELLOW if self.p2_selected else c.BLUE
                pygame.draw.rect(self.screen, color, char_rect.inflate(10 + offset * 2, 10 + offset * 2), 5)
                
                p2_label = self.text_renderer.render("P2", 'small', c.BLUE)
                label_x = x + box_width // 2 - p2_label.get_width() // 2
                y_pos = y + box_height + 78 if i == self.p1_cursor else y + box_height + 60
                self.screen.blit(p2_label, (label_x, y_pos))
                
                if self.p2_selected:
                        ready = self.text_renderer.render("READY!", 'small', c.YELLOW)
                        ready_x = x + box_width // 2 - ready.get_width() // 2
                        self.screen.blit(ready, (ready_x, y_pos + 18))
        
        # 2 Player mode indicator not used
        # mode_text = self.text_renderer.render("2 PLAYER MODE", 'medium', c.GREEN)
        # mode_x = c.SCREEN_WIDTH // 2 - mode_text.get_width() // 2
        # self.screen.blit(mode_text, (mode_x, 50))
    
    # ==================== FIGHT STATE ====================
    
    def _start_fight(self):
        """Initialize a new fight with selected characters"""
        # Use control configuration from config
        controls_p1 = c.DEFAULT_P1_CONTROLS
        controls_p2 = c.DEFAULT_P2_CONTROLS
        
        # Create fighters at proper ground positions
        stats_p1 = c.CHARACTERS[self.p1_cursor]
        stats_p2 = c.CHARACTERS[self.p2_cursor]
        
        # Spawn fighters on the ground (FLOOR_Y - P_HEIGHT)
        spawn_y = c.FLOOR_Y - c.P_HEIGHT
        self.p1 = Fighter(200, spawn_y, stats_p1, controls_p1, is_p2=False, 
                         combat_system=self.combat_system, fighter_id="p1",
                         joy_input_getter=self.get_joy_action)
        self.p2 = Fighter(550, spawn_y, stats_p2, controls_p2, is_p2=True, 
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
    
    def _start_attract_mode(self):
        """Start AI vs AI attract mode demo - exciting showcase of gameplay!"""
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
        self.p1 = Fighter(200, spawn_y, stats_p1, controls_p1, is_p2=False,
                         combat_system=self.combat_system, fighter_id="p1",
                         joy_input_getter=self.get_joy_action)
        self.p2 = Fighter(550, spawn_y, stats_p2, controls_p2, is_p2=True,
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
            keys = pygame.key.get_pressed()
            # Check only specific keys for arcade compatibility (pygame-ce doesn't support any(keys))
            start_keys_pressed = (
                keys[pygame.K_SPACE] or 
                keys[pygame.K_RETURN] or 
                keys[pygame.K_z] or 
                keys[pygame.K_x]
            )
            any_input = start_keys_pressed or any(self.joy_input_state[0]['buttons']) or any(self.joy_input_state[1]['buttons'])
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
                    self.state = "GAME_OVER"
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
                self.state = "GAME_OVER"
                self.winner_sequence_active = False
                self.winner_sequence_frame = 0
            return  # Don't update fight during winner sequence
        
        # Update screen shake
        if self.screen_shake > 0:
            self.screen_shake -= 1
            shake_amount = min(self.screen_shake, 5)
            self.screen_shake_offset = (
                random.randint(-shake_amount, shake_amount),
                random.randint(-shake_amount, shake_amount)
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
                    self._spawn_particles(self.p2.rect.centerx, self.p2.rect.centery, c.YELLOW)
                    self.hit_effects.append(HitEffect(self.p2.rect.centerx, self.p2.rect.centery, 'parry', c.YELLOW))
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
                    self._spawn_particles(self.p2.rect.centerx, self.p2.rect.centery, c.ORANGE)
                    self.hit_effects.append(HitEffect(self.p2.rect.centerx, self.p2.rect.centery, 'special', c.ORANGE))
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
                    self._spawn_particles(self.p1.rect.centerx, self.p1.rect.centery, c.YELLOW)
                    self.hit_effects.append(HitEffect(self.p1.rect.centerx, self.p1.rect.centery, 'parry', c.YELLOW))
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
                    self._spawn_particles(self.p1.rect.centerx, self.p1.rect.centery, c.ORANGE)
                    self.hit_effects.append(HitEffect(self.p1.rect.centerx, self.p1.rect.centery, 'special', c.ORANGE))
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
                    self._spawn_particles(target.rect.centerx, target.rect.centery, c.ORANGE)
                    self.hit_effects.append(HitEffect(target.rect.centerx, target.rect.centery, 'heavy', c.ORANGE))
                    self.screen_shake = 10
        
        # Spawn particles on hit
        if self.p1.attacking and self.p1.attack_rect and self.p1.attack_rect.colliderect(self.p2.rect):
            self._spawn_particles(self.p2.rect.centerx, self.p2.rect.centery, c.RED)
            # Add hit effect based on attack type with randomness
            effect_type = 'heavy' if 'heavy' in self.p1.attack_type else 'light'
            # Higher chance for heavy attacks (80%), lower for light (30%)
            chance = 0.8 if effect_type == 'heavy' else 0.3
            if random.random() < chance:
                # Position text higher to avoid blood splash overlap (move up by 40 pixels)
                self.hit_effects.append(HitEffect(self.p2.rect.centerx, self.p2.rect.centery - 40, effect_type, c.RED))
            if effect_type == 'heavy':
                self.screen_shake = 10
        if self.p2.attacking and self.p2.attack_rect and self.p2.attack_rect.colliderect(self.p1.rect):
            self._spawn_particles(self.p1.rect.centerx, self.p1.rect.centery, c.BLUE)
            effect_type = 'heavy' if 'heavy' in self.p2.attack_type else 'light'
            # Higher chance for heavy attacks (80%), lower for light (30%)
            chance = 0.8 if effect_type == 'heavy' else 0.3
            if random.random() < chance:
                # Position text higher to avoid blood splash overlap (move up by 40 pixels)
                self.hit_effects.append(HitEffect(self.p1.rect.centerx, self.p1.rect.centery - 40, effect_type, c.BLUE))
            if effect_type == 'heavy':
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
        
        # Draw brown dirt floor (no perspective grid)
        dirt_floor = pygame.Rect(0 + shake_x, c.FLOOR_Y + shake_y, c.SCREEN_WIDTH, c.SCREEN_HEIGHT - c.FLOOR_Y)
        pygame.draw.rect(self.screen, c.DIRT_BROWN, dirt_floor)
        
        # Add subtle texture with random darker spots (using consistent seed from __init__)
        for _ in range(50):
            spot_x = random.randint(0, c.SCREEN_WIDTH)
            spot_y = random.randint(c.FLOOR_Y, c.SCREEN_HEIGHT)
            spot_size = random.randint(3, 8)
            darker_brown = (int(c.DIRT_BROWN[0] * 0.8), int(c.DIRT_BROWN[1] * 0.8), int(c.DIRT_BROWN[2] * 0.8))
            pygame.draw.circle(self.screen, darker_brown, (spot_x + shake_x, spot_y + shake_y), spot_size)
        
        # Floor line
        pygame.draw.line(self.screen, (100, 60, 25), (0 + shake_x, c.FLOOR_Y + shake_y), 
                        (c.SCREEN_WIDTH + shake_x, c.FLOOR_Y + shake_y), 3)
        
        # Create shaken surface for game objects
        if self.screen_shake > 0:
            # Draw everything to a temporary surface then blit with offset
            game_surface = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT), pygame.SRCALPHA)
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
            result = drawing.draw_victory_beatdown(
                game_surface,
                winner.rect.centerx, winner.rect.bottom,
                loser.rect.centerx, c.FLOOR_Y,
                winner.stats['name'], winner.stats['skin'], winner.stats['color'],
                loser.stats['name'], loser.stats['skin'], loser.stats['color'],
                self.winner_sequence_frame
            )
            
            # Apply screen shake from beatdown hits
            if result.get('screen_shake', 0) > 0:
                self.screen_shake = result['screen_shake']
            
            # Flash effect on impact
            if result.get('flash', False):
                flash_surface = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
                flash_surface.fill(c.WHITE)
                flash_surface.set_alpha(100)
                game_surface.blit(flash_surface, (0, 0))
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
        
        # Blit shaken surface if needed
        if self.screen_shake > 0:
            self.screen.blit(game_surface, (shake_x, shake_y))
        
        # Draw HUD (not affected by shake)
        self._draw_fight_hud()
    
    def _draw_fight_hud(self):
        """Draw vintage arcade-style HUD with segmented health bars"""
        bar_width = 300
        bar_height = 30
        num_segments = 10
        segment_width = (bar_width - (num_segments - 1) * 2) / num_segments  # 2px gap between segments
        
        # P1 health bar (segmented)
        ratio_p1 = max(0, self.p1.health / self.p1.max_health)
        pygame.draw.rect(self.screen, c.BLACK, (18, 18, bar_width + 4, bar_height + 4))
        pygame.draw.rect(self.screen, c.DARK_GRAY, (20, 20, bar_width, bar_height))
        
        # Draw segments
        for i in range(num_segments):
            segment_x = 20 + i * (segment_width + 2)
            segment_health = (i + 1) / num_segments
            
            if ratio_p1 >= segment_health:
                # Full segment
                color = c.RED
            elif ratio_p1 > (i / num_segments):
                # Partial segment
                color = c.RED
            else:
                # Empty segment (already dark gray background)
                continue
            
            # Flash on low health
            if ratio_p1 < 0.3 and pygame.time.get_ticks() % 500 < 250:
                color = c.YELLOW
            
            pygame.draw.rect(self.screen, color, (segment_x, 20, segment_width, bar_height))
        
        pygame.draw.rect(self.screen, c.WHITE, (20, 20, bar_width, bar_height), 3)
        
        # P2 health bar (segmented)
        ratio_p2 = max(0, self.p2.health / self.p2.max_health)
        p2_x = c.SCREEN_WIDTH - 20 - bar_width
        pygame.draw.rect(self.screen, c.BLACK, (p2_x - 2, 18, bar_width + 4, bar_height + 4))
        pygame.draw.rect(self.screen, c.DARK_GRAY, (p2_x, 20, bar_width, bar_height))
        
        # Draw segments
        for i in range(num_segments):
            segment_x = p2_x + i * (segment_width + 2)
            segment_health = (i + 1) / num_segments
            
            if ratio_p2 >= segment_health:
                color = c.BLUE
            elif ratio_p2 > (i / num_segments):
                color = c.BLUE
            else:
                continue
            
            # Flash on low health
            if ratio_p2 < 0.3 and pygame.time.get_ticks() % 500 < 250:
                color = c.YELLOW
            
            pygame.draw.rect(self.screen, color, (segment_x, 20, segment_width, bar_height))
        
        pygame.draw.rect(self.screen, c.WHITE, (p2_x, 20, bar_width, bar_height), 3)
        
        # Player names
        p1_name = self.text_renderer.render(self.p1.stats['name'], 'medium', c.WHITE)
        self.screen.blit(p1_name, (25, 55))
        
        p2_name = self.text_renderer.render(self.p2.stats['name'], 'medium', c.WHITE)
        self.screen.blit(p2_name, (p2_x, 55))
        
        # P1 Special ability power bar
        power_bar_width = 150
        power_bar_height = 15
        current_time = pygame.time.get_ticks()
        time_since_special_p1 = current_time - self.p1.last_special_time
        special_cooldown = 2000  # 2 seconds
        power_ratio_p1 = min(1.0, time_since_special_p1 / special_cooldown)
        
        pygame.draw.rect(self.screen, c.BLACK, (18, 78, power_bar_width + 4, power_bar_height + 4))
        pygame.draw.rect(self.screen, c.DARK_GRAY, (20, 80, power_bar_width, power_bar_height))
        if power_ratio_p1 > 0:
            filled_width = int(power_bar_width * power_ratio_p1)
            color = c.YELLOW if power_ratio_p1 >= 1.0 else c.ORANGE
            pygame.draw.rect(self.screen, color, (20, 80, filled_width, power_bar_height))
        pygame.draw.rect(self.screen, c.WHITE, (20, 80, power_bar_width, power_bar_height), 2)
        
        # P2 Special ability power bar
        time_since_special_p2 = current_time - self.p2.last_special_time
        power_ratio_p2 = min(1.0, time_since_special_p2 / special_cooldown)
        
        p2_power_x = c.SCREEN_WIDTH - 20 - power_bar_width
        pygame.draw.rect(self.screen, c.BLACK, (p2_power_x - 2, 78, power_bar_width + 4, power_bar_height + 4))
        pygame.draw.rect(self.screen, c.DARK_GRAY, (p2_power_x, 80, power_bar_width, power_bar_height))
        if power_ratio_p2 > 0:
            filled_width = int(power_bar_width * power_ratio_p2)
            color = c.YELLOW if power_ratio_p2 >= 1.0 else c.ORANGE
            pygame.draw.rect(self.screen, color, (p2_power_x, 80, filled_width, power_bar_height))
        pygame.draw.rect(self.screen, c.WHITE, (p2_power_x, 80, power_bar_width, power_bar_height), 2)
        
        # Timer
        t_color = c.WHITE if self.round_timer > 10 else c.RED
        timer = self.text_renderer.render(str(self.round_timer), 'large', t_color)
        timer_x = c.SCREEN_WIDTH // 2 - timer.get_width() // 2
        timer_bg = pygame.Rect(timer_x - 15, 8, timer.get_width() + 30, timer.get_height() + 10)
        pygame.draw.rect(self.screen, c.BLACK, timer_bg)
        pygame.draw.rect(self.screen, c.ORANGE, timer_bg, 3)
        self.screen.blit(timer, (timer_x, 10))
        
        # Draw combo counters
        self._draw_combo_display()
        
        # Draw round wins indicators
        self._draw_round_wins()
        
        # Draw super meter bars
        self._draw_super_meters()
        
        # FIGHT! text at start or round number
        if self.round_timer > 96:
            # Show round number first, then FIGHT!
            if self.round_timer > 97:
                round_text = self.text_renderer.render_outlined(f"ROUND {self.current_round}", 'large', c.WHITE, c.BLACK, 3)
                round_x = c.SCREEN_WIDTH // 2 - round_text.get_width() // 2
                round_bg = pygame.Rect(round_x - 20, c.SCREEN_HEIGHT // 2 - 50, 
                                      round_text.get_width() + 40, 90)
                pygame.draw.rect(self.screen, c.BLACK, round_bg)
                pygame.draw.rect(self.screen, c.ORANGE, round_bg, 5)
                self.screen.blit(round_text, (round_x, c.SCREEN_HEIGHT // 2 - 30))
            else:
                fight_text = self.text_renderer.render_outlined("FIGHT!", 'large', c.YELLOW, c.BLACK, 3)
                fight_x = c.SCREEN_WIDTH // 2 - fight_text.get_width() // 2
                fight_bg = pygame.Rect(fight_x - 20, c.SCREEN_HEIGHT // 2 - 50, 
                                      fight_text.get_width() + 40, 90)
                pygame.draw.rect(self.screen, c.BLACK, fight_bg)
                pygame.draw.rect(self.screen, c.ORANGE, fight_bg, 5)
                self.screen.blit(fight_text, (fight_x, c.SCREEN_HEIGHT // 2 - 30))
        
        # Draw round over transition
        if self.round_over:
            self._draw_round_transition()
        
        # Draw attract mode banner
        if self.attract_mode:
            banner = self.text_renderer.render_outlined("DEMO - PRESS ANY BUTTON TO PLAY", 'medium', c.YELLOW, c.BLACK, 2)
            banner_x = c.SCREEN_WIDTH // 2 - banner.get_width() // 2
            # Pulsing effect
            pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500.0
            alpha = int(128 + 127 * pulse)
            banner.set_alpha(alpha)
            self.screen.blit(banner, (banner_x, c.SCREEN_HEIGHT - 50))
    
    def _draw_round_wins(self):
        """Draw round win indicators (circles/gems)"""
        gem_radius = 8
        gem_y = 58
        
        # P1 wins (left side)
        for i in range(c.WINS_REQUIRED):
            gem_x = 180 + i * 25
            if i < self.p1_wins:
                # Won round - filled yellow
                pygame.draw.circle(self.screen, c.YELLOW, (gem_x, gem_y), gem_radius)
            else:
                # Not won yet - empty
                pygame.draw.circle(self.screen, c.DARK_GRAY, (gem_x, gem_y), gem_radius)
            pygame.draw.circle(self.screen, c.WHITE, (gem_x, gem_y), gem_radius, 2)
        
        # P2 wins (right side)
        p2_start_x = c.SCREEN_WIDTH - 180 - (c.WINS_REQUIRED - 1) * 25
        for i in range(c.WINS_REQUIRED):
            gem_x = p2_start_x + i * 25
            if i < self.p2_wins:
                # Won round - filled yellow
                pygame.draw.circle(self.screen, c.YELLOW, (gem_x, gem_y), gem_radius)
            else:
                # Not won yet - empty
                pygame.draw.circle(self.screen, c.DARK_GRAY, (gem_x, gem_y), gem_radius)
            pygame.draw.circle(self.screen, c.WHITE, (gem_x, gem_y), gem_radius, 2)
    
    def _draw_super_meters(self):
        """Draw super meter bars at bottom of screen"""
        meter_width = 250
        meter_height = 20
        meter_y = c.SCREEN_HEIGHT - 40
        
        # P1 super meter (bottom left)
        p1_meter = getattr(self.p1, 'super_meter', 0)
        p1_ratio = min(1.0, p1_meter / c.SUPER_METER_MAX)
        
        pygame.draw.rect(self.screen, c.BLACK, (18, meter_y - 2, meter_width + 4, meter_height + 4))
        pygame.draw.rect(self.screen, c.DARK_GRAY, (20, meter_y, meter_width, meter_height))
        
        if p1_ratio > 0:
            # Gradient color from blue to yellow when full
            if p1_ratio >= 1.0:
                color = c.YELLOW
                # Pulsing effect when full
                pulse = abs((pygame.time.get_ticks() % 500) - 250) / 250.0
                color = (int(255 * pulse), int(255 * pulse), 0)
            else:
                color = c.PURPLE
            pygame.draw.rect(self.screen, color, (20, meter_y, int(meter_width * p1_ratio), meter_height))
        
        pygame.draw.rect(self.screen, c.WHITE, (20, meter_y, meter_width, meter_height), 2)
        
        # Super label
        super_label = self.text_renderer.render("SUPER", 'small', c.WHITE)
        self.screen.blit(super_label, (22, meter_y - 15))
        
        # P2 super meter (bottom right)
        p2_meter = getattr(self.p2, 'super_meter', 0)
        p2_ratio = min(1.0, p2_meter / c.SUPER_METER_MAX)
        p2_x = c.SCREEN_WIDTH - 20 - meter_width
        
        pygame.draw.rect(self.screen, c.BLACK, (p2_x - 2, meter_y - 2, meter_width + 4, meter_height + 4))
        pygame.draw.rect(self.screen, c.DARK_GRAY, (p2_x, meter_y, meter_width, meter_height))
        
        if p2_ratio > 0:
            if p2_ratio >= 1.0:
                pulse = abs((pygame.time.get_ticks() % 500) - 250) / 250.0
                color = (int(255 * pulse), int(255 * pulse), 0)
            else:
                color = c.PURPLE
            pygame.draw.rect(self.screen, color, (p2_x, meter_y, int(meter_width * p2_ratio), meter_height))
        
        pygame.draw.rect(self.screen, c.WHITE, (p2_x, meter_y, meter_width, meter_height), 2)
        
        super_label2 = self.text_renderer.render("SUPER", 'small', c.WHITE)
        self.screen.blit(super_label2, (p2_x + 2, meter_y - 15))
    
    def _draw_round_transition(self):
        """Draw round over transition screen"""
        # Semi-transparent overlay
        overlay = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # K.O. text
        if self.round_transition_timer < 60:
            ko_text = self.text_renderer.render_outlined("K.O.!", 'large', c.RED, c.BLACK, 4)
            ko_x = c.SCREEN_WIDTH // 2 - ko_text.get_width() // 2
            self.screen.blit(ko_text, (ko_x, c.SCREEN_HEIGHT // 2 - 60))
        
        # Round winner text
        if self.round_transition_timer >= 60:
            if self.round_winner == "p1":
                winner_text = f"{self.p1.stats['name']} WINS ROUND {self.current_round}!"
                color = c.RED
            elif self.round_winner == "p2":
                winner_text = f"{self.p2.stats['name']} WINS ROUND {self.current_round}!"
                color = c.BLUE
            else:
                winner_text = "DOUBLE K.O!"
                color = c.YELLOW
            
            text_surf = self.text_renderer.render_outlined(winner_text, 'medium', color, c.BLACK, 3)
            text_x = c.SCREEN_WIDTH // 2 - text_surf.get_width() // 2
            self.screen.blit(text_surf, (text_x, c.SCREEN_HEIGHT // 2 - 20))
            
            # Show win counts
            wins_text = f"P1: {self.p1_wins}  -  P2: {self.p2_wins}"
            wins_surf = self.text_renderer.render(wins_text, 'medium', c.WHITE)
            wins_x = c.SCREEN_WIDTH // 2 - wins_surf.get_width() // 2
            self.screen.blit(wins_surf, (wins_x, c.SCREEN_HEIGHT // 2 + 40))
    
    def _draw_combo_display(self):
        """Draw combo counter and announcements"""
        current_time = pygame.time.get_ticks()
        
        # Update combat system to check for dropped combos
        self.combat_system.update(current_time)
        
        # Draw P1 combo counter
        p1_combo = self.combat_system.get_combo_count("p1")
        if p1_combo >= 2:
            combo_text = self.text_renderer.render_outlined(f"{p1_combo} HITS", 'medium', c.YELLOW, c.BLACK, 2)
            self.screen.blit(combo_text, (20, 110))
        
        # Draw P2 combo counter
        p2_combo = self.combat_system.get_combo_count("p2")
        if p2_combo >= 2:
            combo_text = self.text_renderer.render_outlined(f"{p2_combo} HITS", 'medium', c.YELLOW, c.BLACK, 2)
            self.screen.blit(combo_text, (c.SCREEN_WIDTH - combo_text.get_width() - 20, 110))
        
        # Draw counter attack indicator (flashing "COUNTER!" text)
        if self.counter_attack_window['p1'] > 0:
            flash = (pygame.time.get_ticks() // 100) % 2 == 0
            if flash:
                counter_text = self.text_renderer.render_outlined("COUNTER!", 'small', c.GREEN, c.BLACK, 1)
                self.screen.blit(counter_text, (20, 140))
        
        if self.counter_attack_window['p2'] > 0:
            flash = (pygame.time.get_ticks() // 100) % 2 == 0
            if flash:
                counter_text = self.text_renderer.render_outlined("COUNTER!", 'small', c.GREEN, c.BLACK, 1)
                self.screen.blit(counter_text, (c.SCREEN_WIDTH - counter_text.get_width() - 20, 140))
        
        # Draw combo announcements
        announcements = self.combat_system.get_announcements()
        for announcement in announcements:
            age = current_time - announcement['time']
            if age < 2000:  # Show for 2 seconds
                # Calculate animation
                alpha = int(255 * (1 - age / 2000))
                scale = 1.0 + (age / 2000) * 0.3  # Grow slightly over time
                y_offset = int(age / 50)  # Float upward
                
                text = announcement['text']
                is_p1 = announcement['fighter_id'] == "p1"
                color = c.RED if is_p1 else c.BLUE
                
                # Render announcement text
                ann_text = self.text_renderer.render_outlined(text, 'medium', color, c.BLACK, 2)
                
                # Position based on which player
                if is_p1:
                    x = 100
                else:
                    x = c.SCREEN_WIDTH - ann_text.get_width() - 100
                
                y = 200 - y_offset
                
                # Apply fade
                ann_text.set_alpha(alpha)
                self.screen.blit(ann_text, (x, y))
    
    # ==================== GAME OVER STATE ====================
    
    def _update_game_over(self, mouse_pos, mouse_clicked):
        """Update game over logic"""
        pass
    
    def _draw_game_over(self):
        """Render game over screen with enhanced styling"""
        # Draw faded fight background
        self._draw_fight()
        
        # Dark overlay with gradient effect
        overlay = pygame.Surface((c.SCREEN_WIDTH, c.SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((10, 10, 20))
        self.screen.blit(overlay, (0, 0))
        
        # Determine winner
        if self.p1.health > self.p2.health:
            winner_text = f"{self.p1.stats['name']} WINS!"
            color = c.RED
        elif self.p2.health > self.p1.health:
            winner_text = f"{self.p2.stats['name']} WINS!"
            color = c.BLUE
        else:
            winner_text = "DOUBLE K.O!"
            color = c.YELLOW
        
        # Winner announcement with outlined text
        winner = self.text_renderer.render_outlined(winner_text, 'large', color, c.BLACK, 4)
        winner_x = c.SCREEN_WIDTH // 2 - winner.get_width() // 2
        winner_bg = pygame.Rect(winner_x - 30, 150, winner.get_width() + 60, 90)
        draw_panel(self.screen, winner_bg, (20, 20, 30), color, 5)
        self.screen.blit(winner, (winner_x, 170))
        
        # Subtitle with outline
        subtitle = self.text_renderer.render_outlined("GAME OVER", 'medium', c.WHITE, c.BLACK, 2)
        subtitle_x = c.SCREEN_WIDTH // 2 - subtitle.get_width() // 2
        self.screen.blit(subtitle, (subtitle_x, 280))
        
        # Stats display
        stats_y = 330
        p1_stats = self.text_renderer.render(f"P1: {int(max(0, self.p1.health))} HP", 'small', c.RED)
        p2_stats = self.text_renderer.render(f"P2: {int(max(0, self.p2.health))} HP", 'small', c.BLUE)
        self.screen.blit(p1_stats, (c.SCREEN_WIDTH // 2 - 100, stats_y))
        self.screen.blit(p2_stats, (c.SCREEN_WIDTH // 2 + 30, stats_y))
        
        # Restart prompt (pulsing effect)
        pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500.0
        alpha = int(128 + 127 * pulse)
        prompt = self.text_renderer.render_outlined("PRESS ENTER TO CONTINUE", 'medium', c.YELLOW, c.BLACK, 2)
        prompt.set_alpha(alpha)
        prompt_x = c.SCREEN_WIDTH // 2 - prompt.get_width() // 2
        self.screen.blit(prompt, (prompt_x, 400))
        
        # ESC to exit hint
        esc_hint = self.text_renderer.render("ESC to return to menu", 'small', c.GRAY)
        esc_x = c.SCREEN_WIDTH // 2 - esc_hint.get_width() // 2
        self.screen.blit(esc_hint, (esc_x, 450))
    
    # ==================== HELPER METHODS ====================
    
    def _spawn_particles(self, x, y, color):
        """Spawn particle effects at position"""
        for _ in range(5):
            vx = random.uniform(-5, 5)
            vy = random.uniform(-5, -2)
            self.particles.append(Particle(x, y, color, (vx, vy)))
    
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
            vx = random.uniform(-3, 3)
            vy = random.uniform(-1, -0.5)
            color = (139, 90, 43)  # Dirt brown
            self.particles.append(Particle(x, y, color, (vx, vy)))
