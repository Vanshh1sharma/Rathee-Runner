# game.py
# Single-file game with Modern Menu, Settings (volume & difficulty), save/load high score,
# one-window game. Place this file next to your assets/ folder.
#
# Run: python game.py

import pygame, os, random, json, sys, math
from typing import Tuple

# ---------------------------
# CONFIG / DEFAULTS
# ---------------------------
APP_TITLE = "Dog-Human Runner"
ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
SAVE_FILE = os.path.join(os.path.dirname(__file__), "save.json")
ICON_PATH = os.path.join(ASSET_DIR, "icon.png")  # optional

WIDTH, HEIGHT = 960, 540
GROUND_HEIGHT = 70
GROUND_Y = HEIGHT - GROUND_HEIGHT
FPS = 60

# Gameplay constants (base)
GRAVITY = 0.7
JUMP_FORCE = -14
PLAYER_START_SPEED_BASE = 4.0   # multiplied by difficulty modifier
SPEED_INCREASE_STEP = 0.5
SCORE_STEP = 10
PLAYER_MAX_HEALTH = 3

MIN_SPAWN_DIST = 600
MAX_SPAWN_DIST = 1100

PLAYER_SIZE = (96, 128)
ENEMY_SIZE = (96, 128)
BOX_SIZE = (64, 64)
POTION_SIZE = (40, 40)

# Settings defaults
DEFAULT_SETTINGS = {
    "volume": 0.6,                # 0.0 - 1.0
    "difficulty": "Normal"        # "Easy", "Normal", "Hard"
}

# Difficulty modifiers
DIFFICULTY_MOD = {
    "Easy": 0.85,
    "Normal": 1.0,
    "Hard": 1.25
}

# Potion spawn weights baseline (will be adjusted by difficulty)
POTION_BASE_WEIGHT = 0.05

# ---------------------------
# UTILS: asset loaders, save/load
# ---------------------------
def asset_path(name: str) -> str:
    return os.path.join(ASSET_DIR, name)

def load_image(name):
    path = asset_path(name)
    try:
        img = pygame.image.load(path)
        return img.convert_alpha()
    except Exception:
        print("[MISSING IMAGE]", name)
        return None

def load_sound(name):
    path = asset_path(name)
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        # print("[MISSING SOUND]", name)
        return None

def load_frames(prefix, count):
    frames = []
    for i in range(count):
        f = load_image(f"{prefix}_{i}.png")
        if f:
            frames.append(f)
    return frames

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("Failed to save", path, e)

# ---------------------------
# GLOBAL ASSETS (filled by load_all)
# ---------------------------
player_run_frames = []
player_idle_frames = []
player_jump_frame = None
player_dead_frame = None

enemy_run_frames = []
enemy_idle_frames = []
enemy_attack_frames = []
enemy_dead_frame = None

bg_img = None
logo_img = None
box_img = None
potion_img = None

player_jump_sfx = None
player_hit_sfx = None
player_heal_sfx = None
player_death_sfx = None
enemy_attack_sfx = None

music_path = asset_path("music.mp3")

# ---------------------------
# Load settings & save
# ---------------------------
settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS.copy())
save_data = load_json(SAVE_FILE, {"high_score": 0})

def apply_volume_to_all(vol):
    # adjust mixer and known sounds
    try:
        pygame.mixer.music.set_volume(vol * 0.6)
    except Exception:
        pass
    for s in (player_jump_sfx, player_hit_sfx, player_heal_sfx, player_death_sfx, enemy_attack_sfx):
        try:
            if s:
                s.set_volume(vol)
        except Exception:
            pass

# ---------------------------
# ASSET LOADER
# ---------------------------
def load_all():
    global player_run_frames, player_idle_frames, player_jump_frame, player_dead_frame
    global enemy_run_frames, enemy_idle_frames, enemy_attack_frames, enemy_dead_frame
    global bg_img, logo_img, box_img, potion_img
    global player_jump_sfx, player_hit_sfx, player_heal_sfx, player_death_sfx, enemy_attack_sfx

    print("Loading assets from:", ASSET_DIR)
    # player
    player_run_frames = load_frames("player_run", 6)
    player_idle_frames = load_frames("player_idle", 4)
    player_jump_frame = load_image("player_jump.png")
    player_dead_frame = load_image("player_dead.png")
    if player_run_frames:
        player_run_frames = [pygame.transform.smoothscale(f, PLAYER_SIZE) for f in player_run_frames]
    if player_idle_frames:
        player_idle_frames = [pygame.transform.smoothscale(f, PLAYER_SIZE) for f in player_idle_frames]
    if player_jump_frame:
        player_jump_frame = pygame.transform.smoothscale(player_jump_frame, PLAYER_SIZE)
    if player_dead_frame:
        player_dead_frame = pygame.transform.smoothscale(player_dead_frame, PLAYER_SIZE)

    # enemy
    enemy_run_frames = load_frames("enemy_run", 4)
    enemy_idle_frames = load_frames("enemy_idle", 2)
    enemy_attack_frames = load_frames("enemy_attack", 3)
    enemy_dead_frame = load_image("enemy_dead.png")
    if enemy_run_frames:
        enemy_run_frames = [pygame.transform.smoothscale(f, ENEMY_SIZE) for f in enemy_run_frames]
    if enemy_idle_frames:
        enemy_idle_frames = [pygame.transform.smoothscale(f, ENEMY_SIZE) for f in enemy_idle_frames]
    if enemy_attack_frames:
        enemy_attack_frames = [pygame.transform.smoothscale(f, ENEMY_SIZE) for f in enemy_attack_frames]
    if enemy_dead_frame:
        enemy_dead_frame = pygame.transform.smoothscale(enemy_dead_frame, ENEMY_SIZE)

    # env
    bg_img = load_image("bg.png")
    logo_img = load_image("logo.png")  # optional; used in menu if present
    box_img = load_image("box.png")
    potion_img = load_image("potion.png")
    if box_img:
        box_img = pygame.transform.smoothscale(box_img, BOX_SIZE)
    if potion_img:
        potion_img = pygame.transform.smoothscale(potion_img, POTION_SIZE)

    # sounds
    player_jump_sfx = load_sound("player_jump.wav")
    player_hit_sfx = load_sound("player_hit.wav")
    player_heal_sfx = load_sound("player_heal.wav")
    player_death_sfx = load_sound("player_death.wav")
    enemy_attack_sfx = load_sound("enemy_attack.wav")
    print("Assets loaded. Use console logs for missing assets.")

# ---------------------------
# UTILS
# ---------------------------
def world_to_screen_x(world_x, camera_x):
    return world_x - camera_x

def clamp(v, a, b):
    return max(a, min(b, v))

# ---------------------------
# ENTITY BASE and classes
# ---------------------------
class Entity:
    def __init__(self, world_x):
        self.world_x = world_x
    def update(self, dt, game): pass
    def draw(self, surf, camera_x): pass
    def rect(self, camera_x): return pygame.Rect(0,0,0,0)

class Player:
    def __init__(self, world_x):
        self.world_x = world_x
        self.y = GROUND_Y
        self.vel_y = 0.0
        self.state = "idle"   # idle, run, jump, dead
        self.frame = 0
        self.frame_timer = 0
        self.frame_speed = 100
        self.alive = True
        self.health = PLAYER_MAX_HEALTH

        fallback = pygame.Surface((80,110), pygame.SRCALPHA)
        fallback.fill((220,120,120))

        self.run_frames = player_run_frames or [fallback]
        self.idle_frames = player_idle_frames or [fallback]
        self.jump_frame = player_jump_frame or fallback
        self.dead_frame = player_dead_frame or fallback

        self.image = self.idle_frames[0]

    def on_ground(self):
        return self.y >= GROUND_Y

    def jump(self):
        if not self.alive: return
        if self.on_ground():
            # balanced jump
            self.vel_y = JUMP_FORCE * 1.10
            # small forward boost
            self.world_x += 10
            self.state = "jump"
            if player_jump_sfx:
                player_jump_sfx.play()

    def apply_gravity(self, dt):
        self.vel_y += GRAVITY * (dt/16.67)
        self.y += self.vel_y * (dt/16.67)
        if self.y >= GROUND_Y:
            self.y = GROUND_Y
            self.vel_y = 0
            if self.state == "jump":
                self.state = "run"

    def take_damage(self, amt=1):
        if not self.alive: return
        # silent final death
        if self.health == 1:
            self.health = 0
            self.alive = False
            self.state = "dead"
            self.frame = 0
            return
        self.health -= amt
        if player_hit_sfx:
            player_hit_sfx.play()
        if self.health <= 0:
            self.die()

    def heal(self, amt=1):
        if not self.alive: return
        self.health = min(PLAYER_MAX_HEALTH, self.health + amt)
        if player_heal_sfx:
            player_heal_sfx.play()

    def die(self):
        if not self.alive: return
        self.alive = False
        self.state = "dead"
        if player_death_sfx:
            player_death_sfx.play()

    def update_animation(self, dt):
        if self.state == "dead":
            self.image = self.dead_frame
            return
        if self.state == "jump":
            self.image = self.jump_frame
            return
        anim = self.run_frames if self.state == "run" else self.idle_frames
        self.frame_timer += dt
        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0
            self.frame = (self.frame + 1) % len(anim)
        self.image = anim[self.frame]

    def update(self, dt, game):
        self.apply_gravity(dt)
        if self.on_ground() and self.state not in ("dead","jump"):
            self.state = "run"
        self.update_animation(dt)
        # auto-run scaled by difficulty modifier
        self.world_x += game.speed * (dt/16.67)

    def draw(self, surf, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        if hasattr(self, "image") and self.image:
            r = self.image.get_rect(midbottom=(screen_x, self.y))
            surf.blit(self.image, r)
        else:
            pygame.draw.rect(surf, (255,100,100), (screen_x-20, self.y-60, 40, 60))

    def rect(self, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        if hasattr(self, "image") and self.image:
            return self.image.get_rect(midbottom=(screen_x, self.y))
        return pygame.Rect(screen_x-20, int(self.y-60), 40, 60)

class Enemy(Entity):
    def __init__(self, world_x):
        super().__init__(world_x)
        fallback = pygame.Surface((80,110), pygame.SRCALPHA)
        fallback.fill((180,50,50))
        self.frames = enemy_run_frames or [fallback]
        self.image = self.frames[0]
        self.frame = 0
        self.frame_timer = 0
        self.frame_speed = 140
        self.left = self.world_x - 120
        self.right = self.world_x + 120
        self.dir = -1
        self.speed = random.uniform(1.5, 2.5)

    def update(self, dt, game):
        # patrol
        self.world_x += self.dir * self.speed * (dt/16.67)
        if self.world_x < self.left:
            self.world_x = self.left
            self.dir = 1
        elif self.world_x > self.right:
            self.world_x = self.right
            self.dir = -1
        # animation
        self.frame_timer += dt
        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0
            self.frame = (self.frame + 1) % len(self.frames)
        self.image = self.frames[self.frame]

    def draw(self, surf, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        r = self.image.get_rect(midbottom=(screen_x, GROUND_Y))
        surf.blit(self.image, r)

    def rect(self, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        return self.image.get_rect(midbottom=(screen_x, GROUND_Y))

class Box(Entity):
    def __init__(self, world_x):
        super().__init__(world_x)
        self.image = box_img or pygame.Surface(BOX_SIZE)
        if box_img is None:
            self.image.fill((120,80,40))
    def update(self, dt, game): pass
    def draw(self, surf, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        r = self.image.get_rect(midbottom=(screen_x, GROUND_Y))
        surf.blit(self.image, r)
    def rect(self, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        return self.image.get_rect(midbottom=(screen_x, GROUND_Y))

class Potion(Entity):
    def __init__(self, world_x):
        super().__init__(world_x)
        self.image = potion_img or pygame.Surface(POTION_SIZE)
        if potion_img is None:
            self.image.fill((80,200,120))
    def update(self, dt, game): pass
    def draw(self, surf, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        r = self.image.get_rect(midbottom=(screen_x, GROUND_Y-10))
        surf.blit(self.image, r)
    def rect(self, camera_x):
        screen_x = world_to_screen_x(self.world_x, camera_x)
        return self.image.get_rect(midbottom=(screen_x, GROUND_Y-10))

# ---------------------------
# GAME (camera, spawn, logic)
# ---------------------------
class Game:
    def __init__(self, screen, settings_local):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.player = Player(100)
        self.camera_x = 0.0
        self.settings = settings_local
        # base speed multiplied by difficulty modifier
        self.base_speed = PLAYER_START_SPEED_BASE * DIFFICULTY_MOD.get(self.settings.get("difficulty","Normal"), 1.0)
        self.speed = self.base_speed
        self.score = 0
        self.last_milestone = -1
        self.entities = []
        self._seed_initial_world()
        # adjust potion weight by difficulty (hard = fewer potions)
        self.potion_weight = POTION_BASE_WEIGHT * (1.0 if self.settings.get("difficulty","Normal")=="Normal" else (0.8 if self.settings.get("difficulty","Normal")=="Easy" else 0.6))

    def _seed_initial_world(self):
        x = 600
        for i in range(5):
            t = random.choice(["box","enemy","potion"])
            if t=="box":
                self.entities.append(Box(x))
            elif t=="enemy":
                self.entities.append(Enemy(x))
            else:
                self.entities.append(Potion(x))
            x += random.randint(300, 500)

    def spawn_if_needed(self):
        furthest = max([e.world_x for e in self.entities] + [self.player.world_x])
        while furthest < self.camera_x + WIDTH + MIN_SPAWN_DIST:
            x = furthest + random.randint(MIN_SPAWN_DIST, MAX_SPAWN_DIST)
            # probabilities, potions rarer, affected by difficulty param
            weights = [0.60, 0.35, clamp(self.potion_weight, 0.02, 0.15)]
            typ = random.choices(["box","enemy","potion"], weights=weights)[0]
            if typ=="box": e = Box(x)
            elif typ=="enemy": e = Enemy(x)
            else: e = Potion(x)
            self.entities.append(e)
            furthest = x

    def update(self, dt):
        if not self.player.alive:
            return
        # update player
        self.player.update(dt, self)
        # camera follow: keep player at 35% screen
        self.camera_x = self.player.world_x - (WIDTH * 0.35)
        # update entities
        for e in list(self.entities):
            e.update(dt, self)
        # collisions
        p_rect = self.player.rect(self.camera_x)
        for e in list(self.entities):
            try:
                if p_rect.colliderect(e.rect(self.camera_x)):
                    if isinstance(e, Enemy):
                        if self.player.health == 1:
                            if enemy_attack_sfx:
                                enemy_attack_sfx.play()
                        self.player.take_damage()
                        try: self.entities.remove(e)
                        except: pass
                    elif isinstance(e, Box):
                        # box does not damage and does not disappear on touch
                        pass
                    elif isinstance(e, Potion):
                        self.player.heal()
                        try: self.entities.remove(e)
                        except: pass
            except Exception:
                pass
        # remove passed entities (score)
        for e in list(self.entities):
            if e.world_x < self.player.world_x - 220:
                # grant score if player passed
                if self.player.world_x > e.world_x:
                    self.score += 1
                try: self.entities.remove(e)
                except: pass
        # speed increase by score
        milestone = self.score // SCORE_STEP
        if milestone > self.last_milestone:
            self.last_milestone = milestone
            self.speed += SPEED_INCREASE_STEP
            if self.speed > 18: self.speed = 18
        # spawn more
        self.spawn_if_needed()

    def draw_background(self):
        if bg_img:
            bg_w = bg_img.get_width()
            scale = HEIGHT / bg_img.get_height()
            draw_w = int(bg_w * scale)
            bg_scaled = pygame.transform.smoothscale(bg_img, (draw_w, HEIGHT))
            offset = int(self.camera_x % draw_w)
            self.screen.blit(bg_scaled, (-offset, 0))
            # second tile
            if -offset + draw_w < WIDTH:
                self.screen.blit(bg_scaled, (-offset + draw_w, 0))
        else:
            self.screen.fill((120,180,255))

    def draw(self):
        self.draw_background()
        pygame.draw.rect(self.screen, (160,120,60), (0, GROUND_Y, WIDTH, GROUND_HEIGHT))
        # draw world objects (boxes, potions, enemies)
        # draw enemies last among objects to be under player? we'll draw all, then player on top
        for e in self.entities:
            e.draw(self.screen, self.camera_x)
        # player
        self.player.draw(self.screen, self.camera_x)
        # HUD
        self.draw_hud()
        pygame.display.flip()

    def draw_hud(self):
        font = pygame.font.Font(None, 36)
        s = font.render(f"Score: {self.score}", True, (255,255,255))
        self.screen.blit(s, (WIDTH-160, 12))
        for i in range(self.player.health):
            pygame.draw.rect(self.screen, (220,40,40), (12 + i*30, 12, 22, 22))
        if not self.player.alive:
            fbig = pygame.font.Font(None, 64)
            t = fbig.render("GAME OVER", True, (255,255,255))
            self.screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 80))
            finfo = pygame.font.Font(None, 28)
            rtxt = finfo.render("Press R to Restart  ·  ESC to Quit", True, (230,230,230))
            self.screen.blit(rtxt, (WIDTH//2 - rtxt.get_width()//2, HEIGHT//2 + 4))

# ---------------------------
# UI: Buttons & Menu
# ---------------------------
class Button:
    def __init__(self, rect:pygame.Rect, text:str, font:pygame.font.Font, base=(40,40,40), hover=(80,80,80), text_color=(255,255,255)):
        self.rect = rect
        self.text = text
        self.font = font
        self.base = base
        self.hover = hover
        self.text_color = text_color
        self.hovered = False

    def draw(self, surf):
        color = self.hover if self.hovered else self.base
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        text_s = self.font.render(self.text, True, self.text_color)
        surf.blit(text_s, (self.rect.centerx - text_s.get_width()//2, self.rect.centery - text_s.get_height()//2))

    def update_hover(self, mx, my):
        self.hovered = self.rect.collidepoint(mx, my)

    def is_clicked(self, mx, my):
        return self.rect.collidepoint(mx, my)

# ---------------------------
# Main App that orchestrates menu, settings, game
# ---------------------------
class App:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(APP_TITLE)
        # icon
        if os.path.isfile(ICON_PATH):
            try:
                pygame.display.set_icon(pygame.image.load(ICON_PATH))
            except Exception:
                pass
        # load assets & settings
        load_all()
        apply_volume_to_all(settings.get("volume", DEFAULT_SETTINGS["volume"]))
        # start music if present
        try:
            if os.path.isfile(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(settings.get("volume",0.6)*0.6)
                pygame.mixer.music.play(-1)
        except Exception:
            pass

        # Menu fonts
        self.font_large = pygame.font.Font(None, 72)
        self.font_med = pygame.font.Font(None, 40)
        self.font_small = pygame.font.Font(None, 28)
        # buttons
        btn_w, btn_h = 300, 64
        cx = WIDTH//2 - btn_w//2
        self.btn_start = Button(pygame.Rect(cx, 220, btn_w, btn_h), "Start Game", self.font_med)
        self.btn_settings = Button(pygame.Rect(cx, 300, btn_w, btn_h), "Settings", self.font_med)
        self.btn_quit = Button(pygame.Rect(cx, 380, btn_w, btn_h), "Quit", self.font_med)
        # settings UI elements (simple sliders)
        self.volume = settings.get("volume", DEFAULT_SETTINGS["volume"])
        self.difficulty = settings.get("difficulty", DEFAULT_SETTINGS["difficulty"])
        # persistent high score
        self.high_score = save_data.get("high_score", 0)
        # state
        self.state = "menu"  # menu, settings, playing
        self.game = None

    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            dt = clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.MOUSEMOTION:
                    mx, my = ev.pos
                    self.btn_start.update_hover(mx,my)
                    self.btn_settings.update_hover(mx,my)
                    self.btn_quit.update_hover(mx,my)
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mx,my = ev.pos
                    if self.state == "menu":
                        if self.btn_start.is_clicked(mx,my):
                            self.start_game()
                        elif self.btn_settings.is_clicked(mx,my):
                            self.state = "settings"
                        elif self.btn_quit.is_clicked(mx,my):
                            running = False
                    elif self.state == "settings":
                        # click regions for sliders/buttons handled in draw step via mouse pos check
                        pass
                elif ev.type == pygame.KEYDOWN:
                    if self.state == "playing":
                        if ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                            if self.game and self.game.player.alive:
                                self.game.player.jump()
                        elif ev.key == pygame.K_r:
                            # restart
                            self.start_game()
                        elif ev.key == pygame.K_ESCAPE:
                            # quit to menu
                            self.end_game()
                    elif self.state == "settings":
                        if ev.key == pygame.K_ESCAPE:
                            self.save_settings_and_back()
                # pass other events to game
            # update & draw per state
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "playing":
                self.update_game(dt)
                self.draw_game()
        # exit save settings and high score
        save_json(SETTINGS_FILE, {"volume": self.volume, "difficulty": self.difficulty})
        save_json(SAVE_FILE, {"high_score": self.high_score})
        pygame.quit()
        sys.exit()

    # -------------------------
    # Menu/Settings/Game control
    # -------------------------
    def start_game(self):
        # apply settings to sound volume
        settings["volume"] = self.volume
        settings["difficulty"] = self.difficulty
        apply_volume_to_all(self.volume)
        save_json(SETTINGS_FILE, settings)
        # create Game instance
        self.game = Game(self.screen, settings)
        # sync speed base to difficulty modifier immediate
        self.game.speed = self.game.base_speed
        self.state = "playing"

    def end_game(self):
        # when leaving game (back to menu) update high score
        if self.game:
            if self.game.score > self.high_score:
                self.high_score = self.game.score
                save_json(SAVE_FILE, {"high_score": self.high_score})
        self.game = None
        self.state = "menu"

    def save_settings_and_back(self):
        settings["volume"] = self.volume
        settings["difficulty"] = self.difficulty
        save_json(SETTINGS_FILE, settings)
        apply_volume_to_all(self.volume)
        self.state = "menu"

    # -------------------------
    # Drawing: Menu / Settings
    # -------------------------
    def draw_menu(self):
        self.screen.fill((18,18,18))
        # optionally draw logo
        if logo_img:
            logo_s = pygame.transform.smoothscale(logo_img, (480, 160))
            self.screen.blit(logo_s, (WIDTH//2 - logo_s.get_width()//2, 40))
        else:
            title = self.font_large.render(APP_TITLE, True, (230,230,230))
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))
        # draw buttons
        self.btn_start.draw(self.screen)
        self.btn_settings.draw(self.screen)
        self.btn_quit.draw(self.screen)
        # high score
        hs = self.font_small.render(f"High Score: {self.high_score}", True, (200,200,200))
        self.screen.blit(hs, (20, HEIGHT-40))
        # instructions small
        inst = self.font_small.render("Space = Jump · R = Restart · Esc = Quit/Game Over", True, (130,130,130))
        self.screen.blit(inst, (20, HEIGHT-20))
        pygame.display.flip()

    def draw_settings(self):
        self.screen.fill((24,24,30))
        # title
        t = self.font_large.render("Settings", True, (240,240,240))
        self.screen.blit(t, (WIDTH//2 - t.get_width()//2, 30))
        # Volume slider
        label = self.font_med.render("Volume", True, (220,220,220))
        self.screen.blit(label, (180, 150))
        # slider background rect
        slider_rect = pygame.Rect(320, 150, 420, 36)
        pygame.draw.rect(self.screen, (60,60,60), slider_rect, border_radius=8)
        # slider fill
        fill_w = int(self.volume * slider_rect.width)
        pygame.draw.rect(self.screen, (100,190,100), (slider_rect.x, slider_rect.y, fill_w, slider_rect.height), border_radius=8)
        # slider handle
        handle_x = slider_rect.x + fill_w
        pygame.draw.circle(self.screen, (240,240,240), (handle_x, slider_rect.centery), 10)
        # slider text
        vol_text = self.font_small.render(f"{int(self.volume*100)}%", True, (220,220,220))
        self.screen.blit(vol_text, (slider_rect.x + slider_rect.width + 12, slider_rect.y))

        # Difficulty options
        dlabel = self.font_med.render("Difficulty", True, (220,220,220))
        self.screen.blit(dlabel, (180, 240))
        # difficulty buttons
        diffs = ["Easy", "Normal", "Hard"]
        bx = 320
        by = 240
        for d in diffs:
            r = pygame.Rect(bx, by, 140, 42)
            color = (80,120,200) if self.difficulty == d else (60,60,60)
            pygame.draw.rect(self.screen, color, r, border_radius=8)
            txt = self.font_small.render(d, True, (255,255,255))
            self.screen.blit(txt, (r.centerx - txt.get_width()//2, r.centery - txt.get_height()//2))
            bx += 160

        # Back button
        back_rect = pygame.Rect(WIDTH//2 - 72, HEIGHT - 100, 144, 44)
        pygame.draw.rect(self.screen, (140,60,60), back_rect, border_radius=8)
        back_txt = self.font_small.render("Back (Esc)", True, (255,255,255))
        self.screen.blit(back_txt, (back_rect.centerx - back_txt.get_width()//2, back_rect.centery - back_txt.get_height()//2))

        # Interactions: mouse-based slider and clicks
        mx, my = pygame.mouse.get_pos()
        mb = pygame.mouse.get_pressed()
        if mb[0]:
            # if clicked on slider area adjust volume
            if slider_rect.collidepoint(mx,my):
                rel = clamp((mx - slider_rect.x) / slider_rect.width, 0.0, 1.0)
                self.volume = rel
                apply_volume_to_all(self.volume)
        # check difficulty clicks
        bx = 320
        for d in diffs:
            r = pygame.Rect(bx, by, 140, 42)
            if pygame.mouse.get_pressed()[0] and r.collidepoint(mx,my):
                self.difficulty = d
            bx += 160
        # check back click
        if pygame.mouse.get_pressed()[0] and back_rect.collidepoint(mx,my):
            self.save_settings_and_back()

        # footer
        footer = self.font_small.render("Toggle volume by dragging slider. Click difficulty. Press Esc to save & back.", True, (160,160,160))
        self.screen.blit(footer, (40, HEIGHT-40))
        pygame.display.flip()

    def save_settings_and_back(self):
        settings["volume"] = self.volume
        settings["difficulty"] = self.difficulty
        save_json(SETTINGS_FILE, settings)
        apply_volume_to_all(self.volume)
        self.state = "menu"

    # -------------------------
    # Game run/draw/update
    # -------------------------
    def update_game(self, dt):
        if not self.game:
            self.state = "menu"
            return
        self.game.update(dt)
        # when game over update high score
        if not self.game.player.alive:
            if self.game.score > self.high_score:
                self.high_score = self.game.score
                save_json(SAVE_FILE, {"high_score": self.high_score})

    def draw_game(self):
        if not self.game:
            return
        self.game.draw()

# ---------------------------
# MAIN
# ---------------------------
def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
