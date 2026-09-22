import os
from enum import Enum, auto
import copy

import pygame
from pygame.sprite import LayeredUpdates


class Platform (pygame.sprite.Sprite):
    position: pygame.Vector2
    size: pygame.Vector2
    def __init__(self, pos_x: float, pos_y: float, z_index:int,  file_name: str):
        super().__init__()
        # image loading
        image_path = os.path.join("assets", file_name)
        self.source_image = pygame.image.load(image_path).convert_alpha()
        self.image = self.source_image
        self.width = self.image.get_width()
        self.height = self.image.get_height()

        self.position = pygame.Vector2(pos_x, pos_y)
        self.size = pygame.Vector2(self.width, self.height)
        self.rect = pygame.Rect(pos_x, pos_y, self.width, self.height)
        self._layer = z_index
        # image loading
        image_path = os.path.join("assets", file_name)
        self.image = pygame.image.load(image_path).convert_alpha()

    def setCameraPosition(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

class Entity(pygame.sprite.Sprite):
    class AnimationState(Enum): # TODO: animaton handling
        IDLE = auto()
        WALKING = auto()
        RUNNING = auto()
        AIRBORNE = auto()
    animation_state: AnimationState
    position: pygame.Vector2
    size: pygame.Vector2
    speed: pygame.Vector2
    gravity: float
    dead: bool
    animation_frames: list[list[pygame.Surface]]
    def get_image(self, sheet, x, y, width, height):
        rect = pygame.Rect(x, y, width, height)
        image = sheet.subsurface(rect)
        return image
    def __init__(self, x:int, y:int, z_index:int, name: str, sprite_width: int, sprite_height: int):
        super().__init__()
        # image loading
        width = sprite_width
        height = sprite_height
        # other stuff
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(width, height)
        self.rect = pygame.Rect(0, 0, width, height)
        self._layer = z_index
        self.buttons_last_frame = []

        self.dead = False
        self.speed = pygame.Vector2(0, 0)
        self.gravity = 1
        self.animation_state = self.AnimationState.IDLE
        self.animation_frequency = 3 # update every 3 frames (3/60)
        self.frame_counter = 0
        self.animation_frames = [[] for _ in range(len(self.AnimationState))]
        for state in self.AnimationState:
            image_path = os.path.join(f"assets/{name}", state.name + ".png")
            if not os.path.exists(image_path):
                print(f"Didn't find asset at: {image_path}")
                continue
            spritesheet = pygame.image.load(image_path).convert_alpha()
            image_count = spritesheet.get_width() // sprite_width
            tup = [(sprite_width * x, 0, sprite_width, sprite_height) for x in range(image_count)]
            self.animation_frames[state.value] = [self.get_image(spritesheet, *frame) for frame in tup]
        if len(self.animation_frames[self.AnimationState.IDLE.value]) == 0:
            raise FileNotFoundError(f"There is no IDLE animation spritesheet for Entity {name}! I looked at path: {os.path.join("assets", name+"_IDLE.png")}")
        self.image = self.animation_frames[self.AnimationState.IDLE.value][0]
    # sets camera-space coordinates to (x,y)
    def setCameraPosition(self, x, y):
        self.rect = pygame.Rect(x, y, self.size.x, self.size.y)
    def update(self):
        self.frame_counter += 1
        if self.frame_counter % self.animation_frequency != 0:
            return
        animation_duration = len(self.animation_frames[self.animation_state.value])
        self.frame_counter %= self.animation_frequency * animation_duration
        frame_id = self.frame_counter // self.animation_frequency
        self.image = self.animation_frames[self.animation_state.value][frame_id]
    def setAnimationState(self, new_animation_state: AnimationState):
        self.frame_counter = 0
        self.animation_state = new_animation_state
        self.image = self.animation_frames[new_animation_state.value][0]

class Enemy(Entity):
    pass

class Player(Entity): # TODO: add movement
    def __init__(self, x, y, z_index):
        super().__init__(x, y, z_index, "player", 48, 48) # player sprite size is 48x48
        self.animation_state = self.AnimationState.IDLE
        self.dead = False

        # state stuff
        self.grounded = False
        self.head_clipping = False
        self.wall_to_left = False
        self.wall_to_right = False
        self.can_jump = False


        self.movement_speed = 4
        self.gravity = 0.8
        self.terminal_velocity = 10;

        # jump
        self.jump_speed = 4
        self.jump_time = 8 # max time to hold a jump in frames
        self.jump_timer = 0
        self.can_jump = False # see if player can continue to jump upwards by holding tge button


    def move(self, buttons):
        self.speed.x = 0

        if self.grounded:
            self.speed.y = min(self.speed.y, 0)

        else:
            # Properly apply gravity and cap it at terminal velocity
            self.speed.y = min(self.speed.y + self.gravity, self.terminal_velocity)

        if self.head_clipping:
            self.speed.y = max(0, self.speed.y)

        if buttons[pygame.K_a]:
            self.speed.x -= self.movement_speed
        if buttons[pygame.K_d]:
            self.speed.x += self.movement_speed

        ## jump
        # initial jump
        if self.grounded and buttons[pygame.K_SPACE] and not self.buttons_last_frame[K_SPACE]:
            self.speed.y = -10
            self.can_jump = True
            self.jump_timer = 0

        # holding space
        if self.can_jump and buttons[pygame.K_SPACE]:
            if self.jump_timer < self.jump_time and not self.head_clipping:
                self.speed.y = -10
                self.jump_timer += 1
            else:
                self.can_jump = False
        else:
            self.can_jump = False




        print(f"position: {self.position}")
        print(f"speed:    {self.speed}")
        print(f"grounded: {self.grounded}")
        self.position += self.speed
        self.buttons_last_frame = copy.copy(buttons)

class World:
    frame_timer: int
    platforms: list[Platform]
    enemies: list[Enemy]
    player: Player
    all_sprites: pygame.sprite.LayeredUpdates

    def __init__(self, player: Player):
        self.platforms = []
        self.enemies = []
        self.player = player
        self.frame_timer = 0
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.all_sprites.add(player)
    def addPlatform(self, platform: Platform):
        self.platforms.append(platform)
        self.all_sprites.add(platform)
    def addEnemy(self, enemy: Enemy):
        self.enemies.append(enemy)
        self.all_sprites.add(enemy)


    @staticmethod
    def entityPlatformCollision(platform: Platform, entity: Entity):
        return (platform.position.x < entity.position.x + entity.size.x and
            platform.position.x + platform.size.x > entity.position.x and
                platform.position.y < entity.position.y + entity.size.y and
                platform.position.y + platform.size.y > entity.position.y)

    @staticmethod
    def platformRectCollision(rect: pygame.Rect, platform: Platform):
        return (rect.x < platform.position.x + platform.size.x and
            rect.x + rect.w > platform.position.x and
                rect.y < platform.position.y + platform.size.y and
                rect.y + rect.h > platform.position.y)

    def rectWorldCollision(self, rect: pygame.Rect):
        for platform in self.platforms:
            if self.platformRectCollision(rect, platform):
                return True
        return False
    def playerCollision(self):
        for platform in self.platforms:
            if not self.entityPlatformCollision(platform, self.player):
                continue
            overlap_x = min(
                            (self.player.position.x + self.player.size.x) - platform.position.x,
                            (platform.position.x + platform.size.x) - self.player.position.x
                        )
            overlap_y = min(
                (self.player.position.y + self.player.size.y) - platform.position.y,
                (platform.position.y + platform.size.y) - self.player.position.y
            )
            if overlap_x < overlap_y:
                if self.player.position.x < platform.position.x:
                    self.player.position.x -= overlap_x
                else:
                    self.player.position.x += overlap_x
            else:
                if self.player.position.y < platform.position.y:
                    self.player.position.y -= overlap_y
                else:
                    self.player.position.y += overlap_y
            # TODO: ADD PROPER COLLISION PUSHING INVOLVING DX AND DY PLEASE PLEASE PLEASE REMEMBER THIS


    def playerTouchCheck(self):
        self.player.grounded = False
        self.player.head_clipping = False
        self.player.wall_to_right = False
        self.player.wall_to_left = False

        touch_check = pygame.Rect(1, 1, 1, 1)

        feet_box = pygame.Rect(self.player.position.x, self.player.position.y + touch_check.h + self.player.size.y, self.player.size.x, touch_check.h)
        head_box = pygame.Rect(self.player.position.x, self.player.position.y - touch_check.h, self.player.size.x, touch_check.h)
        left_box = pygame.Rect(self.player.position.x - touch_check.w, self.player.position.y + self.player.size.y / 4, touch_check.w, self.player.size.y / 2)
        right_box = pygame.Rect(self.player.position.x + self.player.size.x, self.player.position.y + self.player.size.y / 4, touch_check.w, self.player.size.y / 2)

        if self.rectWorldCollision(feet_box):
            self.player.grounded = True
        if self.rectWorldCollision(head_box):
            self.player.head_clipping = True
        if self.rectWorldCollision(left_box):
            self.player.wall_to_left = True
        if self.rectWorldCollision(right_box):
            self.player.wall_to_right = True

    def enemyCollision(self):
        pass

    def handleCollisions(self):
        self.enemyCollision()
        self.playerCollision()
        self.playerTouchCheck()

    def advancePhysics(self, buttons): # TODO: make this move the player and perform collision checks
        self.enemies = [e for e in self.enemies if not e.dead]

        self.player.move(buttons)
        self.handleCollisions()

class Margins:
    def __init__(self, up, down, left, right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right

class Camera:
    def __init__(self, x, y, world_width, world_height, pixel_width, pixel_height, world: World, window: pygame.Surface):
        self.world_width = world_width
        self.world_height = world_height  #height in world units
        self.pixel_width = pixel_width
        self.pixel_height = pixel_height
        self.x = x
        self.y = y
        self.softzone = Margins(15, 8, 30, 30)
        self.deadzone = Margins(10, 5, 10, 10)
        self.camera_follow_speed = 3
        self.world = world
        self.window = window
        self.resize = True

    def update(self):
        if self.resize:
            scale_x = self.pixel_width / self.world_width
            scale_y = self.pixel_height / self.world_height
            for sprite in self.world.all_sprites:
                pos = self.pointToScreen(pygame.Vector2(sprite.position.x, sprite.position.y))
                sprite.setCameraPosition(
                    pos.x,
                    pos.y,
                    sprite.size.x * scale_x,
                    sprite.size.y * scale_y
                )
                scaled_w = int(sprite.size.x * scale_x)
                scaled_h = int(sprite.size.y * scale_y)
                for animation in sprite.animation_frames:
                    for i, frame in enumerate(animation):
                        animation[i] = pygame.transform.scale(frame, (scaled_w, scaled_h)) # TODO: make this run only once per screen resize and also make it work on future spritesheets
            self.resize = False
        self.world.all_sprites.update()
        self.world.all_sprites.draw(self.window)

    def pointToScreen(self, point: pygame.Vector2) -> pygame.Vector2:
        offset_point = point - pygame.Vector2(self.x, self.y)

        screen_x = (offset_point.x / self.world_width) * self.pixel_width
        screen_y = (offset_point.y / self.world_height) * self.pixel_height
        return pygame.Vector2(screen_x, screen_y)


    def moveCamera(self):
        player = self.world.player

        # deadzone
        ## right
        if player.position.x - self.x + player.size.x > self.world_width - self.deadzone.right:
            self.x = player.position.x - self.world_width + player.size.x + self.deadzone.right
        ## left
        if player.position.x - self.x < self.deadzone.left:
            self.x = player.position.x - self.deadzone.left
        ## down
        if player.position.y - self.y + player.size.y > self.world_height - self.deadzone.down:
            self.y = player.position.y - self.world_height + player.size.y + self.deadzone.down
        ## up
        if player.position.y - self.y < self.deadzone.up:
            self.y = player.position.y - self.deadzone.up

        # softzone
        ## right
        if player.position.x - self.x + player.size.x > self.world_width - self.softzone.right:
            self.x += self.camera_follow_speed
        ## left
        if player.position.x - self.x < self.softzone.left:
            self.x -= self.camera_follow_speed
        ## down
        if player.position.y - self.y + player.size.y > self.world_height - self.softzone.down:
            self.y += self.camera_follow_speed
        ## up
        if player.position.y - self.y < self.softzone.up:
            self.y -= self.camera_follow_speed


def main():
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080

    pygame.init()
    window = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
    )

    pygame.display.set_caption("pygame")

    player = Player(0, 0, 0)

    plat10 = Platform(-118, 100, 1, "debug-platform-128x32.png")
    plat11 = Platform(-10, 100, 1, "debug-platform-128x32.png")

    plat2 = Platform(-10, 0, 1, "debug-platform-128x32.png")

    world = World(player)

    world.addPlatform(plat10)
    world.addPlatform(plat11)

    world.addPlatform(plat2)

    camera = Camera(0, 0, 640, 360, WINDOW_WIDTH, WINDOW_HEIGHT, world, window)



    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        window.fill((0, 0, 0))
        buttons = pygame.key.get_pressed()
        world.advancePhysics(buttons)
        camera.moveCamera()
        camera.update()


        pygame.display.flip()
        pygame.time.delay(16)

if __name__ == "__main__":
    main()
