import pygame
import math
import random
import sys
import json
import os

# Initialize Pygame
pygame.init()

# Get screen dimensions for fullscreen
info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

# Colors
SAND_COLOR = (194, 178, 128)  # Desert sand
DARK_TAN = (139, 119, 101)    # Player tanks
BLACK = (0, 0, 0)             # Enemy tanks
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)        # Explosion colors
YELLOW = (255, 255, 0)

# Game Variables - Easy to tweak for balancing
PLAYER_VARS = {
    'movement_speed': 2,
    'shot_speed': 8,
    'shot_distance': 500,
    'fire_rate': 500,  # milliseconds
    'powerup_duration': 5000,  # milliseconds
    'max_health': 100,
    'tank_size': (60, 45),
    'barrel_length': 35,
    'barrel_width': 12
}

ENEMY_VARS = {
    'movement_speed': 1,
    'shot_speed': 6,
    'shot_distance': 350,
    'fire_rate': 1500,  # milliseconds
    'powerup_duration': 3000,  # milliseconds
    'max_health': 50,
    'tank_size': (55, 40),
    'barrel_length': 30,
    'barrel_width': 10,
    'base_damage': 10,  # Add base damage for enemies
}

GAME_VARS = {
    'starting_enemies': 1,  # Start with 1 for single player
    'enemies_per_wave': 1,  # How many enemies to add each wave
    'spawn_distance': 100,  # How far off-screen enemies spawn
    'health_bar_width': 70,
    'health_bar_height': 8,
    'enemy_spawn_delay': 3000,  # 3 seconds between enemy spawns in milliseconds
    'enemy_upgrade_min_waves': 1,  # Minimum waves before first upgrade
    'enemy_upgrade_max_waves': 5,  # Maximum waves before upgrade
    'enemy_upgrade_percentages': [5, 10, 15, 20, 25, 30],  # Possible upgrade percentages
    'enemy_upgrade_weights': [40, 30, 15, 10, 3, 2],  # Weights for percentages (higher = more likely)
}

OBSTACLE_VARS = {
    'min_obstacles': 3,
    'max_obstacles': 8,
    'min_size': 40,
    'max_size': 120,
    'rock_color': (101, 67, 33),  # Dark brown rocks
    'min_distance_from_spawn': 150,  # Keep obstacles away from spawn points
    'min_distance_between': 80  # Minimum distance between obstacles
}

EFFECT_VARS = {
    'explosion_duration': 500,  # milliseconds
    'explosion_max_size': 80,
    'hit_effect_duration': 200,
    'hit_effect_size': 30,
    'particle_count': 8,
    'particle_speed': 3,
    'track_trail_length': 600,  # Maximum length of track trail in pixels
    'track_spacing': 12,  # Distance between track points (increased for segmented look)
    'track_width': 20,  # Width of the tank tracks
    'track_fade_steps': 30,  # Number of fade steps for tracks
}

LEVELING_VARS = {
    'base_level_xp': 500,  # XP needed for first level
    'xp_increase_percent': 10,  # How much more XP needed each level (%)
    'xp_per_hit': 10,  # XP gained when bullet hits enemy
    'xp_per_kill': 25,  # XP gained when enemy is destroyed
    'stat_increase_percent': 10,  # How much each stat increases per level (%)
    'max_stat_increase': 100,  # Maximum total increase (% - so 100% = double)
}

POWERUP_VARS = {
    'shield_base_duration': 10000,  # 10 seconds in milliseconds
    'speed_boost_multiplier': 1.5,  # 50% speed increase
    'rapid_fire_shots': 100,
    'shotgun_shots': 100,
    'shotgun_pellets': 5,  # Number of pellets per shot
    'shotgun_spread': 0.3,  # Spread angle in radians
    'homing_shots': 40,  # Doubled from 20 to 40
    'homing_turn_speed': 0.05,  # How fast homing missiles turn
    
    # New spawn system variables
    'spawn_frequency': 8000,  # Time between powerup spawns in milliseconds (8 seconds)
    'max_powerups': 3,  # Maximum powerups on screen at once
    'min_distance_from_tanks': 100,  # Minimum distance from players and enemies when spawning
}

class Particle:
    def __init__(self, x, y, color, speed, angle, life):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.angle = angle
        self.life = life
        self.max_life = life
        self.size = random.randint(2, 6)
    
    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.life -= 1
        self.speed *= 0.98  # Slow down over time
        return self.life <= 0
    
    def draw(self, screen):
        if self.life > 0:
            alpha = self.life / self.max_life
            size = int(self.size * alpha)
            if size > 0:
                pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)

class Effect:
    def __init__(self, x, y, effect_type):
        self.x = x
        self.y = y
        self.effect_type = effect_type  # 'explosion' or 'hit'
        self.start_time = pygame.time.get_ticks()
        self.particles = []
        
        if effect_type == 'explosion':
            self.duration = EFFECT_VARS['explosion_duration']
            # Create explosion particles
            for _ in range(EFFECT_VARS['particle_count'] * 2):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(1, EFFECT_VARS['particle_speed'] * 2)
                color = random.choice([RED, ORANGE, YELLOW])
                life = random.randint(20, 40)
                self.particles.append(Particle(x, y, color, speed, angle, life))
        else:  # hit effect
            self.duration = EFFECT_VARS['hit_effect_duration']
            # Create hit particles
            for _ in range(EFFECT_VARS['particle_count']):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(0.5, EFFECT_VARS['particle_speed'])
                color = random.choice([WHITE, YELLOW, ORANGE])
                life = random.randint(10, 20)
                self.particles.append(Particle(x, y, color, speed, angle, life))
    
    def update(self):
        # Update particles
        self.particles = [p for p in self.particles if not p.update()]
        
        # Check if effect is done
        elapsed = pygame.time.get_ticks() - self.start_time
        return elapsed >= self.duration and len(self.particles) == 0
    
    def draw(self, screen):
        elapsed = pygame.time.get_ticks() - self.start_time
        
        if self.effect_type == 'explosion':
            # Draw expanding explosion circle
            if elapsed < self.duration:
                progress = elapsed / self.duration
                size = int(EFFECT_VARS['explosion_max_size'] * progress)
                alpha = 1.0 - progress
                
                # Draw multiple circles for explosion effect
                for i, color in enumerate([YELLOW, ORANGE, RED]):
                    circle_size = max(1, int(size * (1 - i * 0.2)))
                    if circle_size > 0:
                        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), circle_size)
                        if i == 0:  # Outer ring
                            pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), circle_size, 2)
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)

class Obstacle:
    def __init__(self, x, y, width, height, obstacle_type=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.rect = pygame.Rect(x - width//2, y - height//2, width, height)

        # Define obstacle types: bunker, barracks, watchtower, satellite, supply_depot
        if obstacle_type is None:
            self.type = random.choice(['bunker', 'barracks', 'watchtower', 'satellite', 'supply_depot'])
        else:
            self.type = obstacle_type

    def draw(self, screen):
        if self.type == 'bunker':
            self._draw_bunker(screen)
        elif self.type == 'barracks':
            self._draw_barracks(screen)
        elif self.type == 'watchtower':
            self._draw_watchtower(screen)
        elif self.type == 'satellite':
            self._draw_satellite(screen)
        elif self.type == 'supply_depot':
            self._draw_supply_depot(screen)
        else:
            # Default fallback
            pygame.draw.rect(screen, OBSTACLE_VARS['rock_color'], self.rect)
            pygame.draw.rect(screen, BLACK, self.rect, 2)

    def _draw_bunker(self, screen):
        """Draw a military bunker with sandbags"""
        # Main bunker body (dark gray concrete)
        bunker_color = (80, 80, 80)
        pygame.draw.rect(screen, bunker_color, self.rect)

        # Darker top (roof)
        roof_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height // 4)
        pygame.draw.rect(screen, (60, 60, 60), roof_rect)

        # Firing slit (small black rectangle)
        slit_width = self.width // 3
        slit_height = 4
        slit_x = self.rect.x + (self.width - slit_width) // 2
        slit_y = self.rect.y + self.height // 2
        pygame.draw.rect(screen, BLACK, (slit_x, slit_y, slit_width, slit_height))

        # Sandbag details (small brown circles on the sides)
        sandbag_color = (101, 67, 33)
        bag_size = 6
        for i in range(3):
            # Left side sandbags
            pygame.draw.circle(screen, sandbag_color,
                             (self.rect.x + 5, self.rect.y + 10 + i * 12), bag_size)
            # Right side sandbags
            pygame.draw.circle(screen, sandbag_color,
                             (self.rect.x + self.width - 5, self.rect.y + 10 + i * 12), bag_size)

        # Border
        pygame.draw.rect(screen, BLACK, self.rect, 2)

    def _draw_barracks(self, screen):
        """Draw military barracks building"""
        # Main building (olive drab)
        building_color = (107, 98, 71)
        pygame.draw.rect(screen, building_color, self.rect)

        # Roof (darker)
        roof_rect = pygame.Rect(self.rect.x - 3, self.rect.y - 3, self.rect.width + 6, self.rect.height // 5)
        pygame.draw.rect(screen, (70, 65, 50), roof_rect)

        # Windows (small dark rectangles)
        window_color = (30, 30, 40)
        window_width = max(8, self.width // 8)
        window_height = max(8, self.height // 6)

        # Draw 2x2 grid of windows
        for row in range(2):
            for col in range(2):
                window_x = self.rect.x + (col + 1) * (self.width // 3) - window_width // 2
                window_y = self.rect.y + (row + 1) * (self.height // 3) - window_height // 2
                pygame.draw.rect(screen, window_color, (window_x, window_y, window_width, window_height))

        # Door (brown rectangle at bottom center)
        door_width = self.width // 4
        door_height = self.height // 3
        door_x = self.rect.x + (self.width - door_width) // 2
        door_y = self.rect.y + self.height - door_height - 2
        pygame.draw.rect(screen, (60, 40, 20), (door_x, door_y, door_width, door_height))

        # Border
        pygame.draw.rect(screen, BLACK, self.rect, 2)

    def _draw_watchtower(self, screen):
        """Draw a military watchtower"""
        # Base/legs (dark brown)
        base_color = (70, 50, 30)
        base_width = self.width // 2
        base_x = self.rect.x + (self.width - base_width) // 2
        base_rect = pygame.Rect(base_x, self.rect.y + self.height // 2, base_width, self.height // 2)
        pygame.draw.rect(screen, base_color, base_rect)

        # Tower platform (gray)
        platform_color = (90, 90, 90)
        platform_height = self.height // 2
        platform_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, platform_height)
        pygame.draw.rect(screen, platform_color, platform_rect)

        # Railing (white lines)
        pygame.draw.rect(screen, WHITE, (self.rect.x, self.rect.y + platform_height - 3, self.rect.width, 2))

        # Observation window
        window_size = min(self.width // 3, self.height // 4)
        window_x = self.rect.x + (self.width - window_size) // 2
        window_y = self.rect.y + platform_height // 3
        pygame.draw.rect(screen, BLACK, (window_x, window_y, window_size, window_size))

        # Support beams
        beam_width = 3
        pygame.draw.rect(screen, base_color, (base_x + 2, self.rect.y + platform_height, beam_width, self.height // 2))
        pygame.draw.rect(screen, base_color, (base_x + base_width - beam_width - 2, self.rect.y + platform_height, beam_width, self.height // 2))

        # Border
        pygame.draw.rect(screen, BLACK, self.rect, 2)

    def _draw_satellite(self, screen):
        """Draw a satellite dish installation"""
        # Base platform (gray)
        platform_color = (100, 100, 100)
        pygame.draw.rect(screen, platform_color, self.rect)

        # Control box (darker gray box at bottom)
        box_height = self.height // 3
        box_rect = pygame.Rect(self.rect.x + 5, self.rect.y + self.height - box_height - 5,
                              self.width // 3, box_height)
        pygame.draw.rect(screen, (60, 60, 60), box_rect)

        # Small indicator lights
        pygame.draw.circle(screen, GREEN, (box_rect.x + 8, box_rect.y + 8), 3)
        pygame.draw.circle(screen, RED, (box_rect.x + 16, box_rect.y + 8), 3)

        # Satellite dish (white/light gray circle)
        dish_radius = min(self.width, self.height) // 3
        dish_center_x = self.rect.x + self.width - dish_radius - 10
        dish_center_y = self.rect.y + dish_radius + 10

        # Dish outer rim
        pygame.draw.circle(screen, (200, 200, 200), (dish_center_x, dish_center_y), dish_radius)
        # Dish inner
        pygame.draw.circle(screen, (180, 180, 180), (dish_center_x, dish_center_y), dish_radius - 3)
        # Dish center
        pygame.draw.circle(screen, (140, 140, 140), (dish_center_x, dish_center_y), dish_radius // 3)

        # Support pole
        pole_width = 4
        pygame.draw.rect(screen, (80, 80, 80),
                        (dish_center_x - pole_width//2, dish_center_y + dish_radius//2,
                         pole_width, self.height // 3))

        # Border
        pygame.draw.rect(screen, BLACK, self.rect, 2)

    def _draw_supply_depot(self, screen):
        """Draw a military supply depot with crates"""
        # Main depot (tan/brown)
        depot_color = (120, 100, 70)
        pygame.draw.rect(screen, depot_color, self.rect)

        # Crates stacked (darker brown rectangles)
        crate_color = (80, 60, 40)
        crate_size = min(self.width, self.height) // 4

        # Draw grid of crates
        for row in range(2):
            for col in range(2):
                crate_x = self.rect.x + col * (self.width // 2) + 10
                crate_y = self.rect.y + row * (self.height // 2) + 10
                crate_rect = pygame.Rect(crate_x, crate_y, crate_size, crate_size)
                pygame.draw.rect(screen, crate_color, crate_rect)
                pygame.draw.rect(screen, BLACK, crate_rect, 1)

                # X marking on crate
                pygame.draw.line(screen, YELLOW,
                               (crate_x + 2, crate_y + 2),
                               (crate_x + crate_size - 2, crate_y + crate_size - 2), 2)
                pygame.draw.line(screen, YELLOW,
                               (crate_x + crate_size - 2, crate_y + 2),
                               (crate_x + 2, crate_y + crate_size - 2), 2)

        # Warning stripes (yellow and black)
        stripe_width = 5
        for i in range(0, self.width, stripe_width * 2):
            pygame.draw.rect(screen, YELLOW, (self.rect.x + i, self.rect.y, stripe_width, 3))

        # Border
        pygame.draw.rect(screen, BLACK, self.rect, 2)

    def get_rect(self):
        return self.rect

class Missile:
    def __init__(self, x, y, angle, speed, max_distance, is_player=True, player_owner=None):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.max_distance = max_distance
        self.distance_traveled = 0
        self.is_player = is_player
        self.radius = 5
        self.player_owner = player_owner  # Track which player fired this missile
        self.owner_tank = player_owner  # For tracking enemy tank owners too
        
    def update(self):
        # Move missile
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.distance_traveled += self.speed
        
        # Check if missile should be removed
        return self.distance_traveled >= self.max_distance or \
               self.x < 0 or self.x > SCREEN_WIDTH or \
               self.y < 0 or self.y > SCREEN_HEIGHT
    
    def draw(self, screen):
        color = BLUE if self.is_player else RED
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
    
    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, 
                          self.radius * 2, self.radius * 2)

class HomingMissile(Missile):
    def __init__(self, x, y, angle, speed, max_distance, target_enemies, player_owner=None):
        super().__init__(x, y, angle, speed, max_distance, True, player_owner)
        self.target_enemies = target_enemies
        self.target = None
        
    def update(self):
        # Find nearest enemy if no target or target is dead
        if not self.target or self.target not in self.target_enemies:
            if self.target_enemies:
                self.target = min(self.target_enemies, key=lambda e: 
                    math.sqrt((e.x - self.x)**2 + (e.y - self.y)**2))
        
        # Home in on target
        if self.target:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            target_angle = math.atan2(dy, dx)
            
            # Turn towards target
            angle_diff = target_angle - self.angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # Apply turning
            if abs(angle_diff) > POWERUP_VARS['homing_turn_speed']:
                if angle_diff > 0:
                    self.angle += POWERUP_VARS['homing_turn_speed']
                else:
                    self.angle -= POWERUP_VARS['homing_turn_speed']
            else:
                self.angle = target_angle
        
        # Regular missile update
        return super().update()
    
    def draw(self, screen):
        # Draw as yellow missile with trail
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius + 1)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius)

class Powerup:
    def __init__(self, x, y, powerup_type):
        self.x = x
        self.y = y
        self.powerup_type = powerup_type
        self.size = 30
        self.pulse_timer = 0
        
        # Define powerup colors
        self.colors = {
            'shield': BLUE,
            'speed': GREEN,
            'rapid_fire': RED,
            'shotgun': ORANGE,
            'homing': YELLOW
        }
    
    def update(self):
        self.pulse_timer += 0.1
    
    def draw(self, screen):
        # Pulsing effect
        pulse_size = self.size + int(math.sin(self.pulse_timer) * 5)
        color = self.colors.get(self.powerup_type, WHITE)
        
        # Draw powerup
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), pulse_size)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), pulse_size, 3)
        
        # Draw symbol
        font = pygame.font.Font(None, 24)
        symbol = self.powerup_type[0].upper()
        text = font.render(symbol, True, BLACK)
        text_rect = text.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(text, text_rect)
    
    def get_rect(self):
        return pygame.Rect(self.x - self.size, self.y - self.size, self.size * 2, self.size * 2)

class TrackTrail:
    def __init__(self, tank):
        self.tank = tank
        self.trail_points = []  # List of (x, y, angle, alpha) tuples
        self.last_position = (tank.x, tank.y)
        self.distance_since_last_point = 0
    
    def update(self):
        current_pos = (self.tank.x, self.tank.y)
        
        # Calculate distance moved since last update
        dx = current_pos[0] - self.last_position[0]
        dy = current_pos[1] - self.last_position[1]
        distance_moved = math.sqrt(dx*dx + dy*dy)
        
        self.distance_since_last_point += distance_moved
        
        # Add new trail point if tank has moved enough
        if self.distance_since_last_point >= EFFECT_VARS['track_spacing']:
            # Add new point at tank's current position
            self.trail_points.append((
                self.tank.x,
                self.tank.y,
                self.tank.angle,
                1.0  # Full alpha
            ))
            self.distance_since_last_point = 0
        
        # Remove old trail points that exceed max length
        total_distance = 0
        valid_points = []
        
        # Go through points in reverse order (newest first)
        for i in range(len(self.trail_points) - 1, -1, -1):
            if i < len(self.trail_points) - 1:
                # Calculate distance to next point
                curr_point = self.trail_points[i]
                next_point = self.trail_points[i + 1]
                dx = next_point[0] - curr_point[0]
                dy = next_point[1] - curr_point[1]
                total_distance += math.sqrt(dx*dx + dy*dy)
            
            if total_distance <= EFFECT_VARS['track_trail_length']:
                # Calculate fade based on distance
                fade_factor = 1.0 - (total_distance / EFFECT_VARS['track_trail_length'])
                faded_point = (
                    self.trail_points[i][0],
                    self.trail_points[i][1],
                    self.trail_points[i][2],
                    fade_factor
                )
                valid_points.insert(0, faded_point)
            else:
                break
        
        self.trail_points = valid_points
        self.last_position = current_pos
    
    def draw(self, screen):
        # Draw track marks for each trail point
        for i, (x, y, angle, alpha) in enumerate(self.trail_points):
            if alpha <= 0:
                continue
            
            # Calculate track color based on fade
            if self.tank.is_player:
                base_color = (120, 100, 80)  # Darker brown for player tracks
            else:
                base_color = (100, 80, 60)  # Even darker brown for enemy tracks
            faded_color = (
                int(SAND_COLOR[0] + (base_color[0] - SAND_COLOR[0]) * alpha),
                int(SAND_COLOR[1] + (base_color[1] - SAND_COLOR[1]) * alpha),
                int(SAND_COLOR[2] + (base_color[2] - SAND_COLOR[2]) * alpha)
            )
            
            # Draw two parallel track lines (left and right tracks)
            track_offset = EFFECT_VARS['track_width'] // 2
            
            # Calculate perpendicular offset for track width
            perp_angle = angle + math.pi / 2
            
            # Left track
            left_x = x + math.cos(perp_angle) * track_offset
            left_y = y + math.sin(perp_angle) * track_offset
            
            # Right track
            right_x = x - math.cos(perp_angle) * track_offset
            right_y = y - math.sin(perp_angle) * track_offset
            
            # Draw realistic tank track patterns
            self._draw_tank_track_pattern(screen, left_x, left_y, angle, faded_color, alpha)
            self._draw_tank_track_pattern(screen, right_x, right_y, angle, faded_color, alpha)
    
    def _draw_tank_track_pattern(self, screen, x, y, angle, color, alpha):
        # Draw individual track pads that look like real tank treads
        track_pad_length = 10
        track_pad_width = 6
        
        # Main track pad (rectangular)
        self._draw_rotated_rect(screen, x, y, angle, track_pad_length, track_pad_width, color)
        
        # Add track cleats (the grippy parts) - small perpendicular lines
        if alpha > 0.3:  # Only draw details on more visible tracks
            cleat_length = track_pad_width + 2
            cleat_thickness = 1
            
            # Draw 2-3 cleats across the track pad
            for cleat_offset in [-3, 0, 3]:
                cleat_x = x + math.cos(angle) * cleat_offset
                cleat_y = y + math.sin(angle) * cleat_offset
                
                # Cleats are perpendicular to the track direction
                cleat_angle = angle + math.pi / 2
                self._draw_rotated_rect(screen, cleat_x, cleat_y, cleat_angle, cleat_length, cleat_thickness, color)
        
        # Add track pad bolts/rivets for extra detail
        if alpha > 0.5:  # Only on most visible tracks
            rivet_color = (
                max(0, color[0] - 20),
                max(0, color[1] - 20),
                max(0, color[2] - 20)
            )
            
            # Two rivets on each track pad
            for rivet_offset in [-2, 2]:
                rivet_x = x + math.cos(angle + math.pi/2) * rivet_offset
                rivet_y = y + math.sin(angle + math.pi/2) * rivet_offset
                pygame.draw.circle(screen, rivet_color, (int(rivet_x), int(rivet_y)), 1)
    
    def _draw_rotated_rect(self, screen, x, y, angle, length, width, color):
        # Calculate the four corners of the rectangle
        half_length = length / 2
        half_width = width / 2
        
        # Local corners (before rotation)
        corners = [
            (-half_length, -half_width),
            (half_length, -half_width),
            (half_length, half_width),
            (-half_length, half_width)
        ]
        
        # Rotate and translate corners
        rotated_corners = []
        for corner_x, corner_y in corners:
            rotated_x = corner_x * math.cos(angle) - corner_y * math.sin(angle)
            rotated_y = corner_x * math.sin(angle) + corner_y * math.cos(angle)
            rotated_corners.append((x + rotated_x, y + rotated_y))
        
        # Draw the rectangle
        if len(rotated_corners) >= 3:
            pygame.draw.polygon(screen, color, rotated_corners)

class Tank:
    def __init__(self, x, y, is_player=True, player_num=1):
        self.x = x
        self.y = y
        self.angle = 0
        self.is_player = is_player
        self.player_num = player_num
        
        # Use appropriate variables based on tank type
        vars_dict = PLAYER_VARS if is_player else ENEMY_VARS
        self.base_movement_speed = vars_dict['movement_speed']
        self.base_shot_speed = vars_dict['shot_speed']
        self.base_fire_rate = vars_dict['fire_rate']
        self.base_powerup_duration = vars_dict['powerup_duration']
        
        # Current stats (modified by leveling)
        self.movement_speed = self.base_movement_speed
        self.shot_speed = self.base_shot_speed
        self.fire_rate = self.base_fire_rate
        self.powerup_duration = self.base_powerup_duration
        
        self.base_shot_distance = vars_dict['shot_distance']
        self.shot_distance = self.base_shot_distance
        
        self.base_max_health = vars_dict['max_health']
        self.max_health = self.base_max_health
        self.tank_size = vars_dict['tank_size']
        self.barrel_length = vars_dict['barrel_length']
        self.barrel_width = vars_dict['barrel_width']
        
        self.health = self.max_health
        self.last_shot = 0
        self.target = None  # For enemy AI

        # Enemy upgrade tracking (only for enemies)
        if not is_player:
            self.base_damage = ENEMY_VARS['base_damage']
            self.damage = self.base_damage
            self.upgrade_multipliers = {
                'movement_speed': 1.0,
                'shot_speed': 1.0,
                'shot_distance': 1.0,
                'health': 1.0,
                'damage': 1.0
            }
        
        # Leveling system (only for players)
        if is_player:
            self.level = 1
            self.xp = 0
            self.xp_to_next_level = LEVELING_VARS['base_level_xp']
            
            # Track stat upgrades (how many times each stat has been upgraded)
            self.movement_upgrades = 0
            self.shot_speed_upgrades = 0
            self.shot_distance_upgrades = 0
            self.fire_rate_upgrades = 0
            self.powerup_upgrades = 0
            self.health_upgrades = 0
            
            self.max_upgrades = LEVELING_VARS['max_stat_increase'] // LEVELING_VARS['stat_increase_percent']
            
            # Powerup system
            self.active_powerups = {}
            self.powerup_shots_remaining = {}
            self.shield_active = False
            self.speed_boost_active = False

        # Tank trail system (only for players)
        self.trail = TrackTrail(self)
               
    def move_forward(self):
        speed = self.movement_speed
        if self.is_player and self.speed_boost_active:
            speed *= POWERUP_VARS['speed_boost_multiplier']
        
        self.x += math.cos(self.angle) * speed
        self.y += math.sin(self.angle) * speed
        self._keep_in_bounds()

        # Update trail for players
        if self.is_player and self.trail:
            self.trail.update()
    
    def move_backward(self):
        speed = self.movement_speed
        if self.is_player and self.speed_boost_active:
            speed *= POWERUP_VARS['speed_boost_multiplier']
        
        self.x -= math.cos(self.angle) * speed
        self.y -= math.sin(self.angle) * speed
        self._keep_in_bounds()

        # Update trail for players
        if self.is_player and self.trail:
            self.trail.update()
    
    def turn_left(self):
        self.angle -= 0.05  # Reduced from 0.1 to 0.05 (half speed)
    
    def turn_right(self):
        self.angle += 0.05  # Reduced from 0.1 to 0.05 (half speed)
    
    def _keep_in_bounds(self):
        self.x = max(self.tank_size[0]//2, min(SCREEN_WIDTH - self.tank_size[0]//2, self.x))
        self.y = max(self.tank_size[1]//2, min(SCREEN_HEIGHT - self.tank_size[1]//2, self.y))
    
    def check_obstacle_collision(self, obstacles, new_x=None, new_y=None):
        # Check if moving to new position would collide with obstacles
        test_x = new_x if new_x is not None else self.x
        test_y = new_y if new_y is not None else self.y
        test_rect = pygame.Rect(test_x - self.tank_size[0]//2, test_y - self.tank_size[1]//2,
                               self.tank_size[0], self.tank_size[1])
        
        for obstacle in obstacles:
            if test_rect.colliderect(obstacle.get_rect()):
                return True
        return False
    
    def can_shoot(self):
        # Rapid fire powerup reduces cooldown
        fire_rate = self.fire_rate
        if self.is_player and 'rapid_fire' in self.powerup_shots_remaining:
            fire_rate = self.fire_rate // 4  # 4x faster
        
        return pygame.time.get_ticks() - self.last_shot > fire_rate
    
    def shoot(self, enemies=None):
        if self.can_shoot():
            self.last_shot = pygame.time.get_ticks()
            missiles = []
            
            # Calculate missile start position at end of barrel
            barrel_end_x = self.x + math.cos(self.angle) * self.barrel_length
            barrel_end_y = self.y + math.sin(self.angle) * self.barrel_length
            
            if self.is_player:
                # Check for special shot types
                if 'shotgun' in self.powerup_shots_remaining and self.powerup_shots_remaining['shotgun'] > 0:
                    # Shotgun burst
                    self.powerup_shots_remaining['shotgun'] -= 1
                    for i in range(POWERUP_VARS['shotgun_pellets']):
                        spread = (i - POWERUP_VARS['shotgun_pellets']//2) * (POWERUP_VARS['shotgun_spread'] / POWERUP_VARS['shotgun_pellets'])
                        pellet_angle = self.angle + spread
                        missile = Missile(barrel_end_x, barrel_end_y, pellet_angle, 
                                        self.shot_speed, self.shot_distance, True, self)
                        missiles.append(missile)
                
                elif 'homing' in self.powerup_shots_remaining and self.powerup_shots_remaining['homing'] > 0:
                    # Homing missile
                    self.powerup_shots_remaining['homing'] -= 1
                    missile = HomingMissile(barrel_end_x, barrel_end_y, self.angle, 
                                          self.shot_speed, self.shot_distance, enemies or [], self)
                    missiles.append(missile)
                
                else:
                    # Regular shot
                    missile = Missile(barrel_end_x, barrel_end_y, self.angle, 
                                    self.shot_speed, self.shot_distance, True, self)
                    missiles.append(missile)
                    
                    # Consume rapid fire shot if active
                    if 'rapid_fire' in self.powerup_shots_remaining:
                        self.powerup_shots_remaining['rapid_fire'] -= 1
                        if self.powerup_shots_remaining['rapid_fire'] <= 0:
                            del self.powerup_shots_remaining['rapid_fire']
                
                # Clean up empty powerups
                self.powerup_shots_remaining = {k: v for k, v in self.powerup_shots_remaining.items() if v > 0}
            else:
                # Enemy regular shot
                missile = Missile(barrel_end_x, barrel_end_y, self.angle, 
                                self.shot_speed, self.shot_distance, False, None)
                missile.owner_tank = self  # Track which enemy fired this
                missiles.append(missile)
            
            return missiles
        return []    
    def take_damage(self, damage=10):
        # Shield blocks damage
        if self.is_player and self.shield_active:
            return False
        
        self.health -= damage
        return self.health <= 0

    def draw(self, screen):
            # Choose color based on tank type
            if self.is_player:
                color = DARK_TAN
            else:
                color = BLACK
        
            # Calculate tank corners
            half_width = self.tank_size[0] // 2
            half_height = self.tank_size[1] // 2
        
            # Tank body corners (before rotation)
            corners = [
                (-half_width, -half_height),
                (half_width, -half_height),
                (half_width, half_height),
                (-half_width, half_height)
            ]
        
            # Rotate and translate corners
            rotated_corners = []
            for corner_x, corner_y in corners:
                rotated_x = corner_x * math.cos(self.angle) - corner_y * math.sin(self.angle)
                rotated_y = corner_x * math.sin(self.angle) + corner_y * math.cos(self.angle)
                rotated_corners.append((self.x + rotated_x, self.y + rotated_y))
        
            # Draw tank body
            pygame.draw.polygon(screen, color, rotated_corners)
            pygame.draw.polygon(screen, WHITE, rotated_corners, 2)
        
            # Draw shield effect if active
            if self.is_player and self.shield_active:
                shield_radius = max(self.tank_size) + 10
                pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), shield_radius, 3)
                # Pulsing effect
                pulse = int(math.sin(pygame.time.get_ticks() * 0.01) * 5)
                pygame.draw.circle(screen, (100, 150, 255), (int(self.x), int(self.y)), shield_radius + pulse, 1)
        
            # Draw barrel
            barrel_end_x = self.x + math.cos(self.angle) * self.barrel_length
            barrel_end_y = self.y + math.sin(self.angle) * self.barrel_length
        
            # Calculate barrel rectangle
            barrel_corners = []
            barrel_half_width = self.barrel_width // 2
        
            # Barrel corners relative to barrel center line
            barrel_local_corners = [
                (0, -barrel_half_width),
                (self.barrel_length, -barrel_half_width),
                (self.barrel_length, barrel_half_width),
                (0, barrel_half_width)
            ]
        
            for corner_x, corner_y in barrel_local_corners:
                rotated_x = corner_x * math.cos(self.angle) - corner_y * math.sin(self.angle)
                rotated_y = corner_x * math.sin(self.angle) + corner_y * math.cos(self.angle)
                barrel_corners.append((self.x + rotated_x, self.y + rotated_y))
        
            pygame.draw.polygon(screen, color, barrel_corners)
            pygame.draw.polygon(screen, WHITE, barrel_corners, 1)

            # Draw health bar
            self.draw_health_bar(screen)

            # Draw ammo indicator for players
            if self.is_player:
                self.draw_ammo_indicator(screen)
    
    def draw_health_bar(self, screen):
        bar_x = self.x - GAME_VARS['health_bar_width'] // 2
        bar_y = self.y - self.tank_size[1] - 15

        # Background
        pygame.draw.rect(screen, RED, (bar_x, bar_y, GAME_VARS['health_bar_width'], GAME_VARS['health_bar_height']))

        # Health
        health_ratio = self.health / self.max_health
        health_width = int(GAME_VARS['health_bar_width'] * health_ratio)
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, health_width, GAME_VARS['health_bar_height']))

        # Border
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, GAME_VARS['health_bar_width'], GAME_VARS['health_bar_height']), 1)

    def draw_ammo_indicator(self, screen):
        """Draw ammo count indicator below the player tank with militaristic styling"""
        if not self.is_player:
            return

        # Create font for ammo display
        ammo_font = pygame.font.Font(None, 24)

        # Get total special ammo count
        total_special_ammo = sum(self.powerup_shots_remaining.values())

        # Position below the tank
        indicator_y = self.y + self.tank_size[1] + 15

        if total_special_ammo > 0:
            # Draw background box with military styling
            box_width = 80
            box_height = 20
            box_x = self.x - box_width // 2
            box_y = indicator_y

            # Dark background with yellow/black warning stripes
            pygame.draw.rect(screen, (40, 40, 40), (box_x, box_y, box_width, box_height))

            # Warning stripes on the sides
            stripe_width = 3
            for i in range(0, box_height, 6):
                pygame.draw.rect(screen, YELLOW if (i // 6) % 2 == 0 else BLACK,
                               (box_x, box_y + i, stripe_width, min(6, box_height - i)))
                pygame.draw.rect(screen, YELLOW if (i // 6) % 2 == 0 else BLACK,
                               (box_x + box_width - stripe_width, box_y + i, stripe_width, min(6, box_height - i)))

            # Determine color based on powerup type
            active_powerup = None
            powerup_colors = {
                'rapid_fire': RED,
                'shotgun': ORANGE,
                'homing': YELLOW
            }

            # Find which powerup is active
            for powerup_type, ammo_count in self.powerup_shots_remaining.items():
                if ammo_count > 0:
                    active_powerup = powerup_type
                    break

            # Choose text color
            if active_powerup and active_powerup in powerup_colors:
                text_color = powerup_colors[active_powerup]
            else:
                text_color = ORANGE

            # Draw ammo count text
            ammo_text = ammo_font.render(f"AMMO: {total_special_ammo}", True, text_color)
            text_rect = ammo_text.get_rect(center=(self.x, indicator_y + box_height // 2))
            screen.blit(ammo_text, text_rect)

            # Border
            pygame.draw.rect(screen, text_color, (box_x, box_y, box_width, box_height), 2)
        else:
            # Show "STANDARD" when no special ammo
            box_width = 90
            box_height = 20
            box_x = self.x - box_width // 2
            box_y = indicator_y

            # Dark gray background
            pygame.draw.rect(screen, (50, 50, 50), (box_x, box_y, box_width, box_height))

            # Standard ammo text in white
            ammo_text = ammo_font.render("STANDARD", True, WHITE)
            text_rect = ammo_text.get_rect(center=(self.x, indicator_y + box_height // 2))
            screen.blit(ammo_text, text_rect)

            # White border
            pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height), 1)

    def get_rect(self):
        return pygame.Rect(self.x - self.tank_size[0]//2, self.y - self.tank_size[1]//2,
                          self.tank_size[0], self.tank_size[1])
    
    def gain_xp(self, amount):
        """Gain XP and check for level up (only for players)"""
        if not self.is_player:
            return False
            
        self.xp += amount
        if self.xp >= self.xp_to_next_level:
            self.level_up()
            return True
        return False
    
    def level_up(self):
        """Level up the player"""
        self.level += 1
        self.xp -= self.xp_to_next_level
        
        # Calculate next level XP requirement
        increase_factor = 1 + (LEVELING_VARS['xp_increase_percent'] / 100)
        self.xp_to_next_level = int(LEVELING_VARS['base_level_xp'] * (increase_factor ** (self.level - 1)))
    
    def upgrade_stat(self, stat_name):
        """Upgrade a specific stat"""
        if not self.is_player:
            return
            
        increase_percent = LEVELING_VARS['stat_increase_percent']
        
        if stat_name == "movement_speed" and self.movement_upgrades < self.max_upgrades:
            self.movement_upgrades += 1
            self.movement_speed = self.base_movement_speed * (1 + (self.movement_upgrades * increase_percent / 100))
        elif stat_name == "shot_speed" and self.shot_speed_upgrades < self.max_upgrades:
            self.shot_speed_upgrades += 1
            self.shot_speed = self.base_shot_speed * (1 + (self.shot_speed_upgrades * increase_percent / 100))
        elif stat_name == "shot_distance" and self.shot_distance_upgrades < self.max_upgrades:
            self.shot_distance_upgrades += 1
            self.shot_distance = self.base_shot_distance * (1 + (self.shot_distance_upgrades * increase_percent / 100))
        elif stat_name == "fire_rate" and self.fire_rate_upgrades < self.max_upgrades:
            self.fire_rate_upgrades += 1
            # Fire rate improvement means LOWER cooldown
            self.fire_rate = int(self.base_fire_rate / (1 + (self.fire_rate_upgrades * increase_percent / 100)))
        elif stat_name == "powerup_duration" and self.powerup_upgrades < self.max_upgrades:
            self.powerup_upgrades += 1
            self.powerup_duration = int(self.base_powerup_duration * (1 + (self.powerup_upgrades * increase_percent / 100)))
        elif stat_name == "health" and self.health_upgrades < self.max_upgrades:
            self.health_upgrades += 1
            old_max = self.max_health
            self.max_health = int(self.base_max_health * (1 + (self.health_upgrades * increase_percent / 100)))
            # Heal proportionally to the increase
            self.health += (self.max_health - old_max)
    
    def can_upgrade_stat(self, stat_name):
        """Check if a stat can be upgraded"""
        if not self.is_player:
            return False
            
        if stat_name == "movement_speed":
            return self.movement_upgrades < self.max_upgrades
        elif stat_name == "shot_speed":
            return self.shot_speed_upgrades < self.max_upgrades
        elif stat_name == "shot_distance":
            return self.shot_distance_upgrades < self.max_upgrades
        elif stat_name == "fire_rate":
            return self.fire_rate_upgrades < self.max_upgrades
        elif stat_name == "powerup_duration":
            return self.powerup_upgrades < self.max_upgrades
        elif stat_name == "health":
            return self.health_upgrades < self.max_upgrades
        return False
    
    def get_stat_info(self, stat_name):
        """Get detailed info about a stat's current level"""
        if not self.is_player:
            return None
            
        if stat_name == "movement_speed":
            upgrades = self.movement_upgrades
        elif stat_name == "shot_speed":
            upgrades = self.shot_speed_upgrades
        elif stat_name == "shot_distance":
            upgrades = self.shot_distance_upgrades
        elif stat_name == "fire_rate":
            upgrades = self.fire_rate_upgrades
        elif stat_name == "powerup_duration":
            upgrades = self.powerup_upgrades
        elif stat_name == "health":
            upgrades = self.health_upgrades
        else:
            return None
            
        current_percent = upgrades * LEVELING_VARS['stat_increase_percent']
        return {
            'upgrades': upgrades,
            'max_upgrades': self.max_upgrades,
            'current_percent': current_percent
        }

    def activate_powerup(self, powerup_type):
            """Activate a powerup"""
            if not self.is_player:
                return
        
            current_time = pygame.time.get_ticks()
            duration = int(POWERUP_VARS['shield_base_duration'] * (1 + (self.powerup_upgrades * LEVELING_VARS['stat_increase_percent'] / 100)))
        
            if powerup_type == 'shield':
                self.shield_active = True
                self.active_powerups['shield'] = current_time + duration
        
            elif powerup_type == 'speed':
                self.speed_boost_active = True
                self.active_powerups['speed'] = current_time + duration
        
            elif powerup_type == 'rapid_fire':
                # Replace any existing weapon powerup
                self.powerup_shots_remaining.clear()
                shots = int(POWERUP_VARS['rapid_fire_shots'] * (1 + (self.powerup_upgrades * LEVELING_VARS['stat_increase_percent'] / 100)))
                self.powerup_shots_remaining['rapid_fire'] = shots
        
            elif powerup_type == 'shotgun':
                # Replace any existing weapon powerup
                self.powerup_shots_remaining.clear()
                shots = int(POWERUP_VARS['shotgun_shots'] * (1 + (self.powerup_upgrades * LEVELING_VARS['stat_increase_percent'] / 100)))
                self.powerup_shots_remaining['shotgun'] = shots
        
            elif powerup_type == 'homing':
                # Replace any existing weapon powerup
                self.powerup_shots_remaining.clear()
                shots = int(POWERUP_VARS['homing_shots'] * (1 + (self.powerup_upgrades * LEVELING_VARS['stat_increase_percent'] / 100)))
                self.powerup_shots_remaining['homing'] = shots
    
    def update_powerups(self):
        """Update powerup timers"""
        if not self.is_player:
            return
        
        current_time = pygame.time.get_ticks()
        
        # Check timed powerups
        for powerup_type in list(self.active_powerups.keys()):
            if current_time >= self.active_powerups[powerup_type]:
                del self.active_powerups[powerup_type]
                
                if powerup_type == 'shield':
                    self.shield_active = False
                elif powerup_type == 'speed':
                    self.speed_boost_active = False
    
    def heal_to_full(self):
        """Restore full health"""
        self.health = self.max_health
    
    def update_ai(self, players, obstacles):
        if not self.is_player and players:
            # Initialize stuck detection if not present
            if not hasattr(self, 'last_position'):
                self.last_position = (self.x, self.y)
                self.stuck_counter = 0
                self.unstuck_angle = None

            # Filter out dead players
            alive_players = [p for p in players if not getattr(p, 'is_dead', False)]

            if not alive_players:
                return None

            # Check if stuck (hasn't moved much)
            distance_moved = math.sqrt((self.x - self.last_position[0])**2 + (self.y - self.last_position[1])**2)
            if distance_moved < 0.5:  # Barely moved
                self.stuck_counter += 1
            else:
                self.stuck_counter = 0
                self.unstuck_angle = None

            # Update last position
            self.last_position = (self.x, self.y)

            # Find nearest alive player
            nearest_player = min(alive_players, key=lambda p:
                math.sqrt((p.x - self.x)**2 + (p.y - self.y)**2))

            # Calculate direct angle to player
            dx = nearest_player.x - self.x
            dy = nearest_player.y - self.y
            direct_angle = math.atan2(dy, dx)
            distance_to_player = math.sqrt(dx*dx + dy*dy)

            # If stuck for too long, execute unstuck maneuver
            if self.stuck_counter > 30:
                if self.unstuck_angle is None:
                    # Choose a random direction to escape
                    self.unstuck_angle = self.angle + random.choice([math.pi/2, -math.pi/2, math.pi])

                # Turn toward unstuck angle
                angle_diff = self.unstuck_angle - self.angle
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi

                if abs(angle_diff) > 0.1:
                    if angle_diff > 0:
                        self.turn_right()
                    else:
                        self.turn_left()

                # Try to move in unstuck direction
                new_x = self.x + math.cos(self.angle) * self.movement_speed
                new_y = self.y + math.sin(self.angle) * self.movement_speed
                if not self.check_obstacle_collision(obstacles, new_x, new_y):
                    self.x = new_x
                    self.y = new_y
                    self._keep_in_bounds()
                    if self.trail:
                        self.trail.update()

                # Reset stuck counter after trying to escape
                if self.stuck_counter > 60:
                    self.stuck_counter = 0
                    self.unstuck_angle = None

                return self.shoot()

            # Check if direct path to player is blocked
            path_blocked = self._is_path_blocked(self.x, self.y, nearest_player.x, nearest_player.y, obstacles)

            if not path_blocked:
                # Direct path is clear - turn toward player
                angle_diff = direct_angle - self.angle
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi

                if abs(angle_diff) > 0.1:
                    if angle_diff > 0:
                        self.turn_right()
                    else:
                        self.turn_left()
            else:
                # Path is blocked - use improved wall following to navigate around obstacles
                self._follow_wall_to_target(direct_angle, obstacles, nearest_player)

            # Try to move forward
            new_x = self.x + math.cos(self.angle) * self.movement_speed
            new_y = self.y + math.sin(self.angle) * self.movement_speed

            if not self.check_obstacle_collision(obstacles, new_x, new_y):
                # Maintain appropriate combat distance
                if distance_to_player > 200:  # Move closer
                    self.x = new_x
                    self.y = new_y
                    self._keep_in_bounds()
                    # Update trail for enemy movement
                    if self.trail:
                        self.trail.update()
                elif distance_to_player < 80:  # Back up
                    back_x = self.x - math.cos(self.angle) * self.movement_speed
                    back_y = self.y - math.sin(self.angle) * self.movement_speed
                    if not self.check_obstacle_collision(obstacles, back_x, back_y):
                        self.x = back_x
                        self.y = back_y
                        self._keep_in_bounds()
                        # Update trail for enemy movement
                        if self.trail:
                            self.trail.update()
                else:  # Good distance, keep moving
                    self.x = new_x
                    self.y = new_y
                    self._keep_in_bounds()
                    # Update trail for enemy movement
                    if self.trail:
                        self.trail.update()

            return self.shoot()
        return None
    
    def _is_path_blocked(self, start_x, start_y, end_x, end_y, obstacles):
        """Check if there's a clear line of sight between two points"""
        # Sample points along the line
        num_samples = 20
        for i in range(num_samples):
            t = i / (num_samples - 1)
            sample_x = start_x + (end_x - start_x) * t
            sample_y = start_y + (end_y - start_y) * t
            
            # Check if this point collides with any obstacle
            test_rect = pygame.Rect(sample_x - self.tank_size[0]//2, sample_y - self.tank_size[1]//2,
                                   self.tank_size[0], self.tank_size[1])
            for obstacle in obstacles:
                if test_rect.colliderect(obstacle.get_rect()):
                    return True
        return False
    
    def _follow_wall_to_target(self, target_angle, obstacles, target_player):
        """Improved wall following behavior to navigate around obstacles"""
        # Use multiple look-ahead distances for better obstacle detection
        look_ahead_distances = [60, 80, 100]
        collision_detected = False

        for distance in look_ahead_distances:
            forward_x = self.x + math.cos(self.angle) * distance
            forward_y = self.y + math.sin(self.angle) * distance
            if self.check_obstacle_collision(obstacles, forward_x, forward_y):
                collision_detected = True
                break

        if collision_detected:
            # We're facing an obstacle, find the best escape route
            # Test multiple angles to find the clearest path
            test_angles = [
                self.angle + math.pi/4,      # 45 degrees right
                self.angle - math.pi/4,      # 45 degrees left
                self.angle + math.pi/2,      # 90 degrees right
                self.angle - math.pi/2,      # 90 degrees left
                self.angle + 3*math.pi/4,    # 135 degrees right
                self.angle - 3*math.pi/4     # 135 degrees left
            ]

            best_angle = None
            best_score = -float('inf')

            for test_angle in test_angles:
                # Check if this angle is clear
                test_x = self.x + math.cos(test_angle) * 60
                test_y = self.y + math.sin(test_angle) * 60

                if not self.check_obstacle_collision(obstacles, test_x, test_y):
                    # Calculate score based on:
                    # 1. How close it gets us to the target
                    # 2. How clear the path is
                    angle_to_target = math.atan2(target_player.y - self.y, target_player.x - self.x)
                    angle_diff = abs(test_angle - angle_to_target)
                    while angle_diff > math.pi:
                        angle_diff -= 2 * math.pi
                    while angle_diff < -math.pi:
                        angle_diff += 2 * math.pi

                    # Prefer angles closer to target direction
                    score = -abs(angle_diff)

                    if score > best_score:
                        best_score = score
                        best_angle = test_angle

            if best_angle is not None:
                # Turn toward the best angle
                angle_diff = best_angle - self.angle
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi

                if abs(angle_diff) > 0.1:
                    if angle_diff > 0:
                        self.turn_right()
                    else:
                        self.turn_left()
            else:
                # No clear path found, turn around
                self.turn_right()
        else:
            # Path ahead is clear, gradually turn toward target
            angle_diff = target_angle - self.angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi

            # Only turn toward target if it won't immediately cause collision
            turn_amount = 0.15 if abs(angle_diff) > 0.15 else abs(angle_diff)
            test_angle = self.angle + (turn_amount if angle_diff > 0 else -turn_amount)
            test_x = self.x + math.cos(test_angle) * 50
            test_y = self.y + math.sin(test_angle) * 50

            if not self.check_obstacle_collision(obstacles, test_x, test_y):
                if abs(angle_diff) > 0.1:
                    if angle_diff > 0:
                        self.turn_right()
                    else:
                        self.turn_left()

class NameInputScreen:
    def __init__(self, screen, score, wave, level, is_coop=False):
        self.screen = screen
        self.score = score
        self.wave = wave
        self.level = level
        self.is_coop = is_coop
        self.font_large = pygame.font.Font(None, 96)
        self.font_medium = pygame.font.Font(None, 64)
        self.font_small = pygame.font.Font(None, 48)
        
        # Name input system - exactly like Space Invaders
        self.name = ["A", "A", "A"]
        self.current_position = 0
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
        self.current_letter_index = [0, 0, 0]  # Track current letter index for each position
        self.input_mode = "controller"
        self.keyboard_name = ""
        self.finished = False
        self.ok_selected = False
        
        # Detect controllers
        self.controllers = []
        for i in range(pygame.joystick.get_count()):
            controller = pygame.joystick.Joystick(i)
            controller.init()
            self.controllers.append(controller)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                self.input_mode = "keyboard"
                if event.key == pygame.K_RETURN:
                    if self.keyboard_name.strip():
                        return self.keyboard_name.strip()[:10]  # Allow longer names with keyboard
                    return "PLAYER"
                elif event.key == pygame.K_BACKSPACE:
                    self.keyboard_name = self.keyboard_name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    return "PLAYER"
                elif len(self.keyboard_name) < 10 and event.unicode.isprintable():
                    self.keyboard_name += event.unicode.upper()
            
            elif event.type == pygame.JOYBUTTONDOWN:
                self.input_mode = "controller"
                if event.button == 0:  # A button
                    if self.ok_selected:
                        return "".join(self.name)
                    else:
                        # Move to next position or to OK
                        if self.current_position < 2:
                            self.current_position += 1
                        else:
                            self.ok_selected = True
                elif event.button == 1:  # B button
                    if self.ok_selected:
                        self.ok_selected = False
                        self.current_position = 2
                    elif self.current_position > 0:
                        self.current_position -= 1
            
            elif event.type == pygame.JOYHATMOTION:
                self.input_mode = "controller"
                if event.value[1] == 1:  # Up
                    if not self.ok_selected:
                        self.current_letter_index[self.current_position] = (
                            self.current_letter_index[self.current_position] - 1
                        ) % len(self.alphabet)
                        self.name[self.current_position] = self.alphabet[self.current_letter_index[self.current_position]]
                elif event.value[1] == -1:  # Down
                    if not self.ok_selected:
                        self.current_letter_index[self.current_position] = (
                            self.current_letter_index[self.current_position] + 1
                        ) % len(self.alphabet)
                        self.name[self.current_position] = self.alphabet[self.current_letter_index[self.current_position]]
                elif event.value[0] == -1:  # Left
                    if self.ok_selected:
                        self.ok_selected = False
                        self.current_position = 2
                    elif self.current_position > 0:
                        self.current_position -= 1
                elif event.value[0] == 1:  # Right
                    if self.current_position < 2:
                        self.current_position += 1
                    else:
                        self.ok_selected = True
                        
        return None
    
    def draw(self):
        # Draw sand background if available, otherwise use sand color
        if hasattr(self, 'parent_game') and hasattr(self.parent_game, 'sand_image') and self.parent_game.sand_image:
            self.screen.blit(self.parent_game.sand_image, (0, 0))
        else:
            self.screen.fill(SAND_COLOR)
        
        # Add dark overlay for better text visibility
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(150)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Title
        title_text = self.font_large.render("NEW HIGH SCORE!", True, YELLOW)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
        self.screen.blit(title_text, title_rect)
        
        # Mode indicator
        mode_text = self.font_medium.render(f"{'CO-OP' if self.is_coop else 'SINGLE PLAYER'} MODE", True, BLUE)
        mode_rect = mode_text.get_rect(center=(SCREEN_WIDTH // 2, 270))
        self.screen.blit(mode_text, mode_rect)
        
        # Score info
        score_text = self.font_medium.render(f"Score: {self.score:,}", True, WHITE)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 350))
        self.screen.blit(score_text, score_rect)
        
        wave_text = self.font_medium.render(f"Wave: {self.wave}", True, WHITE)
        wave_rect = wave_text.get_rect(center=(SCREEN_WIDTH // 2, 410))
        self.screen.blit(wave_text, wave_rect)
        
        level_text = self.font_medium.render(f"Level: {self.level}", True, WHITE)
        level_rect = level_text.get_rect(center=(SCREEN_WIDTH // 2, 470))
        self.screen.blit(level_text, level_rect)
        
        # Input method indicator
        if self.input_mode == "keyboard":
            prompt_text = self.font_medium.render("Enter your name:", True, WHITE)
            prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, 550))
            self.screen.blit(prompt_text, prompt_rect)
            
            name_display = self.keyboard_name + "_" if len(self.keyboard_name) < 10 else self.keyboard_name
            name_text = self.font_large.render(name_display, True, BLUE)
            name_rect = name_text.get_rect(center=(SCREEN_WIDTH // 2, 650))
            
            box_rect = name_rect.inflate(40, 20)
            pygame.draw.rect(self.screen, WHITE, box_rect, 3)
            self.screen.blit(name_text, name_rect)
            
            inst_text = self.font_small.render("Type your name and press ENTER", True, GRAY)
            inst_rect = inst_text.get_rect(center=(SCREEN_WIDTH // 2, 770))
            self.screen.blit(inst_text, inst_rect)
            
        else:
            # Controller mode - 3 letter input
            prompt_text = self.font_medium.render("Enter your initials:", True, WHITE)
            prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, 550))
            self.screen.blit(prompt_text, prompt_rect)
            
            letter_spacing = 120
            start_x = SCREEN_WIDTH // 2 - letter_spacing
            
            for i, letter in enumerate(self.name):
                x = start_x + i * letter_spacing
                color = YELLOW if i == self.current_position and not self.ok_selected else WHITE
                
                # Highlight current position
                if i == self.current_position and not self.ok_selected:
                    box_rect = pygame.Rect(x - 40, 630, 80, 80)
                    pygame.draw.rect(self.screen, YELLOW, box_rect, 3)
                
                letter_text = self.font_large.render(letter, True, color)
                letter_rect = letter_text.get_rect(center=(x, 670))
                self.screen.blit(letter_text, letter_rect)
            
            # OK button
            ok_color = YELLOW if self.ok_selected else WHITE
            ok_text = self.font_medium.render("OK", True, ok_color)
            ok_rect = ok_text.get_rect(center=(SCREEN_WIDTH // 2, 800))
            
            if self.ok_selected:
                box_rect = ok_rect.inflate(40, 20)
                pygame.draw.rect(self.screen, YELLOW, box_rect, 3)
            
            self.screen.blit(ok_text, ok_rect)
            
            # Instructions
            instructions = [
                "D-pad Up/Down: Change letter",
                "D-pad Left/Right: Move cursor",
                "A button: Confirm/Next",
                "B button: Go back"
            ]
            
            for i, inst in enumerate(instructions):
                inst_text = self.font_small.render(inst, True, GRAY)
                inst_rect = inst_text.get_rect(center=(SCREEN_WIDTH // 2, 900 + i * 30))
                self.screen.blit(inst_text, inst_rect)

class HighScoreScreen:
    def __init__(self, screen, high_scores):
        self.screen = screen
        self.high_scores = high_scores
        self.font_large = pygame.font.Font(None, 96)
        self.font_medium = pygame.font.Font(None, 64)
        self.font_small = pygame.font.Font(None, 48)
        self.viewing_coop = False  # False = single player, True = coop
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    return "back"
                elif event.key == pygame.K_TAB or event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    self.viewing_coop = not self.viewing_coop
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0 or event.button == 1:  # A or B button
                    return "back"
            elif event.type == pygame.JOYHATMOTION:
                if event.value[0] != 0:  # Left or Right
                    self.viewing_coop = not self.viewing_coop
        return None
    
    def draw(self):
        # Draw high scores background image or fallback to sand color
        if hasattr(self, 'parent_game') and hasattr(self.parent_game, 'highscores_image') and self.parent_game.highscores_image:
            self.screen.blit(self.parent_game.highscores_image, (0, 0))
        else:
            self.screen.fill(SAND_COLOR)
        
        # Add dark overlay for better text visibility
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(100)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Title
        mode_text = "CO-OP" if self.viewing_coop else "SINGLE PLAYER"
        title_text = self.font_large.render(f"{mode_text} HIGH SCORES", True, YELLOW)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 120))
        self.screen.blit(title_text, title_rect)
        
        # Mode toggle instruction
        toggle_text = self.font_small.render("Press TAB or Left/Right to switch modes", True, BLUE)
        toggle_rect = toggle_text.get_rect(center=(SCREEN_WIDTH // 2, 180))
        self.screen.blit(toggle_text, toggle_rect)
        
        # Headers
        header_y = 250
        if self.viewing_coop:
            # Co-op headers
            rank_header = self.font_medium.render("RANK", True, WHITE)
            p1_header = self.font_medium.render("PLAYER 1", True, WHITE)
            p2_header = self.font_medium.render("PLAYER 2", True, WHITE) 
            wave_header = self.font_medium.render("WAVE", True, WHITE)
            score_header = self.font_medium.render("SCORE", True, WHITE)
            
            self.screen.blit(rank_header, (150, header_y))
            self.screen.blit(p1_header, (350, header_y))
            self.screen.blit(p2_header, (600, header_y))
            self.screen.blit(wave_header, (850, header_y))
            self.screen.blit(score_header, (1100, header_y))
        else:
            # Single player headers
            rank_header = self.font_medium.render("RANK", True, WHITE)
            name_header = self.font_medium.render("PLAYER", True, WHITE)
            wave_header = self.font_medium.render("WAVE", True, WHITE)
            level_header = self.font_medium.render("LEVEL", True, WHITE)
            score_header = self.font_medium.render("SCORE", True, WHITE)
            
            self.screen.blit(rank_header, (200, header_y))
            self.screen.blit(name_header, (400, header_y))
            self.screen.blit(wave_header, (650, header_y))
            self.screen.blit(level_header, (850, header_y))
            self.screen.blit(score_header, (1100, header_y))
        
        # Header underline
        pygame.draw.line(self.screen, WHITE, (100, header_y + 60), (SCREEN_WIDTH - 100, header_y + 60), 2)
        
        # High scores list
        scores = self.high_scores['coop'] if self.viewing_coop else self.high_scores['single_player']
        start_y = 350
        
        for i, score_entry in enumerate(scores[:10]):  # Show top 10
            y = start_y + i * 60
            
            # Alternating row background - transparent dark overlay
            if i % 2 == 1:
                row_rect = pygame.Rect(100, y - 10, SCREEN_WIDTH - 200, 50)
                # Create a transparent surface
                row_surface = pygame.Surface((SCREEN_WIDTH - 200, 50), pygame.SRCALPHA)
                row_surface.fill((0, 0, 0, 100))  # Black with 100/255 alpha (about 40% opacity)
                self.screen.blit(row_surface, (100, y - 10))
            
            # Rank number with special colors for top 3
            rank_color = YELLOW if i == 0 else ORANGE if i < 3 else WHITE
            rank_text = self.font_small.render(f"{i + 1}.", True, rank_color)
            
            if self.viewing_coop:
                # Co-op format: (player1_name, player2_name, wave, total_score)
                p1_name, p2_name, wave, points = score_entry
                
                self.screen.blit(rank_text, (150, y))
                
                p1_text = self.font_small.render(p1_name[:12], True, WHITE)
                self.screen.blit(p1_text, (350, y))
                
                p2_text = self.font_small.render(p2_name[:12], True, WHITE)
                self.screen.blit(p2_text, (600, y))
                
                wave_text = self.font_small.render(f"{wave}", True, WHITE)
                self.screen.blit(wave_text, (850, y))
                
                score_text = self.font_small.render(f"{points:,}", True, WHITE)
                self.screen.blit(score_text, (1100, y))
            else:
                # Single player format: (player_name, wave, level, score)
                name, wave, level, points = score_entry
                
                self.screen.blit(rank_text, (200, y))
                
                name_text = self.font_small.render(name[:12], True, WHITE)
                self.screen.blit(name_text, (400, y))
                
                wave_text = self.font_small.render(f"{wave}", True, WHITE)
                self.screen.blit(wave_text, (650, y))
                
                level_text = self.font_small.render(f"{level}", True, WHITE)
                self.screen.blit(level_text, (850, y))
                
                score_text = self.font_small.render(f"{points:,}", True, WHITE)
                self.screen.blit(score_text, (1100, y))
        
        # No scores message
        if not scores:
            no_scores_text = self.font_medium.render(f"No {mode_text.lower()} high scores yet!", True, GRAY)
            no_scores_rect = no_scores_text.get_rect(center=(SCREEN_WIDTH // 2, 500))
            self.screen.blit(no_scores_text, no_scores_rect)
        
        # Instructions
        instruction_text = self.font_small.render("Press ESC, ENTER, or controller button to return to menu", True, GRAY)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80))
        self.screen.blit(instruction_text, instruction_rect)
        
        pygame.display.flip()

class Game:
    def __init__(self):            
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Tanks For Nothing")
        self.clock = pygame.time.Clock()

        # Load title screen image
        try:
            self.title_image = pygame.image.load("assets/title.png").convert()
            # Scale to screen size if needed (though your image should already be 1920x1080)
            self.title_image = pygame.transform.scale(self.title_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e:
            print(f"Could not load title image: {e}")
            print("Using fallback tan background")
            self.title_image = None

        # Load warning screen image
        try:
            self.warning_image = pygame.image.load("assets/warning.png").convert()
            self.warning_image = pygame.transform.scale(self.warning_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print("Warning image loaded successfully")
        except pygame.error as e:
            print(f"Could not load warning image: {e}")
            print("Will use title image as fallback for warnings")
            self.warning_image = None

        # Load game over screen image
        try:
            self.gameover_image = pygame.image.load("assets/gameover.png").convert()
            self.gameover_image = pygame.transform.scale(self.gameover_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print("Game over image loaded successfully")
        except pygame.error as e:
            print(f"Could not load game over image: {e}")
            print("Will use title image as fallback for game over")
            self.gameover_image = None

        # Load sand background image for gameplay
        try:
            self.sand_image = pygame.image.load("assets/sand.png").convert()
            self.sand_image = pygame.transform.scale(self.sand_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print("Sand background image loaded successfully")
        except pygame.error as e:
            print(f"Could not load sand background image: {e}")
            print("Will use default sand color for gameplay background")
            self.sand_image = None

        # Load high scores background image
        try:
            self.highscores_image = pygame.image.load("assets/highscores.png").convert()
            self.highscores_image = pygame.transform.scale(self.highscores_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print("High scores background image loaded successfully")
        except pygame.error as e:
            print(f"Could not load high scores background image: {e}")
            print("Will use default sand color for high scores background")
            self.highscores_image = None
        
        # Initialize joysticks
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for joystick in self.joysticks:
            joystick.init()
        
        self.state = "menu"  # menu, game, game_over, level_up, high_scores
        self.coop_mode = False
        self.obstacles = []
        self.effects = []
        self.pending_level_ups = []  # Players who need to level up
        self.level_up_selection = 0  # Current selection in level up menu
        self.background_surface = None  # For blurred background
        self.powerups = []
        self.waves_until_enemy_upgrade = random.randint(
            GAME_VARS['enemy_upgrade_min_waves'], 
            GAME_VARS['enemy_upgrade_max_waves']
        )
        print(f"First enemy upgrade will happen at wave {self.waves_until_enemy_upgrade}")

        self.enemy_upgrade_info = None  # Stores upgrade info for warning screen
        self.pending_enemy_upgrade = False

        # Enemy upgrade tracking
        self.global_enemy_multipliers = {
            'movement_speed': 1.0,
            'shot_speed': 1.0,
            'shot_distance': 1.0,
            'health': 1.0,
            'damage': 1.0
        }
        
        # Menu system
        self.menu_selection = 0  # 0=Single Player, 1=Co-op, 2=High Scores, 3=Quit
        
        # High scores storage
        self.high_scores = {
            'single_player': [],  # List of (player_name, wave, level, score)
            'coop': []  # List of (player1_name, player2_name, wave, total_score)
        }
        
        # Name input system
        self.awaiting_name_input = False
        self.name_input_screen = None
        
        # Load existing high scores
        self.load_high_scores()
        
        # New powerup spawn system
        self.last_powerup_spawn = 0

        # NEW: Enemy spawning system
        self.enemies_to_spawn = []  # List of enemy spawn data (x, y, spawn_time)
        self.wave_start_time = 0  # When the current wave started
        self.is_spawning_wave = False  # Whether we're currently spawning enemies
        
        self.reset_game()
    
    def draw_pixel_text(self, text, x, y, size, color, border_color=BLACK):
        """Draw text with pixel art style and black border"""
        font = pygame.font.Font(None, size)
        
        # Draw border (8 directions)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    border_surface = font.render(text, True, border_color)
                    self.screen.blit(border_surface, (x + dx, y + dy))
        
        # Draw main text
        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))
        
        return text_surface.get_size()

    def generate_obstacles(self):
        """Generate random obstacles for the current wave"""
        self.obstacles = []
        
        # Increase obstacles slightly with each wave (but cap it)
        obstacle_count = min(
            OBSTACLE_VARS['max_obstacles'],
            OBSTACLE_VARS['min_obstacles'] + (self.wave - 1) // 2
        )
        
        attempts = 0
        max_attempts = 100
        
        while len(self.obstacles) < obstacle_count and attempts < max_attempts:
            attempts += 1
            
            # Random size
            width = random.randint(OBSTACLE_VARS['min_size'], OBSTACLE_VARS['max_size'])
            height = random.randint(OBSTACLE_VARS['min_size'], OBSTACLE_VARS['max_size'])
            
            # Random position (keep away from edges)
            x = random.randint(width//2 + 50, SCREEN_WIDTH - width//2 - 50)
            y = random.randint(height//2 + 50, SCREEN_HEIGHT - height//2 - 50)
            
            # Check if this position is valid
            valid_position = True
            
            # Check distance from player spawn points
            spawn_points = [
                (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2),  # Single player spawn
                (SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2),  # Coop player 1 spawn
                (2 * SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2)  # Coop player 2 spawn
            ]
            
            for spawn_x, spawn_y in spawn_points:
                distance = math.sqrt((x - spawn_x)**2 + (y - spawn_y)**2)
                if distance < OBSTACLE_VARS['min_distance_from_spawn']:
                    valid_position = False
                    break
            
            # Check distance from other obstacles
            if valid_position:
                for obstacle in self.obstacles:
                    distance = math.sqrt((x - obstacle.x)**2 + (y - obstacle.y)**2)
                    if distance < OBSTACLE_VARS['min_distance_between']:
                        valid_position = False
                        break
            
            if valid_position:
                self.obstacles.append(Obstacle(x, y, width, height))
    
    def reset_game(self):
        self.players = []
        self.enemies = []
        self.player_missiles = []
        self.enemy_missiles = []
        self.wave = 1
        self.enemies_remaining = 0
        self.effects = []
        self.pending_level_ups = []
        self.powerups = []
        self.last_powerup_spawn = pygame.time.get_ticks()

        # Reset enemy spawning system
        self.enemies_to_spawn = []
        self.wave_start_time = 0
        self.is_spawning_wave = False

        # Reset enemy upgrade multipliers
        self.global_enemy_multipliers = {
            'movement_speed': 1.0,
            'shot_speed': 1.0,
            'shot_distance': 1.0,
            'health': 1.0,
            'damage': 1.0
        }
        
        # Create players
        if self.coop_mode:
            self.players.append(Tank(SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2, True, 1))
            self.players.append(Tank(2 * SCREEN_WIDTH // 3, SCREEN_HEIGHT // 2, True, 2))
        else:
            self.players.append(Tank(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, True, 1))
        
        self.generate_obstacles()  # Generate obstacles before spawning wave
        self.spawn_wave()
    
    def reset_players_to_start_positions(self):
        """Reset players to their starting positions"""
        if self.coop_mode:
            if len(self.players) >= 1:
                self.players[0].x = SCREEN_WIDTH // 3
                self.players[0].y = SCREEN_HEIGHT // 2
                self.players[0].angle = 0
                if self.players[0].trail:
                    self.players[0].trail.trail_points = []  # Clear trail
            if len(self.players) >= 2:
                self.players[1].x = 2 * SCREEN_WIDTH // 3
                self.players[1].y = SCREEN_HEIGHT // 2
                self.players[1].angle = 0
                if self.players[1].trail:
                    self.players[1].trail.trail_points = []  # Clear trail
        else:
            if len(self.players) >= 1:
                self.players[0].x = SCREEN_WIDTH // 2
                self.players[0].y = SCREEN_HEIGHT // 2
                self.players[0].angle = 0
                if self.players[0].trail:
                    self.players[0].trail.trail_points = []  # Clear trail

    def spawn_wave(self):
        # Reset players to starting positions
        self.reset_players_to_start_positions()
        
        # For single player, start with 1 enemy; for coop, start with more
        base_enemies = 1 if not self.coop_mode else 3
        enemy_count = base_enemies + (self.wave - 1) * GAME_VARS['enemies_per_wave']
        
        # Clear existing enemies and prepare spawn queue
        self.enemies = []
        self.enemies_to_spawn = []
        
        # Generate spawn positions and times for all enemies
        for i in range(enemy_count):
            # Spawn enemies around the edges of the screen
            side = random.randint(0, 3)  # 0=top, 1=right, 2=bottom, 3=left
            
            if side == 0:  # Top
                x = random.randint(0, SCREEN_WIDTH)
                y = -GAME_VARS['spawn_distance']
            elif side == 1:  # Right
                x = SCREEN_WIDTH + GAME_VARS['spawn_distance']
                y = random.randint(0, SCREEN_HEIGHT)
            elif side == 2:  # Bottom
                x = random.randint(0, SCREEN_WIDTH)
                y = SCREEN_HEIGHT + GAME_VARS['spawn_distance']
            else:  # Left
                x = -GAME_VARS['spawn_distance']
                y = random.randint(0, SCREEN_HEIGHT)
            
            # Calculate spawn time: immediate for first enemy, then staggered
            spawn_time = i * GAME_VARS['enemy_spawn_delay']
            
            self.enemies_to_spawn.append({
                'x': x,
                'y': y,
                'spawn_time': spawn_time
            })
        
        # Start wave spawning
        self.wave_start_time = pygame.time.get_ticks()
        self.is_spawning_wave = True
        self.enemies_remaining = enemy_count
    

    def advance_to_next_wave(self):
        """Handle advancement to the next wave, including enemy upgrades"""
        print(f"Wave {self.wave} completed. Next enemy upgrade at wave {self.waves_until_enemy_upgrade}")
        
        # Check for enemy upgrades BEFORE incrementing the wave
        if self.check_for_enemy_upgrade():
            self.pending_enemy_upgrade = True
            self.state = "enemy_upgrade_warning"
        else:
            # No upgrades, continue to next wave immediately
            self.state = "game"
            self.wave += 1
            self.generate_obstacles()
            self.spawn_wave()

    def update_enemy_spawning(self):
        """Handle staggered enemy spawning"""
        if not self.is_spawning_wave or not self.enemies_to_spawn:
            return
            
        current_time = pygame.time.get_ticks()
        elapsed_time = current_time - self.wave_start_time
        
        # Check if any enemies are ready to spawn
        enemies_spawned = []
        for enemy_data in self.enemies_to_spawn:
            if elapsed_time >= enemy_data['spawn_time']:
                # Spawn this enemy with upgrades
                new_enemy = self.create_upgraded_enemy(enemy_data['x'], enemy_data['y'])
                self.enemies.append(new_enemy)
                enemies_spawned.append(enemy_data)
        
        # Remove spawned enemies from the queue
        for spawned_enemy in enemies_spawned:
            self.enemies_to_spawn.remove(spawned_enemy)
        
        # Check if all enemies have been spawned
        if not self.enemies_to_spawn:
            self.is_spawning_wave = False

    def spawn_powerup(self):
        """Spawn a new powerup at a random location"""
        attempts = 0
        max_attempts = 50
        
        while attempts < max_attempts:
            attempts += 1
            
            # Random position
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            
            # Check if position is valid (not too close to tanks or obstacles)
            valid_position = True
            
            # Check distance from all tanks (players and enemies)
            all_tanks = self.players + self.enemies
            for tank in all_tanks:
                distance = math.sqrt((x - tank.x)**2 + (y - tank.y)**2)
                if distance < POWERUP_VARS['min_distance_from_tanks']:
                    valid_position = False
                    break
            
            # Check distance from obstacles
            if valid_position:
                for obstacle in self.obstacles:
                    # Simple check if powerup would overlap with obstacle
                    if (abs(x - obstacle.x) < obstacle.width//2 + 40 and 
                        abs(y - obstacle.y) < obstacle.height//2 + 40):
                        valid_position = False
                        break
            
            if valid_position:
                # Choose random powerup type
                powerup_types = ['shield', 'speed', 'rapid_fire', 'shotgun', 'homing']
                powerup_type = random.choice(powerup_types)
                self.powerups.append(Powerup(x, y, powerup_type))
                break
    
    def update_powerup_spawning(self):
        """Handle automatic powerup spawning"""
        current_time = pygame.time.get_ticks()
        
        # Check if it's time to spawn a new powerup
        if (current_time - self.last_powerup_spawn > POWERUP_VARS['spawn_frequency'] and
            len(self.powerups) < POWERUP_VARS['max_powerups']):
            
            self.spawn_powerup()
            self.last_powerup_spawn = current_time

    def handle_input(self):
            keys = pygame.key.get_pressed()
        
            if self.state == "game":
                # Player 1 controls (WASD + Space)
                if len(self.players) >= 1:
                    player1 = self.players[0]
                
                    # Check movement before applying it
                    if keys[pygame.K_w]:
                        new_x = player1.x + math.cos(player1.angle) * player1.movement_speed
                        new_y = player1.y + math.sin(player1.angle) * player1.movement_speed
                        if not player1.check_obstacle_collision(self.obstacles, new_x, new_y):
                            player1.move_forward()
                
                    if keys[pygame.K_s]:
                        new_x = player1.x - math.cos(player1.angle) * player1.movement_speed
                        new_y = player1.y - math.sin(player1.angle) * player1.movement_speed
                        if not player1.check_obstacle_collision(self.obstacles, new_x, new_y):
                            player1.move_backward()
                
                    if keys[pygame.K_a]:
                        player1.turn_left()
                    if keys[pygame.K_d]:
                        player1.turn_right()
                    if keys[pygame.K_SPACE]:
                        missiles = player1.shoot(self.enemies)
                        if missiles:
                            self.player_missiles.extend(missiles)
                
                    # Controller support for Player 1
                    if len(self.joysticks) >= 1:
                        joy = self.joysticks[0]
                        # Left stick for movement
                        if joy.get_axis(1) < -0.5:  # Up
                            new_x = player1.x + math.cos(player1.angle) * player1.movement_speed
                            new_y = player1.y + math.sin(player1.angle) * player1.movement_speed
                            if not player1.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player1.move_forward()
                        if joy.get_axis(1) > 0.5:   # Down
                            new_x = player1.x - math.cos(player1.angle) * player1.movement_speed
                            new_y = player1.y - math.sin(player1.angle) * player1.movement_speed
                            if not player1.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player1.move_backward()
                        if joy.get_axis(0) < -0.5:  # Left
                            player1.turn_left()
                        if joy.get_axis(0) > 0.5:   # Right
                            player1.turn_right()
                        # D-pad controls
                        if joy.get_hat(0)[1] == 1:  # D-pad Up
                            new_x = player1.x + math.cos(player1.angle) * player1.movement_speed
                            new_y = player1.y + math.sin(player1.angle) * player1.movement_speed
                            if not player1.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player1.move_forward()
                        if joy.get_hat(0)[1] == -1:  # D-pad Down
                            new_x = player1.x - math.cos(player1.angle) * player1.movement_speed
                            new_y = player1.y - math.sin(player1.angle) * player1.movement_speed
                            if not player1.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player1.move_backward()
                        if joy.get_hat(0)[0] == -1:  # D-pad Left
                            player1.turn_left()
                        if joy.get_hat(0)[0] == 1:   # D-pad Right
                            player1.turn_right()
                        if joy.get_button(0):  # A button
                            missiles = player1.shoot(self.enemies)
                            if missiles:
                                self.player_missiles.extend(missiles)
            
                # Player 2 controls (Arrow keys + Right Ctrl) - only in coop mode
                if self.coop_mode and len(self.players) >= 2:
                    player2 = self.players[1]
                
                    if keys[pygame.K_UP]:
                        new_x = player2.x + math.cos(player2.angle) * player2.movement_speed
                        new_y = player2.y + math.sin(player2.angle) * player2.movement_speed
                        if not player2.check_obstacle_collision(self.obstacles, new_x, new_y):
                            player2.move_forward()
                
                    if keys[pygame.K_DOWN]:
                        new_x = player2.x - math.cos(player2.angle) * player2.movement_speed
                        new_y = player2.y - math.sin(player2.angle) * player2.movement_speed
                        if not player2.check_obstacle_collision(self.obstacles, new_x, new_y):
                            player2.move_backward()
                
                    if keys[pygame.K_LEFT]:
                        player2.turn_left()
                    if keys[pygame.K_RIGHT]:
                        player2.turn_right()
                    if keys[pygame.K_RCTRL]:
                        missiles = player2.shoot(self.enemies)
                        if missiles:
                            self.player_missiles.extend(missiles)
                
                    # Controller support for Player 2
                    if len(self.joysticks) >= 2:
                        joy = self.joysticks[1]
                        if joy.get_axis(1) < -0.5:
                            new_x = player2.x + math.cos(player2.angle) * player2.movement_speed
                            new_y = player2.y + math.sin(player2.angle) * player2.movement_speed
                            if not player2.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player2.move_forward()
                        if joy.get_axis(1) > 0.5:
                            new_x = player2.x - math.cos(player2.angle) * player2.movement_speed
                            new_y = player2.y - math.sin(player2.angle) * player2.movement_speed
                            if not player2.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player2.move_backward()
                        if joy.get_axis(0) < -0.5:
                            player2.turn_left()
                        if joy.get_axis(0) > 0.5:
                            player2.turn_right()
                        # D-pad controls for Player 2
                        if joy.get_hat(0)[1] == 1:  # D-pad Up
                            new_x = player2.x + math.cos(player2.angle) * player2.movement_speed
                            new_y = player2.y + math.sin(player2.angle) * player2.movement_speed
                            if not player2.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player2.move_forward()
                        if joy.get_hat(0)[1] == -1:  # D-pad Down
                            new_x = player2.x - math.cos(player2.angle) * player2.movement_speed
                            new_y = player2.y - math.sin(player2.angle) * player2.movement_speed
                            if not player2.check_obstacle_collision(self.obstacles, new_x, new_y):
                                player2.move_backward()
                        if joy.get_hat(0)[0] == -1:  # D-pad Left
                            player2.turn_left()
                        if joy.get_hat(0)[0] == 1:   # D-pad Right
                            player2.turn_right()
                        if joy.get_button(0):
                            missiles = player2.shoot(self.enemies)
                            if missiles:
                                self.player_missiles.extend(missiles)

    def check_for_enemy_upgrade(self):
        """Check if enemies should be upgraded this wave"""
        if self.wave >= self.waves_until_enemy_upgrade:
            self.apply_enemy_upgrade()
            # Set next upgrade to happen after 1-5 MORE waves from current wave
            waves_to_add = random.randint(
                GAME_VARS['enemy_upgrade_min_waves'], 
                GAME_VARS['enemy_upgrade_max_waves']
            )
            self.waves_until_enemy_upgrade = self.wave + waves_to_add
            print(f"Enemy upgrade applied at wave {self.wave}. Next upgrade will be at wave {self.waves_until_enemy_upgrade}")
            return True
        return False
    
    def apply_enemy_upgrade(self):
        """Apply random upgrade to all enemy tanks"""
        # Choose random upgrade type
        upgrade_types = ['movement_speed', 'shot_speed', 'shot_distance', 'health', 'damage']
        upgrade_type = random.choice(upgrade_types)
        
        # Choose weighted random percentage
        percentages = GAME_VARS['enemy_upgrade_percentages']
        weights = GAME_VARS['enemy_upgrade_weights']
        upgrade_percentage = random.choices(percentages, weights=weights)[0]
        
        # Store upgrade info for warning screen
        self.enemy_upgrade_info = {
            'type': upgrade_type,
            'percentage': upgrade_percentage
        }
        
        # Update global multipliers
        multiplier = 1.0 + (upgrade_percentage / 100.0)
        self.global_enemy_multipliers[upgrade_type] *= multiplier
        
        # Apply upgrade to all existing enemies
        for enemy in self.enemies:
            if hasattr(enemy, 'upgrade_multipliers'):
                enemy.upgrade_multipliers[upgrade_type] *= multiplier
                
                # Apply the actual stat changes
                if upgrade_type == 'movement_speed':
                    enemy.movement_speed = enemy.base_movement_speed * enemy.upgrade_multipliers['movement_speed']
                elif upgrade_type == 'shot_speed':
                    enemy.shot_speed = enemy.base_shot_speed * enemy.upgrade_multipliers['shot_speed']
                elif upgrade_type == 'shot_distance':
                    enemy.shot_distance = enemy.base_shot_distance * enemy.upgrade_multipliers['shot_distance']
                elif upgrade_type == 'health':
                    old_max = enemy.max_health
                    enemy.max_health = int(enemy.base_max_health * enemy.upgrade_multipliers['health'])
                    # Heal proportionally
                    health_ratio = enemy.health / old_max if old_max > 0 else 1.0
                    enemy.health = int(enemy.max_health * health_ratio)
                elif upgrade_type == 'damage':
                    enemy.damage = int(enemy.base_damage * enemy.upgrade_multipliers['damage'])
    
    def draw_enemy_upgrade_warning(self):
        # Draw warning background image with blur effect
        if self.warning_image:
            blurred_warning = self.create_blur_effect(self.warning_image, blur_radius=20)
            self.screen.blit(blurred_warning, (0, 0))
        elif self.title_image:
            # Fallback to title image
            blurred_title = self.create_blur_effect(self.title_image, blur_radius=20)
            self.screen.blit(blurred_title, (0, 0))
        else:
            self.screen.fill((100, 50, 50))  # Dark red background
        
        font_large = pygame.font.Font(None, 84)
        font_medium = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 36)
        
        # Warning title
        warning_text = font_large.render("⚠ ENEMY UPGRADE DETECTED ⚠", True, RED)
        warning_rect = warning_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
        self.screen.blit(warning_text, warning_rect)
        
        if self.enemy_upgrade_info:
            upgrade_type = self.enemy_upgrade_info['type'].replace('_', ' ').title()
            upgrade_percentage = self.enemy_upgrade_info['percentage']
            
            # Upgrade details
            upgrade_text = font_medium.render(f"Enemy {upgrade_type} increased by {upgrade_percentage}%!", True, YELLOW)
            upgrade_rect = upgrade_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(upgrade_text, upgrade_rect)
            
            # Additional warning
            warning_detail = font_small.render("All enemy tanks have been enhanced!", True, WHITE)
            detail_rect = warning_detail.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 60))
            self.screen.blit(warning_detail, detail_rect)
        
        # Continue instruction
        continue_text = font_small.render("Press ENTER/SPACE or A Button to continue", True, GRAY)
        continue_rect = continue_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100))
        self.screen.blit(continue_text, continue_rect)

    def create_upgraded_enemy(self, x, y):
        """Create a new enemy with all current upgrades applied"""
        enemy = Tank(x, y, False)
        
        # Apply global multipliers to new enemy
        for upgrade_type, multiplier in self.global_enemy_multipliers.items():
            enemy.upgrade_multipliers[upgrade_type] = multiplier
            
            # Apply the actual stat changes
            if upgrade_type == 'movement_speed':
                enemy.movement_speed = enemy.base_movement_speed * multiplier
            elif upgrade_type == 'shot_speed':
                enemy.shot_speed = enemy.base_shot_speed * multiplier
            elif upgrade_type == 'shot_distance':
                enemy.shot_distance = enemy.base_shot_distance * multiplier
            elif upgrade_type == 'health':
                enemy.max_health = int(enemy.base_max_health * multiplier)
                enemy.health = enemy.max_health
            elif upgrade_type == 'damage':
                enemy.damage = int(enemy.base_damage * multiplier)
        
        return enemy

    def update(self):
        if self.state == "game":

            # Update enemy spawning
            self.update_enemy_spawning()

            # Update powerup spawning
            self.update_powerup_spawning()
            
            # Update powerups
            for powerup in self.powerups[:]:
                powerup.update()
            
            # Update player powerups
            for player in self.players:
                player.update_powerups()
            
            # Update missiles
            self.player_missiles = [m for m in self.player_missiles if not m.update()]
            self.enemy_missiles = [m for m in self.enemy_missiles if not m.update()]
            
            # Update effects
            self.effects = [e for e in self.effects if not e.update()]
            
            # Update enemy AI and collect missiles
            for enemy in self.enemies[:]:
                missiles = enemy.update_ai(self.players, self.obstacles)
                if missiles:
                    self.enemy_missiles.extend(missiles)
            
            # Check collisions - missiles vs obstacles
            for missile in self.player_missiles[:]:
                for obstacle in self.obstacles:
                    if missile.get_rect().colliderect(obstacle.get_rect()):
                        self.player_missiles.remove(missile)
                        break
            
            for missile in self.enemy_missiles[:]:
                for obstacle in self.obstacles:
                    if missile.get_rect().colliderect(obstacle.get_rect()):
                        self.enemy_missiles.remove(missile)
                        break
            
            # Check collisions - player vs powerups
            for powerup in self.powerups[:]:
                for player in self.players:
                    if powerup.get_rect().colliderect(player.get_rect()):
                        player.activate_powerup(powerup.powerup_type)
                        self.powerups.remove(powerup)
                        break
            
            # Check collisions - player missiles vs enemies
            for missile in self.player_missiles[:]:
                for enemy in self.enemies[:]:
                    if missile.get_rect().colliderect(enemy.get_rect()):
                        # Award XP only to the player who shot the missile
                        if missile.player_owner:
                            missile.player_owner.gain_xp(LEVELING_VARS['xp_per_hit'])
                        
                        # Create hit effect
                        self.effects.append(Effect(enemy.x, enemy.y, 'hit'))
                        
                        if enemy.take_damage():
                            # Award kill XP only to the shooting player
                            if missile.player_owner:
                                missile.player_owner.gain_xp(LEVELING_VARS['xp_per_kill'])
                            
                            # Create explosion effect
                            self.effects.append(Effect(enemy.x, enemy.y, 'explosion'))
                            
                            self.enemies.remove(enemy)
                        self.player_missiles.remove(missile)
                        break
            
            # Check collisions - enemy missiles vs players
            for missile in self.enemy_missiles[:]:
                for player in self.players[:]:
                    if missile.get_rect().colliderect(player.get_rect()):
                        # Create hit effect
                        self.effects.append(Effect(player.x, player.y, 'hit'))
               
         
                        # Calculate damage from the enemy that fired this missile
                        damage = 10  # Default damage
                        if hasattr(missile, 'owner_tank') and missile.owner_tank:
                            damage = int(missile.owner_tank.damage)
            
                        if player.take_damage(damage):
                            # Create explosion effect
                            self.effects.append(Effect(player.x, player.y, 'explosion'))
                            # Mark player as dead but don't remove from list yet
                            player.is_dead = True
                            player.health = 0
                        self.enemy_missiles.remove(missile)
                        break
            
            # Check win/lose conditions
            alive_players = [p for p in self.players if not getattr(p, 'is_dead', False)]
            
            if not alive_players:
                self.state = "game_over"
                
                # Calculate total score
                total_score = 0
                if self.players:
                    for player in self.players:
                        total_score += self.calculate_score(player)
                
                # Check if it's a high score
                if self.is_high_score(total_score, self.coop_mode):
                    # Create name input screen
                    self.name_input_screen = NameInputScreen(
                        self.screen, 
                        total_score, 
                        self.wave, 
                        max(player.level for player in self.players) if self.players else 1,
                        self.coop_mode
                    )
                    self.name_input_screen.parent_game = self  # So it can access sand image
                    self.awaiting_name_input = True
            elif not self.enemies and not self.is_spawning_wave:  # Wave complete only when all enemies spawned and destroyed
                # Wave complete - revive dead players and heal all players
                for player in self.players:
                    if getattr(player, 'is_dead', False):
                        player.is_dead = False
                        player.health = player.max_health
                        # Reset position
                        if player.player_num == 1:
                            if self.coop_mode:
                                player.x = SCREEN_WIDTH // 3
                            else:
                                player.x = SCREEN_WIDTH // 2
                            player.y = SCREEN_HEIGHT // 2
                        elif player.player_num == 2:
                            player.x = 2 * SCREEN_WIDTH // 3
                            player.y = SCREEN_HEIGHT // 2
                        player.angle = 0
                    else:
                        player.heal_to_full()
                
                # Check if any players leveled up - FIXED VERSION
                players_to_level = []
                for player in self.players:
                    # Initialize tracking if not present
                    if not hasattr(player, 'pending_level_ups'):
                        player.pending_level_ups = 0
                    
                    # Check how many levels the player has gained
                    current_level = player.level
                    last_processed_level = getattr(player, 'last_processed_level', 1)
                    
                    if current_level > last_processed_level:
                        # Calculate how many level ups are pending
                        levels_gained = current_level - last_processed_level
                        player.pending_level_ups += levels_gained
                        player.last_processed_level = current_level
                
                # Add players with pending level ups to the queue
                for player in self.players:
                    if getattr(player, 'pending_level_ups', 0) > 0:
                        players_to_level.append(player)
                
                if players_to_level:
                    # Capture background for blur effect
                    self.background_surface = self.screen.copy()
                    self.pending_level_ups = players_to_level.copy()
                    self.level_up_selection = 0
                    self.state = "level_up"
                else:
                    # No level ups, advance to next wave
                    self.advance_to_next_wave()
    def draw_menu(self):
        # Draw title background image or fallback to tan
        if self.title_image:
            self.screen.blit(self.title_image, (0, 0))

            # Optional: Add semi-transparent overlay for better text readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(100)  # Adjust transparency (0-255, lower = more transparent)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(SAND_COLOR)
        
        # Title with pixel art style
        title_y = SCREEN_HEIGHT // 6
        title_width, title_height = self.draw_pixel_text(
            "TANKS FOR NOTHING", 
            SCREEN_WIDTH//2 - 300, 
            title_y, 
            84, 
            YELLOW, 
            BLACK
        )
        
        # Subtitle
        subtitle_y = title_y + title_height + 20
        self.draw_pixel_text(
            "A Co-op Tank Battle Experience", 
            SCREEN_WIDTH//2 - 200, 
            subtitle_y, 
            36, 
            WHITE, 
            BLACK
        )
        
        # Menu options
        menu_options = [
            "Single Player",
            "Co-op Mode", 
            "High Scores",
            "Quit Game"
        ]
        
        menu_start_y = SCREEN_HEIGHT//2 - 50
        
        for i, option in enumerate(menu_options):
            color = YELLOW if i == self.menu_selection else WHITE
            border_color = RED if i == self.menu_selection else BLACK
            
            # Add selection indicator
            prefix = "> " if i == self.menu_selection else "  "
            
            option_y = menu_start_y + i * 60
            self.draw_pixel_text(
                prefix + option,
                SCREEN_WIDTH//2 - 150,
                option_y,
                48,
                color,
                border_color
            )
        
        # Controls info
        controls_y = SCREEN_HEIGHT - 100
        self.draw_pixel_text(
            "Use WASD/Arrow Keys or Controller to navigate • ENTER/A Button to select",
            SCREEN_WIDTH//2 - 350,
            controls_y,
            24,
            GRAY,
            BLACK
        )

    def draw_high_scores(self):
        """Handle high scores screen with new table-based layout"""
        if not hasattr(self, 'high_score_screen'):
            self.high_score_screen = HighScoreScreen(self.screen, self.high_scores)
            self.high_score_screen.parent_game = self  # For accessing background images
        
        # Handle high score screen events here instead of in main loop
        action = self.high_score_screen.handle_events()
        if action == "back":
            self.state = "menu"
            del self.high_score_screen
            return
        elif action == "quit":
            pygame.quit()
            sys.exit()
        
        self.high_score_screen.draw()

    def load_high_scores(self):
        """Load high scores from file"""
        try:
            if os.path.exists('high_scores.json'):
                with open('high_scores.json', 'r') as f:
                    self.high_scores = json.load(f)
            else:
                self.high_scores = {
                    'single_player': [],
                    'coop': []
                }
        except:
            self.high_scores = {
                'single_player': [],
                'coop': []
            }

    def save_high_scores(self):
        """Save high scores to file"""
        try:
            with open('high_scores.json', 'w') as f:
                json.dump(self.high_scores, f, indent=2)
        except:
            pass  # Fail silently if can't save
    
    def draw_game(self):
        # Draw sand background image or fallback to sand color
        if self.sand_image:
            self.screen.blit(self.sand_image, (0, 0))
        else:
            self.screen.fill(SAND_COLOR)
        
        # Draw game objects
        for obstacle in self.obstacles:
            obstacle.draw(self.screen)

        # Draw tank trails (before drawing tanks so trails appear behind them)
        for player in self.players:
            if not getattr(player, 'is_dead', False) and player.trail:
                player.trail.draw(self.screen)

        # Draw enemy trails
        for enemy in self.enemies:
            if enemy.trail:
                enemy.trail.draw(self.screen)
        
        # Draw powerups
        for powerup in self.powerups:
            powerup.draw(self.screen)
        
        # Only draw alive players
        for player in self.players:
            if not getattr(player, 'is_dead', False):
                player.draw(self.screen)
        
        for enemy in self.enemies:
            enemy.draw(self.screen)
        
        for missile in self.player_missiles:
            missile.draw(self.screen)
        
        for missile in self.enemy_missiles:
            missile.draw(self.screen)
        
        # Draw effects
        for effect in self.effects:
            effect.draw(self.screen)
        
        # Draw HUD
        font = pygame.font.Font(None, 36)
        wave_text = font.render(f"Wave: {self.wave}", True, BLACK)
        self.screen.blit(wave_text, (10, 10))
        
        enemies_text = font.render(f"Enemies: {len(self.enemies)}", True, BLACK)
        self.screen.blit(enemies_text, (10, 50))
        
        # Show enemies waiting to spawn
        if self.is_spawning_wave and self.enemies_to_spawn:
            spawning_text = font.render(f"Spawning: {len(self.enemies_to_spawn)}", True, RED)
            self.screen.blit(spawning_text, (10, 90))
            
            powerups_text = font.render(f"Powerups: {len(self.powerups)}", True, BLACK)
            self.screen.blit(powerups_text, (10, 130))
            y_offset = 170
        else:
            powerups_text = font.render(f"Powerups: {len(self.powerups)}", True, BLACK)
            self.screen.blit(powerups_text, (10, 90))
            y_offset = 130
        
        # Draw player stats (including dead players)
        for i, player in enumerate(self.players):
            status = " (DEAD)" if getattr(player, 'is_dead', False) else ""
            player_text = font.render(f"Player {player.player_num}: Level {player.level}{status}", True, BLACK)
            self.screen.blit(player_text, (10, y_offset))
            
            # XP Bar
            xp_bar_width = 200
            xp_bar_height = 15
            xp_ratio = player.xp / player.xp_to_next_level
            
            # Background
            pygame.draw.rect(self.screen, GRAY, (10, y_offset + 25, xp_bar_width, xp_bar_height))
            # XP
            pygame.draw.rect(self.screen, BLUE, (10, y_offset + 25, int(xp_bar_width * xp_ratio), xp_bar_height))
            # Border
            pygame.draw.rect(self.screen, BLACK, (10, y_offset + 25, xp_bar_width, xp_bar_height), 2)
            
            # XP Text
            small_font = pygame.font.Font(None, 24)
            xp_text = small_font.render(f"XP: {player.xp}/{player.xp_to_next_level}", True, BLACK)
            self.screen.blit(xp_text, (220, y_offset + 27))
            
            # Show active powerups (only for alive players)
            if not getattr(player, 'is_dead', False):
                powerup_y = y_offset + 45
                if player.shield_active:
                    shield_text = small_font.render("SHIELD", True, BLUE)
                    self.screen.blit(shield_text, (10, powerup_y))
                    powerup_y += 20
                
                if player.speed_boost_active:
                    speed_text = small_font.render("SPEED", True, GREEN)
                    self.screen.blit(speed_text, (10, powerup_y))
                    powerup_y += 20
                
                # Show shot-based powerups
                for powerup_type, shots in player.powerup_shots_remaining.items():
                    powerup_text = small_font.render(f"{powerup_type.upper()}: {shots}", True, ORANGE)
                    self.screen.blit(powerup_text, (10, powerup_y))
                    powerup_y += 20
            
            y_offset += 120

        # Debug: Show enemy upgrade info
        if self.enemies:
            debug_y = y_offset + 20
            enemy = self.enemies[0]  # Show first enemy's stats
            small_font = pygame.font.Font(None, 24)
            
            debug_text = small_font.render(f"Enemy Stats: Speed={enemy.movement_speed:.1f} Damage={enemy.damage}", True, RED)
            self.screen.blit(debug_text, (10, debug_y))
            
            multiplier_text = small_font.render(f"Multipliers: Dmg={enemy.upgrade_multipliers['damage']:.2f} Spd={enemy.upgrade_multipliers['movement_speed']:.2f}", True, RED)
            self.screen.blit(multiplier_text, (10, debug_y + 20))
            
            # Show global multipliers too
            global_text = small_font.render(f"Global: Dmg={self.global_enemy_multipliers['damage']:.2f} Health={self.global_enemy_multipliers['health']:.2f}", True, RED)
            self.screen.blit(global_text, (10, debug_y + 40))
    
    def create_blur_effect(self, surface, blur_radius=8):
        """Create a nice blur effect by applying multiple passes"""
        # Create a copy to work with
        blurred = surface.copy()
        
        # Apply multiple blur passes for smoother effect
        for _ in range(blur_radius):
            # Scale down and up for blur effect
            w, h = blurred.get_size()
            small = pygame.transform.smoothscale(blurred, (w//2, h//2))
            blurred = pygame.transform.smoothscale(small, (w, h))
        
        return blurred
    
    def draw_game_over(self):
        # Handle name input screen
        if self.awaiting_name_input and self.name_input_screen:
            self.name_input_screen.draw()
            return

        # Draw game over background image with blur effect
        if self.gameover_image:
            # Create a blurred version of the game over image
            blurred_gameover = self.create_blur_effect(self.gameover_image, blur_radius=32)
            self.screen.blit(blurred_gameover, (0, 0))
            
            # Add a subtle dark overlay for better text visibility
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(120)  # Slightly more opaque than menu for better readability
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
        elif self.title_image:
            # Fallback to title image if gameover image not available
            blurred_title = self.create_blur_effect(self.title_image, blur_radius=32)
            self.screen.blit(blurred_title, (0, 0))
            
            # Add a subtle dark overlay for better text visibility
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(120)
            overlay.fill(BLACK)
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(SAND_COLOR)
            
        # Title
        self.draw_pixel_text(
            "GAME OVER",
            SCREEN_WIDTH//2 - 150,
            SCREEN_HEIGHT//3 - 50,
            84,
            RED,
            BLACK
        )
        
        # Stats
        stats_y = SCREEN_HEIGHT//2 - 50
        self.draw_pixel_text(
            f"You reached Wave {self.wave}",
            SCREEN_WIDTH//2 - 120,
            stats_y,
            48,
            WHITE,
            BLACK
        )
        
        # Player scores
        if self.players:
            for i, player in enumerate(self.players):
                score = self.calculate_score(player)
                score_y = stats_y + 60 + (i * 40)
                self.draw_pixel_text(
                    f"Player {player.player_num}: Level {player.level}, Score {score}",
                    SCREEN_WIDTH//2 - 150,
                    score_y,
                    32,
                    YELLOW,
                    BLACK
                )
        elif hasattr(self, 'dead_players_scores'):
            # Show scores for dead players
            for i, (player_num, level, score) in enumerate(self.dead_players_scores):
                score_y = stats_y + 60 + (i * 40)
                self.draw_pixel_text(
                    f"Player {player_num}: Level {level}, Score {score}",
                    SCREEN_WIDTH//2 - 150,
                    score_y,
                    32,
                    YELLOW,
                    BLACK
                )
        
        # Check if this is a high score
        mode = 'coop' if self.coop_mode else 'single_player'
        if self.high_scores[mode] and hasattr(self, 'score_added'):
            # Check if any current score made it to top 10
            current_scores = []
            if self.players:
                for player in self.players:
                    current_scores.append(self.calculate_score(player))
            
            top_10_threshold = self.high_scores[mode][min(9, len(self.high_scores[mode])-1)][3] if len(self.high_scores[mode]) >= 10 else 0
            
            if any(score > top_10_threshold for score in current_scores) or len(self.high_scores[mode]) < 10:
                self.draw_pixel_text(
                    "NEW HIGH SCORE!",
                    SCREEN_WIDTH//2 - 100,
                    stats_y - 60,
                    36,
                    YELLOW,
                    RED
                )
        
        # Instructions
        self.draw_pixel_text(
            "Press 'R' to Restart • 'ESC' for Menu",
            SCREEN_WIDTH//2 - 150,
            SCREEN_HEIGHT - 150,
            32,
            GRAY,
            BLACK
        )

    def draw_level_up(self):
        # Draw enhanced blurred background
        if self.background_surface:
            # Create a high-quality blur effect
            blurred_surface = self.create_blur_effect(self.background_surface, blur_radius=12)
            
            # Add a subtle dark overlay for better text visibility
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(60)  # Much lighter darkening
            overlay.fill(BLACK)
            
            self.screen.blit(blurred_surface, (0, 0))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(SAND_COLOR)
        
        # Get current player leveling up
        current_player = self.pending_level_ups[0] if self.pending_level_ups else None
        if not current_player:
            return
        
        font_large = pygame.font.Font(None, 74)
        font_medium = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 36)
        font_tiny = pygame.font.Font(None, 28)
        
        # Title
        title_text = font_large.render("LEVEL UP!", True, YELLOW)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//4))
        self.screen.blit(title_text, title_rect)
        
        # Player info with pending upgrades
        pending_upgrades = getattr(current_player, 'pending_level_ups', 0)
        player_info = f"Player {current_player.player_num} - Level {current_player.level}"
        if pending_upgrades > 1:
            player_info += f" ({pending_upgrades} upgrades remaining)"
        
        player_text = font_medium.render(player_info, True, WHITE)
        player_rect = player_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//4 + 80))
        self.screen.blit(player_text, player_rect)
        
        # Upgrade options with detailed progression info
        options = [
            ("Movement Speed", "movement_speed"),
            ("Shot Speed", "shot_speed"),
            ("Shot Distance", "shot_distance"),
            ("Fire Rate", "fire_rate"),
            ("Powerup Duration", "powerup_duration"),
            ("Health", "health")
        ]
        
        start_y = SCREEN_HEIGHT//2 - 75
        for i, (display_name, stat_name) in enumerate(options):
            color = WHITE
            prefix = "  "
            
            # Get stat info
            stat_info = current_player.get_stat_info(stat_name)
            can_upgrade = current_player.can_upgrade_stat(stat_name)
            
            # Build the display text with progression info
            if stat_info:
                progress_text = f" ({stat_info['upgrades']}/{stat_info['max_upgrades']}) +{stat_info['current_percent']}%"
                full_text = display_name + progress_text
            else:
                full_text = display_name
            
            # Check if this stat is maxed out
            if not can_upgrade:
                color = GRAY
                if " (MAX)" not in full_text:
                    full_text += " (MAX)"
            
            # Show selection arrow
            if i == self.level_up_selection:
                prefix = "> "
                color = YELLOW if can_upgrade else GRAY
            
            option_text = font_small.render(prefix + full_text, True, color)
            self.screen.blit(option_text, (SCREEN_WIDTH//2 - 200, start_y + i * 50))
        
        # Instructions
        instruction_text = font_tiny.render("Use Arrow Keys/WASD to select, ENTER/SPACE to confirm", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100))
        self.screen.blit(instruction_text, instruction_rect)
    
    def apply_level_up_choice(self):
        """Apply the selected level up choice"""
        if not self.pending_level_ups:
            return
        
        current_player = self.pending_level_ups[0]
        options = ["movement_speed", "shot_speed", "shot_distance", "fire_rate", "powerup_duration", "health"]
        selected_stat = options[self.level_up_selection]
        
        # Only upgrade if the stat can be upgraded
        if current_player.can_upgrade_stat(selected_stat):
            current_player.upgrade_stat(selected_stat)
            
            # Reduce pending level ups for this player
            if hasattr(current_player, 'pending_level_ups'):
                current_player.pending_level_ups -= 1
                
                # If this player still has more level ups pending, keep them in queue
                if current_player.pending_level_ups > 0:
                    # Reset selection for next upgrade
                    self.level_up_selection = 0
                    return
            
            # Remove this player from pending level ups (they're done for now)
            self.pending_level_ups.pop(0)
            
            # If more players need to level up, continue
            if self.pending_level_ups:
                self.level_up_selection = 0
            else:
                # All level ups done - check for enemy upgrades but handle wave increment properly
                print(f"Wave {self.wave} completed. Next enemy upgrade at wave {self.waves_until_enemy_upgrade}")
                
                # Check for enemy upgrades BEFORE incrementing the wave
                if self.check_for_enemy_upgrade():
                    # Enemy upgrade will be applied, show warning
                    self.pending_enemy_upgrade = True
                    self.state = "enemy_upgrade_warning"
                else:
                    # No upgrades, continue to next wave immediately
                    self.state = "game"
                    self.wave += 1
                    self.generate_obstacles()
                    self.spawn_wave()
    
    def handle_menu_selection(self):
        """Handle menu selection"""
        if self.menu_selection == 0:  # Single Player
            self.coop_mode = False
            self.state = "game"
            self.reset_game()
        elif self.menu_selection == 1:  # Co-op
            self.coop_mode = True
            self.state = "game"
            self.reset_game()
        elif self.menu_selection == 2:  # High Scores
            self.state = "high_scores"
            self.high_scores_page = 0
        elif self.menu_selection == 3:  # Quit
            pygame.quit()
            sys.exit()

    def calculate_score(self, player):
        """Calculate final score for a player"""
        # Score = (Wave * 1000) + (Level * 500) + XP
        return (self.wave * 1000) + (player.level * 500) + player.xp

    def add_high_score(self, name, score, wave, level, is_coop=False):
        """Add a new score to the appropriate list"""
        if is_coop:
            # For coop, calculate combined score from both players
            if len(self.players) >= 2:
                combined_score = self.calculate_score(self.players[0]) + self.calculate_score(self.players[1])
                player1_name = name  # The name entered
                player2_name = f"P2"  # You might want to modify NameInputScreen to get both names
                score_entry = (player1_name, player2_name, wave, combined_score)
            else:
                # Fallback for single player in coop mode
                score_entry = (name, "P2", wave, score)
            
            self.high_scores['coop'].append(score_entry)
            self.high_scores['coop'].sort(key=lambda x: x[3], reverse=True)
            self.high_scores['coop'] = self.high_scores['coop'][:10]
        else:
            score_entry = (name, wave, level, score)
            self.high_scores['single_player'].append(score_entry)
            self.high_scores['single_player'].sort(key=lambda x: x[3], reverse=True)
            self.high_scores['single_player'] = self.high_scores['single_player'][:10]
        
        self.save_high_scores()

    def load_high_scores(self):
        """Load high scores from file"""
        try:
            if os.path.exists('tank_high_scores.json'):
                with open('tank_high_scores.json', 'r') as f:
                    self.high_scores = json.load(f)
            else:
                self.high_scores = {
                    'single_player': [],
                    'coop': []
                }
        except:
            self.high_scores = {
                'single_player': [],
                'coop': []
            }

    def save_high_scores(self):
        """Save high scores to file"""
        try:
            with open('tank_high_scores.json', 'w') as f:
                json.dump(self.high_scores, f, indent=2)
        except:
            pass  # Fail silently if can't save

    def is_high_score(self, score, is_coop=False):
        """Check if score qualifies for high score list"""
        scores = self.high_scores['coop'] if is_coop else self.high_scores['single_player']
        return len(scores) < 10 or (scores and score > scores[-1][3])

    def add_high_score(self, name, score, wave, level, is_coop=False):
        """Add a new score to the appropriate list"""
        if is_coop:
            # For coop, you might want to handle two player names differently
            # For now, just use the single name for both players
            score_entry = (name, name, wave, score)
            self.high_scores['coop'].append(score_entry)
            self.high_scores['coop'].sort(key=lambda x: x[3], reverse=True)
            self.high_scores['coop'] = self.high_scores['coop'][:10]
        else:
            score_entry = (name, wave, level, score)
            self.high_scores['single_player'].append(score_entry)
            self.high_scores['single_player'].sort(key=lambda x: x[3], reverse=True)
            self.high_scores['single_player'] = self.high_scores['single_player'][:10]
        
        self.save_high_scores()

    def run(self):
        running = True
        
        # Add input timing to prevent rapid menu scrolling
        last_input_time = 0
        input_delay = 200  # milliseconds
        
        while running:
            current_time = pygame.time.get_ticks()
            
            # Special handling for name input
            if self.state == "game_over" and self.awaiting_name_input:
                name = self.name_input_screen.handle_events()
                if name == "quit":
                    running = False
                elif name:
                    # Calculate total score again
                    total_score = 0
                    if self.players:
                        for player in self.players:
                            total_score += self.calculate_score(player)
                    
                    # Add to high scores
                    self.add_high_score(
                        name, 
                        total_score, 
                        self.wave, 
                        max(player.level for player in self.players) if self.players else 1,
                        self.coop_mode
                    )
                    self.awaiting_name_input = False
                    self.name_input_screen = None
            else:
                # Normal event handling for everything else
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if self.state == "high_scores":
                                self.state = "menu"
                            else:
                                running = False
                        
                        elif self.state == "menu":
                            if event.key == pygame.K_UP or event.key == pygame.K_w:
                                self.menu_selection = (self.menu_selection - 1) % 4
                            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                                self.menu_selection = (self.menu_selection + 1) % 4
                            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                                self.handle_menu_selection()
                        
                        elif self.state == "high_scores":
                            if event.key == pygame.K_ESCAPE:
                                self.state = "menu"
                                if hasattr(self, 'high_score_screen'):
                                    del self.high_score_screen
                        
                        elif self.state == "game_over":
                            # Only handle game over inputs if NOT awaiting name input
                            if not self.awaiting_name_input:
                                if event.key == pygame.K_r:
                                    self.state = "game"
                                    self.reset_game()
                                elif event.key == pygame.K_ESCAPE:
                                    self.state = "menu"
                                    self.menu_selection = 0
                        
                        elif self.state == "level_up":
                            if event.key == pygame.K_UP or event.key == pygame.K_w:
                                self.level_up_selection = (self.level_up_selection - 1) % 6
                            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                                self.level_up_selection = (self.level_up_selection + 1) % 6
                            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                                self.apply_level_up_choice()

                        elif self.state == "enemy_upgrade_warning":
                            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                                self.state = "game"
                                self.wave += 1  # NOW increment the wave
                                self.generate_obstacles()
                                self.spawn_wave()
                                self.pending_enemy_upgrade = False
                    
                    # Controller button presses
                    elif event.type == pygame.JOYBUTTONDOWN:
                        if self.state == "menu":
                            if event.button == 0:  # A button
                                self.handle_menu_selection()
                            elif event.button == 1:  # B button
                                running = False
                        elif self.state == "high_scores":
                            # High scores navigation is now handled in HighScoreScreen.handle_events()
                            pass
                        elif self.state == "game_over":
                            # Only handle controller inputs if NOT awaiting name input
                            if not self.awaiting_name_input:
                                if event.button == 0:  # A button - Restart
                                    self.state = "game"
                                    self.reset_game()
                                elif event.button == 1:  # B button - Menu
                                    self.state = "menu"
                                    self.menu_selection = 0
                        elif self.state == "level_up" and self.pending_level_ups:
                            current_player = self.pending_level_ups[0]
                            player_controller_id = current_player.player_num - 1
                            if event.joy == player_controller_id and event.button == 0:
                                self.apply_level_up_choice()

                        elif self.state == "enemy_upgrade_warning":
                            if event.button == 0:  # A button
                                self.state = "game"
                                self.wave += 1  # NOW increment the wave
                                self.generate_obstacles()
                                self.spawn_wave()
                                self.pending_enemy_upgrade = False
                    
                    # Controller D-pad
                    elif event.type == pygame.JOYHATMOTION:
                        if current_time - last_input_time > input_delay:
                            if self.state == "menu":
                                hat_value = event.value
                                if hat_value[1] == 1:  # D-pad Up
                                    self.menu_selection = (self.menu_selection - 1) % 4
                                    last_input_time = current_time
                                elif hat_value[1] == -1:  # D-pad Down
                                    self.menu_selection = (self.menu_selection + 1) % 4
                                    last_input_time = current_time
                            elif self.state == "high_scores":
                                # High scores navigation is now handled in HighScoreScreen.handle_events()
                                pass
                            elif self.state == "level_up" and self.pending_level_ups:
                                current_player = self.pending_level_ups[0]
                                player_controller_id = current_player.player_num - 1
                                if event.joy == player_controller_id:
                                    hat_value = event.value
                                    if hat_value[1] == 1:
                                        self.level_up_selection = (self.level_up_selection - 1) % 6
                                        last_input_time = current_time
                                    elif hat_value[1] == -1:
                                        self.level_up_selection = (self.level_up_selection + 1) % 6
                                        last_input_time = current_time
                    
                    # Controller analog sticks
                    elif event.type == pygame.JOYAXISMOTION:
                        if current_time - last_input_time > input_delay:
                            if self.state == "menu":
                                if event.axis == 1:  # Left stick Y-axis
                                    if event.value < -0.5:  # Up
                                        self.menu_selection = (self.menu_selection - 1) % 4
                                        last_input_time = current_time
                                    elif event.value > 0.5:  # Down
                                        self.menu_selection = (self.menu_selection + 1) % 4
                                        last_input_time = current_time
                            elif self.state == "high_scores":
                                if event.axis == 0:  # Left stick X-axis
                                    if event.value < -0.5:  # Left
                                        self.high_scores_page = (self.high_scores_page - 1) % 2
                                        last_input_time = current_time
                                    elif event.value > 0.5:  # Right
                                        self.high_scores_page = (self.high_scores_page + 1) % 2
                                        last_input_time = current_time
                            elif self.state == "level_up" and self.pending_level_ups:
                                current_player = self.pending_level_ups[0]
                                player_controller_id = current_player.player_num - 1
                                if event.joy == player_controller_id and event.axis == 1:
                                    if event.value < -0.5:
                                        self.level_up_selection = (self.level_up_selection - 1) % 6
                                        last_input_time = current_time
                                    elif event.value > 0.5:
                                        self.level_up_selection = (self.level_up_selection + 1) % 6
                                        last_input_time = current_time
            
            # Handle continuous input (only for game state)
            if self.state == "game":
                self.handle_input()
            
            # Update game state
            self.update()
            
            # Draw everything
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "game":
                self.draw_game()
            elif self.state == "game_over":
                self.draw_game_over()
            elif self.state == "level_up":
                self.draw_level_up()
            elif self.state == "enemy_upgrade_warning":
                self.draw_enemy_upgrade_warning()
            elif self.state == "high_scores":
                self.draw_high_scores()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()