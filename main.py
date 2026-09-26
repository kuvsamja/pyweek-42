import copy
import os
import random
import sys
from enum import Enum, auto
from time import perf_counter

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


    def __init__(self, x, y, w, h, damage: float, owner: Owner, alive_time: int, stun_time: int, knockback_speed: float):
        self.box = pygame.Rect(x, y, w, h)
        self.damage = damage
        self.owner = owner
        self.stun_time = stun_time

        self.alive_time = alive_time # TODO: add knockback

        self.knockback_speed = knockback_speed
    def tick(self):
        """decreases the alive time, hitbox should be killed when it reaches 0"""
        self.alive_time -= 1

class Entity(pygame.sprite.Sprite):
    class AnimationState(Enum):
        US_IDLE = auto()
        US_RUN = auto()
        US_RISE = auto()
        US_FALL = auto()

        S_IDLE = auto()
        S_WALK = auto()
        S_HIT1 = auto()
        S_HIT2 = auto()
        S_HIT3 = auto()
        S_HIT4 = auto()
        S_BLOCK = auto()
        S_RISE = auto()
        S_FALL = auto()

        STANCING = auto()

    animation_state: AnimationState
    position: pygame.Vector2
    size: pygame.Vector2
    facing_left: bool
    speed: pygame.Vector2
    gravity_acceleration: float
    dead: bool
    animation_frames: list[list[pygame.Surface]]
    hitbox: pygame.Rect
    def get_image(self, sheet, x, y, width, height):
        rect = pygame.Rect(x, y, width, height)
        image = sheet.subsurface(rect)
        return image
    def __init__(self, x:int, y:int, z_index:int, name: str, sprite_width: int, sprite_height: int, hitbox: pygame.Rect):
        super().__init__()
        # other stuff
        self.facing_left = False
        self.hitbox = hitbox
        self.position = pygame.Vector2(x, y)
        self.size = pygame.Vector2(sprite_width, sprite_height)
        self.rect = pygame.Rect(0, 0, sprite_width, sprite_height)
        self._layer = z_index
        self.buttons_last_frame = []
        self.sprite_name = name

        self.dead = False
        self.speed = pygame.Vector2(0, 0)
        self.gravity_acceleration = 1
        self.animation_state = self.AnimationState.US_IDLE
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
        if len(self.animation_frames[self.AnimationState.US_IDLE.value]) == 0:
            raise FileNotFoundError(f"There is no US_IDLE animation spritesheet for Entity {name}! I looked at path: {os.path.join("assets", name+"_US_IDLE.png")}")
        self.image = self.animation_frames[self.AnimationState.US_IDLE.value][0]
    # sets camera-space coordinates to (x,y)
    def setCameraPosition(self, x, y):
        self.rect = pygame.Rect(x, y, self.size.x, self.size.y)
    def update(self):
        self.frame_counter += 1
        if self.frame_counter % self.animation_frequency != 0:
            return
        animation_duration = len(self.animation_frames[self.animation_state.value])
        try:
            self.frame_counter %= self.animation_frequency * animation_duration
        except ZeroDivisionError:
            print(f"Tweakuje zbog {self.sprite_name}")
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

class Particle(Entity):
    def __init__(self, lifetime, x, y, z_index, width, height, name: str):
        super().__init__(x, y, z_index, name, width, height, pygame.Rect(16,16,16,32))
        self.lifetime = lifetime
        self.image_src = self.image


    def update(self):
        super().update()
        if self.lifetime >= 0:
            self.image = self.animation_frames[self.AnimationState.US_IDLE.value][0]
        else:
            self.image = pygame.Surface((0, 0), pygame.SRCALPHA)


    def tick(self):
        self.lifetime -= 1


class Kitsune(Entity):
    def __init__(self, x, y, z_index, name: str):
        """name: type of the enemy"""
        super().__init__(x, y, z_index, name, 48, 48, pygame.Rect(16,16,16,32))
        self.animation_state = self.AnimationState.US_IDLE
        self.dead = False
        self.is_active = False

        # state stuff
        self.hp = 1000
        self.knockback_speed = 0
        self.knockback_drop = 1

        self.invincibility_timer = 0
        self.stun_timer = 0

        self.grounded = False
        self.head_clipping = False
        self.wall_to_left = False
        self.wall_to_right = False
        self.facing_left = False

        self.time_to_hit = 0
        self.hit_index = 0
        self.hit_timer = 0
        self.is_hitting = False

        # const parameters
        self.run_speed = 0
        self.gravity_acceleration = 0
        self.terminal_velocity = 10
        self.invincibility_duration = 10 # change for the boss

        self.wait_between_hits = 1

        self.single_hit_damage = 10
        self.single_hit_duration = 100
        self.single_hit_timings = [50]
        self.single_hit_box = pygame.Rect(
            0,
            0,
            96,
            96,
        )

        self.pierce_damage = 10
        self.pierce_duration = 100
        self.pierce_timings = [50]
        self.pierce_box = pygame.Rect(
            0,
            0,
            96,
            96,
        )

        self.five_hits_damage = 10
        self.five_hits_duration = 100
        self.five_hits_timings = [10, 30, 50, 70, 90]
        self.five_hits_box = pygame.Rect(
            0,
            0,
            96,
            96,
        )

        self.projectile_damage = 10
        self.projectiles_duration = 100
        self.projectile_timings = [50]
        self.projectile_box = pygame.Rect(
            0,
            0,
            96,
            96,
        )


        self.hitbox.x = 0
        self.hitbox.y = 0
        self.hitbox.w = 96
        self.hitbox.h = 96

        self.arena_left = 0
        self.arena_right = 700



    def damage(self, damage_box: DamageBox): # TODO: finish this
        if self.invincibility_timer > 0: return

        self.knockback_speed = damage_box.knockback_speed
        self.hp -= damage_box.damage
        self.stun_timer = damage_box.stun_time
        self.invincibility_timer = self.invincibility_duration

        print(self.hp)
    def getDB(self, index) -> DamageBox | None:
        match index:
            case 0:
                box_x = (self.position.x + self.hitbox.x - self.single_hit_box.width) if self.facing_left else (self.position.x + self.hitbox.x + self.hitbox.w)
                return DamageBox(
                    x=box_x,
                    y=self.position.y + self.hitbox.h / 2 - self.single_hit_box.height / 2,
                    w=self.single_hit_box.width,
                    h=self.single_hit_box.height,
                    damage=self.single_hit_damage,
                    owner=DamageBox.Owner.SMALL_ENEMY,
                    alive_time=5,
                    stun_time=0,
                    knockback_speed=-5 if self.facing_left else 5
                )
            case 1:
                box_x = (self.position.x + self.hitbox.x - self.single_hit_box.width) if self.facing_left else (self.position.x + self.hitbox.x + self.hitbox.w)
                return DamageBox(
                    x=box_x,
                    y=self.position.y + self.hitbox.h / 2 - self.pierce_box.height / 2,
                    w=self.pierce_box.width,
                    h=self.pierce_box.height,
                    damage=self.pierce_damage,
                    owner=DamageBox.Owner.SMALL_ENEMY,
                    alive_time=5,
                    stun_time=0,
                    knockback_speed=-5 if self.facing_left else 5
                )
            case 2:
                box_x = (self.position.x + self.hitbox.x - self.single_hit_box.width) if self.facing_left else (self.position.x + self.hitbox.x + self.hitbox.w)
                return DamageBox(
                    x=box_x,
                    y=self.position.y + self.hitbox.h / 2 - self.five_hits_box.height / 2,
                    w=self.five_hits_box.width,
                    h=self.five_hits_box.height,
                    damage=self.five_hits_damage,
                    owner=DamageBox.Owner.SMALL_ENEMY,
                    alive_time=5,
                    stun_time=0,
                    knockback_speed=-5 if self.facing_left else 5
                )

        return None


    def teleport(self, player_x):
        distance = 20
        dir = random.randint(0, 1)
        self.facing_left = bool(dir)

        if dir == 0:
            self.position.x = player_x - self.hitbox.width - distance
        else:
            self.position.x = player_x + 48 + distance

    def handle(self, player_x: float) -> list[DamageBox]:
        """updates the enemy"""


        if self.hit_timer < 0:
            self.setAnimationState(self.AnimationState.S_IDLE)
            self.time_to_hit = (self.time_to_hit-1) % self.wait_between_hits
        self.hit_timer -= 1
        self.invincibility_timer -= 1

        db = None
        if self.time_to_hit == 0:
            self.time_to_hit = -1
            self.hit = random.randint(0, 3)
            self.teleport(player_x)

            match self.hit:
                case 0:
                    self.hit_timer = self.single_hit_duration
                    self.setAnimationState(self.AnimationState.S_HIT1)
                case 1:
                    self.hit_timer = self.pierce_duration
                    self.setAnimationState(self.AnimationState.S_HIT2)
                case 2:
                    self.hit_timer = self.five_hits_duration
                    self.setAnimationState(self.AnimationState.S_HIT3)
                case 3:
                    self.hit_timer = self.projectiles_duration
                    self.setAnimationState(self.AnimationState.S_HIT4)
        elif self.hit_timer > 0:
            match self.hit:
                case 0: # TODO: fix this
                    if self.single_hit_duration - self.hit_timer in self.single_hit_timings:
                        db = self.getDB(self.hit)
                case 1:
                    if self.pierce_duration - self.hit_timer in self.pierce_timings:
                        db = self.getDB(self.hit)
                case 2:
                    if self.five_hits_duration - self.hit_timer in self.five_hits_timings:
                        db = self.getDB(self.hit)
                case 3:
                    if self.projectiles_duration - self.hit_timer in self.projectile_timings:
                        db = self.getDB(self.hit)

        db_list = []
        db_list.append(
            DamageBox(
                x=self.position.x + self.hitbox.x,
                y=self.position.y + self.hitbox.y,
                w=self.hitbox.w/2,
                h=self.hitbox.h,
                damage=10,
                owner=DamageBox.Owner.SMALL_ENEMY,
                alive_time=1,
                stun_time=0,
                knockback_speed=-5
            )
        )
        
        db_list.append(
            DamageBox(
                x=self.position.x + self.hitbox.x + self.hitbox.w/2,
                y=self.position.y + self.hitbox.y,
                w=self.hitbox.w/2,
                h=self.hitbox.h,
                damage=10,
                owner=DamageBox.Owner.SMALL_ENEMY,
                alive_time=1,
                stun_time=0,
                knockback_speed=5
            )
        )
        if db is not None:
            db_list.append(db)
        return db_list

class Enemy(Entity):
    def __init__(self, x, y, z_index, name: str):
        """name: type of the enemy"""
        super().__init__(x, y, z_index, name, 48, 48, pygame.Rect(16,16,16,32))
        self.animation_state = self.AnimationState.US_IDLE
        self.dead = False

        # state stuff
        self.hp = 100
        self.knockback_speed = 0
        self.knockback_drop = 0.2

        self.invincibility_timer = 0
        self.stun_timer = 0
        self.is_hitting = False
        self.hit_timer = 0

        self.grounded = False
        self.head_clipping = False
        self.wall_to_left = False
        self.wall_to_right = False
        self.looking_right = True

        # const parameters
        self.run_speed = 1
        self.gravity_acceleration = 0.8
        self.terminal_velocity = 10
        self.invincibility_duration = 10 # change for the boss
        self.hit_time = 40
        self.player_detection_dist = 200
        self.player_hit_dist = 100
        self.sword_box_width = 100
        self.sword_box_height = 20

        self.sword_particle = Particle(
            -1, # TODO: make this be as long as the swing animation
            0,
            0,
            self._layer,
            self.sword_box_width,
            self.sword_box_height,
            "player_sword_swing"
        )

    def damage(self, damage_box: DamageBox): # TODO: finish this
        if self.invincibility_timer > 0: return

        self.knockback_speed = damage_box.knockback_speed
        self.hp -= damage_box.damage
        self.stun_timer = damage_box.stun_time
        self.invincibility_timer = self.invincibility_duration

    def resetSwordParticle(self, x, y, lifetime):
        self.sword_particle.position.x = x
        self.sword_particle.position.y = y
        self.sword_particle.lifetime = lifetime

    def handle(self, player_x: float) -> list[DamageBox]:
        """updates the enemy"""
        self.speed.x = self.knockback_speed
        self.invincibility_timer -= 1
        self.stun_timer -= 1
        self.hit_timer -= 1

        if self.grounded:
            self.speed.y = min(self.speed.y, 0)

        else:
            # apply gravity and cap it at terminal velocity
            self.speed.y = min(self.speed.y + self.gravity_acceleration, self.terminal_velocity)

        if self.head_clipping:
            self.speed.y = max(0, self.speed.y)
        box_x = (self.position.x + self.hitbox.x - self.sword_box_width) if self.facing_left else (self.position.x + self.hitbox.x + self.hitbox.w)

        dir = 0
        if self.hit_timer < 0:
            dir = 1 if self.position.x - player_x < 0 else -1
            self.facing_left = dir==-1
        if abs(self.position.x - player_x) < self.player_hit_dist and self.hit_timer < 0:
            self.hit_timer = self.hit_time
        if player_x is not None and self.hit_timer < 0 and abs(self.position.x - player_x) < self.player_detection_dist: # TODO: make the dist checl the same left and right
            self.speed.x += self.run_speed * dir


        db = []
        if self.hit_timer >= 0:
            self.setAnimationState(self.AnimationState.S_HIT1)
            if self.hit_timer == int(self.hit_time / 2):
                self.resetSwordParticle(box_x, self.position.y + self.hitbox.h - self.sword_box_height / 2, 10)
                db.append(
                    DamageBox(
                        x=box_x,
                        y=self.position.y + self.hitbox.h - self.sword_box_height / 2,
                        w=self.sword_box_width,
                        h=self.sword_box_height,
                        damage=10,
                        owner=DamageBox.Owner.SMALL_ENEMY,
                        alive_time=5,
                        stun_time=10,
                        knockback_speed=-5 if self.facing_left else 5
                    )
                )

        if self.knockback_speed > 0:
            self.knockback_speed -= self.knockback_drop
            self.knockback_speed = max(self.knockback_speed, 0)
        elif self.knockback_speed < 0:
            self.knockback_speed += self.knockback_drop
            self.knockback_speed = min(self.knockback_speed, 0)
        self.position += self.speed

        # print(f"hp: {self.hp}")
        # print(f"position: {self.position}")
        # print(f"speed:    {self.speed}")
        # print(f"grounded: {self.grounded}")
        return db

class Player(Entity): # TODO: add movement
    def __init__(self, x, y, z_index):
        super().__init__(x, y, z_index, "player", 48, 48, pygame.Rect(16,16,16,32)) # player sprite size is 48x48
        self.animation_state = self.AnimationState.US_IDLE
        self.dead = False

        # state stuff
        self.hp = 100
        self.knockback_speed = 0
        # self.poise = 100 TODO: mabye this
        self.invincibility_timer = 0
        self.stun_timer = 0

        self.sword_timer = 0
        self.swing_count = 0

        self.parry_window = 0
        self.parry_timer = 0
        self.blocking = False

        self.stanced = False
        self.stance_transition_timer = 0

        self.grounded = False
        self.head_clipping = False
        self.wall_to_left = False
        self.wall_to_right = False
        self.can_jump = False
        self.looking_right = True


        # const parameters
        ## unstanced
        self.run_speed = 10
        self.knockback_drop_us = 0.2 # how much knockback speed to decrease by frame

        ## stanced
        self.stance_transition_duration = 30
        self.walk_speed = 3
        self.knockback_drop_s = 0.4
        self.knockback_drop_s_block = 0.5

        self.parry_window_base = 8

        self.sword_box_width = 100
        self.sword_box_height = 20

        self.sword_particle = Particle(
            -1, # TODO: make this be as long as the swing animation
            0,
            0,
            self._layer,
            self.sword_box_width,
            self.sword_box_height,
            "player_sword_swing"
        )

        ## other
        self.gravity_acceleration = 0.8
        self.terminal_velocity = 10

        self.invincibility_duration = 10
        self.sword_delay = 25

        # jump unstanced
        self.jump_speed = 8
        self.jump_time = 14 # max time to hold a jump in frames
        self.jump_timer = 0
        self.can_jump = False # see if player can continue to jump upwards by holding tge button

        # jump stanced
        self.stanced_jump_speed = 7
        self.stanced_jump_time = 5 # max time to hold a jump in frames

    def setScreenShakeFunc(self, func):
        self.screen_shake = func
    def resetSwordParticle(self, x, y, lifetime):
        self.sword_particle.position.x = x
        self.sword_particle.position.y = y
        self.sword_particle.lifetime = lifetime

    def parryCallback(self, damage_box):
        self.invincibility_timer = self.invincibility_duration
        self.knockback_speed = damage_box.knockback_speed

    def damage(self, damage_box: DamageBox): # TODO: finish this
        if self.invincibility_timer > 0: return
        if self.parry_timer >= 0:
           self.parryCallback(damage_box)
           return
        if self.blocking:
            self.hp -= damage_box.damage/2
            self.screen_shake(1, 10)
            return
        self.hp -= damage_box.damage
        self.stun_timer = damage_box.stun_time
        self.invincibility_timer = self.invincibility_duration

        self.knockback_speed = damage_box.knockback_speed

        self.screen_shake(3, 10)


    def handleUnstanced(self, buttons) -> list[DamageBox]:
        self.setAnimationState(Entity.AnimationState.US_IDLE)

        dir = 0
        if buttons[pygame.K_LEFT]: dir = -1
        if buttons[pygame.K_RIGHT]: dir = 1
        if buttons[pygame.K_LEFT] and buttons[pygame.K_RIGHT]: dir = 0

        if dir != 0:
            self.speed.x += self.run_speed*dir
            self.facing_left = dir==-1
            self.setAnimationState(Entity.AnimationState.US_RUN)
        ## jump
        # initial jump
        if self.grounded and buttons[pygame.K_z] and not self.buttons_last_frame[pygame.K_z]:
            self.speed.y = -self.jump_speed
            self.can_jump = True
            self.jump_timer = 0
        # holding space
        if self.can_jump and buttons[pygame.K_z]:
            if self.jump_timer < self.jump_time and not self.head_clipping:
                self.speed.y = -self.jump_speed
                self.jump_timer += 1
            else:
                self.can_jump = False
        else:
            self.can_jump = False


        if not self.grounded:
            if self.speed.y > 0: self.setAnimationState(self.AnimationState.US_FALL)
            else: self.setAnimationState(self.AnimationState.US_RISE)


        return []

    def handleStanced(self, buttons) -> list[DamageBox]:
        self.setAnimationState(Entity.AnimationState.S_IDLE)

        self.blocking = False
        if buttons[pygame.K_c]:
            if not self.buttons_last_frame[pygame.K_c]:
                if self.parry_timer > -10:
                    self.parry_window -= 2
                else:
                    self.parry_window = self.parry_window_base
                self.parry_timer = self.parry_window # TODO: make this better

            self.blocking = True
            self.setAnimationState(self.AnimationState.S_BLOCK)
            return []

        dir = 0
        if buttons[pygame.K_LEFT]: dir = -1
        if buttons[pygame.K_RIGHT]: dir = 1
        if buttons[pygame.K_LEFT] and buttons[pygame.K_RIGHT]: dir = 0

        if dir != 0:
            self.speed.x += self.walk_speed*dir
            self.facing_left = dir==-1
            self.setAnimationState(Entity.AnimationState.S_WALK)

        # jump
        ## initial jump
        if self.grounded and buttons[pygame.K_z] and not self.buttons_last_frame[pygame.K_z]:
            self.speed.y = -self.stanced_jump_speed
            self.can_jump = True
            self.jump_timer = 0
        ## holding space
        if self.can_jump and buttons[pygame.K_z]:
            if self.jump_timer < self.stanced_jump_time and not self.head_clipping:
                self.speed.y = -self.stanced_jump_speed
                self.jump_timer += 1
            else:
                self.can_jump = False
        else:
            self.can_jump = False

        if not self.grounded:
            if self.speed.y > 0: self.setAnimationState(self.AnimationState.S_FALL)
            else: self.setAnimationState(self.AnimationState.S_RISE)



        db_list = []
        if buttons[pygame.K_x] and not self.buttons_last_frame[pygame.K_x] and self.sword_timer < 0: # TODO: add hit polling

            box_x = (self.position.x + self.hitbox.x - self.sword_box_width) if self.facing_left else (self.position.x + self.hitbox.x + self.hitbox.w)

            # box_x = (self.position.x - self.sword_box_width) if self.facing_left else (self.position.x + self.size.x)
            self.resetSwordParticle(box_x, self.position.y + self.hitbox.h - self.sword_box_height / 2, 10)
            if self.sword_timer > -20:

                self.swing_count += 1
                self.swing_count %= 3

            else:
                self.swing_count = 0

            self.sword_timer = self.sword_delay

            db_list.append(
                DamageBox(
                    x=box_x,
                    y=self.position.y + self.hitbox.h - self.sword_box_height / 2,
                    w=self.sword_box_width,
                    h=self.sword_box_height,
                    damage=10,
                    owner=DamageBox.Owner.PLAYER,
                    alive_time=5,
                    stun_time=10,
                    knockback_speed=-5 if self.facing_left else 5
                )
            )


        if self.sword_timer >= 0:
            self.setAnimationState(self.AnimationState(self.AnimationState.S_HIT1.value + self.swing_count))

        return db_list

    def handle(self, buttons) -> list[DamageBox]:
        """updates the player"""
        self.speed.x = self.knockback_speed
        self.invincibility_timer -= 1
        self.stun_timer -= 1
        self.sword_timer -= 1
        self.parry_timer -= 1
        self.stance_transition_timer -= 1

        if self.grounded:
            self.speed.y = min(self.speed.y, 0)

        else:
            # apply gravity and cap it at terminal velocity
            self.speed.y = min(self.speed.y + self.gravity_acceleration, self.terminal_velocity)

        if self.head_clipping:
            self.speed.y = max(0, self.speed.y)

        if buttons[pygame.K_LSHIFT] and not self.buttons_last_frame[pygame.K_LSHIFT] and self.grounded:
            self.stance_transition_timer = self.stance_transition_duration
            self.stanced = not self.stanced

        db_list = []

        if self.stance_transition_timer >= 0:
            self.setAnimationState(self.AnimationState.STANCING)

        elif self.stanced: db_list = self.handleStanced(buttons)
        else:            db_list = self.handleUnstanced(buttons)

        if self.knockback_speed > 0:
            if self.blocking:  self.knockback_speed -= self.knockback_drop_s_block
            elif self.stanced: self.knockback_speed -= self.knockback_drop_s
            else:              self.knockback_speed -= self.knockback_drop_us
            self.knockback_speed = max(self.knockback_speed, 0)
        elif self.knockback_speed < 0:
            if self.blocking:  self.knockback_speed += self.knockback_drop_s_block
            elif self.stanced: self.knockback_speed += self.knockback_drop_s
            else:              self.knockback_speed += self.knockback_drop_us
            self.knockback_speed = min(self.knockback_speed, 0)
        self.position += self.speed
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
        self.all_sprites.add(player.sword_particle)
    def addPlatform(self, platform: Platform):
        self.platforms.append(platform)
        self.all_sprites.add(platform)
    def addEnemy(self, enemy: Enemy):
        self.enemies.append(enemy)
        self.all_sprites.add(enemy)
        self.all_sprites.add(enemy.sword_particle)
    def addKitsune(self, kitsune: Kitsune):
        self.kitsune = kitsune
        self.all_sprites.add(kitsune)
        # self.all_sprites.add(kitsune.slash)

    @staticmethod
    def entityPlatformCollision(platform: Platform, entity: Entity) -> bool:
        ex = entity.position.x + entity.hitbox.x
        ey = entity.position.y + entity.hitbox.y

        return (
            platform.position.x < ex + entity.hitbox.w and
            platform.position.x + platform.size.x > ex and
            platform.position.y < ey + entity.hitbox.h and
            platform.position.y + platform.size.y > ey
        )

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

            ex = self.player.position.x + self.player.hitbox.x
            ey = self.player.position.y + self.player.hitbox.y

            overlap_x = min(
                (ex + self.player.hitbox.w) - platform.position.x,
                (platform.position.x + platform.size.x) - ex
            )
            overlap_y = min(
                (ey + self.player.hitbox.h) - platform.position.y,
                (platform.position.y + platform.size.y) - ey
            )

            if overlap_x < overlap_y:
                if (ex + self.player.hitbox.w / 2) < (platform.position.x + platform.size.x / 2):
                    self.player.position.x -= overlap_x
                else:
                    self.player.position.x += overlap_x
            else:
                if (ey + self.player.hitbox.h / 2) < (platform.position.y + platform.size.y / 2):
                    self.player.position.y -= overlap_y
                else:
                    self.player.position.y += overlap_y
            # TODO: ADD PROPER COLLISION PUSHING INVOLVING DX AND DY PLEASE PLEASE PLEASE REMEMBER THIS
    def playerTouchCheck(self):
        self.player.grounded = False
        self.player.head_clipping = False
        self.player.wall_to_right = False
        self.player.wall_to_left = False

        ex = self.player.position.x + self.player.hitbox.x
        ey = self.player.position.y + self.player.hitbox.y

        touch_check = pygame.Rect(1, 1, 1, 1) # TODO: fix player floating by one pixel

        feet_box = pygame.Rect(ex, self.player.position.y + self.player.hitbox.y + self.player.hitbox.h, self.player.hitbox.w, touch_check.h)
        head_box = pygame.Rect(ex, ey - touch_check.h, self.player.hitbox.w, touch_check.h)
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

            ex = enemy.position.x + enemy.hitbox.x
            ey = enemy.position.y + enemy.hitbox.y


            feet_box = pygame.Rect(ex, enemy.position.y + enemy.hitbox.y + enemy.hitbox.h, enemy.hitbox.w, touch_check.h)
            head_box = pygame.Rect(ex, ey - touch_check.h, enemy.hitbox.w, touch_check.h)
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
                ex = enemy.position.x + enemy.hitbox.x
                ey = enemy.position.y + enemy.hitbox.y
                overlap_x = min(
                                (ex + enemy.hitbox.w) - platform.position.x,
                                (platform.position.x + platform.size.x) - ex
                            )
                overlap_y = min(
                    (ey + enemy.hitbox.h) - platform.position.y,
                    (platform.position.y + platform.size.y) - ey
                )
                if overlap_x < overlap_y:
                    if (ex + enemy.hitbox.w / 2) < (platform.position.x + platform.size.x / 2):
                        enemy.position.x -= overlap_x
                    else:
                        enemy.position.x += overlap_x
                else:
                    if (ey + enemy.hitbox.h / 2) < (platform.position.y + platform.size.y / 2):
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
                            enemy.position.x + enemy.hitbox.x,
                            enemy.position.y + enemy.hitbox.y,
                            enemy.hitbox.w,
                            enemy.hitbox.h
                        )
                    ):
                        enemy.damage(db)
                if db.box.colliderect(
                    self.kitsune.position.x + self.kitsune.hitbox.x,
                    self.kitsune.position.y + self.kitsune.hitbox.y,
                    self.kitsune.hitbox.w,
                    self.kitsune.hitbox.h
                ):
                    self.kitsune.damage(db)
            elif db.owner == DamageBox.Owner.SMALL_ENEMY and db.box.colliderect(
                    pygame.Rect(self.player.position.x + self.player.hitbox.x,
                                self.player.position.y + self.player.hitbox.y,
                                self.player.hitbox.w,
                                self.player.hitbox.h)):
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
        self.player.sword_particle.tick()
        for enemy in self.enemies: enemy.sword_particle.tick()

        for enemy in self.enemies: self.damage_boxes += enemy.handle(self.player.position.x)
        self.damage_boxes += self.player.handle(buttons)
        self.damage_boxes += self.kitsune.handle(self.player.position.x)


        self.handleCollisions()

class Margins:
    def __init__(self, up, down, left, right):
        self.up = up
        self.down = down
        self.left = left
        self.right = right

class Camera:
    def __init__(self, x, y, world_width, world_height, pixel_width, pixel_height, world: World, window: pygame.Surface, screen: pygame.Surface):
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
        self.screen = screen
        self.render_offset = [0,0]
        self.shake_timer = 0
        self.shake_intensity = 5
    def screenShake(self, shake_intensity: int, shake_duration: int):
        """Shake the screen. shake_duration is in frames"""
        self.shake_timer = shake_duration
        self.shake_intensity = shake_intensity
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

        if self.shake_timer > 0:
            self.render_offset[0] = random.randint(-self.shake_intensity, self.shake_intensity)
            self.render_offset[1] = random.randint(-self.shake_intensity, self.shake_intensity)

            self.shake_timer -= 1
            if self.shake_timer == 0:
                self.render_offset = [0, 0]
        self.screen.blit(self.window, self.render_offset)
    def drawDebug(self):
        scale_x = self.pixel_width / self.world_width
        scale_y = self.pixel_height / self.world_height
        self.draw()
        for sprite in self.world.all_sprites:
            if isinstance(sprite, Entity):
                hitbox_world_pos = pygame.Vector2(
                    sprite.hitbox.x + sprite.position.x,
                    sprite.hitbox.y + sprite.position.y
                )
                screen_pos = self.pointToScreen(hitbox_world_pos)
                screen_w = int(sprite.hitbox.w * scale_x)
                screen_h = int(sprite.hitbox.h * scale_y)
                temp_r = pygame.Rect(int(screen_pos.x), int(screen_pos.y), screen_w, screen_h)
                pygame.draw.rect(self.screen, (255, 0, 0), temp_r, width=3)

        for db in self.world.damage_boxes:
            screen_pos = self.pointToScreen(pygame.Vector2(db.box.x, db.box.y))

            screen_w = int(db.box.width * scale_x)
            screen_h = int(db.box.height * scale_y)

            debug_rect = pygame.Rect(screen_pos.x, screen_pos.y, screen_w, screen_h)
            pygame.draw.rect(self.screen, (255, 0, 0), debug_rect, width=2)

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
    def pixel_text(text: str, font: pygame.Font, scale=1.0, color=(255, 255, 255)):
        tempsurface = font.render(text, False, color)
        scale *= permscaling * 0.5
        if scale != 1:
            tempsurface = pygame.transform.scale_by(tempsurface, scale)

        return tempsurface
    if not os.path.isfile(os.path.join("assets", "scaling.txt")):
        with open(os.path.join("assets", "scaling.txt"), "w") as f:
            scaling = 2.0
            permscaling = 2.0
            f.write(str(permscaling))
    else:
        with open(os.path.join("assets", "scaling.txt"), "r") as f:
            scaling = float(f.read()) # current/unapplied scaling
            permscaling = scaling # permanent scaling
    WINDOW_WIDTH = round(640 * permscaling)
    WINDOW_HEIGHT = round(360 * permscaling)

    pygame.init()
    window = pygame.display.set_mode(
        (WINDOW_WIDTH, WINDOW_HEIGHT),
    )

    pygame.display.set_caption("pygame")

    display_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    player = Player(0, 0, 0)

    enemy = Enemy(-10, -100, 0, "dummy")


    kitsune = Kitsune(1024+30+640/2-96/2, 100 + 4, 0, "kitsune")
    kitsune.arena_left = 1024+30
    kitsune.arena_right = 1024+30+640


    world = World(player)

    world.addKitsune(kitsune)

    world.addEnemy(enemy)

    world.addPlatform(
        Platform(0, 100, 1, "debug-platform-1024x32.png")
    )
    world.addPlatform(
        Platform(-10, 0, 1, "debug-platform-128x32.png")
    )
    world.addPlatform(
        Platform(1024, 100, 1, "debug-platform-30x100.png")
    )
    world.addPlatform(
        Platform(1024+30+640, 100, 1, "debug-platform-30x100.png")
    )
    world.addPlatform(
        Platform(1024+30, 200, 1, "debug-platform-640x100.png")
    )

    camera = Camera(-100, -100, 640, 360, WINDOW_WIDTH, WINDOW_HEIGHT, world, display_canvas, window)

    player.setScreenShakeFunc(camera.screenShake)
    # fonts and messages
    fontPath = os.path.join("assets", "Geist-Static.ttf")
    base_font = pygame.font.Font(fontPath, 40)

    total_char_index = 0
    word_char_index = 0
    MESSAGE1 = ["170 AK", "(After Kōfuku)", " ", "Japan has forgotten the pandas.", "Nearly all were eradicated.", " ", "One remains.", " ", "His name is Iskra Blasko.", "And he's coming for the fox", "who brought his kind to extinction."]
    MESSAGE1LEN = sum(len(item) for item in MESSAGE1)
    last_text = []
    current_text = None
    current_word = 0
    next_char_time = 0
    typing_speed = 0.11
    time_finished = 0
    fadeaway_time = 3
    black_time = 0.5 # seconds to be black after text completely dissapears
    text_stay_time = 1.5 # seconds for text to stay before fading away
    just_title_time = 1 # how many seconds after entering main menu to be just title displayed
    # main menu
    current_option = 0
    total_options = 4
    last_time_arrow_key_pressed = 0
    delay_between_two_presses = 0.2 # delay between two arrow key presses
    main_menu_at = 0
    main_menu = True
    controls_menu = False
    settings_menu = False
    clock = pygame.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        display_canvas.fill((0, 0, 0))
        buttons = pygame.key.get_pressed()


        if total_char_index < MESSAGE1LEN:
            current_time = perf_counter()

            if current_time >= next_char_time:
                word_char_index += 1

                current_text = MESSAGE1[current_word][:word_char_index]

                if word_char_index == len(MESSAGE1[current_word]):
                    if current_word + 1 < len(MESSAGE1):
                        last_text.append(current_text)
                        current_text = ""

                    current_word += 1
                    word_char_index = 0

                next_char_time = current_time + typing_speed
                total_char_index += 1
        elif total_char_index==MESSAGE1LEN and time_finished==0:
            time_finished = perf_counter() + text_stay_time
        elif perf_counter() - time_finished > fadeaway_time + black_time + 2 and not main_menu:
            world.advancePhysics(buttons)
            camera.moveCamera()
            camera.drawDebug()
        elif controls_menu:
            if buttons[pygame.K_ESCAPE]:
                controls_menu = False
            SPACING = 20
            prev_text = ""
            subtitle_text = pixel_text("Guidance", base_font, 1.25)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, WINDOW_HEIGHT // 8)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Left/Right arrow to move", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("L Shift to toggle the attacking stance", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Z to jump", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("X to attack (when stanced)", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("C to block/parry enemy attack", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("The goal of the game is to reach and kill the", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + 2 * SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("fox (Kitsune) who eradicated all pandas from Japan.", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("But beware, everyone's HP is degrading with time.", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("When you hit an enemy you take some of it's time, and", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("same goes vice versa. If you run out of time, you die.", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Good luck and try to avenge your kind!", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Press [ESC] to exit to main menu", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, WINDOW_HEIGHT - subtitle_text.get_height() - SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
        elif settings_menu:
            if buttons[pygame.K_ESCAPE]:
                settings_menu = False
            if buttons[pygame.K_RIGHT] and scaling < 3 and perf_counter() - last_time_arrow_key_pressed > delay_between_two_presses:
                scaling += 0.5
                last_time_arrow_key_pressed = perf_counter()
            if buttons[pygame.K_LEFT] and scaling > 1 and perf_counter() - last_time_arrow_key_pressed > delay_between_two_presses:
                scaling -= 0.5
                last_time_arrow_key_pressed = perf_counter()
            if buttons[pygame.K_z] and permscaling!=scaling:
                permscaling = scaling
                WINDOW_WIDTH = 640 * scaling
                WINDOW_HEIGHT = 360 * scaling
                with open(os.path.join("assets", "scaling.txt"), "w") as f:
                    f.write(str(permscaling))
                window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                display_canvas = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
                camera = Camera(-100, -100, 640, 360, WINDOW_WIDTH, WINDOW_HEIGHT, world, display_canvas, window)
            SPACING = 20
            prev_text = ""
            subtitle_text = pixel_text("Options", base_font, 1.25)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, WINDOW_HEIGHT // 8)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Press [Z] to apply scaling options", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Scaling", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text(f"‹ {scaling}X ›", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, temp_pos[1] + prev_text.get_height() + SPACING)
            prev_text = subtitle_text
            display_canvas.blit(subtitle_text, temp_pos)
            subtitle_text = pixel_text("Press [ESC] to exit to main menu", base_font, 0.75)
            temp_pos = (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, WINDOW_HEIGHT - subtitle_text.get_height() - SPACING)
            display_canvas.blit(subtitle_text, temp_pos)
        elif perf_counter() - time_finished > fadeaway_time + black_time and main_menu:
            if main_menu_at == 0:
                main_menu_at = perf_counter()
            # main menu

            title_text = pixel_text("REMAINDER.", base_font, 2)
            display_canvas.blit(title_text, (WINDOW_WIDTH // 2 - title_text.get_width() // 2, WINDOW_HEIGHT//8))
            subtitle_text = pixel_text("A PyWeek 42 Entry", base_font)
            display_canvas.blit(subtitle_text, (WINDOW_WIDTH // 2 - subtitle_text.get_width() // 2, WINDOW_HEIGHT//8 + title_text.get_height()))
            if perf_counter() - main_menu_at > just_title_time:
                if buttons[pygame.K_DOWN] and perf_counter() - last_time_arrow_key_pressed > delay_between_two_presses:
                    current_option = (current_option + 1) % total_options
                    last_time_arrow_key_pressed = perf_counter()
                if buttons[pygame.K_UP] and perf_counter() - last_time_arrow_key_pressed > delay_between_two_presses:
                    current_option = (current_option - 1) % total_options
                    last_time_arrow_key_pressed = perf_counter()
                if buttons[pygame.K_RETURN]:
                    match current_option:
                        case 0:
                            main_menu = False
                        case 1:
                            controls_menu = True
                        case 2:
                            settings_menu = True
                        case 3:
                            running = False
                start_text = pixel_text("Embark", base_font)
                temp_pos = (WINDOW_WIDTH // 2 - start_text.get_width() // 2, WINDOW_HEIGHT//8 + title_text.get_height() + subtitle_text.get_height() + WINDOW_HEIGHT//24)
                display_canvas.blit(start_text, temp_pos)
                # they are all centering based on start_text, which may not be so bad, but note for the future
                help_text = pixel_text("Guidance", base_font)
                display_canvas.blit(help_text, (WINDOW_WIDTH // 2 - start_text.get_width() // 2, temp_pos[1] + start_text.get_height()))
                settings_text = pixel_text("Options", base_font)
                display_canvas.blit(settings_text, (WINDOW_WIDTH // 2 - start_text.get_width() // 2,  temp_pos[1] + start_text.get_height() + help_text.get_height()))
                exit_text = pixel_text("Depart", base_font)
                display_canvas.blit(exit_text, (WINDOW_WIDTH // 2 - start_text.get_width() // 2,  temp_pos[1] + start_text.get_height() + help_text.get_height() + settings_text.get_height()))

                minx = min(WINDOW_WIDTH // 2 - start_text.get_width() // 2, WINDOW_WIDTH // 2 - start_text.get_width() // 2, WINDOW_WIDTH // 2 - exit_text.get_width() // 2)
                pygame.draw.circle(display_canvas, (255,255,255), (minx - WINDOW_WIDTH//64, WINDOW_HEIGHT//8 + title_text.get_height() + subtitle_text.get_height() + WINDOW_HEIGHT//24 + start_text.get_height() // 2 + current_option * start_text.get_height()), round(WINDOW_HEIGHT * 10 / 720))
        if buttons[pygame.K_z] and main_menu_at == 0: #0.0139
            time_finished = perf_counter() - (fadeaway_time + black_time + 1)
            total_char_index = 9999999999
        fps = int(clock.get_fps())
        fps_text = pixel_text(f"FPS: {fps}", base_font, color=pygame.Color(255,0,0))
        display_canvas.blit(fps_text, (10, 10))
        if time_finished==0 or perf_counter() - time_finished < 0:
            for i, t in enumerate(last_text):
                message_text = pixel_text(f"{t}", base_font, 0.75)
                display_canvas.blit(message_text, (WINDOW_WIDTH // 2 - message_text.get_width() // 2, WINDOW_HEIGHT//16 + i * WINDOW_HEIGHT * 1/24))
            message_text = pixel_text(f"{current_text}", base_font, 0.75)
            display_canvas.blit(message_text, (WINDOW_WIDTH // 2 - message_text.get_width() // 2, WINDOW_HEIGHT//16 + len(last_text) * WINDOW_HEIGHT * 1/24))


            exit_text = pixel_text("Press [Z] to skip", base_font, 0.75)
            display_canvas.blit(exit_text, (WINDOW_WIDTH // 2 - exit_text.get_width() // 2, WINDOW_HEIGHT - exit_text.get_height() - WINDOW_HEIGHT//24))
        elif perf_counter() - time_finished > 0 and perf_counter() - time_finished < fadeaway_time:
            dt = perf_counter() - time_finished
            dtClamped = (1 - dt/fadeaway_time)
            for i, t in enumerate(last_text):
                message_text = pixel_text(f"{t}", base_font, 0.75, color=pygame.Color(int(dtClamped * 255),int(dtClamped * 255),int(dtClamped * 255)))
                display_canvas.blit(message_text, (WINDOW_WIDTH // 2 - message_text.get_width() // 2, WINDOW_HEIGHT//16 + i * WINDOW_HEIGHT * 1/24))
            message_text = pixel_text(f"{current_text}", base_font, 0.75, color=pygame.Color(int(dtClamped * 255),int(dtClamped * 255),int(dtClamped * 255)))
            display_canvas.blit(message_text, (WINDOW_WIDTH // 2 - message_text.get_width() // 2, WINDOW_HEIGHT//16 + len(last_text) * WINDOW_HEIGHT * 1/24))

            exit_text = pixel_text("Press [Z] to skip", base_font, 0.75)
            display_canvas.blit(exit_text, (WINDOW_WIDTH // 2 - exit_text.get_width() // 2, WINDOW_HEIGHT - exit_text.get_height() - WINDOW_HEIGHT//24))
        if buttons[pygame.K_SPACE]:
            camera.screenShake(5, 60)
        if main_menu:
            window.blit(display_canvas, (0,0))
        pygame.display.flip()

        clock.tick(60)
    pygame.quit()
    sys.exit(0)
if __name__ == "__main__":
    main()
