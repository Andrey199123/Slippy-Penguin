# Andrey Vasilyev, April 26th, 2025
import pygame
import pytmx
import sys
import os
import random
import math
import itertools
import pygame.mixer
import numpy as np

# CONSTANTS
OUTPUT_TMX_FILE = 'map.tmx'
TILESET_SOURCE = 'graphics.tsx'
ACTIVE_MAP_WIDTH_TILES = 11
ACTIVE_MAP_HEIGHT_TILES = 200
PADDING_TILES = 15
DOT_VISUAL_OFFSET_X_PX = -15
DOT_VISUAL_OFFSET_Y_PX = -130
TOTAL_MAP_WIDTH_TILES = ACTIVE_MAP_WIDTH_TILES + 2 * PADDING_TILES
TOTAL_MAP_HEIGHT_TILES = ACTIVE_MAP_HEIGHT_TILES + 2 * PADDING_TILES
OFFSET_X = PADDING_TILES
OFFSET_Y = PADDING_TILES
MAP_WIDTH_TILES = ACTIVE_MAP_WIDTH_TILES
MAP_HEIGHT_TILES = ACTIVE_MAP_HEIGHT_TILES
MAX_Z_LEVEL = 5
PATH_Z_LEVEL = 1
BACKGROUND_Z_LEVEL = 0
TILE_WIDTH_PX = 111
TILE_HEIGHT_PX = 128
ISO_TILE_WIDTH_HALF = TILE_WIDTH_PX / 2.3
ISO_TILE_STEP_HEIGHT_HALF = (TILE_WIDTH_PX / 2.0) / 2.0
TILE_Z_STEP_PX = TILE_HEIGHT_PX / 6.0
INITIAL_PATH_X_RELATIVE = MAP_WIDTH_TILES // 2
MIN_SEGMENT_LENGTH = 2
MAX_SEGMENT_LENGTH = 10
TURN_PROBABILITY = 0.8
BRANCH_PROBABILITY = 0.30
MIN_BRANCH_LENGTH = 1
MAX_BRANCH_LENGTH = 4
BRANCH_TURN_PROBABILITY = 0.7
MAX_BRANCH_TOTAL_STEPS = 10
WATER_TILE_LOCAL_ID = 23
WATER_TILE_LOCAL_ID_ALT1 = 24
WATER_TILE_LOCAL_ID_ALT2 = 25
PATH_TILE_LOCAL_ID = 5
OUTER_BG_TILE_LOCAL_ID = 1
WATER_PROB_BASE = 0.85
WATER_PROB_ALT1 = 0.10
WATER_PROB_ALT2 = 0.05
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
WINDOW_TITLE = "Generated Slippy Terrain - Score"
FPS = 60
choose = random.randint(1, 2)
BG_IMAGE_FILE = 'bg' + str(choose) + '.png'
BG_SCROLL_SPEED = 50
DOT_Z_LEVEL = PATH_Z_LEVEL
CAMERA_FOLLOW_SMOOTHING = 0.05
CAMERA_TARGET_SCREEN_X_FRAC = 0.5
CAMERA_TARGET_SCREEN_Y_FRAC = 0.7
TILESET_FIRST_GID = 1
TILESET_NAME = os.path.splitext(TILESET_SOURCE)[0]
BASE_LAYER_NAME = "Terrain"
GAME_OVER_FONT_SIZE = 72
RESTART_FONT_SIZE = 36
FONT_COLOR = (255, 255, 255)
INITIAL_SPEED_TILES_PER_SEC = 2.0
MAX_SPEED_TILES_PER_SEC = 15.0
ACCELERATION_TILES_PER_SEC2 = 0.3
DOT_INITIAL_DIRECTION = (0, -1)
MAP_DIR_UP = (0, -1)
MAP_DIR_DOWN = (0, 1)
MAP_DIR_LEFT = (-1, 0)
MAP_DIR_RIGHT = (1, 0)
lose_sound_already_played = False

# SNOW
SNOW_SPAWN_RATE_FPS = 120
SNOW_MAX_PARTICLES = 350
SNOW_RADIUS_MIN, SNOW_RADIUS_MAX = 2, 4
SNOW_GRAVITY_PX_S = 90
SNOW_WIND_DRIFT_PX_S = 25

# SPRITE IMAGES
PENGUIN_IMG_FORWARD = 'forward.png'
PENGUIN_IMG_LEFT = 'left.png'
PENGUIN_IMG_RIGHT = 'right.png'
PENGUIN_SCALE_FACTOR = 0.6

# SCOREBOARD
SCORE_FONT_SIZE = 36
HIGHSCORE_FONT_SIZE = 24
SCORE_COLOR = (255, 255, 0)
HIGHSCORE_COLOR = (200, 200, 200)
SCORE_POS_X = SCREEN_WIDTH - 10
SCORE_POS_Y = 10
HIGHSCORE_POS_Y = SCORE_POS_Y + SCORE_FONT_SIZE + 5
HIGHSCORE_FILENAME = "highscore.txt"


class SnowSystem:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.particles = []
        self._time_accum = 0.0

    def _spawn(self):
        x = random.uniform(0, self.w)
        y = random.uniform(-20, -5)
        rad = random.randint(SNOW_RADIUS_MIN, SNOW_RADIUS_MAX)
        vx = random.uniform(-SNOW_WIND_DRIFT_PX_S, SNOW_WIND_DRIFT_PX_S)
        vy = random.uniform(0.6, 1.0) * SNOW_GRAVITY_PX_S
        self.particles.append([x, y, rad, vx, vy])

    def update(self, dt):
        self._time_accum += dt * SNOW_SPAWN_RATE_FPS
        while self._time_accum >= 1 and len(self.particles) < SNOW_MAX_PARTICLES:
            self._spawn()
            self._time_accum -= 1
        alive = []
        for p in self.particles:
            p[0] += p[3] * dt
            p[1] += p[4] * dt
            if p[1] < self.h + 10:
                alive.append(p)
        self.particles = alive

    def draw(self, surf):
        for x, y, r, *_ in self.particles:
            pygame.draw.circle(surf, (255, 255, 255), (int(x), int(y)), int(r))


# HELPER FUNCTIONS
def pitch_shift(sound: pygame.mixer.Sound, semitones: float) -> pygame.mixer.Sound:
    """
    Shifts the milestone.wav file higher in pitch the higher the score.
    """
    if semitones == 0:
        return sound
    arr = pygame.sndarray.array(sound)
    orig_dtype = arr.dtype
    factor = 2 ** (semitones / 12.0)
    n_samples = arr.shape[0]
    new_len = max(1, int(n_samples / factor))
    old_idx = np.arange(n_samples, dtype=np.float32)
    new_idx = np.linspace(0, n_samples - 1, new_len, dtype=np.float32)
    if arr.ndim == 1:
        resampled = np.interp(new_idx, old_idx, arr).astype(np.float32)
    else:
        channels = []
        for ch in range(arr.shape[1]):
            channels.append(
                np.interp(new_idx, old_idx, arr[:, ch]).astype(np.float32)
            )
        resampled = np.stack(channels, axis=1)
    if np.issubdtype(orig_dtype, np.integer):
        limits = np.iinfo(orig_dtype)
        resampled = np.clip(resampled, limits.min, limits.max).astype(orig_dtype)
    else:
        resampled = resampled.astype(orig_dtype)
    return pygame.sndarray.make_sound(resampled.copy())


def format_csv(grid_data, width):
    all_gids = list(itertools.chain.from_iterable(grid_data))
    all_gids_str = map(str, all_gids)
    return ',\n'.join(','.join(row) for row in grouper(all_gids_str, width))


def grouper(iterable, n, fillvalue='0'):
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def create_tmx_content(total_map_w, total_map_h, tile_w, tile_h, tsx_source, tsx_firstgid, tsx_name, layers_data):
    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<map version="1.9" tiledversion="1.9.2" orientation="isometric" staggeraxis="y" staggerindex="odd" renderorder="right-down" width="{total_map_w}" height="{total_map_h}" tilewidth="{tile_w}" tileheight="{tile_h}" infinite="0" nextlayerid="{len(layers_data) + 2}" nextobjectid="1">
 <tileset firstgid="{tsx_firstgid}" name="{tsx_name}" source="{tsx_source}"/>"""
    layer_xml_parts = []
    layer_id_counter = 2
    layers_data.sort(key=lambda l: l['z'])
    for layer_info in layers_data:
        layer_name = layer_info['name']
        z_level = layer_info['z']
        csv_data = layer_info['csv_data']
        layer_xml = f""" <layer id="{layer_id_counter}" name="{layer_name}" width="{total_map_w}" height="{total_map_h}">
  <properties>
   <property name="z_level" type="int" value="{z_level}"/>
  </properties>
  <data encoding="csv">
{csv_data}
  </data>
 </layer>"""
        layer_xml_parts.append(layer_xml)
        layer_id_counter += 1
    footer = "\n</map>"
    return header + "".join(layer_xml_parts) + footer


def generate_branch(tile_data, start_x, start_y, initial_dir, width, height, path_gid):
    branch_x, branch_y = start_x, start_y
    branch_z = PATH_Z_LEVEL
    branch_dir = initial_dir
    steps_taken = 0
    while steps_taken < MAX_BRANCH_TOTAL_STEPS:
        segment_len = random.randint(MIN_BRANCH_LENGTH, MAX_BRANCH_LENGTH)
        for _ in range(segment_len):
            next_x = branch_x + branch_dir[0]
            next_y = branch_y + branch_dir[1]
            if not (0 <= next_x < width and 0 <= next_y < height):
                return
            branch_x, branch_y = next_x, next_y
            tile_data[(branch_x, branch_y, branch_z)] = path_gid
            steps_taken += 1
            if steps_taken >= MAX_BRANCH_TOTAL_STEPS:
                return
        if random.random() < BRANCH_TURN_PROBABILITY:
            potential_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            reverse_dir = (-branch_dir[0], -branch_dir[1])
            if reverse_dir in potential_dirs:
                potential_dirs.remove(reverse_dir)
            valid_turns = []
            for turn in potential_dirs:
                check_x = branch_x + turn[0]
                check_y = branch_y + turn[1]
                if 0 <= check_x < width and 0 <= check_y < height:
                    valid_turns.append(turn)
            check_x = branch_x + branch_dir[0]
            check_y = branch_y + branch_dir[1]
            if 0 <= check_x < width and 0 <= check_y < height:
                valid_turns.append(branch_dir)
            if valid_turns:
                branch_dir = random.choice(valid_turns)
            else:
                return


def spawn_branch(tile_data, current_x, current_y, main_path_dir, width, height, path_gid):
    if random.random() < BRANCH_PROBABILITY:
        possible_branch_dirs = []
        if main_path_dir[0] == 0:
            if current_x - 1 >= 0:
                possible_branch_dirs.append(MAP_DIR_LEFT)
            if current_x + 1 < width:
                possible_branch_dirs.append(MAP_DIR_RIGHT)
        else:
            if current_y - 1 >= 0:
                possible_branch_dirs.append(MAP_DIR_UP)
            if current_y + 1 < height:
                possible_branch_dirs.append(MAP_DIR_DOWN)
        if possible_branch_dirs:
            chosen_branch_dir = random.choice(possible_branch_dirs)
            branch_start_x = current_x + chosen_branch_dir[0]
            branch_start_y = current_y + chosen_branch_dir[1]
            if 0 <= branch_start_x < width and 0 <= branch_start_y < height:
                tile_data[(branch_start_x, branch_start_y, PATH_Z_LEVEL)] = path_gid
                generate_branch(tile_data, branch_start_x, branch_start_y, chosen_branch_dir, width, height, path_gid)


def segmented_path(active_width, active_height, start_x_rel, min_len, max_len, turn_prob, init_dir,
                   water_base_gid, path_gid):
    if not (0 <= start_x_rel < active_width):
        start_x_rel = max(0, min(active_width - 1, start_x_rel))
    water_gid_alt1 = water_base_gid + (WATER_TILE_LOCAL_ID_ALT1 - WATER_TILE_LOCAL_ID)
    water_gid_alt2 = water_base_gid + (WATER_TILE_LOCAL_ID_ALT2 - WATER_TILE_LOCAL_ID)
    water_choices = [(water_gid_alt1, WATER_PROB_ALT1), (water_gid_alt2, WATER_PROB_ALT1 + WATER_PROB_ALT2)]
    tile_data_3d = {}
    for y in range(active_height):
        for x in range(active_width):
            rand_val = random.random()
            chosen_water_gid = water_base_gid
            if rand_val < water_choices[0][1]:
                chosen_water_gid = water_choices[0][0]
            elif rand_val < water_choices[1][1]:
                chosen_water_gid = water_choices[1][0]
            tile_data_3d[(x, y, BACKGROUND_Z_LEVEL)] = chosen_water_gid
    current_x = start_x_rel
    current_y = active_height - 1
    current_z = PATH_Z_LEVEL
    direction = init_dir
    path_tiles_generated = 0
    max_path_tiles = active_width * active_height
    while 0 <= current_y and path_tiles_generated < max_path_tiles:
        if 0 <= current_x < active_width:
            tile_data_3d[(current_x, current_y, current_z)] = path_gid
            path_tiles_generated += 1
        else:
            break
        spawn_branch(tile_data_3d, current_x, current_y, direction, active_width, active_height, path_gid)
        segment_length = random.randint(min_len, max_len)
        for i in range(segment_length):
            next_x = current_x + direction[0]
            next_y = current_y + direction[1]
            if next_y < 0:
                current_y = next_y
                break
            if not (0 <= next_x < active_width):
                break
            current_x = next_x
            current_y = next_y
            tile_data_3d[(current_x, current_y, current_z)] = path_gid
            path_tiles_generated += 1
            if i < segment_length - 1:
                spawn_branch(tile_data_3d, current_x, current_y, direction, active_width,
                             active_height, path_gid)
        if current_y < 0:
            break
        if direction[0] != 0:
            direction = MAP_DIR_UP
        elif random.random() < turn_prob:
            possible_turns = []
            if current_x - 1 >= 0:
                possible_turns.append(MAP_DIR_LEFT)
            if current_x + 1 < active_width:
                possible_turns.append(MAP_DIR_RIGHT)
            if possible_turns:
                direction = random.choice(possible_turns)
    return tile_data_3d


def generate_and_save_tmx():
    water_base_gid = TILESET_FIRST_GID + WATER_TILE_LOCAL_ID
    path_gid = TILESET_FIRST_GID + PATH_TILE_LOCAL_ID
    active_tile_data = segmented_path(MAP_WIDTH_TILES, MAP_HEIGHT_TILES, INITIAL_PATH_X_RELATIVE,
                                      MIN_SEGMENT_LENGTH, MAX_SEGMENT_LENGTH, TURN_PROBABILITY,
                                      DOT_INITIAL_DIRECTION, water_base_gid, path_gid)
    z_levels_present = sorted(list(set(z for _, _, z in active_tile_data.keys())))
    if BACKGROUND_Z_LEVEL not in z_levels_present:
        z_levels_present.insert(0, BACKGROUND_Z_LEVEL)
    if PATH_Z_LEVEL not in z_levels_present and any(
            gid == path_gid for gid in active_tile_data.values()):
        z_levels_present.append(PATH_Z_LEVEL)
    z_levels_present.sort()
    layers_data = []
    for z in z_levels_present:
        layer_grid = [[0 for _ in range(TOTAL_MAP_WIDTH_TILES)] for _ in range(TOTAL_MAP_HEIGHT_TILES)]
        for total_y in range(TOTAL_MAP_HEIGHT_TILES):
            for total_x in range(TOTAL_MAP_WIDTH_TILES):
                gid = 0
                is_in_active_area = (
                        OFFSET_X <= total_x < OFFSET_X + ACTIVE_MAP_WIDTH_TILES and OFFSET_Y <= total_y < OFFSET_Y + ACTIVE_MAP_HEIGHT_TILES)
                if is_in_active_area:
                    active_x = total_x - OFFSET_X
                    active_y = total_y - OFFSET_Y
                    gid = active_tile_data.get((active_x, active_y, z), 0)
                layer_grid[total_y][total_x] = gid
        csv_layer_data = format_csv(layer_grid, TOTAL_MAP_WIDTH_TILES)
        layer_name = f"{BASE_LAYER_NAME}_Z{z}"
        if z == BACKGROUND_Z_LEVEL:
            layer_name += "_Background"
        elif z == PATH_Z_LEVEL:
            layer_name += "_Path"
        layers_data.append({'name': layer_name, 'z': z, 'csv_data': csv_layer_data})
    tmx_xml = create_tmx_content(TOTAL_MAP_WIDTH_TILES, TOTAL_MAP_HEIGHT_TILES, TILE_WIDTH_PX, TILE_HEIGHT_PX,
                                 TILESET_SOURCE, TILESET_FIRST_GID, TILESET_NAME, layers_data)
    with open(OUTPUT_TMX_FILE, 'w', encoding='utf-8') as f:
        f.write(tmx_xml)
    return True, path_gid, active_tile_data


def map_to_screen_anchor(map_x, map_y, map_z):
    screen_x = (map_x - map_y) * ISO_TILE_WIDTH_HALF
    screen_y = (map_x + map_y) * ISO_TILE_STEP_HEIGHT_HALF
    screen_y -= map_z * TILE_Z_STEP_PX
    return screen_x, screen_y


def draw_text(surface, text, size, x, y, color, align="center"):
    try:
        font = pygame.font.Font("8-BIT WONDER.TTF", size)
        text_surface = font.render(text, True, color)
        if align == "center":
            text_rect = text_surface.get_rect(center=(x, y))
        elif align == "topleft":
            text_rect = text_surface.get_rect(topleft=(x, y))
        elif align == "topright":
            text_rect = text_surface.get_rect(topright=(x, y))
        else:
            text_rect = text_surface.get_rect(center=(x, y))
        surface.blit(text_surface, text_rect)
    except FileNotFoundError:
        font = pygame.font.Font(None, size)  # Use default font
        text_surface = font.render(text, True, color)
        if align == "center":
            text_rect = text_surface.get_rect(center=(x, y))
        elif align == "topleft":
            text_rect = text_surface.get_rect(topleft=(x, y))
        elif align == "topright":
            text_rect = text_surface.get_rect(topright=(x, y))
        else:
            text_rect = text_surface.get_rect(center=(x, y))
        surface.blit(text_surface, text_rect)


def main(path_gid, active_tile_data):
    global lose_sound_already_played

    # SOUND INITIALIZATION
    pygame.mixer.init()
    ambient_wind = pygame.mixer.Sound("wind.wav")
    turn_sfx = pygame.mixer.Sound("turn.mp3")
    lose_sfx = pygame.mixer.Sound("lose.mp3")
    milestone_raw = pygame.mixer.Sound("milestone.wav")
    ambient_wind.set_volume(0.30)
    ambient_wind.play(loops=-1)

    milestone_count = 0
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(f"{WINDOW_TITLE}")
    clock = pygame.time.Clock()
    snow = SnowSystem(SCREEN_WIDTH, SCREEN_HEIGHT)
    with open(HIGHSCORE_FILENAME, 'r') as f:
        txt = f.read().strip()
        high_score = int(txt) if txt else 0
    new_highscore_achieved = False
    original_img_fwd = pygame.image.load(PENGUIN_IMG_FORWARD).convert_alpha()
    original_img_left = pygame.image.load(PENGUIN_IMG_LEFT).convert_alpha()
    original_img_right = pygame.image.load(PENGUIN_IMG_RIGHT).convert_alpha()

    def scale_image(img, factor):
        orig_w, orig_h = img.get_size()
        new_w = int(orig_w * factor)
        new_h = int(orig_h * factor)
        return pygame.transform.smoothscale(img, (new_w, new_h))

    scaled_img_fwd = scale_image(original_img_fwd, PENGUIN_SCALE_FACTOR)
    scaled_img_left = scale_image(original_img_left, PENGUIN_SCALE_FACTOR)
    scaled_img_right = scale_image(original_img_right, PENGUIN_SCALE_FACTOR)
    penguin_images = {
        MAP_DIR_UP: scaled_img_fwd,
        MAP_DIR_DOWN: scaled_img_fwd,
        MAP_DIR_LEFT: scaled_img_left,
        MAP_DIR_RIGHT: scaled_img_right
    }
    tiled_map = pytmx.util_pygame.load_pygame(OUTPUT_TMX_FILE, pixelalpha=True)
    bg_image = pygame.image.load(
        BG_IMAGE_FILE).convert()
    bg_width = bg_image.get_width()
    bg_tiles_needed = math.ceil(SCREEN_WIDTH / bg_width) + 1
    bg_scroll = 0
    game_state = "playing"
    start_map_y = (ACTIVE_MAP_HEIGHT_TILES - 1) + OFFSET_Y
    player_precise_map_x = float(INITIAL_PATH_X_RELATIVE + OFFSET_X) + 0.5
    player_precise_map_y = float(start_map_y) + 0.5
    player_map_z = PATH_Z_LEVEL
    player_direction = DOT_INITIAL_DIRECTION
    time_elapsed_seconds = 0.0
    lowest_y_reached = start_map_y
    score = 0

    # CAMERA
    initial_anchor_x_raw, initial_anchor_y_raw = map_to_screen_anchor(player_precise_map_x, player_precise_map_y,
                                                                      player_map_z)
    camera_x = initial_anchor_x_raw - SCREEN_WIDTH * CAMERA_TARGET_SCREEN_X_FRAC
    camera_y = initial_anchor_y_raw - SCREEN_HEIGHT * CAMERA_TARGET_SCREEN_Y_FRAC

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        if dt == 0:
            continue
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if game_state == "game_over":
                    if event.key == pygame.K_r:
                        lose_sound_already_played = False
                        return True
                    elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        return False
                elif game_state == "playing":
                    requested_direction = None
                    if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        requested_direction = MAP_DIR_LEFT
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        requested_direction = MAP_DIR_RIGHT
                    elif event.key == pygame.K_UP or event.key == pygame.K_w:
                        requested_direction = MAP_DIR_UP
                    if requested_direction is not None and requested_direction != player_direction:
                        player_direction = requested_direction
                        turn_sfx.play()
                    # backwards functionality: elif event.key == pygame.K_DOWN or event.key == pygame.K_s: requested_direction = MAP_DIR_DOWN
                    if requested_direction is not None and requested_direction != player_direction:
                        # Prevent 180 turns:
                        # is_reverse = (requested_direction[0] == -player_direction[0] and
                        #               requested_direction[1] == -player_direction[1])
                        # if not is_reverse:
                        player_direction = requested_direction
        if game_state == "playing":
            if score > 0 and score % 25 == 0:
                new_count = score // 25
                if new_count > milestone_count:
                    milestone_count = new_count
                    pitch_up = pitch_shift(milestone_raw, semitones=milestone_count)
                    pitch_up.play()
            time_elapsed_seconds += dt
            current_speed = min(MAX_SPEED_TILES_PER_SEC,
                                INITIAL_SPEED_TILES_PER_SEC + time_elapsed_seconds * ACCELERATION_TILES_PER_SEC2)
            move_distance = current_speed * dt
            next_precise_map_x = player_precise_map_x + player_direction[0] * move_distance
            next_precise_map_y = player_precise_map_y + player_direction[1] * move_distance
            logical_map_x = int(next_precise_map_x)
            logical_map_y = int(next_precise_map_y)

            # UPDATE SCORE
            if logical_map_y < lowest_y_reached:
                lowest_y_reached = logical_map_y
                score = start_map_y - lowest_y_reached

            # COLLISIONS
            if (OFFSET_X <= logical_map_x < OFFSET_X + ACTIVE_MAP_WIDTH_TILES and
                    OFFSET_Y <= logical_map_y < OFFSET_Y + ACTIVE_MAP_HEIGHT_TILES):
                active_x = logical_map_x - OFFSET_X
                active_y = logical_map_y - OFFSET_Y
                gid_on_path = active_tile_data.get((active_x, active_y, PATH_Z_LEVEL), 0)
                if gid_on_path == path_gid:
                    player_precise_map_x = next_precise_map_x
                    player_precise_map_y = next_precise_map_y
                else:
                    player_precise_map_x = next_precise_map_x
                    player_precise_map_y = next_precise_map_y
                    game_state = "game_over"
            else:
                player_precise_map_x = next_precise_map_x
                player_precise_map_y = next_precise_map_y
                game_state = "game_over"
            if game_state == "game_over":
                if score > high_score:
                    high_score = score
                    with open(HIGHSCORE_FILENAME, 'w') as f:
                        f.write(str(high_score))
                    new_highscore_achieved = True

            target_anchor_x_raw, target_anchor_y_raw = map_to_screen_anchor(player_precise_map_x, player_precise_map_y,
                                                                            player_map_z)
            target_cam_x = target_anchor_x_raw - SCREEN_WIDTH * CAMERA_TARGET_SCREEN_X_FRAC
            target_cam_y = target_anchor_y_raw - SCREEN_HEIGHT * CAMERA_TARGET_SCREEN_Y_FRAC
            camera_x += (target_cam_x - camera_x) * CAMERA_FOLLOW_SMOOTHING * (
                    60 * dt)
            camera_y += (target_cam_y - camera_y) * CAMERA_FOLLOW_SMOOTHING * (
                    60 * dt)
        snow.update(dt)
        screen.fill((0, 0, 0))
        current_bg_scroll_speed = BG_SCROLL_SPEED * dt
        bg_scroll -= current_bg_scroll_speed
        if abs(bg_scroll) > bg_width:
            bg_scroll = 0
        for i in range(0, bg_tiles_needed):
            screen.blit(bg_image, (i * bg_width + bg_scroll, 0))

        # DRAW TILES
        tiles_to_draw = []
        screen_rect = screen.get_rect()
        cull_buffer = max(TILE_WIDTH_PX, TILE_HEIGHT_PX) * 1.5
        visible_screen_rect_cull = screen_rect.inflate(cull_buffer, cull_buffer)
        for layer in tiled_map.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                map_z = layer.properties.get('z_level', 0)
                for map_x, map_y, gid in layer.iter_data():
                    if gid != 0:
                        anchor_x_raw, anchor_y_raw = map_to_screen_anchor(map_x, map_y, map_z)
                        final_anchor_x = anchor_x_raw - camera_x
                        final_anchor_y = anchor_y_raw - camera_y
                        if visible_screen_rect_cull.collidepoint(final_anchor_x, final_anchor_y):
                            blit_x = final_anchor_x - TILE_WIDTH_PX / 2
                            blit_y = final_anchor_y - TILE_HEIGHT_PX
                            tile_screen_rect = pygame.Rect(blit_x, blit_y, TILE_WIDTH_PX, TILE_HEIGHT_PX)
                            if tile_screen_rect.colliderect(screen_rect):
                                image = tiled_map.get_tile_image_by_gid(gid)
                                if image:
                                    tiles_to_draw.append({
                                        'sort_key': (map_x + map_y, map_z),
                                        'blit_pos': (blit_x, blit_y),
                                        'image': image
                                    })
        tiles_to_draw.sort(key=lambda t: t['sort_key'])
        for tile_data in tiles_to_draw:
            screen.blit(tile_data['image'], tile_data['blit_pos'])
        current_penguin_image = penguin_images.get(player_direction,
                                                   penguin_images[MAP_DIR_UP])
        player_anchor_x_raw, player_anchor_y_raw = map_to_screen_anchor(player_precise_map_x, player_precise_map_y,
                                                                        player_map_z)
        player_anchor_screen_x = player_anchor_x_raw - camera_x
        player_anchor_screen_y = player_anchor_y_raw - camera_y
        img_width = current_penguin_image.get_width()
        img_height = current_penguin_image.get_height()
        sprite_center_x = player_anchor_screen_x + DOT_VISUAL_OFFSET_X_PX
        sprite_center_y = player_anchor_screen_y + DOT_VISUAL_OFFSET_Y_PX
        blit_x = sprite_center_x - img_width / 2
        blit_y = sprite_center_y - img_height / 2
        screen.blit(current_penguin_image, (int(blit_x), int(blit_y)))
        snow.draw(screen)
        score_text = f"Score {score}"
        highscore_text = f"High {high_score}"
        draw_text(screen, score_text, SCORE_FONT_SIZE, SCORE_POS_X, SCORE_POS_Y, SCORE_COLOR, align="topright")
        draw_text(screen, highscore_text, HIGHSCORE_FONT_SIZE, SCORE_POS_X, HIGHSCORE_POS_Y, HIGHSCORE_COLOR,
                  align="topright")

        # GAME OVER SCREEN
        if game_state == "game_over":
            ambient_wind.fadeout(700)
            if not lose_sound_already_played:
                lose_sfx.play()
                lose_sound_already_played = True
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)  # Transparent
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            game_over_y_offset = -80
            draw_text(screen, "GAME OVER", GAME_OVER_FONT_SIZE, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + game_over_y_offset - 100, FONT_COLOR, align="center")
            final_score_text = f"Final Score {score}"
            draw_text(screen, final_score_text, RESTART_FONT_SIZE, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + 0 + game_over_y_offset, FONT_COLOR, align="center")
            if new_highscore_achieved:
                highscore_msg = "NEW HIGH SCORE"
                draw_text(screen, highscore_msg, RESTART_FONT_SIZE, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2 + 50 + game_over_y_offset, SCORE_COLOR, align="center")
            else:
                highscore_msg = f"High Score {high_score}"
                draw_text(screen, highscore_msg, RESTART_FONT_SIZE, SCREEN_WIDTH // 2,
                          SCREEN_HEIGHT // 2 + 50 + game_over_y_offset, FONT_COLOR, align="center")
            draw_text(screen, "Press R to Restart", RESTART_FONT_SIZE, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + 100 + game_over_y_offset, FONT_COLOR, align="center")
            draw_text(screen, "Press ESC to Exit", RESTART_FONT_SIZE // 2, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + 140 + game_over_y_offset, FONT_COLOR, align="center")
        pygame.display.flip()
    pygame.font.quit()
    return False


if __name__ == "__main__":
    required_files = [TILESET_SOURCE, BG_IMAGE_FILE, PENGUIN_IMG_FORWARD, PENGUIN_IMG_LEFT, PENGUIN_IMG_RIGHT]
    while True:
        success, path_gid_result, active_tile_data_result = generate_and_save_tmx()
        should_restart = main(path_gid_result, active_tile_data_result)
        if not should_restart:
            break
    pygame.quit()
    sys.exit()
