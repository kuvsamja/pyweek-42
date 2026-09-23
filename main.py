import copy
import os
from enum import Enum, auto

import pygame


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

    def setCameraPosition(self, x, y):
        self.rect = pygame.Rect(x, y, self.width, self.height)

class DamageBox:
    class Owner(Enum):
        PLAYER = auto()
        SMALL_ENEMY = auto()
        BOSS = auto()
    box: pygame.Rect
    owner: Owner
    damage: float
    alive_time: int # how long the box lingers in frames


    def __init__(self, x, y, w, h, damage: float, owner: Owner, alive_time: int, stun_time: int):
        self.box = pygame.Rect(x, y, w, h)
        self.damage = damage
        self.owner = owner
        self.stun_time = stun_time
        
        self.alive_time = alive_time # TODO: add knockback

    def tick(self):
        """decreases the alive time, hitbox should be killed when it reaches 0"""
        self.alive_time -= 1

class Entity(pygame.sprite.Sprite):
    class AnimationState(Enum):
        IDLE = auto()
        RUNNING = auto()
        AIRBORNE = auto()
        JUMPING = auto()
    animation_state: AnimationState
    position: pygame.Vector2
    size: pygame.Vector2
    facing_left: bool
    speed: pygame.Vector2
    gravity_acceleration: float
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
        self.facing_left = False
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(width, height)
        self.rect = pygame.Rect(0, 0, width, height)
        self._layer = z_index
        self.buttons_last_frame = []

        self.dead = False
        self.speed = pygame.Vector2(0, 0)
        self.gravity_acceleration = 1
        self.animation_state = self.AnimationState.IDLE
        self.animation_frequency = 3 # update every 3 frames (3/60)
        self.frame_counter = 0
        self.animation_frames = [[] for _ in range(len(self.AnimationState) + 1)]
        self.animation_frames_flipped = [[] for _ in range(len(self.AnimationState) + 1)]
        for state in self.AnimationState:
            image_path = os.path.join(f"assets/{name}", state.name + ".png")
            if not os.path.exists(image_path):
                print(f"Didn't find asset at: {image_path}")
                continue
            spritesheet = pygame.image.load(image_path).convert_alpha()
            image_count = spritesheet.get_width() // sprite_width
            tup = [(sprite_width * x, 0, sprite_width, sprite_height) for x in range(image_count)]
            self.animation_frames[state.value] = [self.get_image(spritesheet, *frame) for frame in tup]
            self.animation_frames_flipped[state.value] = [pygame.transform.flip(self.get_image(spritesheet, *frame), True, False) for frame in tup]
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
        if self.facing_left:
            self.image = self.animation_frames_flipped[self.animation_state.value][frame_id]
        else:
            self.image = self.animation_frames[self.animation_state.value][frame_id]
    def setAnimationState(self, new_animation_state: AnimationState):
        if new_animation_state == self.animation_state:
            return
        self.frame_counter = 0
        self.animation_state = new_animation_state
        if len(self.animation_frames[new_animation_state.value])!=0:
            if not self.facing_left:
                self.image = self.animation_frames[new_animation_state.value][0]
            else:
                self.image = self.animation_frames_flipped[new_animation_state.value][0]

class Enemy(Entity):
    def __init__(self, x, y, z_index, name: str):
        """name: type of the enemy"""
        super().__init__(x, y, z_index, name, 48, 48)
        self.animation_state = self.AnimationState.IDLE
        self.dead = False

        # state stuff
        self.hp = 100
        
        self.invincibility_timer = 0
        self.stun_timer = 0

        self.grounded = False
        self.head_clipping = False
        self.wall_to_left = False
        self.wall_to_right = False
        self.looking_right = True

        # const parameters
        self.run_speed = 4
        self.gravity_acceleration = 0.8
        self.terminal_velocity = 10
        self.invincibility_duration = 10 # change for the boss

    def damage(self, damage_box: DamageBox): # TODO: finish this
        print("b")
        if self.invincibility_timer > 0: return
        
        self.hp -= damage_box.damage
        self.stun_timer = damage_box.stun_time
        self.invincibility_timer = self.invincibility_duration

    def runLogic(self) -> list[DamageBox]:
        """updates the enemy"""
        self.speed.x = 0
        self.invincibility_timer -= 1
        self.stun_timer -= 1

        if self.grounded:
            self.speed.y = min(self.speed.y, 0)

        else:
            # apply gravity and cap it at terminal velocity
            self.speed.y = min(self.speed.y + self.gravity_acceleration, self.terminal_velocity)

        if self.head_clipping:
            self.speed.y = max(0, self.speed.y)


        self.position += self.speed
        print(f"hp: {self.hp}")
        # print(f"position: {self.position}")
        # print(f"speed:    {self.speed}")
        # print(f"grounded: {self.grounded}")
        return []

class Player(Entity): # TODO: add movement
    def __init__(self, x, y, z_index):
        super().__init__(x, y, z_index, "player", 48, 48) # player sprite size is 48x48
        self.animation_state = self.AnimationState.IDLE
        self.dead = False

        # state stuff
        self.hp = 100
        # self.poise = 100 TODO: mabye this
        self.invincibility_timer = 0
        self.stun_timer = 0
        self.sword_timer = 0

        self.stanced = False

        self.grounded = False
        self.head_clipping = False
        self.wall_to_left = False
        self.wall_to_right = False
        self.can_jump = False
        self.looking_right = True

        # const parameters
        self.run_speed = 4
        self.gravity_acceleration = 0.8
        self.terminal_velocity = 10

        self.invincibility_duration = 10
        self.sword_delay = 25

        # jump
        self.jump_speed = 4
        self.jump_time = 8 # max time to hold a jump in frames
        self.jump_timer = 0
        self.can_jump = False # see if player can continue to jump upwards by holding tge button


    def damage(self, damage_box: DamageBox): # TODO: finish this
        if self.invincibility_timer > 0: return

        self.hp -= damage_box.damage
        self.stun_timer = damage_box.stun_time
        self.invincibility_timer = self.invincibility_duration

    def runLogic(self, buttons) -> list[DamageBox]:
        """updates the player"""
        self.speed.x = 0
        self.invincibility_timer -= 1
        self.stun_timer -= 1
        self.sword_timer -= 1

        if self.grounded:
            self.speed.y = min(self.speed.y, 0)

        else:
            # apply gravity and cap it at terminal velocity
            self.speed.y = min(self.speed.y + self.gravity_acceleration, self.terminal_velocity)

        if self.head_clipping:
            self.speed.y = max(0, self.speed.y)
        self.setAnimationState(Entity.AnimationState.IDLE)
        if buttons[pygame.K_LEFT]:
            self.speed.x -= self.run_speed
            self.facing_left = True
            self.setAnimationState(Entity.AnimationState.RUNNING)
        if buttons[pygame.K_RIGHT]:
            self.speed.x += self.run_speed
            self.facing_left = False
            self.setAnimationState(Entity.AnimationState.RUNNING)
        ## jump
        # initial jump
        if self.grounded and buttons[pygame.K_z] and not self.buttons_last_frame[pygame.K_z]:
            self.speed.y = -10
            self.can_jump = True
            self.jump_timer = 0
            self.setAnimationState(Entity.AnimationState.JUMPING)
        # holding space
        if self.can_jump and buttons[pygame.K_z]:
            if self.jump_timer < self.jump_time and not self.head_clipping:
                self.speed.y = -10
                self.jump_timer += 1
            else:
                self.can_jump = False
        else:
            self.can_jump = False

        # if buttons[pygame.] # TODO: add hits



        # print(f"position: {self.position}")
        # print(f"speed:    {self.speed}")
        # print(f"grounded: {self.grounded}")
        self.position += self.speed

        db_list = []
        if buttons[pygame.K_x] and not self.buttons_last_frame[pygame.K_x] and self.sword_timer < 0: # TODO: add hit polling
            self.sword_timer = self.sword_delay
            box_width = 20
            box_x = (self.position.x - box_width) if self.facing_left else (self.position.x + self.size.x)
            
            db_list.append(
                DamageBox(
                    x=box_x, 
                    y=self.position.y + 10, 
                    w=box_width, 
                    h=28, 
                    damage=10, 
                    owner=DamageBox.Owner.PLAYER, 
                    alive_time=5, 
                    stun_time=10
                )
            )

        self.buttons_last_frame = copy.copy(buttons)
        return db_list

class World:
    frame_timer: int
    player: Player
    enemies: list[Enemy]
    platforms: list[Platform]
    damage_boxes: list[DamageBox]
    all_sprites: pygame.sprite.LayeredUpdates

    def __init__(self, player: Player):
        self.platforms = []
        self.enemies = []
        self.player = player
        self.damage_boxes = []
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

        touch_check = pygame.Rect(1, 1, 1, 1) # TODO: fix player floating by one pixel

        feet_box = pygame.Rect(self.player.position.x, self.player.position.y + touch_check.h + self.player.size.y, self.player.size.x, touch_check.h)
        head_box = pygame.Rect(self.player.position.x, self.player.position.y - touch_check.h, self.player.size.x, touch_check.h)
        left_box = pygame.Rect(self.player.position.x - touch_check.w, self.player.position.y + self.player.size.y / 4, touch_check.w, self.player.size.y / 2)
        right_box = pygame.Rect(self.player.position.x + self.player.size.x, self.player.position.y + self.player.size.y / 4, touch_check.w, self.player.size.y / 2)
        # TODO: check if this math is alr
        if self.rectWorldCollision(feet_box):
            self.player.grounded = True
        if self.rectWorldCollision(head_box):
            self.player.head_clipping = True
        if self.rectWorldCollision(left_box):
            self.player.wall_to_left = True
        if self.rectWorldCollision(right_box):
            self.player.wall_to_right = True

    def enemyTouchCheck(self):
        for enemy in self.enemies:
            enemy.grounded = False
            enemy.head_clipping = False
            enemy.wall_to_right = False
            enemy.wall_to_left = False

            touch_check = pygame.Rect(1, 1, 1, 1) # TODO: fix player floating by one pixel

            feet_box = pygame.Rect(enemy.position.x, enemy.position.y + touch_check.h + enemy.size.y, enemy.size.x, touch_check.h)
            head_box = pygame.Rect(enemy.position.x, enemy.position.y - touch_check.h, enemy.size.x, touch_check.h)
            left_box = pygame.Rect(enemy.position.x - touch_check.w, enemy.position.y + enemy.size.y / 4, touch_check.w, enemy.size.y / 2)
            right_box = pygame.Rect(enemy.position.x + enemy.size.x, enemy.position.y + enemy.size.y / 4, touch_check.w, enemy.size.y / 2)

            if self.rectWorldCollision(feet_box):
                enemy.grounded = True
            if self.rectWorldCollision(head_box):
                enemy.head_clipping = True
            if self.rectWorldCollision(left_box):
                enemy.wall_to_left = True
            if self.rectWorldCollision(right_box):
                enemy.wall_to_right = True
    def enemyCollision(self):
        for enemy in self.enemies:
            for platform in self.platforms:
                if not self.entityPlatformCollision(platform, enemy):
                    continue
                overlap_x = min(
                                (enemy.position.x + enemy.size.x) - platform.position.x,
                                (platform.position.x + platform.size.x) - enemy.position.x
                            )
                overlap_y = min(
                    (enemy.position.y + enemy.size.y) - platform.position.y,
                    (platform.position.y + platform.size.y) - enemy.position.y
                )
                if overlap_x < overlap_y:
                    if enemy.position.x < platform.position.x:
                        enemy.position.x -= overlap_x
                    else:
                        enemy.position.x += overlap_x
                else:
                    if enemy.position.y < platform.position.y:
                        enemy.position.y -= overlap_y
                    else:
                        enemy.position.y += overlap_y
                # TODO: ADD PROPER COLLISION PUSHING INVOLVING DX AND DY PLEASE PLEASE PLEASE REMEMBER THIS

    def damageCollisions(self):
        for db in self.damage_boxes:
            if db.owner == DamageBox.Owner.PLAYER:
                for enemy in self.enemies:
                    if db.box.colliderect(
                        pygame.Rect(
                            enemy.position.x,
                            enemy.position.y,
                            enemy.size.x,
                            enemy.size.y
                        )
                    ):
                        enemy.damage(db)
            elif db.owner == DamageBox.Owner.SMALL_ENEMY and db.box.colliderect(
                    pygame.Rect(self.player.position.x,
                                self.player.position.y,
                                self.player.size.x,
                                self.player.size.y)):
                    self.player.damage(db)

    def handleCollisions(self):
        self.playerCollision()
        self.playerTouchCheck()
        self.enemyCollision()
        self.enemyTouchCheck()
        self.damageCollisions()



    def advancePhysics(self, buttons): # TODO: make this perform collision checks for enemies
        self.enemies = [e for e in self.enemies if not e.dead]

        self.damage_boxes = [db for db in self.damage_boxes if db.alive_time > 0]
        for damage_box in self.damage_boxes: damage_box.tick()

        for enemy in self.enemies: self.damage_boxes += enemy.runLogic()
        self.damage_boxes += self.player.runLogic(buttons)

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

    def draw(self):
        scale_x = self.pixel_width / self.world_width
        scale_y = self.pixel_height / self.world_height
        for sprite in self.world.all_sprites:
            pos = self.pointToScreen(pygame.Vector2(sprite.position.x, sprite.position.y))
            sprite.setCameraPosition(
                pos.x,
                pos.y
            )
            if self.resize:

                scaled_w = int(sprite.size.x * scale_x)
                scaled_h = int(sprite.size.y * scale_y)
                if isinstance(sprite, Entity):
                    for i, animation in enumerate(sprite.animation_frames):
                        for j, frame in enumerate(animation):
                            animation[j] = pygame.transform.scale(frame, (scaled_w, scaled_h))
                            sprite.animation_frames_flipped[i][j] = pygame.transform.flip(animation[j], True, False)
                elif isinstance(sprite, Platform):
                    sprite.image = pygame.transform.scale(sprite.source_image, (scaled_w, scaled_h))
                    
        self.world.all_sprites.update()
        self.world.all_sprites.draw(self.window)
        self.resize = False
        
    def drawDebug(self):
        scale_x = self.pixel_width / self.world_width
        scale_y = self.pixel_height / self.world_height
        for sprite in self.world.all_sprites:
            pos = self.pointToScreen(pygame.Vector2(sprite.position.x, sprite.position.y))
            sprite.setCameraPosition(
                pos.x,
                pos.y
            )
            if self.resize:

                scaled_w = int(sprite.size.x * scale_x)
                scaled_h = int(sprite.size.y * scale_y)
                if isinstance(sprite, Entity):
                    for i, animation in enumerate(sprite.animation_frames):
                        for j, frame in enumerate(animation):
                            animation[j] = pygame.transform.scale(frame, (scaled_w, scaled_h))
                            sprite.animation_frames_flipped[i][j] = pygame.transform.flip(animation[j], True, False)
                elif isinstance(sprite, Platform):
                    sprite.image = pygame.transform.scale(sprite.source_image, (scaled_w, scaled_h))
                    
        self.world.all_sprites.update()
        self.world.all_sprites.draw(self.window)
        self.resize = False

        for db in self.world.damage_boxes:
            screen_pos = self.pointToScreen(pygame.Vector2(db.box.x, db.box.y))
            
            screen_w = int(db.box.width * scale_x)
            screen_h = int(db.box.height * scale_y)
            
            debug_rect = pygame.Rect(screen_pos.x, screen_pos.y, screen_w, screen_h)
            pygame.draw.rect(self.window, (255, 0, 0), debug_rect, width=2)

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

    plat10 = Platform(-118, 100, 1, "debug-platform-1024x32.png")

    plat2 = Platform(-10, 0, 1, "debug-platform-128x32.png")

    enemy = Enemy(-10, -100, 0, "dummy")

    world = World(player)

    world.addEnemy(enemy)

    world.addPlatform(plat10)
    world.addPlatform(plat2)

    camera = Camera(-100, -100, 640, 360, WINDOW_WIDTH, WINDOW_HEIGHT, world, window)

    font = pygame.font.SysFont("Arial", 24, bold=True)

    clock = pygame.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        window.fill((0, 0, 0))
        buttons = pygame.key.get_pressed()
        world.advancePhysics(buttons)
        camera.moveCamera()
        camera.drawDebug()

        fps = int(clock.get_fps())
        fps_text = font.render(f"FPS: {fps}", True, pygame.Color(255,0,0))
        window.blit(fps_text, (10, 10))
        pygame.display.flip()

        clock.tick(60)
    pygame.quit()
if __name__ == "__main__":
    main()
