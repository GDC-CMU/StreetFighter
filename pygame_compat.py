"""
Pygame compatibility layer for CMU Arcade Box (FIXED)

This module safely loads the real pygame by verifying the loaded module
actually supports init() and display. If a shim is found, it identifies
where it came from, removes ONLY that specific path, and reloads.
"""
import sys
import os
import importlib

def _debug_log(msg):
    print(f"[pygame_compat] {msg}")

def load_robust_pygame():
    _debug_log(f"--- STARTING ROBUST IMPORT ---")
    _debug_log(f"CWD: {os.getcwd()}")
    
    # 1. ATTEMPT INITIAL IMPORT
    # We do NOT scrub sys.path yet. We trust the venv first.
    try:
        import pygame
    except ImportError:
        pygame = None

    # 2. VERIFY THE LOADED MODULE
    # The real pygame must have 'init' and 'display'
    is_valid = pygame and hasattr(pygame, 'init') and hasattr(pygame, 'display')

    if is_valid:
        _debug_log(f"SUCCESS: Initial import looked good.")
        _debug_log(f"File: {getattr(pygame, '__file__', 'unknown')}")
        return pygame

    # 3. PURGE THE IMPOSTER
    if pygame:
        _debug_log(f"WARNING: Loaded module is an IMPOSTER (missing init/display).")
        
        # Identify the enemy
        bad_file = getattr(pygame, '__file__', '')
        if bad_file:
            _debug_log(f"Imposter location: {bad_file}")
            # The bad path is the directory containing the bad package
            # e.g. if file is /opt/cmu/lib/pygame/__init__.py, bad path is /opt/cmu/lib
            bad_dir = os.path.dirname(os.path.dirname(bad_file)) if '__init__' in bad_file else os.path.dirname(bad_file)
            
            _debug_log(f"Attempting to remove path from sys.path: {bad_dir}")
            
            # Remove from sys.path
            sys.path = [p for p in sys.path if os.path.abspath(p) != os.path.abspath(bad_dir)]
        else:
            _debug_log("Imposter has no __file__ attribute. Cannot trace path.")

        # Remove from sys.modules
        if 'pygame' in sys.modules:
            del sys.modules['pygame']
            _debug_log("Deleted 'pygame' from sys.modules")
            
        # Also clean up any cmu_graphics modules that might be holding onto references
        for mod in list(sys.modules.keys()):
            if 'cmu_graphics' in mod:
                del sys.modules[mod]

    # 4. FORCE RE-IMPORT
    try:
        import pygame
        _debug_log(f"Re-import result: {pygame}")
        _debug_log(f"File: {getattr(pygame, '__file__', 'unknown')}")
        
        if hasattr(pygame, 'init'):
            _debug_log("SUCCESS: Re-imported pygame works!")
            return pygame
        else:
            raise ImportError("Re-imported pygame is still broken/missing init.")
            
    except ImportError as e:
        _debug_log(f"FATAL: Could not import pygame after purge. Error: {e}")
        # Debug helper: print where we are looking now
        _debug_log("Current sys.path:")
        for p in sys.path:
            _debug_log(f"  {p}")
        raise e

# ==========================================
# EXECUTE LOAD
# ==========================================
try:
    pygame = load_robust_pygame()
    pygame.init()
    _debug_log("pygame.init() called successfully")
except Exception as e:
    _debug_log(f"CRITICAL FAILURE: {e}")
    sys.exit(1)

# ==========================================
# CONSTANT INJECTION (Keep this!)
# ==========================================
# Standard SDL key values (fallback)
_KEY_CONSTANTS = {
    'K_a': 97, 'K_b': 98, 'K_c': 99, 'K_d': 100, 'K_e': 101,
    'K_f': 102, 'K_g': 103, 'K_h': 104, 'K_i': 105, 'K_j': 106,
    'K_k': 107, 'K_l': 108, 'K_m': 109, 'K_n': 110, 'K_o': 111,
    'K_p': 112, 'K_q': 113, 'K_r': 114, 'K_s': 115, 'K_t': 116,
    'K_u': 117, 'K_v': 118, 'K_w': 119, 'K_x': 120, 'K_y': 121,
    'K_z': 122,
    'K_UP': 1073741906, 'K_DOWN': 1073741905,
    'K_LEFT': 1073741904, 'K_RIGHT': 1073741903,
    'K_LSHIFT': 1073742049, 'K_RSHIFT': 1073742053,
    'K_LCTRL': 1073742048, 'K_RCTRL': 1073742052,
    'K_LALT': 1073742050, 'K_RALT': 1073742054,
    'K_SPACE': 32, 'K_RETURN': 13, 'K_ESCAPE': 27,
    'K_BACKSPACE': 8, 'K_TAB': 9, 'K_DELETE': 127,
    'K_0': 48, 'K_1': 49, 'K_2': 50, 'K_3': 51, 'K_4': 52,
    'K_5': 53, 'K_6': 54, 'K_7': 55, 'K_8': 56, 'K_9': 57,
}

for key_name, key_value in _KEY_CONSTANTS.items():
    if not hasattr(pygame, key_name):
        setattr(pygame, key_name, key_value)