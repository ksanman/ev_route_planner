"""
Utility file used to test a small environment against the value iteration algorithm.
"""

from enum import Enum
from math import pow
import geopy.distance
import random
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta

class NavigationAction(Enum):
    """
    Enumeration of the action space.
    """
    driving = 0
    charging = 1

class Waypoint:
    """
    Represents a waypoint along the route. 
    """
    def __init__(self, id, lat, lon, has_charger=True):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.has_charger = has_charger

class TestEnv:
    """
    Test environment class used to test value iteration algorithm.
    """
    def __init__(self):
        self.end = 3
        self.time_max = 8
        self.T = range(self.time_max+1)
        self.batt_max = 10
        self.B = range(self.batt_max+1)
        self.route = [Waypoint(0, 41.735210, -111.834860), Waypoint(1,41.772030,-111.813440),
            Waypoint(2,41.799020,-111.816740), Waypoint(3, 41.836510, -111.832690), 
            Waypoint(4, 41.922720, -111.814330, False)]

        self.states = self.compute_states()
        self.actions = [NavigationAction.driving, NavigationAction.charging]

    def get_random_state(self):
        state_indexes = range(len(self.states))
        return random.sample(state_indexes, 1)[0]
        
    # Enumerate states
    def compute_states(self):
        states = []
        for t in self.T:
            for level in self.B:
                for stop in range(len(self.route)):
                    states.append([t, level, stop])
        return states

    def calculate_terminal_reward(self, state_index):
        state = self.states[state_index]
        w = self.route[state[2]]
        battery_level = state[1]
        time_reward = 6 - state[0]
        battery_reward = -pow((1/5) * battery_level - 10, 2) if battery_level < 50 else 0
        if w.has_charger:
            return time_reward
        else:
            return time_reward + battery_reward

    def act(self, state, action):
        #If we are at the last point, the end has been reached. 
        if(self.states[state][2] == len(self.route) - 1):
            return (state, self.calculate_terminal_reward(state), True)

        if action == NavigationAction.charging.value:
            return self.charge_act(state)
        else:
            return self.drive_act(state)

    def charge_act(self, state):
        cur_state = self.states[state]
        new_time = cur_state[0] + 1
        new_batt = self.calculate_battery_level(cur_state[1])
        new_loc = cur_state[2]
        reward = self.calculate_charge_reward(new_batt)
        done = False
        if new_batt > self.batt_max:
            done = True
        if new_time > self.time_max:
            done = True
        
        return (state, reward, done) if done else (self.states.index([new_time, new_batt, new_loc]), reward, done)

    def drive_act(self, state):
        cur_state = self.states[state]
        current_location = self.route[cur_state[2]]
        next_location = self.route[cur_state[2] + 1]
        distance_traveled = self.calculate_distance_between_points([current_location.lat, current_location.lon],
            [next_location.lat, next_location.lon])
        
        new_battery_level = self.calculate_battery_consumption(cur_state[1], distance_traveled)
        new_time = self.calculate_new_time(cur_state[0], distance_traveled)
        done = False
        reward = 0
        if new_battery_level < 0:
            new_battery_level =  0
            reward -= 100
            done = True
        else:
            reward = self.calculate_driving_reward(new_battery_level)

        if new_time > self.time_max:
            new_time = self.time_max - 1
            reward -= 100
        
        return (state, reward, done) if done else (self.states.index([new_time, new_battery_level, next_location.id]), reward, done)

    def get_instant_reward_and_next_state(self, state_index, action):
        """ Returns the instant reward for the current state, and
        computes the next state given an action. For use with 
        value iteration. """
        state = self.states[state_index]

        if action == NavigationAction.charging.value:
            return self.calculate_charge_instant_reward(state)
        else:
            return self.calculate_driving_instant_reward(state)

    # Calculates the reward for charging a vehicle. 
    # The reward is the amount charged * the price for electricity
    # Initial case (For 15 min) is 1.6 ( 10 points in 1.5 hour)
    def calculate_charge_instant_reward(self, state):
        if state[2] == len(self.route) - 1:
            state_index = self.states.index(state)
            return state_index, self.calculate_terminal_reward(state_index)

        # Don't charge over 100%
        reward = self.calculate_charge_reward(state[1])
        #large negative reward for going over the expected time + extra time
        if state[0] + 1 >= self.time_max:
            next_time = state[0]
            reward += -1000
        else:
            next_time = state[0] + 1
        
        next_battery_level = self.calculate_battery_level(state[1]) if state[1] < self.batt_max - 1 else state[1]

        #Don't charge over 100 percent
        if next_battery_level > self.batt_max:
            next_battery_level = self.batt_max
            reward -= 100

        next_location = state[2]
        return self.states.index([next_time, next_battery_level, next_location]), reward

    def calculate_charge_reward(self, batt_level):
        return -(1.6 * 1.20) if batt_level < self.batt_max else -100

    def calculate_battery_level(self, batt_state):
        return int(Decimal(batt_state + 1.6).quantize(Decimal('0'), rounding=ROUND_HALF_UP))

    # The driving instant reward is 0 if the battery is over 20% during travel.
    # Otherwise, there is a negative reward.
    def calculate_driving_instant_reward(self, state):
        if state[2]  == len(self.route) - 1:
            state_index = self.states.index(state)
            return state_index, self.calculate_terminal_reward(state_index)

        reward = self.calculate_driving_reward(state[1])

        current_location = self.route[state[2]]
        next_location = self.route[state[2] + 1]
        distance_traveled = self.calculate_distance_between_points([current_location.lat, current_location.lon],
            [next_location.lat, next_location.lon])
        
        new_battery_level = self.calculate_battery_consumption(state[1], distance_traveled)
        # make sure the battery level doesn't go below zero. 
        # give a large negative reward for running out. 
        if new_battery_level < 0:
            new_battery_level =  0
            reward += -100
            
        if state[0] + 1 >= self.time_max:
            new_time = state[0]
            reward += -1000
        else:
            new_time = self.calculate_new_time(state[0], distance_traveled)

        return self.states.index([new_time, new_battery_level, state[2] + 1]), reward

    def calculate_battery_consumption(self, cur_battery_level, distance):
        battery_consumed = distance / 5
        return int(Decimal(cur_battery_level - battery_consumed).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
        
    def calculate_driving_reward(self, battery_state):
        return 0 if battery_state >  self.batt_max * (1/5) else -(pow((1/2) * battery_state - 10, 2))

    # calculate the time to go x distance. .75 is 45 mph in mp minute
    def calculate_new_time(self, cur_time, distance):
        time_to_travel = self.round_to_nearest_quarter_hour(distance / .75)
        new_time = cur_time + int((time_to_travel / 60) * 4)
        return new_time

    def round_to_nearest_quarter_hour(self, t):
        return 15 * int(Decimal(t/15).quantize(Decimal('0'), ROUND_HALF_UP))


    def calculate_distance_between_points(self, point_1, point_2):
        return geopy.distance.distance(point_1, point_2).miles