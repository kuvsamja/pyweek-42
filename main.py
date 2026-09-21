from enum import Enum, auto
import pygame


class Platform:
    position: pygame.Vector2
    size: pygame.Vector2
    z_order: int
    def __init__(self, pos_x: float, pos_y: float, width: float, height: float, z_order: int):
        self.position = pygame.Vector2(pos_x, pos_y)
        self.size = pygame.Vector2(width, height)
        self.z_order = z_order



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
    dead: bool
    
    def __init__(self, x, y, width, height):
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(width, height)
        self.speed = pygame.Vector2(0, 0)
        self.gravity = 1
        self.animation_state = self.AnimationState.IDLE
        self.dead = False


class Enemy(Entity):
    pass
class Player(Entity): # TODO: add movement
    def __init__(self, x, y, width, height):
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(width, height)
        self.speed = pygame.Vector2(0, 0)
        self.gravity = 1
        self.animation_state = self.AnimationState.IDLE
        self.dead = False
        
        self.movement_speed = 4
        self.grounded = False
        self.gravity = 20
        self.jump_timer = 0
        self.jump_speed = 5
        self.jump_time = 30 # max time to hold a jump
        self.head_clipping = False
        self.can_jump = False

    def move(self, buttons):
        self.speed.x = 0
        self.speed.y -= self.gravity
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
    def __init__(self, player: Player):
        self.platforms = []
        self.enemies = []
        self.player = player
        self.frame_timer = 0

    def addPlatform(self, platform: Platform):
        self.platforms.append(platform)
    def addEnemy(self, enemy: Enemy):
        self.enemies.append(enemy)


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
        self.softzone = Margins(150, 75, 300, 300)
        self.deadzone = Margins(100, 50, 100, 100)
        self.camera_follow_speed = 3
        self.world = world
        self.window = window

    def pointToScreen(self, point: pygame.Vector2) -> pygame.Vector2:
        point -= pygame.Vector2(self.x, self.y)
        point.x /= self.world_width
        point.y /= self.world_height
        return point
    
    def draw(self):
        pass
    
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
        pygame.RESIZABLE
    )

    pygame.display.set_caption("pygame")


    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        
        buttons = pygame.key.get_pressed()



if __name__ == "__main__":
    main()
