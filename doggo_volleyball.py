# Ensure you have pygame and requests installed:
# pip install pygame requests
# OR
# python -m pip install pygame requests

import pygame
import sys
import os
import requests # To download images from URLs
import io       # To handle image data in memory
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

# Sprite Info (Based on user confirmation)
SPRITE_WIDTH = 64
SPRITE_HEIGHT = 64

# Scaling
DOG_SCALE_FACTOR = 1.5 # Adjust size as needed
DOG_DRAW_WIDTH = int(SPRITE_WIDTH * DOG_SCALE_FACTOR)
DOG_DRAW_HEIGHT = int(SPRITE_HEIGHT * DOG_SCALE_FACTOR)

# Animation Info
WALK_FRAMES_INFO = {'row': 0, 'count': 6}
RUN_FRAMES_INFO = {'row': 1, 'count': 6}
IDLE_FRAMES_INFO = {'row': 2, 'count': 4}

ANIMATION_FPS = 5 # How many times per second the animation frame changes
WALK_TO_RUN_THRESHOLD = 20 # Game loop frames (~1/3 sec) of continuous movement

# --- Asset Loading ---

def fetch_image(url):
    """Downloads an image from a URL and returns image data."""
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        return io.BytesIO(response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image from {url}: {e}")
        return None

def load_sprite_sheet(image_data, frame_width, frame_height):
    """Loads a sprite sheet from image data and extracts frames."""
    if image_data is None:
        return None, 0, 0 # Return None if image data failed to fetch

    try:
        sheet = pygame.image.load(image_data).convert_alpha()
        sheet_width, sheet_height = sheet.get_size()
        rows = sheet_height // frame_height
        cols = sheet_width // frame_width
        
        frames = []
        for r in range(rows):
            row_frames = []
            for c in range(cols):
                rect = pygame.Rect(c * frame_width, r * frame_height, frame_width, frame_height)
                frame = sheet.subsurface(rect)
                row_frames.append(frame)
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

        self.dx = 0
        self.speed = speed
        self.moving_timer = 0

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


    def update(self):
        """Placeholder for movement logic - to be implemented in subclasses."""
        self.update_animation_state()
        self.animate()
        # Apply movement (example, replace in subclasses)
        # self.rect.x += self.dx


class Player(Dog):
    def __init__(self, x, y, speed, animations):
        super().__init__(x, y, speed, animations)

    def update(self):
        keys_pressed = pygame.key.get_pressed()
        is_moving_left = keys_pressed[pygame.K_LEFT]
        is_moving_right = keys_pressed[pygame.K_RIGHT]
        is_trying_to_move = is_moving_left or is_moving_right

        if is_moving_left:
            self.dx = -self.speed
        elif is_moving_right:
            self.dx = self.speed
        else:
            self.dx = 0

        # Update state based on dx (which reflects input)
        self.update_animation_state() # Determines state and increments/resets timer
        self.animate() # Updates self.image based on state

        # Apply movement
        self.rect.x += self.dx

        # Boundary checks
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > NET_X: # Player stays left of net
            self.rect.right = NET_X
        # Ensure y stays correct (in case of future jump implementation)
        self.rect.bottom = GROUND_Y


class AI(Dog):
    def __init__(self, x, y, speed, animations, ball_ref):
        super().__init__(x, y, speed, animations)
        self.ball = ball_ref # Reference to the ball sprite

    def update(self):
        intended_dx = 0
        # Simple AI: Move towards the ball's x-position if it's on AI side or coming towards AI
        target_x = self.ball.rect.centerx
        ai_center = self.rect.centerx

        # Only actively move if ball is reasonably close or moving towards AI
        if self.ball.dx < 0 or self.ball.rect.centerx > SCREEN_WIDTH / 2:
            if ai_center < target_x - self.rect.width * 0.3: # Move right if ball is to the right
                 intended_dx = self.speed
            elif ai_center > target_x + self.rect.width * 0.3: # Move left if ball is to the left
                 intended_dx = -self.speed
            # Add some randomness or imperfection? Maybe a reaction delay? (Optional)

        else:
             # If ball is far on player side, maybe slowly return to center?
             default_pos_x = SCREEN_WIDTH * 3 / 4
             if ai_center < default_pos_x - self.speed * 0.5:
                 intended_dx = self.speed * 0.5
             elif ai_center > default_pos_x + self.speed * 0.5:
                 intended_dx = -self.speed * 0.5

        self.dx = intended_dx

        # Update state based on dx
        self.update_animation_state()
        self.animate()

        # Apply movement
        self.rect.x += self.dx

        # Boundary checks
        if self.rect.left < NET_X + NET_WIDTH: # AI stays right of net
            self.rect.left = NET_X + NET_WIDTH
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        # Ensure y stays correct
        self.rect.bottom = GROUND_Y


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
        # Apply gravity
        self.dy += GRAVITY
        # Update precise position
        self.x += self.dx
        self.y += self.dy
        # Update rect position based on float values
        self.rect.center = (round(self.x), round(self.y))

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
        """Resets ball position and velocity for the next serve."""
        self.y = SCREEN_HEIGHT / 3
        self.dy = 0
        if serve_side == 'player':
            self.x = SCREEN_WIDTH / 4
            self.dx = 4 + random.uniform(-1, 1) # Serve towards AI
            self.dy = -7 + random.uniform(-1, 1)
        else: # AI serves
            self.x = SCREEN_WIDTH * 3 / 4
            self.dx = -4 + random.uniform(-1, 1) # Serve towards Player
            self.dy = -7 + random.uniform(-1, 1)
        self.rect.center = (round(self.x), round(self.y))


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
player_sheet_url = 'https://i.imgur.com/d2g12jg.png' # Black Dog
ai_sheet_url = 'https://i.imgur.com/LQcxtwC.png'     # White Dog

player_image_data = fetch_image(player_sheet_url)
ai_image_data = fetch_image(ai_sheet_url)

player_all_frames, _, _ = load_sprite_sheet(player_image_data, SPRITE_WIDTH, SPRITE_HEIGHT)
ai_all_frames, _, _ = load_sprite_sheet(ai_image_data, SPRITE_WIDTH, SPRITE_HEIGHT)

# Create animation dictionaries
player_animations = {
    'idle': get_animation_frames(player_all_frames, IDLE_FRAMES_INFO),
    'walk': get_animation_frames(player_all_frames, WALK_FRAMES_INFO),
    'run': get_animation_frames(player_all_frames, RUN_FRAMES_INFO),
}
ai_animations = {
    'idle': get_animation_frames(ai_all_frames, IDLE_FRAMES_INFO),
    'walk': get_animation_frames(ai_all_frames, WALK_FRAMES_INFO),
    'run': get_animation_frames(ai_all_frames, RUN_FRAMES_INFO),
}

# Check if animations loaded correctly (at least idle should have something)
if not player_animations['idle'] or not ai_animations['idle']:
     print("CRITICAL ERROR: Failed to load essential sprite frames. Exiting.")
     pygame.quit()
     sys.exit()


# --- Game State Variables ---
game_state = 'start_menu' # 'start_menu', 'options', 'how_to_play', 'playing', 'serving', 'game_over'
player_score = 0
ai_score = 0
winning_score = 5
serve_side = 'player' # 'player' or 'ai'
winner = None

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
    selected_index = options.index(winning_score) if winning_score in options else 1 # Default to 5

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
    global player_score, ai_score, serve_side, winner
    player_score = 0
    ai_score = 0
    winner = None
    player.reset() # Assuming Dog class has a reset method or we reset manually
    ai.reset()
    player.rect.bottomleft = (SCREEN_WIDTH / 4 - player.rect.width / 2, GROUND_Y)
    ai.rect.bottomleft = (SCREEN_WIDTH * 3 / 4 - ai.rect.width / 2, GROUND_Y)
    serve_side = 'player' if random.random() < 0.5 else 'ai'
    ball.reset(serve_side)
    # Add reset calls to player/ai if they have specific reset logic
    player.movingTimer = 0
    ai.movingTimer = 0
    player.state = 'idle'
    ai.state = 'idle'


# Add a basic reset method to Dog class if needed, or handle in reset_game
def dog_reset(dog_instance):
     dog_instance.currentFrames = dog_instance.animations['idle']
     dog_instance.frameIndex = 0
     dog_instance.movingTimer = 0
     dog_instance.state = 'idle'
     dog_instance.dx = 0
     # Reset position in reset_game

player.reset = lambda: dog_reset(player)
ai.reset = lambda: dog_reset(ai)

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
                 # Simple vertical bounce based on relative position
                 hit_angle = (ball.rect.centerx - collided_dog.rect.centerx) / (collided_dog.rect.width / 2) # -1 to 1
                 ball.dx = hit_angle * 7 # Bounce angle depends on hit location
                 ball.dy = -8 - random.uniform(0, 2) # Bounce upwards strongly
                 # Add dog's dx? ball.dx += collided_dog.dx * 0.5
                 ball.y = collided_dog.rect.top - ball.radius - 1 # Move ball out of dog
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
                # Reset for next serve
                ball.reset(serve_side)
                game_state = 'serving' # Or directly to playing? Add delay?

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

    # --- Update Display ---
    pygame.display.flip()

    # --- Control Framerate ---
    clock.tick(FPS)

# --- End Game ---
pygame.quit()
sys.exit()