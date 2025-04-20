# Ensure you have pygame and requests installed:
# pip install pygame requests
# OR
# python -m pip install pygame requests

import pygame
import sys
import os
import random

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235)
GREEN = (34, 139, 34)
GREY = (128, 128, 128)
GOLD = (255, 215, 0)

# Game Physics & Layout
GRAVITY = 0.5
GROUND_Y = SCREEN_HEIGHT - 80 # Make ground thicker
NET_HEIGHT = 150
NET_WIDTH = 10
NET_X = SCREEN_WIDTH // 2 - NET_WIDTH // 2
NET_RECT = pygame.Rect(NET_X, GROUND_Y - NET_HEIGHT, NET_WIDTH, NET_HEIGHT)

# Movement Physics
JUMP_POWER = -12  # Negative because y-axis is inverted
ACCELERATION = 0.8  # How quickly to accelerate
DECELERATION = 0.85  # Friction/drag factor (0-1)
MAX_SPEED = 8  # Maximum horizontal speed

# Sprite Info (Based on wolf sprite sheet dimensions)
SPRITE_WIDTH = 16
SPRITE_HEIGHT = 16

# Scaling
DOG_SCALE_FACTOR = 5 # Adjust size as needed
DOG_DRAW_WIDTH = int(SPRITE_WIDTH * DOG_SCALE_FACTOR)
DOG_DRAW_HEIGHT = int(SPRITE_HEIGHT * DOG_SCALE_FACTOR)

# Animation Info
WALK_FRAMES_INFO = {'row': 0, 'count': 8}  # Using all 4 frames for all animations
RUN_FRAMES_INFO = {'row': 0, 'count': 8}   # Using all 4 frames for all animations
IDLE_FRAMES_INFO = {'row': 0, 'count': 8}   # Using all 4 frames for all animations

ANIMATION_FPS = 10 # How many times per second the animation frame changes
WALK_TO_RUN_THRESHOLD = 20 # Game loop frames (~1/3 sec) of continuous movement

# --- Asset Loading ---

def load_image(file_path):
    """Loads an image from a file path."""
    try:
        return pygame.image.load(file_path).convert_alpha()
    except pygame.error as e:
        print(f"Error loading image from {file_path}: {e}")
        return None

def load_sprite_sheet(sheet, frame_width, frame_height):
    """Loads a sprite sheet and extracts frames."""
    if sheet is None:
        return None, 0, 0 # Return None if sheet failed to load

    try:
        sheet_width, sheet_height = sheet.get_size()
        rows = sheet_height // frame_height
        cols = sheet_width // frame_width

        # Debug information
        print(f"Sprite sheet dimensions: {sheet_width}x{sheet_height}")
        print(f"Frame dimensions: {frame_width}x{frame_height}")
        print(f"Calculated: {rows} rows, {cols} cols")

        frames = []
        for r in range(rows):
            row_frames = []
            for c in range(cols):
                # Calculate exact pixel coordinates for this frame
                x = c * frame_width
                y = r * frame_height
                # Create a rect for this specific frame
                rect = pygame.Rect(x, y, frame_width, frame_height)
                # Extract just this frame from the sheet
                frame = sheet.subsurface(rect)
                # Create a new surface with per-pixel alpha to ensure clean isolation
                clean_frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
                # Copy the frame to the new surface
                clean_frame.blit(frame, (0, 0))
                # Add the clean frame to our row
                row_frames.append(clean_frame)
            frames.append(row_frames)
        print(f"Loaded sprite sheet: {sheet_width}x{sheet_height}, {rows} rows, {cols} cols")
        return frames, sheet_width, sheet_height
    except pygame.error as e:
        print(f"Error loading/parsing sprite sheet: {e}")
        return None, 0, 0
    except ValueError as e:
         print(f"Error in subsurface calculation (check frame dimensions): {e}")
         return None, 0, 0


def get_animation_frames(all_frames, animation_info):
    """Extracts specific animation frames based on row and count."""
    if all_frames is None or animation_info['row'] >= len(all_frames):
        print(f"Warning: Cannot get frames for row {animation_info['row']}. Sheet not loaded or row index out of bounds.")
        # Return placeholder frames if loading failed or row is invalid
        placeholder = pygame.Surface((SPRITE_WIDTH, SPRITE_HEIGHT), pygame.SRCALPHA)
        placeholder.fill((random.randint(50,200), random.randint(50,200), random.randint(50,200), 180)) # Random semi-transparent color
        return [placeholder] * animation_info['count']

    row_index = animation_info['row']
    count = animation_info['count']
    # Ensure we don't try to get more frames than exist in the row
    available_frames_in_row = len(all_frames[row_index])
    actual_count = min(count, available_frames_in_row)
    if count > available_frames_in_row:
         print(f"Warning: Requested {count} frames from row {row_index}, but only {available_frames_in_row} exist.")

    return all_frames[row_index][:actual_count]


# --- Classes ---

class Dog(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, animations):
        super().__init__()
        self.animations = animations # Dict like {'idle': [frames], 'walk': [frames], 'run': [frames]}
        self.state = 'idle' # 'idle', 'walk', 'run'
        self.frame_index = 0
        self.last_update_time = pygame.time.get_ticks() # For animation timing
        self.animation_delay = 1000 // ANIMATION_FPS # Milliseconds per frame

        # Scale the first frame for initial image and rect setup
        self.image = pygame.transform.scale(self.animations['idle'][0], (DOG_DRAW_WIDTH, DOG_DRAW_HEIGHT))
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y) # Use bottomleft for ground alignment

        # Physics properties
        self.dx = 0  # Horizontal velocity
        self.dy = 0  # Vertical velocity
        self.speed = speed
        self.moving_timer = 0
        self.is_jumping = False
        self.is_grounded = True

        # For precise position tracking
        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

    def update_animation_state(self):
        """Determines the correct animation state based on movement."""
        is_moving = abs(self.dx) > 0.1

        new_state = 'idle'
        if not is_moving:
            new_state = 'idle'
            self.moving_timer = 0 # Reset timer when stopped
        elif self.moving_timer < WALK_TO_RUN_THRESHOLD:
            new_state = 'walk'
            self.moving_timer += 1 # Increment timer while moving
        else:
            new_state = 'run'
            self.moving_timer += 1 # Keep incrementing while running

        if new_state != self.state:
            self.state = new_state
            self.frame_index = 0 # Reset animation on state change

    def animate(self):
        """Cycles through the animation frames for the current state."""
        now = pygame.time.get_ticks()
        if now - self.last_update_time > self.animation_delay:
            self.last_update_time = now
            frames = self.animations.get(self.state, self.animations['idle']) # Fallback to idle
            if not frames: # Handle case where animation frames might be missing
                print(f"Warning: No frames found for state '{self.state}'. Using idle.")
                frames = self.animations['idle']
                if not frames: # If idle is also missing, use a placeholder
                     self.image.fill(GREY) # Simple placeholder color
                     return

            self.frame_index = (self.frame_index + 1) % len(frames)
            # Get the correct frame and scale it
            new_frame = frames[self.frame_index]
            self.image = pygame.transform.scale(new_frame, (DOG_DRAW_WIDTH, DOG_DRAW_HEIGHT))
            # Important: Update rect center based on new image if needed,
            # but since we scale consistently, just keeping the bottomleft aligned might be okay.
            # Keep bottom aligned after scaling
            bottom = self.rect.bottom
            self.rect = self.image.get_rect(bottom=bottom, centerx=self.rect.centerx)

    def jump(self):
        """Make the dog jump if it's on the ground."""
        if self.is_grounded:
            self.dy = JUMP_POWER
            self.is_jumping = True
            self.is_grounded = False

    def apply_physics(self):
        """Apply gravity and handle ground collision."""
        # Apply gravity
        self.dy += GRAVITY

        # Apply horizontal deceleration (friction)
        if abs(self.dx) > 0.1:
            self.dx *= DECELERATION
        else:
            self.dx = 0  # Stop completely if very slow

        # Cap horizontal speed
        if self.dx > MAX_SPEED:
            self.dx = MAX_SPEED
        elif self.dx < -MAX_SPEED:
            self.dx = -MAX_SPEED

        # Update position with velocity
        self.x += self.dx
        self.y += self.dy

        # Update rect position from float values
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        # Check for ground collision
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.y = float(self.rect.y)
            self.dy = 0
            self.is_grounded = True
            self.is_jumping = False

    def update(self):
        """Placeholder for movement logic - to be implemented in subclasses."""
        self.update_animation_state()
        self.animate()
        self.apply_physics()


class Player(Dog):
    def __init__(self, x, y, speed, animations):
        super().__init__(x, y, speed, animations)
        self.space_pressed_last_frame = False  # Track space bar state for serve release

    def update(self):
        global game_state, serve_power, serve_charging

        keys_pressed = pygame.key.get_pressed()
        is_moving_left = keys_pressed[pygame.K_LEFT]
        is_moving_right = keys_pressed[pygame.K_RIGHT]
        is_up_pressed = keys_pressed[pygame.K_UP]  # Changed to up arrow for jumping
        is_space_pressed = keys_pressed[pygame.K_SPACE]  # Space is now only for serving

        # Handle serving state
        if game_state == 'serving' and serve_side == 'player':
            # Start charging serve when space is pressed
            if is_space_pressed and not serve_charging:
                serve_charging = True
                serve_power = 0

            # Continue charging while space is held
            elif is_space_pressed and serve_charging:
                serve_power = min(serve_power + SERVE_POWER_RATE, MAX_SERVE_POWER)

            # Release serve when space is released after charging
            elif not is_space_pressed and serve_charging and self.space_pressed_last_frame:
                serve_charging = False
                # Serve the ball with the charged power
                ball.serve_with_power(serve_side, serve_power)
                game_state = 'playing'
                serve_power = 0  # Reset serve power

            # Allow movement during serving
            if is_moving_left:
                self.dx -= ACCELERATION  # Accelerate left
            elif is_moving_right:
                self.dx += ACCELERATION  # Accelerate right

        # Normal gameplay controls
        elif game_state == 'playing':
            # Handle jumping with UP arrow
            if is_up_pressed:
                self.jump()

            # Apply acceleration based on input
            if is_moving_left:
                self.dx -= ACCELERATION  # Accelerate left
            elif is_moving_right:
                self.dx += ACCELERATION  # Accelerate right

        # Update space bar state for next frame
        self.space_pressed_last_frame = is_space_pressed

        # Update animation state based on movement
        self.update_animation_state()
        self.animate()

        # Apply physics (gravity, velocity, collisions)
        self.apply_physics()

        # Boundary checks
        if self.rect.left < 0:
            self.rect.left = 0
            self.x = float(self.rect.x)  # Update float position
        if self.rect.right > NET_X:  # Player stays left of net
            self.rect.right = NET_X
            self.x = float(self.rect.x)  # Update float position


class AI(Dog):
    def __init__(self, x, y, speed, animations, ball_ref):
        super().__init__(x, y, speed, animations)
        self.ball = ball_ref # Reference to the ball sprite
        self.jump_cooldown = 0
        self.serve_timer = 0  # Timer for AI serving
        self.serve_delay = 60  # Frames to wait before serving (1 second)

    def update(self):
        global game_state, serve_power

        # Handle serving state for AI
        if game_state == 'serving' and serve_side == 'ai':
            # Move to a good serving position
            default_serve_pos_x = SCREEN_WIDTH * 3 / 4
            if self.rect.centerx < default_serve_pos_x - 10:
                self.dx += ACCELERATION * 0.4
            elif self.rect.centerx > default_serve_pos_x + 10:
                self.dx -= ACCELERATION * 0.4
            else:
                self.dx *= DECELERATION  # Slow down when in position

                # Start the serve timer once in position
                if self.serve_timer == 0:
                    self.serve_timer = self.serve_delay

            # Count down the serve timer
            if self.serve_timer > 0:
                self.serve_timer -= 1
                # AI charges serve power gradually
                serve_power = MAX_SERVE_POWER * (1 - (self.serve_timer / self.serve_delay))

                # Serve when timer reaches zero
                if self.serve_timer == 0:
                    # Serve with random power between 60-90%
                    power = random.uniform(60, 90)
                    ball.serve_with_power(serve_side, power)
                    game_state = 'playing'
                    serve_power = 0  # Reset serve power

        # Normal gameplay AI
        elif game_state == 'playing':
            # Simple AI: Move towards the ball's x-position if it's on AI side or coming towards AI
            target_x = self.ball.rect.centerx
            ai_center = self.rect.centerx

            # Only actively move if ball is reasonably close or moving towards AI
            if self.ball.dx < 0 or self.ball.rect.centerx > SCREEN_WIDTH / 2:
                if ai_center < target_x - self.rect.width * 0.3: # Move right if ball is to the right
                    self.dx += ACCELERATION * 0.8  # AI accelerates a bit slower than player
                elif ai_center > target_x + self.rect.width * 0.3: # Move left if ball is to the left
                    self.dx -= ACCELERATION * 0.8

                # Jump if the ball is above the AI and close enough horizontally
                if (self.ball.rect.bottom < self.rect.top + 50 and
                    abs(self.ball.rect.centerx - self.rect.centerx) < 100 and
                    self.jump_cooldown <= 0 and self.is_grounded):
                    self.jump()
                    self.jump_cooldown = 45  # Increased cooldown to make AI less aggressive
            else:
                # If ball is far on player side, maybe slowly return to center
                default_pos_x = SCREEN_WIDTH * 3 / 4
                if ai_center < default_pos_x - self.speed * 0.5:
                    self.dx += ACCELERATION * 0.4  # Gentle acceleration toward default position
                elif ai_center > default_pos_x + self.speed * 0.5:
                    self.dx -= ACCELERATION * 0.4

        # Decrement jump cooldown
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1

        # Update animation state based on movement
        self.update_animation_state()
        self.animate()

        # Apply physics (gravity, velocity, collisions)
        self.apply_physics()

        # Boundary checks
        if self.rect.left < NET_X + NET_WIDTH: # AI stays right of net
            self.rect.left = NET_X + NET_WIDTH
            self.x = float(self.rect.x)  # Update float position
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.x = float(self.rect.x)  # Update float position


class Ball(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.radius = 15
        # Create a surface for the ball
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA) # Use SRALPHA for transparency
        pygame.draw.circle(self.image, WHITE, (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=(x, y))
        self.dx = 0
        self.dy = 0
        self.x = float(self.rect.centerx) # Use float for precise position tracking
        self.y = float(self.rect.centery)

    def update(self):
        global game_state

        # Only apply physics when in playing state
        if game_state == 'playing':
            # Apply gravity
            self.dy += GRAVITY
            # Update precise position
            self.x += self.dx
            self.y += self.dy
            # Update rect position based on float values
            self.rect.center = (round(self.x), round(self.y))
        # In serving state, the ball stays in place (no gravity)

        # Wall collisions
        if self.rect.left <= 0:
            self.rect.left = 0
            self.x = float(self.rect.centerx) # Update float pos
            self.dx *= -0.9 # Bounce with slight energy loss
        if self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.x = float(self.rect.centerx) # Update float pos
            self.dx *= -0.9

        # Ceiling collision
        if self.rect.top <= 0:
            self.rect.top = 0
            self.y = float(self.rect.centery) # Update float pos
            self.dy *= -0.9

        # Net collision (simple rect collision)
        if self.rect.colliderect(NET_RECT):
            # Determine hit side more accurately
            overlap_x = min(self.rect.right - NET_RECT.left, NET_RECT.right - self.rect.left)
            overlap_y = min(self.rect.bottom - NET_RECT.top, NET_RECT.bottom - self.rect.top)

            if overlap_x < overlap_y : # Hit the side of the net
                 self.dx *= -1.1 # Bounce horizontally, maybe faster
                 # Nudge out
                 if self.rect.centerx < NET_RECT.centerx:
                     self.rect.right = NET_RECT.left - 1
                 else:
                     self.rect.left = NET_RECT.right + 1
                 self.x = float(self.rect.centerx)
            else: # Hit the top (or bottom, less likely)
                 self.dy *= -0.9 # Bounce vertically
                 # Nudge out
                 if self.rect.centery < NET_RECT.centery: # Hit top
                    self.rect.bottom = NET_RECT.top -1
                 else: # Hit bottom (unlikely)
                    self.rect.top = NET_RECT.bottom + 1
                 self.y = float(self.rect.centery)


    def check_ground_collision(self):
        """Checks for ground collision and returns scoring side ('player' or 'ai') or None."""
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.y = float(self.rect.centery)
            # self.dy *= -0.7 # Bounce effect if needed, but scoring happens first

            if self.rect.centerx < SCREEN_WIDTH // 2:
                return 'ai' # AI scored (ball landed on player side)
            else:
                return 'player' # Player scored
        return None

    def reset(self, serve_side):
        """Resets ball position for the next serve without setting velocity."""
        self.dy = 0
        self.dx = 0

        # Position the ball above the server
        if serve_side == 'player':
            self.x = SCREEN_WIDTH / 4
            self.y = SCREEN_HEIGHT / 3
        else: # AI serves
            self.x = SCREEN_WIDTH * 3 / 4
            self.y = SCREEN_HEIGHT / 3

        self.rect.center = (round(self.x), round(self.y))

    def serve_with_power(self, serve_side, power):
        """Serves the ball with the given power (0-100)."""
        # Convert power percentage to actual velocity
        power_factor = power / 100.0

        # Base velocities
        base_dx = 4
        base_dy = -7

        # Apply power factor (more power = faster serve)
        if serve_side == 'player':
            self.dx = base_dx * (0.5 + power_factor) + random.uniform(-0.5, 0.5)
            self.dy = base_dy * (0.5 + power_factor) + random.uniform(-0.5, 0.5)
        else: # AI serves
            self.dx = -base_dx * (0.5 + power_factor) + random.uniform(-0.5, 0.5)
            self.dy = base_dy * (0.5 + power_factor) + random.uniform(-0.5, 0.5)


class Button:
    def __init__(self, x, y, width, height, text, font, base_color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.base_color = base_color
        self.hover_color = hover_color
        self.current_color = base_color
        self.text_surf = self.font.render(self.text, True, WHITE)
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    def handle_event(self, event):
        """Checks if the button was clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def update(self, mouse_pos):
        """Updates hover state."""
        if self.rect.collidepoint(mouse_pos):
            self.current_color = self.hover_color
        else:
            self.current_color = self.base_color

    def draw(self, surface):
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=10)
        pygame.draw.rect(surface, WHITE, self.rect, width=3, border_radius=10) # Border
        surface.blit(self.text_surf, self.text_rect)


# --- Game Setup ---
pygame.init()
pygame.font.init() # Initialize font module

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Doggo Volleyball (Pygame)")
clock = pygame.time.Clock()

# Load Fonts (Using default Pygame font)
try:
    # Try loading a specific font if available (replace path if needed)
    # title_font = pygame.font.Font("path/to/PressStart2P-Regular.ttf", 40)
    # button_font = pygame.font.Font("path/to/PressStart2P-Regular.ttf", 24)
    # score_font = pygame.font.Font("path/to/PressStart2P-Regular.ttf", 30)
    # If specific font fails or not provided, use default
    default_font_name = pygame.font.get_default_font()
    title_font = pygame.font.Font(default_font_name, 40)
    button_font = pygame.font.Font(default_font_name, 24)
    score_font = pygame.font.Font(default_font_name, 30)
    rules_font = pygame.font.Font(default_font_name, 18)
    print(f"Using default font: {default_font_name}")
except Exception as e:
     print(f"Error loading font: {e}. Using default font.")
     # Fallback just in case get_default_font also fails somehow
     title_font = pygame.font.SysFont(None, 50)
     button_font = pygame.font.SysFont(None, 30)
     score_font = pygame.font.SysFont(None, 36)
     rules_font = pygame.font.SysFont(None, 24)


# --- Load and Process Sprites ---
wolf_sheet_path = 'assets/Dog Wolf Spritesheet.png' # Wolf sprite sheet

wolf_sheet = load_image(wolf_sheet_path)

# Load the sprite sheet once
wolf_all_frames, _, _ = load_sprite_sheet(wolf_sheet, SPRITE_WIDTH, SPRITE_HEIGHT)

# Since there's only one row, we'll split it into two parts
# First two sprites for player, last two for AI
if wolf_all_frames and len(wolf_all_frames[0]) >= 4:
    # Player uses first two sprites (0 and 1) - flip them horizontally
    player_frames = [
        pygame.transform.flip(wolf_all_frames[0][0], True, False),
        pygame.transform.flip(wolf_all_frames[0][1], True, False)
    ]

    # AI uses last two sprites (2 and 3) with a red tint
    ai_frames = []
    for i in range(2, 4):
        # Create a copy of the frame
        ai_frame = wolf_all_frames[0][i].copy()
        # Apply a red tint
        red_overlay = pygame.Surface(ai_frame.get_size(), pygame.SRCALPHA)
        red_overlay.fill((150, 50, 50, 100))  # Semi-transparent red
        ai_frame.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        ai_frames.append(ai_frame)

    # Create new frame arrays
    player_all_frames = [[player_frames[0], player_frames[1], player_frames[0], player_frames[1]]]
    ai_all_frames = [[ai_frames[0], ai_frames[1], ai_frames[0], ai_frames[1]]]
else:
    # Fallback if sprite sheet doesn't have enough frames
    player_all_frames = wolf_all_frames
    ai_all_frames = wolf_all_frames

# Create animation dictionaries - using the frames directly since we've already prepared them
player_animations = {
    'idle': player_all_frames[0],
    'walk': player_all_frames[0],
    'run': player_all_frames[0],
}
ai_animations = {
    'idle': ai_all_frames[0],
    'walk': ai_all_frames[0],
    'run': ai_all_frames[0],
}

# Check if animations loaded correctly (at least idle should have something)
if not player_animations['idle'] or not ai_animations['idle']:
     print("CRITICAL ERROR: Failed to load essential sprite frames. Exiting.")
     pygame.quit()
     sys.exit()


# --- Game State Variables ---
game_state = 'start_menu' # 'start_menu', 'options', 'how_to_play', 'playing', 'serving', 'point_pause', 'game_over'
player_score = 0
ai_score = 0
winning_score = 5
serve_side = 'player' # 'player' or 'ai'
winner = None

# Serve mechanics
serve_power = 0  # Current serve power (0-100)
MAX_SERVE_POWER = 100  # Maximum serve power
SERVE_POWER_RATE = 2  # How fast the power meter increases
serve_charging = False  # Whether the player is currently charging a serve
point_pause_timer = 0  # Timer for pause between points
POINT_PAUSE_DURATION = 60  # Frames to pause after a point (1 second at 60 FPS)

# --- Create Sprites and Groups ---
all_sprites = pygame.sprite.Group()
dogs = pygame.sprite.Group() # Group for player and AI for collision checks

ball = Ball(SCREEN_WIDTH // 4, SCREEN_HEIGHT // 2)
player = Player(SCREEN_WIDTH / 4 - DOG_DRAW_WIDTH / 2, GROUND_Y, 5, player_animations)
ai = AI(SCREEN_WIDTH * 3 / 4 - DOG_DRAW_WIDTH / 2, GROUND_Y, 3.5, ai_animations, ball) # Pass ball reference to AI

all_sprites.add(player, ai, ball)
dogs.add(player, ai)


# --- Menu Functions ---

def draw_text(text, font, color, surface, x, y, center=True):
    """Helper function to draw text."""
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

def start_menu():
    global game_state
    title_text = "Doggo Volleyball!"
    start_button = Button(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 - 50, 300, 60, "Start Game", button_font, GREEN, GREY)
    options_button = Button(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 30, 300, 60, "Options", button_font, GREEN, GREY)
    how_to_play_button = Button(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 110, 300, 60, "How to Play", button_font, GREEN, GREY)
    quit_button = Button(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 190, 300, 60, "Quit", button_font, (200,0,0), GREY)


    buttons = [start_button, options_button, how_to_play_button, quit_button]

    while game_state == 'start_menu':
        mouse_pos = pygame.mouse.get_pos()
        screen.fill(BLACK) # Menu background
        draw_text(title_text, title_font, GOLD, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if start_button.handle_event(event):
                game_state = 'playing' # Start the game
                reset_game() # Ensure game resets before starting
                return
            if options_button.handle_event(event):
                game_state = 'options'
                return
            if how_to_play_button.handle_event(event):
                 game_state = 'how_to_play'
                 return
            if quit_button.handle_event(event):
                 pygame.quit()
                 sys.exit()


        for button in buttons:
            button.update(mouse_pos)
            button.draw(screen)

        pygame.display.flip()
        clock.tick(FPS) # Limit FPS even in menus

def options_menu():
    global game_state, winning_score
    title_text = "Options"
    options = [3, 5, 7, 10]

    option_buttons = []
    button_y = SCREEN_HEIGHT // 2 - 50
    for i, score in enumerate(options):
         button = Button(SCREEN_WIDTH//2 - 100, button_y + i * 70, 200, 50, f"{score} Points", button_font, GREEN, GREY)
         option_buttons.append(button)

    back_button = Button(SCREEN_WIDTH//2 - 100, button_y + len(options) * 70, 200, 50, "Back", button_font, (200, 0, 0), GREY)

    while game_state == 'options':
        mouse_pos = pygame.mouse.get_pos()
        screen.fill(BLACK)
        draw_text(title_text, title_font, GOLD, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if back_button.handle_event(event):
                 game_state = 'start_menu'
                 return
            for i, button in enumerate(option_buttons):
                 if button.handle_event(event):
                     winning_score = options[i]
                     print(f"Winning score set to: {winning_score}")
                     game_state = 'start_menu'
                     return # Go back to start menu after selection


        for i, button in enumerate(option_buttons):
             # Highlight selected option
             if options[i] == winning_score:
                 button.base_color = (0, 100, 0) # Darker green for selected
             else:
                 button.base_color = GREEN
             button.update(mouse_pos)
             button.draw(screen)

        back_button.update(mouse_pos)
        back_button.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

def how_to_play_menu():
    global game_state
    title_text = "How To Play"
    rules = [
        "Move Your Dog: Left/Right Arrow Keys",
        "Objective: Hit the ball over the net.",
        "Scoring: Score if the ball lands on the opponent's side.",
        f"Win: First to {winning_score} points wins!",
        "Serve: After a score, the non-scoring player serves.",
    ]
    back_button = Button(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT - 100, 200, 50, "Back", button_font, (200, 0, 0), GREY)

    while game_state == 'how_to_play':
        mouse_pos = pygame.mouse.get_pos()
        screen.fill(BLACK)
        draw_text(title_text, title_font, GOLD, screen, SCREEN_WIDTH // 2, 100)

        # Display rules
        rule_y = 200
        for line in rules:
             draw_text(line, rules_font, WHITE, screen, SCREEN_WIDTH // 2, rule_y)
             rule_y += 40

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if back_button.handle_event(event):
                 game_state = 'start_menu'
                 return

        back_button.update(mouse_pos)
        back_button.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


def game_over_menu():
    global game_state, winner
    message = f"{winner} Wins!" if winner else "Game Over!"
    restart_button = Button(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2, 300, 60, "Play Again?", button_font, GREEN, GREY)
    quit_button = Button(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT//2 + 80, 300, 60, "Quit to Menu", button_font, (200,0,0), GREY)
    buttons = [restart_button, quit_button]

    while game_state == 'game_over':
        mouse_pos = pygame.mouse.get_pos()
        # Optionally draw semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0,0))

        draw_text(message, title_font, GOLD, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if restart_button.handle_event(event):
                 game_state = 'playing' # Restart
                 reset_game()
                 return
            if quit_button.handle_event(event):
                 game_state = 'start_menu' # Back to main menu
                 return

        for button in buttons:
            button.update(mouse_pos)
            button.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

# --- Helper Functions ---
def reset_game():
    """Resets scores, positions, and serve."""
    global player_score, ai_score, serve_side, winner, serve_power, serve_charging, game_state, point_pause_timer

    # Reset scores
    player_score = 0
    ai_score = 0
    winner = None

    # Reset serve mechanics
    serve_power = 0
    serve_charging = False
    point_pause_timer = 0

    # Reset player and AI
    player.reset()
    ai.reset()
    ai_additional_reset()  # Call the additional AI reset function

    # Reset positions
    player.rect.bottomleft = (SCREEN_WIDTH / 4 - player.rect.width / 2, GROUND_Y)
    ai.rect.bottomleft = (SCREEN_WIDTH * 3 / 4 - ai.rect.width / 2, GROUND_Y)

    # Update float positions
    player.x = float(player.rect.x)
    player.y = float(player.rect.y)
    ai.x = float(ai.rect.x)
    ai.y = float(ai.rect.y)

    # Reset ball and serve
    serve_side = 'player' if random.random() < 0.5 else 'ai'
    ball.reset(serve_side)

    # Set game state to serving
    game_state = 'serving'


# Add a basic reset method to Dog class if needed, or handle in reset_game
def dog_reset(dog_instance):
     dog_instance.frame_index = 0
     dog_instance.moving_timer = 0
     dog_instance.state = 'idle'
     dog_instance.dx = 0
     dog_instance.dy = 0
     dog_instance.is_jumping = False
     dog_instance.is_grounded = True
     # Reset position in reset_game

player.reset = lambda: dog_reset(player)
ai.reset = lambda: dog_reset(ai)

# Additional AI reset
def ai_additional_reset():
    ai.jump_cooldown = 0  # Reset AI jump cooldown
    ai.serve_timer = 0    # Reset AI serve timer

# --- Main Game Loop ---
running = True
while running:

    # --- Handle Menu States ---
    if game_state == 'start_menu':
        start_menu()
        continue # Skip rest of loop until state changes
    elif game_state == 'options':
        options_menu()
        continue
    elif game_state == 'how_to_play':
         how_to_play_menu()
         continue
    elif game_state == 'game_over':
        game_over_menu()
        continue

    # --- Handle Game Events ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Add other event handling if needed (e.g., pause key)

    # --- Game Updates ---
    # Handle point pause state
    if game_state == 'point_pause':
        point_pause_timer -= 1
        if point_pause_timer <= 0:
            game_state = 'serving'
            # Reset AI serve timer when transitioning to serving state
            if serve_side == 'ai':
                ai.serve_timer = 0

    # Update sprites in playing or serving states
    if game_state == 'playing' or game_state == 'serving':
        all_sprites.update() # Calls update() on player, ai, ball

        # Ball-Dog Collision
        if pygame.sprite.spritecollide(ball, dogs, False):
             # More precise collision check might be needed
             collided_dog = None
             if ball.rect.colliderect(player.rect):
                 collided_dog = player
             elif ball.rect.colliderect(ai.rect):
                 collided_dog = ai

             if collided_dog:
                 # Calculate hit angle based on relative position
                 hit_angle = (ball.rect.centerx - collided_dog.rect.centerx) / (collided_dog.rect.width / 2) # -1 to 1

                 # Add dog's momentum to the ball
                 ball.dx = hit_angle * 7 + (collided_dog.dx * 0.6)  # Bounce angle depends on hit location + dog's momentum

                 # Stronger bounce if dog is moving up (jumping)
                 if collided_dog.dy < 0:  # Dog is moving upward
                     ball.dy = -10 - random.uniform(0, 2) - abs(collided_dog.dy * 0.3)  # Extra bounce from jump
                 else:
                     ball.dy = -8 - random.uniform(0, 2)  # Standard bounce

                 # Move ball out of dog
                 ball.y = collided_dog.rect.top - ball.radius - 1
                 ball.rect.centery = round(ball.y)


        # Ball-Ground Collision / Scoring
        score_result = ball.check_ground_collision()
        if score_result:
            if score_result == 'player':
                player_score += 1
                serve_side = 'ai' # AI serves next
            else: # AI scored
                ai_score += 1
                serve_side = 'player' # Player serves next

            # Check for win
            if player_score >= winning_score:
                winner = "Player"
                game_state = 'game_over'
            elif ai_score >= winning_score:
                winner = "AI"
                game_state = 'game_over'
            else:
                # Start point pause
                game_state = 'point_pause'
                point_pause_timer = POINT_PAUSE_DURATION
                # Reset ball position but don't serve yet
                ball.reset(serve_side)

    # --- Drawing ---
    screen.fill(SKY_BLUE) # Background

    # Draw Ground
    pygame.draw.rect(screen, GREEN, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))

    # Draw Net
    pygame.draw.rect(screen, WHITE, NET_RECT)
    pygame.draw.line(screen, GREY, (NET_RECT.left - 2, NET_RECT.top), (NET_RECT.right + 2, NET_RECT.top), 5) # Net top

    # Draw Sprites
    all_sprites.draw(screen)

    # Draw Score
    score_text = f"Player: {player_score} - AI: {ai_score}"
    draw_text(score_text, score_font, WHITE, screen, SCREEN_WIDTH // 2, 30)

    # Draw serve instructions when in serving state
    if game_state == 'serving':
        if serve_side == 'player':
            instruction_text = "Hold SPACE to charge serve, release to serve"
            draw_text(instruction_text, button_font, WHITE, screen, SCREEN_WIDTH // 2, 70)

            # Only draw power meter when actively charging a serve
            if serve_charging:
                # Draw power meter
                meter_width = 300
                meter_height = 20
                meter_x = (SCREEN_WIDTH - meter_width) // 2
                meter_y = 100

                # Draw meter background
                pygame.draw.rect(screen, GREY, (meter_x, meter_y, meter_width, meter_height))

                # Draw filled portion based on serve_power
                fill_width = int((serve_power / MAX_SERVE_POWER) * meter_width)

                # Color changes from green to yellow to red as power increases
                if serve_power < MAX_SERVE_POWER * 0.33:
                    meter_color = (0, 255, 0)  # Green
                elif serve_power < MAX_SERVE_POWER * 0.66:
                    meter_color = (255, 255, 0)  # Yellow
                else:
                    meter_color = (255, 0, 0)  # Red

                pygame.draw.rect(screen, meter_color, (meter_x, meter_y, fill_width, meter_height))

                # Draw meter border
                pygame.draw.rect(screen, WHITE, (meter_x, meter_y, meter_width, meter_height), 2)
        else:
            instruction_text = "AI is preparing to serve..."
            draw_text(instruction_text, button_font, WHITE, screen, SCREEN_WIDTH // 2, 70)

    # Draw point pause message
    if game_state == 'point_pause':
        if serve_side == 'ai':  # Player scored last, so AI serves next
            pause_text = "Player scores!"
        else:  # AI scored last, so player serves next
            pause_text = "AI scores!"
        draw_text(pause_text, score_font, GOLD, screen, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)

    # --- Update Display ---
    pygame.display.flip()

    # --- Control Framerate ---
    clock.tick(FPS)

# --- End Game ---
pygame.quit()
sys.exit()