"""
Joystick/Controller Support for Arcade Box and Gamepads

This module provides joystick and gamepad support for the CMUQ Arena game.
Adapted from the CMU arcade-box-startercode but modified to work with pure pygame
instead of cmu_graphics.

Supports:
- CMU Arcade Box joysticks
- PS4/PS5 controllers
- Nintendo Switch controllers
- Generic USB gamepads

Key-Map for Arcade Machine:
| Key          | Button |
|--------------|--------|
| b            | 0      |
| a            | 1      |
| x            | 2      |
| y            | 3      |
| Insert money | 4      |
| p1 (RESET)   | 5      |
| Select       | 8      |
| Start        | 9      |
"""

from pygame_compat import pygame
import sys

# Store state for all connected joysticks
_joysticks = {}
_all_buttons_down = {}  # Track which buttons are held for each joystick
_all_axis_down = {}     # Track digital axis state for each joystick
_last_joy_axis = {}     # Track last axis values for detecting changes

# Callback functions that users can override
_on_joy_press_callback = None
_on_joy_release_callback = None
_on_joy_button_hold_callback = None
_on_digital_joy_axis_callback = None
_on_joy_axis_callback = None


def init():
    """Initialize the joystick subsystem. Call this after pygame.init()"""
    # Use try/except for arcade box compatibility (some pygame builds lack get_init)
    try:
        if hasattr(pygame.joystick, 'get_init'):
            if not pygame.joystick.get_init():
                pygame.joystick.init()
        else:
            # Arcade box pygame - just call init
            pygame.joystick.init()
    except Exception:
        try:
            pygame.joystick.init()
        except Exception:
            pass  # Already initialized or not available
    
    # Initialize all connected joysticks
    for i in range(pygame.joystick.get_count()):
        joy = pygame.joystick.Joystick(i)
        joy.init()
        _joysticks[joy.get_instance_id()] = joy
        _all_buttons_down[joy.get_instance_id()] = set()
        _all_axis_down[joy.get_instance_id()] = set()
        print(f"Joystick connected: {joy.get_name()} (ID: {joy.get_instance_id()})")


def set_callbacks(on_press=None, on_release=None, on_hold=None, on_digital_axis=None, on_axis=None):
    """
    Set callback functions for joystick events.
    
    Args:
        on_press: Function(button, joystick_id) - Called when button is pressed
        on_release: Function(button, joystick_id) - Called when button is released  
        on_hold: Function(buttons_list, joystick_id) - Called each frame while buttons held
        on_digital_axis: Function(axis_values_list, joystick_id) - Called for digital axis movement
        on_axis: Function(value, axis, joystick_id) - Called for analog axis movement
    """
    global _on_joy_press_callback, _on_joy_release_callback
    global _on_joy_button_hold_callback, _on_digital_joy_axis_callback, _on_joy_axis_callback
    
    _on_joy_press_callback = on_press
    _on_joy_release_callback = on_release
    _on_joy_button_hold_callback = on_hold
    _on_digital_joy_axis_callback = on_digital_axis
    _on_joy_axis_callback = on_axis


def handle_event(event):
    """
    Process a pygame event for joystick input.
    Call this from your main event loop.
    
    Args:
        event: pygame.event object
        
    Returns:
        True if event was a joystick event, False otherwise
    """
    if event.type == pygame.JOYDEVICEADDED:
        joy = pygame.joystick.Joystick(event.device_index)
        joy.init()
        _joysticks[joy.get_instance_id()] = joy
        _all_buttons_down[joy.get_instance_id()] = set()
        _all_axis_down[joy.get_instance_id()] = set()
        print(f"Joystick connected: {joy.get_name()} (ID: {joy.get_instance_id()})")
        # Rumble if supported
        try:
            joy.rumble(0, 0.7, 500)
        except Exception:
            pass
        return True
        
    elif event.type == pygame.JOYDEVICEREMOVED:
        if event.instance_id in _joysticks:
            print(f"Joystick disconnected: ID {event.instance_id}")
            del _joysticks[event.instance_id]
            if event.instance_id in _all_buttons_down:
                del _all_buttons_down[event.instance_id]
            if event.instance_id in _all_axis_down:
                del _all_axis_down[event.instance_id]
            # Clean up axis history
            keys_to_remove = [k for k in _last_joy_axis if k.startswith(f"J{event.instance_id}")]
            for k in keys_to_remove:
                del _last_joy_axis[k]
        return True
        
    elif event.type == pygame.JOYBUTTONDOWN:
        _handle_button_press(str(event.button), event.instance_id)
        return True
        
    elif event.type == pygame.JOYBUTTONUP:
        _handle_button_release(str(event.button), event.instance_id)
        return True
        
    elif event.type == pygame.JOYHATMOTION:
        _handle_hat_motion(event.value, event.instance_id)
        return True
        
    elif event.type == pygame.JOYAXISMOTION:
        _handle_digital_axis(event.value, event.axis, event.instance_id)
        if _on_joy_axis_callback:
            _on_joy_axis_callback(event.value, event.axis, event.instance_id)
        return True
    
    return False


def update():
    """
    Call this once per frame to trigger hold callbacks.
    Should be called after processing all events.
    """
    for joystick_id in _all_buttons_down:
        if len(_all_buttons_down[joystick_id]) > 0:
            if _on_joy_button_hold_callback:
                _on_joy_button_hold_callback(list(_all_buttons_down[joystick_id]), joystick_id)
    
    for joystick_id in _all_axis_down:
        if len(_all_axis_down[joystick_id]) > 0:
            if _on_digital_joy_axis_callback:
                _on_digital_joy_axis_callback(list(_all_axis_down[joystick_id]), joystick_id)


def _handle_button_press(button, joystick_id):
    """Handle button press event"""
    if joystick_id in _all_buttons_down:
        _all_buttons_down[joystick_id].add(button)
    if _on_joy_press_callback:
        _on_joy_press_callback(button, joystick_id)


def _handle_button_release(button, joystick_id):
    """Handle button release event"""
    if joystick_id in _all_buttons_down and button in _all_buttons_down[joystick_id]:
        _all_buttons_down[joystick_id].remove(button)
    if _on_joy_release_callback:
        _on_joy_release_callback(button, joystick_id)


def _handle_hat_motion(values, joystick_id):
    """
    Handle DPAD/Hat motion. Converts hat movement to button presses.
    Hat buttons: H0=up, H1=right, H2=down, H3=left
    """
    key = f"J{joystick_id}H"
    prev = _last_joy_axis.get(key, (0, 0))
    
    # Vertical hat (Up/Down)
    if values[1] == 1 and prev[1] != 1:
        _handle_button_press("H0", joystick_id)  # Up pressed
    elif values[1] == -1 and prev[1] != -1:
        _handle_button_press("H2", joystick_id)  # Down pressed
    
    if values[1] == 0 and prev[1] == 1:
        _handle_button_release("H0", joystick_id)  # Up released
    elif values[1] == 0 and prev[1] == -1:
        _handle_button_release("H2", joystick_id)  # Down released
    
    # Horizontal hat (Left/Right)
    if values[0] == 1 and prev[0] != 1:
        _handle_button_press("H1", joystick_id)  # Right pressed
    elif values[0] == -1 and prev[0] != -1:
        _handle_button_press("H3", joystick_id)  # Left pressed
    
    if values[0] == 0 and prev[0] == 1:
        _handle_button_release("H1", joystick_id)  # Right released
    elif values[0] == 0 and prev[0] == -1:
        _handle_button_release("H3", joystick_id)  # Left released
    
    _last_joy_axis[key] = values


def _almost_equal(a, b, epsilon=0.5):
    """Check if two values are approximately equal"""
    return abs(a - b) < epsilon


def _handle_digital_axis(value, axis, joystick_id):
    """
    Handle analog stick movement as digital input.
    Converts axis values to discrete directions.
    
    Axis 0: Left/Right (-1 left, 1 right)
    Axis 1: Up/Down (-1 up, 1 down)
    """
    # Digitize the analog value
    if _almost_equal(value, 0, 0.5):
        digital_value = 0
    elif _almost_equal(value, 1, 0.5):
        digital_value = 1
    elif _almost_equal(value, -1, 0.5):
        digital_value = -1
    else:
        return
    
    key = f"J{joystick_id}A{axis}"
    prev = _last_joy_axis.get(key, 0)
    
    if joystick_id not in _all_axis_down:
        _all_axis_down[joystick_id] = set()
    
    # Axis pushed in a direction
    if digital_value != 0 and prev == 0:
        _all_axis_down[joystick_id].add((axis, digital_value))
    # Axis released
    elif digital_value == 0 and prev != 0:
        if (axis, prev) in _all_axis_down[joystick_id]:
            _all_axis_down[joystick_id].remove((axis, prev))
    # Axis changed direction
    elif digital_value != 0 and prev != 0 and digital_value != prev:
        if (axis, prev) in _all_axis_down[joystick_id]:
            _all_axis_down[joystick_id].remove((axis, prev))
        _all_axis_down[joystick_id].add((axis, digital_value))
    
    _last_joy_axis[key] = digital_value


def get_joystick_count():
    """Return number of connected joysticks"""
    return len(_joysticks)


def get_buttons_down(joystick_id=None):
    """
    Get set of currently pressed buttons.
    
    Args:
        joystick_id: Specific joystick to query, or None for first joystick
        
    Returns:
        Set of button strings that are currently pressed
    """
    if joystick_id is None:
        # Return buttons from first joystick if any
        if _all_buttons_down:
            return list(_all_buttons_down.values())[0]
        return set()
    return _all_buttons_down.get(joystick_id, set())


def get_axis_down(joystick_id=None):
    """
    Get set of currently active digital axis movements.
    
    Args:
        joystick_id: Specific joystick to query, or None for first joystick
        
    Returns:
        Set of (axis, direction) tuples for active movements
    """
    if joystick_id is None:
        if _all_axis_down:
            return list(_all_axis_down.values())[0]
        return set()
    return _all_axis_down.get(joystick_id, set())


def is_button_down(button, joystick_id=None):
    """Check if a specific button is currently pressed"""
    buttons = get_buttons_down(joystick_id)
    return str(button) in buttons


def quit():
    """Clean up joystick subsystem"""
    _joysticks.clear()
    _all_buttons_down.clear()
    _all_axis_down.clear()
    _last_joy_axis.clear()
    pygame.joystick.quit()
