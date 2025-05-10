#!/usr/bin/env python3
import os
import sys
import random
import math
import threading
import pygame
import socketio

# ----------------------------------
# Pygame Initialization & Settings
# ----------------------------------
pygame.init()

surface = pygame.image.load("assets/images/worm2.png")
pygame.display.set_icon(surface)
# Screen & Board Constants
WIDTH, HEIGHT = 600, 600  
LINE_WIDTH = 20          
BOARD_ROWS, BOARD_COLS = 3, 3
SQUARE_SIZE = WIDTH // BOARD_COLS  
CIRCLE_RADIUS = SQUARE_SIZE // 3  
CIRCLE_WIDTH = 20        
CROSS_WIDTH = 40         
SPACE = SQUARE_SIZE // 4  

# Colors – Pink gummy bear theme
GRADIENT_TOP    = (255, 240, 245)
GRADIENT_BOTTOM = (255, 105, 180)
LINE_COLOR   = (255, 105, 180)
BUTTON_COLOR = (255, 105, 180)
TEXT_COLOR   = (80, 80, 80)
CROSS_COLOR  = (139, 0, 139)
CIRCLE_COLOR = (255, 20, 147)

# Fonts – Attempt to load a custom bubbly font; fallback to system fonts.
pygame.font.init()
try:
    font        = pygame.font.Font("assets/fonts/ComicNeue-Bold.ttf", 40)
    menu_font   = pygame.font.Font("assets/fonts/ComicNeue-Bold.ttf", 100)
    button_font = pygame.font.Font("assets/fonts/ComicNeue-Bold.ttf", 30)
except:
    font        = pygame.font.SysFont("arial", 80)
    menu_font   = pygame.font.SysFont("arial", 100)
    button_font = pygame.font.SysFont("arial", 30)

# Set up the display window.
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tic Tac Toe")

# Initialize sound.
pygame.mixer.init()
try:
    pencil_sound = pygame.mixer.Sound("assets/sounds/draw2.mp3")
    pencil_sound.set_volume(0.3)
except Exception as e:
    pencil_sound = None
    print("Warning: pencil_sound could not be loaded.", e)

# Global game board (3x3 matrix) and game mode settings.
board = [[None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
mode = "pve"         # Options: "pve", "pvp", "online"
difficulty = "hard"  # Default difficulty for PvE

# ----------------------------------
# Socket.IO Client (Online Networking)
# ----------------------------------
sio = socketio.Client()
remote_move = None
your_mark = None
opponent_mark = None
room_code_global = None

@sio.event
def connect():
    print("Connected to the server.")

@sio.event
def disconnect():
    print("Disconnected from the server.")

@sio.on('mark')
def handle_mark(data):
    global your_mark, opponent_mark
    your_mark = data.get("mark")
    opponent_mark = "O" if your_mark == "X" else "X"
    print(f"Assigned mark: {your_mark}")

@sio.on('move')
def handle_move(data):
    global remote_move
    row = data.get("row")
    col = data.get("col")
    remote_move = (row, col)
    print(f"Received move: row {row}, col {col}")

@sio.on('start')
def on_start(data):
    print("Game starting! " + data.get("message", ""))

@sio.on('error')
def on_error(data):
    print("Error:", data.get("message"))

@sio.on('waiting')
def on_waiting(data):
    print(data.get("message"))

def connect_to_server(server_ip, server_port, room_code):
    global room_code_global
    room_code_global = room_code
    # If server_port is None, skip adding it.
    if server_port:
        server_url = f"https://{server_ip}:{server_port}"
    else:
        server_url = f"https://{server_ip}"
    sio.connect(server_url)
    sio.emit('join', {'room': room_code})


def send_move(row, col):
    if room_code_global is None:
        print("Room code is not set; cannot send move.")
        return
    sio.emit('move', {'room': room_code_global, 'row': row, 'col': col})

# ----------------------------------
# Drawing & UI Functions
# ----------------------------------
def fill_gradient(surface, top_color, bottom_color):
    height = surface.get_height()
    width = surface.get_width()
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

def draw_lines():
    for row in range(1, BOARD_ROWS):
        pygame.draw.line(screen, LINE_COLOR, (0, row * SQUARE_SIZE), (WIDTH, row * SQUARE_SIZE), LINE_WIDTH)
    for col in range(1, BOARD_COLS):
        pygame.draw.line(screen, LINE_COLOR, (col * SQUARE_SIZE, 0), (col * SQUARE_SIZE, HEIGHT), LINE_WIDTH)

def draw_figures(skip_cells=None):
    if skip_cells is None:
        skip_cells = []
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if (row, col) in skip_cells:
                continue  # Skip drawing this cell.
            if board[row][col] == "O":
                pygame.draw.circle(screen, CIRCLE_COLOR,
                    (int(col * SQUARE_SIZE + SQUARE_SIZE/2), int(row * SQUARE_SIZE + SQUARE_SIZE/2)),
                    CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif board[row][col] == "X":
                pygame.draw.line(screen, CROSS_COLOR,
                    (col * SQUARE_SIZE + SPACE, row * SQUARE_SIZE + SQUARE_SIZE - SPACE),
                    (col * SQUARE_SIZE + SQUARE_SIZE - SPACE, row * SQUARE_SIZE + SPACE),
                    CROSS_WIDTH)
                pygame.draw.line(screen, CROSS_COLOR,
                    (col * SQUARE_SIZE + SPACE, row * SQUARE_SIZE + SPACE),
                    (col * SQUARE_SIZE + SQUARE_SIZE - SPACE, row * SQUARE_SIZE + SQUARE_SIZE - SPACE),
                    CROSS_WIDTH)


def draw_turn_indicator(text):
    indicator = font.render(text, True, TEXT_COLOR)
    indicator_rect = indicator.get_rect(center=(WIDTH // 2, 50))
    screen.blit(indicator, indicator_rect)

def draw_button(surface, rect, text, font, bg_color, text_color, border_radius=10):
    pygame.draw.rect(surface, bg_color, rect, border_radius=border_radius)
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)

# ----------------------------------
# Splash Screen
# ----------------------------------
def splash_screen():
    # Fill the screen with a white background
    screen.fill((255, 255, 255))
    
    # Load the logo image with transparency preserved
    logo = pygame.image.load("assets/images/Pink_IN.png").convert_alpha()
    
    # Scale the logo down if needed; here it's scaled to half its original size.
    original_width, original_height = logo.get_width(), logo.get_height()
    new_size = (original_width // 2, original_height // 2)
    logo = pygame.transform.scale(logo, new_size)
    
    # Center the logo on the screen.
    logo_rect = logo.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    
    clock = pygame.time.Clock()
    
    # Fade-in loop: gradually increase the alpha from 0 to 255.
    for alpha in range(0, 256, 5):  # '5' gives a smooth increment. Adjust this step for speed.
        # Always refresh the white background.
        screen.fill((255, 255, 255))
        
        # Create a copy so that the original image remains unchanged.
        temp_logo = logo.copy()
        temp_logo.set_alpha(alpha)
        
        # Blit the semi-transparent logo to the screen.
        screen.blit(temp_logo, logo_rect)
        pygame.display.update()
        
        # Delay to control the fade speed; adjust delay for smoother or faster fade.
        pygame.time.delay(30)
        clock.tick(60)
    
    # After the fade-in is complete, display the final logo for 3 seconds.
    pygame.time.delay(3000)

# ----------------------------------
# Restart / Reset Game
# ----------------------------------
def restart_game():
    global board
    board = [[None for _ in range(BOARD_COLS)] for _ in range(BOARD_ROWS)]
    fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
    draw_lines()
    pygame.display.update()

# ----------------------------------
# Difficulty Selection (Optional)
# ----------------------------------
def select_difficulty():
    global difficulty
    diff_active = True
    easy_button   = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 60, 200, 50)
    medium_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 50)
    hard_button   = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 60, 200, 50)
    
    while diff_active:
        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        diff_text = font.render("Select Difficulty:", True, TEXT_COLOR)
        diff_rect = diff_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        screen.blit(diff_text, diff_rect)
        
        draw_button(screen, easy_button, "Easy", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, medium_button, "Medium", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, hard_button, "Hard", button_font, BUTTON_COLOR, TEXT_COLOR)
        
        pygame.display.update()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if easy_button.collidepoint(mouse_pos):
                    difficulty = "easy"
                    diff_active = False
                elif medium_button.collidepoint(mouse_pos):
                    difficulty = "medium"
                    diff_active = False
                elif hard_button.collidepoint(mouse_pos):
                    difficulty = "hard"
                    diff_active = False

# ----------------------------------
# Game Logic Functions
# ----------------------------------
def available_moves():
    return [(r, c) for r in range(BOARD_ROWS) for c in range(BOARD_COLS) if board[r][c] is None]

def check_winner():
    for row in range(BOARD_ROWS):
        if board[row][0] == board[row][1] == board[row][2] and board[row][0] is not None:
            return board[row][0]
    for col in range(BOARD_COLS):
        if board[0][col] == board[1][col] == board[2][col] and board[0][col] is not None:
            return board[0][col]
    if board[0][0] == board[1][1] == board[2][2] and board[0][0] is not None:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] and board[0][2] is not None:
        return board[0][2]
    if all(board[r][c] is not None for r in range(BOARD_ROWS) for c in range(BOARD_COLS)):
        return "Draw"
    return None

def minimax(depth, is_maximizing):
    winner = check_winner()
    if winner == "O":  # AI wins
        return 10 - depth  # Winning faster is better
    elif winner == "X":  # Player wins
        return depth - 10  # Losing later is better (forces mistakes)
    elif winner == "Draw":
        return 0  # Neutral value for draw

    if is_maximizing:
        best_score = -float("inf")
        for row, col in available_moves():
            board[row][col] = "O"
            score = minimax(depth + 1, False)
            board[row][col] = None
            best_score = max(best_score, score)
        return best_score
    else:
        best_score = float("inf")
        for row, col in available_moves():
            board[row][col] = "X"
            score = minimax(depth + 1, True)
            board[row][col] = None
            best_score = min(best_score, score)
        return best_score


def can_set_trap():
    for row, col in available_moves():
        board[row][col] = "O"  # Temporarily place AI move
        win_paths = 0  # Count how many ways this leads to a win
        
        # Check if making this move results in two simultaneous threats
        if check_winner() == "O":
            win_paths += 1  # First winning path detected
        
        # Now check for another potential win path after blocking
        opponent_moves = available_moves()
        for op_row, op_col in opponent_moves:
            board[op_row][op_col] = "X"  # Simulate opponent's best blocking move
            if check_winner() == "O":
                win_paths += 1  # Another winning path detected
            board[op_row][op_col] = None  # Undo opponent simulation
        
        board[row][col] = None  # Undo AI simulation
        
        if win_paths >= 2:
            return row, col  # If two threats exist, return this trap move
    
    return None  # No trap available

def ai_move():
    global difficulty
    if difficulty == "easy":
        moves = available_moves()
        if moves:
            return random.choice(moves)
    elif difficulty == "medium":
        if random.random() < 0.25:
            moves = available_moves()
            if moves:
                return random.choice(moves)
        best_score = -float("inf")
        best_move = None
        for row, col in available_moves():
            board[row][col] = "O"
            score = minimax(0, False)
            board[row][col] = None
            if score > best_score:
                best_score = score
                best_move = (row, col)
        return best_move
    else:  # Hard mode
        trap_move = can_set_trap()
        if trap_move:
            return trap_move  # Prioritize trapping the opponent
        
        # Otherwise, use standard minimax logic
        best_score = -float("inf")
        best_move = None
        for row, col in available_moves():
            board[row][col] = "O"
            score = minimax(0, False)
            board[row][col] = None
            if score > best_score:
                best_score = score
                best_move = (row, col)
        return best_move

def animate_move(row, col, mark):
    # Update the board immediately (if you prefer this approach)
    board[row][col] = mark  
    if pencil_sound:
        pencil_sound.play()
    steps = 20
    x0 = col * SQUARE_SIZE
    y0 = row * SQUARE_SIZE
    if mark == "X":
        start1 = (x0 + SPACE, y0 + SQUARE_SIZE - SPACE)
        end1   = (x0 + SQUARE_SIZE - SPACE, y0 + SPACE)
        start2 = (x0 + SPACE, y0 + SPACE)
        end2   = (x0 + SQUARE_SIZE - SPACE, y0 + SQUARE_SIZE - SPACE)
        for i in range(1, steps + 1):
            frac = i / steps
            current_end = (start1[0] + frac * (end1[0] - start1[0]),
                           start1[1] + frac * (end1[1] - start1[1]))
            fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
            draw_lines()
            # Skip drawing current cell—so the animated strokes aren’t overlaid by a complete mark.
            draw_figures(skip_cells=[(row, col)])
            pygame.draw.line(screen, CROSS_COLOR, start1, current_end, CROSS_WIDTH)
            pygame.display.update()
            pygame.time.wait(20)
        for i in range(1, steps + 1):
            frac = i / steps
            current_end = (start2[0] + frac * (end2[0] - start2[0]),
                           start2[1] + frac * (end2[1] - start2[1]))
            fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
            draw_lines()
            draw_figures(skip_cells=[(row, col)])
            pygame.draw.line(screen, CROSS_COLOR, start1, end1, CROSS_WIDTH)
            pygame.draw.line(screen, CROSS_COLOR, start2, current_end, CROSS_WIDTH)
            pygame.display.update()
            pygame.time.wait(20)
    elif mark == "O":
        rect = pygame.Rect(x0 + SPACE, y0 + SPACE, SQUARE_SIZE - 2 * SPACE, SQUARE_SIZE - 2 * SPACE)
        for i in range(1, steps + 1):
            angle = (360 / steps) * i
            fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
            draw_lines()
            draw_figures(skip_cells=[(row, col)])
            pygame.draw.arc(screen, CIRCLE_COLOR, rect, 0, math.radians(angle), CIRCLE_WIDTH)
            pygame.display.update()
            pygame.time.wait(20)
    # Finally, redraw everything normally.
    fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
    draw_lines()
    draw_figures()
    pygame.display.update()



# ----------------------------------
# Compute Current Turn (by counting marks)
# ----------------------------------
def compute_current_turn():
    move_count = sum(1 for row in board for cell in row if cell is not None)
    return "X" if move_count % 2 == 0 else "O"

# ----------------------------------
# Game Loops
# ----------------------------------
def pve_game_loop():
    global board
    restart_game()
    game_over = False
    pve_turn = "player"  # Player is X, AI is O.
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if not game_over:
                if pve_turn == "player" and event.type == pygame.MOUSEBUTTONDOWN:
                    mouseX, mouseY = event.pos
                    clicked_row = mouseY // SQUARE_SIZE
                    clicked_col = mouseX // SQUARE_SIZE
                    if board[clicked_row][clicked_col] is None:
                        animate_move(clicked_row, clicked_col, "X")
                        winner = check_winner()
                        if winner:
                            game_over = True
                            outcome = draw_restart_menu(winner)
                            if outcome == "restart":
                                restart_game()
                                game_over = False
                                pve_turn = "player"
                            elif outcome == "menu":
                                return
                        else:
                            pve_turn = "ai"
        if not game_over and pve_turn == "ai":
            pygame.time.wait(500)
            move = ai_move()
            if move:
                animate_move(move[0], move[1], "O")
                winner = check_winner()
                if winner:
                    game_over = True
                    outcome = draw_restart_menu(winner)
                    if outcome == "restart":
                        restart_game()
                        game_over = False
                        pve_turn = "player"
                    elif outcome == "menu":
                        return
                else:
                    pve_turn = "player"
        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        draw_lines()
        draw_figures()
        if not game_over:
            indicator_text = "Your Turn (X)" if pve_turn == "player" else "AI's Turn (O)"
            draw_turn_indicator(indicator_text)
        pygame.display.update()
        clock.tick(30)

def pvp_game_loop():
    global board
    restart_game()
    game_over = False
    current_player = "X"
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if not game_over:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouseX, mouseY = event.pos
                    clicked_row = mouseY // SQUARE_SIZE
                    clicked_col = mouseX // SQUARE_SIZE
                    if board[clicked_row][clicked_col] is None:
                        animate_move(clicked_row, clicked_col, current_player)
                        winner = check_winner()
                        if winner:
                            game_over = True
                            outcome = draw_restart_menu(winner)
                            if outcome == "restart":
                                restart_game()
                                game_over = False
                                current_player = "X"
                            elif outcome == "menu":
                                return
                        else:
                            current_player = "O" if current_player == "X" else "X"
        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        draw_lines()
        draw_figures()
        if not game_over:
            indicator_text = f"Player {current_player} Turn"
            draw_turn_indicator(indicator_text)
        pygame.display.update()
        clock.tick(30)

def online_pvp_game_loop():
    global board, remote_move, your_mark, opponent_mark
    restart_game()
    game_over = False
    clock = pygame.time.Clock()
    while True:
        current_turn = compute_current_turn()  # "X" or "O"
        # Local input (only if it's your turn).
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if not game_over and current_turn == your_mark and event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = event.pos
                clicked_row = mouseY // SQUARE_SIZE
                clicked_col = mouseX // SQUARE_SIZE
                if board[clicked_row][clicked_col] is None:
                    animate_move(clicked_row, clicked_col, your_mark)
                    send_move(clicked_row, clicked_col)
                    winner = check_winner()
                    if winner:
                        game_over = True
                        outcome = draw_restart_menu(winner)
                        if outcome == "restart":
                            restart_game()
                            game_over = False
                        elif outcome == "menu":
                            return
        # Process remote move.
        # made by PinkGummyBear/Just_Vik
        if not game_over and current_turn == opponent_mark and remote_move is not None:
            r, c = remote_move
            if board[r][c] is None:
                animate_move(r, c, opponent_mark)
            winner = check_winner()
            if winner:
                game_over = True
                outcome = draw_restart_menu(winner)
                if outcome == "restart":
                    restart_game()
                    game_over = False
                elif outcome == "menu":
                    return
            remote_move = None

        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        draw_lines()
        draw_figures()
        if not game_over:
            indicator_text = f"Your Turn ({your_mark})" if current_turn == your_mark else f"Opponent's Turn ({opponent_mark})"
            draw_turn_indicator(indicator_text)
        pygame.display.update()
        clock.tick(30)

# ----------------------------------
# UI Menus
# ----------------------------------
def main_menu():
    global mode, difficulty
    menu_active = True
    pve_button    = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 120, 200, 50)
    pvp_button    = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 60, 200, 50)
    online_button = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2, 200, 50)
    quit_button   = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 60, 200, 50)
    
    while menu_active:
        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        title_text = menu_font.render("Tic Tac Toe", True, TEXT_COLOR)
        title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 5))
        screen.blit(title_text, title_rect)
        draw_button(screen, pve_button, "Player vs AI", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, pvp_button, "Player vs Player", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, online_button, "Online Multiplayer", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, quit_button, "Quit", button_font, BUTTON_COLOR, TEXT_COLOR)
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if pve_button.collidepoint(mouse_pos):
                    mode = "pve"
                    select_difficulty()
                    menu_active = False
                elif pvp_button.collidepoint(mouse_pos):
                    mode = "pvp"
                    menu_active = False
                elif online_button.collidepoint(mouse_pos):
                    mode = "online"
                    menu_active = False
                elif quit_button.collidepoint(mouse_pos):
                    pygame.quit(); sys.exit()

def room_menu():
    joining = False
    typed_code = ""
    create_room_button = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 100, 300, 50)
    join_room_button   = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 30, 300, 50)
    back_button        = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 40, 300, 50)
    room_menu_active = True
    result_mode = None     # "create" or "join"
    room_code = ""
    
    while room_menu_active:
        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        title_text = menu_font.render("Room Menu", True, TEXT_COLOR)
        title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//3 - 50))
        screen.blit(title_text, title_rect)
        draw_button(screen, create_room_button, "Create Room", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, join_room_button, "Join Room", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, back_button, "Back", button_font, BUTTON_COLOR, TEXT_COLOR)
        
        if joining:
            prompt_text = button_font.render("Enter Room Code: " + typed_code, True, TEXT_COLOR)
            prompt_rect = prompt_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 120))
            screen.blit(prompt_text, prompt_rect)
        
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if create_room_button.collidepoint(mouse_pos):
                    result_mode = "create"
                    room_code = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
                    room_menu_active = False
                    break
                elif join_room_button.collidepoint(mouse_pos):
                    joining = True
                elif back_button.collidepoint(mouse_pos):
                    result_mode = None
                    room_menu_active = False
                    break
            if event.type == pygame.KEYDOWN and joining:
                if event.key == pygame.K_RETURN:
                    if typed_code != "":
                        result_mode = "join"
                        room_code = typed_code
                        room_menu_active = False
                        break
                elif event.key == pygame.K_BACKSPACE:
                    typed_code = typed_code[:-1]
                else:
                    typed_code += event.unicode
    return result_mode, room_code

def display_room_info(room_code, selection):
    fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
    if selection == "create":
        message = "Room Created!\nCode: " + room_code + "\nShare this code with a friend."
    else:
        message = "Joining Room:\n" + room_code
    lines = message.split("\n")
    for idx, line in enumerate(lines):
        line_surf = button_font.render(line, True, TEXT_COLOR)
        line_rect = line_surf.get_rect(center=(WIDTH//2, HEIGHT//2 - 40 + idx * 40))
        screen.blit(line_surf, line_rect)
    pygame.display.update()
    wait_time = 3000  # milliseconds
    start_ticks = pygame.time.get_ticks()
    while pygame.time.get_ticks() - start_ticks < wait_time:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                return
        pygame.time.wait(100)

def draw_restart_menu(winner):
    menu_active = True
    restart_button = pygame.Rect(WIDTH//2 - 150, HEIGHT//2, 300, 50)
    menu_button = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 + 70, 300, 50)
    while menu_active:
        fill_gradient(screen, GRADIENT_TOP, GRADIENT_BOTTOM)
        win_text = menu_font.render(f"{winner} Wins!" if winner != "Draw" else "It's a Draw!", True, TEXT_COLOR)
        win_rect = win_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        screen.blit(win_text, win_rect)
        draw_button(screen, restart_button, "Restart", button_font, BUTTON_COLOR, TEXT_COLOR)
        draw_button(screen, menu_button, "Main Menu", button_font, BUTTON_COLOR, TEXT_COLOR)
        pygame.display.update()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if restart_button.collidepoint(mouse_pos):
                    return "restart"
                elif menu_button.collidepoint(mouse_pos):
                    return "menu"

# ----------------------------------
# Main Function
# ----------------------------------
def main():
    splash_screen()
    while True:
        main_menu()
        if mode == "pve":
            pve_game_loop()
        elif mode == "pvp":
            pvp_game_loop()
        elif mode == "online":
            selection, room_code = room_menu()
            if not room_code:
                continue
            display_room_info(room_code, selection)
            # Replace with your Render service hostname.
            server_ip = "server"
            # Optionally remove the port if not needed – ensure connect_to_server handles a None port appropriately.
            connect_to_server(server_ip, None, room_code)
            # Wait for the server to assign a mark.
            while your_mark is None:
                pygame.time.wait(100)
            online_pvp_game_loop()

if __name__ == "__main__":
    main()
