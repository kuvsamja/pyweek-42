from enum import Enum, auto
import pygame


class Platform:
    position: pygame.Vector2
    size: pygame.Vector2
    def __init__(self, pos_x: float, pos_y: float, width: float, height: float):
        self.position = pygame.Vector2(pos_x, pos_y)
        self.size = pygame.Vector2(width, height)

class Entity:
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

    def __init__(self, x, y, width, height):
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(width, height)
        self.speed = pygame.Vector2(0, 0)
        self.gravity = 1
        self.animation_state = self.AnimationState.IDLE
class Enemy(Entity):
    pass
class Player(Entity): # TODO: add movement
    pass

class World:
    frame_timer: int
    platforms: list[Platform]
    enemies: list[Enemy] # TODO: add proper enemy killing
    player: Player
    def __init__(self, player: Player):
        self.platforms = []
        self.player = player
        self.frame_timer = 0

    def addPlatform(self, platform: Platform):
        self.platforms.append(platform)
    def addEnemy(self, enemy: Enemy):
        self.enemies.append(enemy)

    def enemyCollision(self):
        pass
    def playerCollision(self):
        pass


    def handleCollisions(self):
        self.enemyCollision()
        self.playerCollision()

    def advancePhysics(self): # TODO: make this move the player and perform collision checks
        pass

# TODO: add a camera class

class Margins:
    def __init__(self, up, down, left, right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right

class Camera:
    def __init__(self, x, y, world_width, world_height, pixel_width, pixel_height, world: World):
        self.world_width = world_width
        self.world_height = world_height  #height in world units
        self.pixel_width = pixel_width
        self.pixel_height = pixel_height
        self.x = x
        self.y = y
        self.softzone = Margins(150, 75, 300, 300)
        self.deadzone = Margins(100, 50, 100, 100)
        self.camera_follow_speed = 3
        self.world = world

    # def draw():


    def moveCamera(self):
        # deadzone
        ## right
        if self.world.player.size.x - self.x + self.world.player.size.x > self.world_width - self.deadzone.right:
            self.x = self.world.player.size.x - self.world_width + self.world.player.size.x + self.deadzone.right
        ## left
        if self.world.player.size.x - self.x < self.deadzone.left:
            self.x = self.world.player.size.x - self.deadzone.left
        ## down
        if self.world.player.position.y - self.y + self.world.player.size.y > self.world_height - self.deadzone.down:
            self.y = self.world.player.position.y - self.world_height + self.world.player.size.y + self.deadzone.down
        ##up
        if self.world.player.position.y - self.y < self.deadzone.up:
            self.y = self.world.player.position.y - self.deadzone.up

        # softzone
        ## right
        if self.world.player.size.x - self.x + self.world.player.size.x > self.world_width - self.softzone.right:
            self.x += self.camera_follow_speed
        ## left
        if self.world.player.size.x - self.x < self.softzone.left:
            self.x -= self.camera_follow_speed
        ## down
        if self.world.player.position.y - self.y + self.world.player.size.y > self.world_height - self.softzone.down:
            self.y += self.camera_follow_speed
        ##up
        if self.world.player.position.y - self.y < self.softzone.up:
            self.y -= self.camera_follow_speed


def main():
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080

    pygame.init()
    window = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
        pygame.RESIZABLE
    )

    pygame.display.set_caption("pygame")


    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False




if __name__ == "__main__":
    main()
