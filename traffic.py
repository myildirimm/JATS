import math
import pygame
import random
import sys
import imageio
import numpy as np  # Import numpy for array manipulation

# Initialize Pygame
pygame.init()

# Car settings
CAR_WIDTH = 50
CAR_HEIGHT = 30
CAR_SPEED = 5
SAFE_DISTANCE = 50  # Minimum distance between cars

# Lane settings
NUM_LANES = 3
LANE_HEIGHT = CAR_HEIGHT + 10  # Lane height based on vehicle height
TOTAL_LANES_HEIGHT = LANE_HEIGHT * NUM_LANES

# Screen dimensions
SCREEN_WIDTH = 1400  # Width remains the same
SCREEN_HEIGHT = TOTAL_LANES_HEIGHT  # Height adjusted to fit lanes exactly

# Lane positions
LANES = [LANE_HEIGHT * i + LANE_HEIGHT // 2 for i in range(NUM_LANES)]

# Colors
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)
GREEN = (0, 255, 0)
RED = (255, 0, 0)

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("JATS:Just Another Traffic Simulation")

# Clock object to control the frame rate
clock = pygame.time.Clock()

# Car class
class Car(pygame.sprite.Sprite):
    def __init__(self, lane, x):
        super().__init__()
        self.image = pygame.Surface((CAR_WIDTH, CAR_HEIGHT))
        self.image.fill(random.choice([RED]))
        self.rect = self.image.get_rect()
        self.rect.centery = LANES[lane]
        self.rect.x = x
        self.speed = CAR_SPEED + random.randint(-2, 2)
        self.lane = lane

    def update(self, car_group):
        # Check for cars ahead in the same lane
        cars_ahead = [
            car for car in car_group
            if car.lane == self.lane and car.rect.x > self.rect.x
        ]
        if cars_ahead:
            # Find the closest car ahead
            closest_car = min(cars_ahead, key=lambda car: car.rect.x)
            distance = closest_car.rect.x - self.rect.x - CAR_WIDTH
            if distance < SAFE_DISTANCE:
                # Adjust speed to maintain safe distance
                self.speed = max(0, closest_car.speed - 1)
            else:
                # Accelerate back to original speed if possible
                if self.speed < CAR_SPEED:
                    self.speed += 0.1
        else:
            # No cars ahead, proceed at normal speed
            if self.speed < CAR_SPEED:
                self.speed += 0.1

        self.rect.x += self.speed
        if self.rect.x > SCREEN_WIDTH:
            self.kill()

# GreenCar class with IDM and MOBIL implementation
class GreenCar(Car):
    def __init__(self, lane, x):
        super().__init__(lane, x)
        self.image.fill(GREEN)
        # IDM Parameters
        self.desired_speed = 20  # Desired velocity (v0)
        self.acceleration = 0.5  # Maximum acceleration (a0)
        self.braking = 3.0  # Comfortable braking deceleration (b)
        self.desired_time_headway = 1.5  # Desired time headway (T)
        self.min_distance = 60  # Minimum distance (s0)
        self.safe_lane_change_threshold = 0.005  # Lower threshold for more frequent lane changes
        self.random_lane_change_factor = 0.6  # Add some randomness to encourage lane changes

    def idm_acceleration(self, distance, speed_diff):
        """
        Calculates the IDM acceleration for the green car.
        
        distance: The distance to the vehicle ahead.
        speed_diff: The difference in speed between the green car and the vehicle ahead.
        """
        # Ensure that speed_diff is properly calculated
        current_speed = self.speed  # Use the current speed of the vehicle

        # s_star: dynamic desired distance
        s_star = self.min_distance + current_speed * self.desired_time_headway + (current_speed * speed_diff) / (2 * math.sqrt(self.acceleration * self.braking))
        
        if distance <= 0:
            # If distance is zero or negative, we apply full braking
            return -self.braking
        else:
            # IDM formula for acceleration
            return self.acceleration * (1 - (current_speed / self.desired_speed) ** 4 - (s_star / distance) ** 2)


    def safety_check(self, car_group, target_lane):
        # Ensure there is no car close enough behind in the target lane
        cars_behind = [
            car for car in car_group
            if car.lane == target_lane and car.rect.x < self.rect.x
        ]
        if cars_behind:
            closest_car_behind = max(cars_behind, key=lambda car: car.rect.x)
            distance = self.rect.x - closest_car_behind.rect.x - CAR_WIDTH
            return distance >= SAFE_DISTANCE
        return True

    def mobil_lane_change(self, car_group):
        # Evaluate if a lane change to left or right is beneficial
        current_lane = self.lane
        best_lane = current_lane
        best_acceleration_gain = 0

        # Calculate the current acceleration in the current lane using IDM
        cars_ahead_current_lane = [
            car for car in car_group
            if car.lane == current_lane and car.rect.x > self.rect.x
        ]
        
        if cars_ahead_current_lane:
            closest_car_current_lane = min(cars_ahead_current_lane, key=lambda car: car.rect.x)
            distance_current_lane = closest_car_current_lane.rect.x - self.rect.x - CAR_WIDTH
            speed_diff_current_lane = self.speed - closest_car_current_lane.speed
            current_acceleration = self.idm_acceleration(distance_current_lane, speed_diff_current_lane)
        else:
            # No cars ahead, so use max acceleration in current lane
            current_acceleration = self.acceleration

        # Loop through potential target lanes (left and right)
        for target_lane in [current_lane - 1, current_lane + 1]:
            if 0 <= target_lane < NUM_LANES and self.safety_check(car_group, target_lane):
                # Calculate the potential acceleration in the target lane
                cars_ahead_target_lane = [
                    car for car in car_group
                    if car.lane == target_lane and car.rect.x > self.rect.x
                ]
                if cars_ahead_target_lane:
                    closest_car_target_lane = min(cars_ahead_target_lane, key=lambda car: car.rect.x)
                    distance_target_lane = closest_car_target_lane.rect.x - self.rect.x - CAR_WIDTH
                    speed_diff_target_lane = self.speed - closest_car_target_lane.speed
                    potential_acceleration = self.idm_acceleration(distance_target_lane, speed_diff_target_lane)
                else:
                    # No cars ahead in the target lane, assume max acceleration
                    potential_acceleration = self.acceleration

                # Compare with the current lane acceleration
                acceleration_gain = potential_acceleration - current_acceleration

                # Choose the lane with the best improvement
                if acceleration_gain > best_acceleration_gain:
                    best_acceleration_gain = acceleration_gain
                    best_lane = target_lane

        # Apply lane change if the gain is significant and safe
        if best_lane != current_lane and (best_acceleration_gain > self.safe_lane_change_threshold or random.random() < self.random_lane_change_factor):
            self.lane = best_lane
            self.rect.centery = LANES[self.lane]


    def update(self, car_group):
        cars_ahead = [car for car in car_group if car.lane == self.lane and car.rect.x > self.rect.x]
        if cars_ahead:
            closest_car = min(cars_ahead, key=lambda car: car.rect.x)
            distance = closest_car.rect.x - self.rect.x - CAR_WIDTH
            speed_diff = self.speed - closest_car.speed
            acceleration = self.idm_acceleration(distance, speed_diff)
            self.speed = max(0, self.speed + acceleration)
        else:
            if self.speed < self.desired_speed:
                self.speed += 0.1

        # Attempt to change lane based on MOBIL
        self.mobil_lane_change(car_group)

        # Update the car's position
        self.rect.x += self.speed
        if self.rect.x > SCREEN_WIDTH:
            self.kill()

# Sprite groups
car_group = pygame.sprite.Group()

# Spawn event
SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_EVENT, 400)  # Spawn a car every 0.4 seconds

def draw_lanes():
    for i in range(1, NUM_LANES):
        y = LANE_HEIGHT * i
        pygame.draw.line(screen, WHITE, (0, y), (SCREEN_WIDTH, y), 2)

def save_frame(frames, screen):
    # Convert the screen to an array and append to the frame list
    frame = pygame.surfarray.array3d(screen)
    # Transpose the frame to match the correct orientation (swap axes)
    frame = np.transpose(frame, (1, 0, 2))
    frames.append(frame)

def main():
    running = True
    frames = []  # List to store frames for GIF

    while running:
        clock.tick(60)  # Limit to 60 FPS
        screen.fill(GRAY)
        draw_lanes()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == SPAWN_EVENT:
                lane = random.randint(0, NUM_LANES - 1)
                if random.random() < 0.4:  # % chance to spawn the green car
                    car = GreenCar(lane, -CAR_WIDTH)
                else:
                    car = Car(lane, -CAR_WIDTH)
                car_group.add(car)

        car_group.update(car_group)
        car_group.draw(screen)
        pygame.display.flip()

        # Capture the frame after each update
        #save_frame(frames, screen)

    # Save the frames to a GIF file
    imageio.mimsave('traffic_simulation.gif', frames, fps=30)


    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
