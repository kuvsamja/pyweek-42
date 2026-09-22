import os
from enum import Enum, auto

import pygame
from pygame.sprite import LayeredUpdates


class Platform (pygame.sprite.Sprite):
    position: pygame.Vector2
    size: pygame.Vector2
    def __init__(self, pos_x: float, pos_y: float, width: float, height: float, z_index:int,  file_name: str):
        super().__init__()
        self.position = pygame.Vector2(pos_x, pos_y)
        self.size = pygame.Vector2(width, height)
        self.rect = pygame.Rect(pos_x, pos_y, width, height)
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
    def __init__(self, x: int, y: int, z_index: int, file_name: str):
        super().__init__()
        # image loading
        image_path = os.path.join("assets", file_name)
        self.source_image = pygame.image.load(image_path).convert_alpha()
        self.image = self.source_image
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        # other stuff
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(self.width, self.height)
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self._layer = z_index

        self.dead = False
        self.speed = pygame.Vector2(0, 0)
        self.gravity = 1
        self.animation_state = self.AnimationState.IDLE

    # sets camera-space coordinates to (x,y)
    def setCameraPosition(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

class Enemy(Entity):
    pass
class Player(Entity): # TODO: add movement
    def __init__(self, x, y, z_index, file_name):
        super().__init__(x, y, z_index, file_name)
        self.speed = pygame.Vector2(0, 0)
        self.gravity = 1
        self.animation_state = self.AnimationState.IDLE
        self.dead = False

        self.movement_speed = 0.1
        self.grounded = False
        self.gravity = 20
        self.jump_timer = 0
        self.jump_speed = 5
        self.jump_time = 30 # max time to hold a jump
        self.head_clipping = False
        self.can_jump = False

    def move(self, buttons):
        self.speed.x = 0
        # self.speed.y -= self.gravity
        if self.grounded == 0:
            self.speed.y = max(0, self.speed.y);
        if buttons[pygame.K_a]:
            self.speed.x -= self.movement_speed
        if buttons[pygame.K_d]:
            self.speed.x += self.movement_speed

        self.position += self.speed

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

    def playerCollision(self):
        self.player.grounded = False
        self.player.head_clipping = False

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
                    self.player.grounded = True
                else:
                    self.player.position.y += overlap_y
                    self.player.head_clipping = True
            # TODO: ADD PROPER COLLISION PUSHING INVOLVING DX AND DY



    def enemyCollision(self):
        pass

    def handleCollisions(self):
        self.enemyCollision()
        self.playerCollision()

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

    def update(self):
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
            sprite.image = pygame.transform.scale(sprite.source_image, (scaled_w, scaled_h)) # TODO: make this run only once per screen resize and also make it work on future spritesheets
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

    player = Player(0, 0, 0, "debug-platform-48x48.png")
    world = World(player)

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
