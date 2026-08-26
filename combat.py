"""
Combat system for Professor Fighting Game
Handles frame data, combos, and attack mechanics
"""

from pygame_compat import pygame
import config as c


class CombatSystem:
    """Manages combat mechanics including combos and frame data"""
    
    def __init__(self):
        self.combo_hits = {}  # Track combo hits per fighter
        self.combo_damage = {}  # Track total combo damage
        self.combo_timer = {}  # Track time since last hit for combo drops
        self.last_hit_time = {}  # When the last hit landed
        self.attack_history = {}  # Track attack history for combo strings
        self.active_combo_string = {}  # Currently executing combo string
        self.combo_announcements = []  # Combo announcements to display
        
    def register_fighter(self, fighter_id):
        """Register a fighter for combo tracking"""
        self.combo_hits[fighter_id] = 0
        self.combo_damage[fighter_id] = 0
        self.combo_timer[fighter_id] = 0
        self.last_hit_time[fighter_id] = 0
        self.attack_history[fighter_id] = []
        self.active_combo_string[fighter_id] = None
        
    def reset_combo(self, fighter_id):
        """Reset combo counter for a fighter"""
        # If we had a combo going, announce it dropping
        if self.combo_hits.get(fighter_id, 0) >= 3:
            self._announce_combo_drop(fighter_id)
        
        self.combo_hits[fighter_id] = 0
        self.combo_damage[fighter_id] = 0
        self.combo_timer[fighter_id] = 0
        
    def record_hit(self, attacker_id, damage, attack_type):
        """
        Record a successful hit for combo tracking.
        
        Args:
            attacker_id: ID of the fighter who landed the hit
            damage: Damage dealt
            attack_type: Type of attack that hit
            
        Returns:
            Dict with combo info including multiplier and announcement
        """
        current_time = pygame.time.get_ticks()
        
        # Add to attack history
        if attacker_id in self.attack_history:
            self.attack_history[attacker_id].append(attack_type)
            # Keep only last 10 attacks
            if len(self.attack_history[attacker_id]) > 10:
                self.attack_history[attacker_id].pop(0)
        
        # Check if this extends an existing combo (within combo window)
        combo_window = 1500  # 1.5 seconds to continue combo
        time_since_last = current_time - self.last_hit_time.get(attacker_id, 0)
        
        if time_since_last > combo_window:
            # Combo dropped, start fresh
            self.combo_hits[attacker_id] = 0
            self.combo_damage[attacker_id] = 0
        
        # Increment combo
        self.combo_hits[attacker_id] = self.combo_hits.get(attacker_id, 0) + 1
        self.combo_damage[attacker_id] = self.combo_damage.get(attacker_id, 0) + damage
        self.last_hit_time[attacker_id] = current_time
        
        hits = self.combo_hits[attacker_id]
        
        # Get damage multiplier
        multiplier = self.get_combo_damage_multiplier(attacker_id)
        
        # Check for combo string matches
        combo_string = self._check_combo_strings(attacker_id)
        
        # Generate announcement for big combos
        announcement = None
        if hits == 3:
            announcement = "COMBO!"
        elif hits == 5:
            announcement = "AMAZING COMBO!"
        elif hits >= 7:
            announcement = "LEGENDARY!"
        
        if combo_string:
            announcement = combo_string['name']
        
        if announcement:
            self.combo_announcements.append({
                'text': announcement,
                'fighter_id': attacker_id,
                'time': current_time,
                'hits': hits
            })
        
        return {
            'hits': hits,
            'total_damage': self.combo_damage[attacker_id],
            'multiplier': multiplier,
            'announcement': announcement,
            'combo_string': combo_string
        }
    
    def _check_combo_strings(self, fighter_id):
        """Check if attack history matches any defined combo strings"""
        history = self.attack_history.get(fighter_id, [])
        if len(history) < 2:
            return None
        
        # Check against all combo strings
        for char_name, combos in COMBO_STRINGS.items():
            for combo_name, combo_data in combos.items():
                inputs = combo_data['inputs']
                if len(history) >= len(inputs):
                    if history[-len(inputs):] == inputs:
                        return combo_data
        
        return None
    
    def _announce_combo_drop(self, fighter_id):
        """Announce when a combo drops"""
        hits = self.combo_hits.get(fighter_id, 0)
        if hits >= 3:
            self.combo_announcements.append({
                'text': f"{hits} HIT COMBO!",
                'fighter_id': fighter_id,
                'time': pygame.time.get_ticks(),
                'hits': hits,
                'is_final': True
            })
    
    def update(self, current_time):
        """Update combo system - check for dropped combos"""
        combo_window = 1500  # 1.5 seconds
        
        for fighter_id in list(self.combo_hits.keys()):
            last_hit = self.last_hit_time.get(fighter_id, 0)
            if current_time - last_hit > combo_window and self.combo_hits[fighter_id] > 0:
                self._announce_combo_drop(fighter_id)
                self.combo_hits[fighter_id] = 0
                self.combo_damage[fighter_id] = 0
        
        # Clean up old announcements
        self.combo_announcements = [
            a for a in self.combo_announcements 
            if current_time - a['time'] < 2000  # Show for 2 seconds
        ]
    
    def get_announcements(self):
        """Get current combo announcements for display"""
        return self.combo_announcements
    
    def increment_combo(self, fighter_id):
        """Increment combo counter (legacy support)"""
        self.combo_hits[fighter_id] = self.combo_hits.get(fighter_id, 0) + 1
        
        # Auto-break combo after max hits
        if self.combo_hits[fighter_id] > c.MAX_COMBO_HITS:
            self.reset_combo(fighter_id)
            return False  # Combo broken
        return True  # Combo continues
    
    def get_combo_damage_multiplier(self, fighter_id):
        """Get damage multiplier based on current combo count"""
        hits = self.combo_hits.get(fighter_id, 0)
        return c.COMBO_DAMAGE_SCALING.get(hits, 1.0)
    
    def get_combo_count(self, fighter_id):
        """Get current combo count"""
        return self.combo_hits.get(fighter_id, 0)


class AttackBuffer:
    """
    Input buffering system for smooth attack canceling
    Allows queuing next attack during current attack
    """
    
    def __init__(self, buffer_window=5):
        """
        Initialize attack buffer
        
        Args:
            buffer_window: Number of frames to buffer input
        """
        self.buffer_window = buffer_window
        self.buffered_attacks = {}
        
    def buffer_attack(self, fighter_id, attack_type, timestamp):
        """Buffer an attack input"""
        self.buffered_attacks[fighter_id] = {
            'type': attack_type,
            'timestamp': timestamp
        }
        
    def get_buffered_attack(self, fighter_id, current_time):
        """Get buffered attack if within window"""
        if fighter_id not in self.buffered_attacks:
            return None
            
        buffered = self.buffered_attacks[fighter_id]
        time_diff = current_time - buffered['timestamp']
        
        # Check if within buffer window (convert frames to ms at 60fps)
        if time_diff <= (self.buffer_window * 1000 / 60):
            # Clear buffer and return attack
            attack_type = buffered['type']
            del self.buffered_attacks[fighter_id]
            return attack_type
            
        # Buffer expired
        if time_diff > (self.buffer_window * 1000 / 60):
            del self.buffered_attacks[fighter_id]
        
        return None
    
    def clear_buffer(self, fighter_id):
        """Clear buffered attack"""
        if fighter_id in self.buffered_attacks:
            del self.buffered_attacks[fighter_id]


class FrameData:
    """
    Manages attack frame data and recovery
    Determines when a fighter can move based on attack state
    """
    
    @staticmethod
    def can_move_during_attack(attack_type, frames_elapsed):
        """
        Determine if fighter can move during attack
        
        Args:
            attack_type: Type of attack being performed
            frames_elapsed: Frames since attack started
            
        Returns:
            True if fighter can move, False otherwise
        """
        if attack_type not in c.FRAME_DATA:
            return True
        
        data = c.FRAME_DATA[attack_type]
        
        # For arcade machines, allow movement during startup frames even for heavy attacks
        # This makes simultaneous input feel more responsive
        startup_frames = data['startup']
        if frames_elapsed < startup_frames:
            return True  # Always allow movement during startup
        
        # Light attacks can move after active frames
        if data.get('can_move_early', False):
            active_end = startup_frames + data['active']
            return frames_elapsed >= active_end
        
        # Heavy attacks: allow movement after active frames
        # (was: require full recovery, now: allow after active)
        active_end = startup_frames + data['active']
        return frames_elapsed >= active_end
    
    @staticmethod
    def get_attack_duration(attack_type):
        """Get total duration of attack in frames"""
        if attack_type not in c.FRAME_DATA:
            return 10  # Default
        return c.FRAME_DATA[attack_type]['total']
    
    @staticmethod
    def is_in_active_frames(attack_type, frames_elapsed):
        """Check if attack is in active (hitting) frames"""
        if attack_type not in c.FRAME_DATA:
            return False
        
        data = c.FRAME_DATA[attack_type]
        startup = data['startup']
        active_end = startup + data['active']
        
        return startup <= frames_elapsed < active_end


class SpecialMoveData:
    """Data for special moves"""
    
    # Khalid's Spinning Kick
    SPINNING_KICK = {
        'name': 'Spinning Kick',
        'damage_per_hit': 8,
        'num_hits': 3,
        'forward_movement': 150,  # pixels
        'rotations': 3,
        'cooldown': 2000,
        'duration': 60  # frames
    }
    
    # Eduardo's Pizza Throw
    PIZZA_THROW = {
        'name': 'Pizza Throw',
        'damage_per_slice': 6,
        'num_slices': 3,
        'speed': 5,  # pixels per frame
        'cooldown': 2000,
        'slice_delay': 5  # frames between slices
    }
    
    # Hasan's Fireball
    FIREBALL = {
        'name': 'Fireball',
        'damage': 15,
        'speed': 8,  # pixels per frame
        'amplitude': 30,  # sine wave amplitude
        'wavelength': 50,  # sine wave wavelength
        'cooldown': 2000
    }
    
    # Hammoud's Circuit Board
    CIRCUIT_BOARD = {
        'name': 'Circuit Board',
        'damage': 20,
        'speed': 4,  # pixels per frame
        'homing_strength': 0.05,  # radians per frame
        'cooldown': 2000
    }


def calculate_knockback_velocity(attacker_facing_right, knockback_strength):
    """
    Calculate knockback velocity vector
    
    Args:
        attacker_facing_right: Direction attacker is facing
        knockback_strength: Base knockback strength
        
    Returns:
        (vel_x, vel_y) velocity tuple
    """
    direction = 1 if attacker_facing_right else -1
    vel_x = knockback_strength * direction * 2
    vel_y = -5  # Slight upward knock
    
    return vel_x, vel_y


def check_combo_string(attack_history, combo_string):
    """
    Check if attack history matches a combo string
    
    Args:
        attack_history: List of recent attacks
        combo_string: List of attacks that form combo
        
    Returns:
        True if combo matches, False otherwise
    """
    if len(attack_history) < len(combo_string):
        return False
    
    # Check last N attacks match combo
    recent = attack_history[-len(combo_string):]
    return recent == combo_string


# Character-specific combo definitions
# NOTE: These combo strings are defined for future enhancement
# They can be implemented to provide bonus damage when specific attack sequences are performed
COMBO_STRINGS = {
    'PROF. KHALID': {
        'tornado_kick': {
            'inputs': ['light_kick', 'light_kick', 'heavy_kick'],
            'bonus_damage': 0.3,
            'name': 'TORNADO KICK'
        },
        'flying_axe': {
            'inputs': ['jump', 'heavy_kick'],
            'bonus_damage': 0.3,
            'name': 'FLYING AXE KICK'
        }
    },
    'PROF. EDUARDO': {
        'pizza_barrage': {
            'inputs': ['light_punch', 'light_punch', 'special'],
            'bonus_damage': 0.3,
            'name': 'PIZZA BARRAGE'
        },
        'mega_slice': {
            'inputs': ['heavy_punch', 'special'],
            'bonus_damage': 0.3,
            'name': 'MEGA SLICE'
        }
    },
    'PROF. HASAN': {
        'flame_uppercut': {
            'inputs': ['light_kick', 'heavy_punch', 'special'],
            'bonus_damage': 0.3,
            'name': 'FLAME UPPERCUT'
        }
    },
    'PROF. HAMMOUD': {
        'binary_rush': {
            'inputs': ['light_punch', 'light_punch', 'light_kick', 'heavy_kick'],
            'bonus_damage': 0.3,
            'name': 'BINARY RUSH'
        }
    }
}
