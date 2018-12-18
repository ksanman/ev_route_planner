import router
import charger_database_manager as db
import charger_objects as co
from time import time as t
import collections
import geopy.distance
import datetime
import math
from enum import Enum
import random
from decimal import Decimal
from decimal import ROUND_HALF_UP

METERS_TO_MILES = 1609.344

class NavigationAction(Enum):
    """
    Enumeration of the action space. 
    """
    driving = 0
    charging = 1

class Waypoint:
    """
    Defines a waypoint along the route. Includes information about the charger and information about
    the trip from the previous waypoint
    """
    def __init__(self, id, lat, lon,distance_from_previous_node, time_from_previous_node, 
        energy_to_node, is_charger=True, charge_rate = 10, charge_price = 0.20, title=None):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.is_charger = is_charger
        self.charge_rate = charge_rate
        self.charge_price = charge_price
        self.distance_from_previous_node = distance_from_previous_node
        self.time_from_previous_node = time_from_previous_node
        self.energy_to_node = energy_to_node
        self.Title = title

class EvRouteEnvironment:
    """
    Used to model the route from a start point to a destination. Calculates all distances and travel times. 
    Has functions to model rewards at different states. 
    """
    def __init__(self, trip_time=6, extra_time = 2, battery_cap=100, average_mpkwh = 3, startLocation = ['-111.8338','41.7370'], 
        endLocation=['-109.5498','38.5733'], charger_radius=5, route_from_file=False, 
        chargers_from_file=False):
        """
        Create a new environment. Takes the expected trip time, a buffer of time, the capacity of the battery, 
        the mpkwh for the vehicle, the start location, the end location, and the radius to search for chargers 
        along the route. It also includes flags for loading a route and nearest chargers from a file instead
        of sending requests to the OSRM api and database. If these flags are true, the route and nearest charger
        files must be of the same route. 
        """

        print('Creating new environment')
        self.charger_database = db.ChargerDatabase()
        self.route_machine = router.Router()
        self.expected_time = trip_time * 4
        self.T = (trip_time + extra_time) * 4
        self.B = battery_cap
        self.average_mpkhw = average_mpkwh
        self.final_chargers = []

        if route_from_file:
            #Get a route from a file. 
            self.route_data = self.route_machine.get_route_from_file()
        else:
            #Get a route using the api call.
            self.route_data = self.route_machine.get_route(startLocation, endLocation)

        print('route points: ', len(self.route_data['route']))
        print('intersections: ',len(self.route_data['intersections']))
        if chargers_from_file:
            self.nearest_chargers = self.route_machine.get_nearest_chargers_from_file()
        else:
            self.nearest_chargers = self.route_machine.get_nearest_chargers(self.route_data)

        print('Number of chargers along route: ', len(self.nearest_chargers))

        print('Building route model')
        start_point = self.route_data['route'][0]
        end_point = self.route_data['route'][-1]
        self.route = self.build_route(start_point, end_point)
        self.states = self.compute_states()
        self.actions = [NavigationAction.driving, NavigationAction.charging]

    def build_route(self, start_point, end_point):
        """ Constructs a route of enumerated locations for Makorav Learning. 
        Each stop represents a charger location along the route. 
        The last waypoint is the end point, which may or may not
        have a charger. 
        """
        route = []
        id = 1
        route.append(Waypoint(id, start_point[0], start_point[1], 0,0,0, False))
        for charger in self.nearest_chargers:
            previous_route= route[-1]
            distance_to_node = self.calculate_distance_and_time_between_points([previous_route.lat,previous_route.lon],[charger.Latitude, charger.Longitude])
            time_to_node = self.calculate_new_time_after_distance(0, distance_to_node)
            energy_to_node = self.calculate_battery_level_from_distance_traveled(0, distance_to_node)
            route.append(Waypoint(id, charger.Latitude, charger.Longitude, 
            distance_from_previous_node=distance_to_node,time_from_previous_node= time_to_node, 
            energy_to_node= energy_to_node,is_charger=True,title= charger.Title))

            id += 1

        previous_route = route[-1]
        distance_to_node = self.calculate_distance_and_time_between_points([previous_route.lat,previous_route.lon],[end_point[0], end_point[1]])
        time_to_node = self.calculate_new_time_after_distance(0, distance_to_node)
        energy_to_node = self.calculate_battery_level_from_distance_traveled(0, distance_to_node)
        route.append(Waypoint(id, end_point[0], end_point[1], 
            distance_to_node,time_to_node, energy_to_node, False))
        return route

    def compute_states(self):
        """ Compute every possible state and enumerate in a state table for easy access."""
        states = []
        # Add 1 to account for the destination.
        for stop in range(len(self.nearest_chargers) + 2):
            for t in range(self.T):
                for level in range(self.B):
                    states.append([t, level, stop])
        
        return states

    def get_random_state(self):
        """Get a random state """
        return self.get_index_from_state(random.sample(self.states, 1)[0])
    
    def get_state_from_index(self, index):
        """ Returns a state from the states table"""
        return self.states[index]

    def get_index_from_state(self, state):
        """ Returns the index for a state from the state table. """
        return self.states.index(state)

    def get_waypoint_from_index(self, index):
        """ Returns the waypoint from the route object for the 
        passed in index."""
        return self.route[index]

    def add_waypoint_charger_to_final_route(self, state_index):
        """ Gets a waypoint add adds it to the finally route that will be 
            displayed at the end. """
        state = self.get_state_from_index(state_index)
        waypoint = self.get_waypoint_from_index(state[2])
        if waypoint not in self.final_chargers:
            self.final_chargers.append(waypoint)

    def display_route_in_browser(self):
        """ Generate an HTML map of the route for browser display."""
        print('Displaying route.')
        self.route_machine.draw_route(self.route_data['route'], self.final_chargers)

    def calculate_terminal_reward(self, state_index):
        """ Calculates the terminal reward for state s.
        The terminal reward is achieved by reaching the last location. 
        If the last location has a charger, the reward will be 0. 
        If the last location does not have a charger, the reward will be
        calculated based on the battery percentage left. 
        A reward will also be calculated based on the time the algorithm 
        arrived at the terminus. Postive for arriving early, negative for arriving late. 
        """
        state = self.get_state_from_index(state_index)
        w = self.get_waypoint_from_index(state[2])
        battery_level = state[1]
        time_reward = self.expected_time - state[0]
        battery_reward = -pow((1/5) * ((battery_level/self.B)*100) - 10, 2) if ((battery_level/self.B)*100) < 50 else 0
        if w.is_charger:
            return time_reward
        else:
            return time_reward + battery_reward

    def get_instant_reward_and_next_state(self, state_index, action):
        """ Returns the instant reward for the current state, and
        computes the next state given an action. For use with 
        value iteration. """

        state = self.get_state_from_index(state_index)

        if state[2] == len(self.route) - 1:
            return state_index, self.calculate_terminal_reward(state_index)

        if action == NavigationAction.charging.value:
            return self.calculate_charging_instant_reward(state)
        else:
            return self.calculate_driving_instant_reward(state)

    def calculate_charging_instant_reward(self, state):
        """ Calculates the instant reward for charging in the given state. 
        Returns the reward and the next state."""

        w = self.get_waypoint_from_index(state[2])
        reward = self.calculate_charging_reward(state[1], w.charge_rate, w.charge_price)
       
        if state[2] == 0:
            reward += -1000
        # Give a large negative reward for going over the expected time + extra time
        if state[0] + 1 >= self.T:
            next_time = state[0]
            reward += -1000
        else:
            next_time = state[0] + 1
        
        next_battery_level = self.calculate_battery_level_after_charging(state[1], w.charge_rate) if state[1] < self.B - 1 else state[1]

        if next_battery_level >= self.B:
            next_battery_level = self.B - 1
            reward -= 100

        return self.get_index_from_state([next_time, next_battery_level, w.id]), reward

    def calculate_driving_instant_reward(self, state):
        """ Calculates the instant reward for driving in the given state. 
        Returns the reward and the next state."""
        reward = self.calculate_driving_reward(state[1])
        next_location = self.get_waypoint_from_index(state[2] + 1)
        
        new_battery_level = state[1] + next_location.energy_to_node
        
        # make sure the battery level doesn't go below zero. 
        # give a large negative reward for running out. 
        if new_battery_level < 1:
            new_battery_level =  0
            reward += -1000
            
        new_time = state[0] + next_location.time_from_previous_node

        if new_time >= self.T:
            new_time = state[0]
            reward += -1000

        return self.get_index_from_state([new_time, new_battery_level, state[2] + 1]), reward

    def act(self, state_index, action):
        """ Perform a an action, generate the next state, and compute the reward for 
        moving to the next state."""

        # If we are in the final state, calculate the terminal reward
        if(self.get_state_from_index(state_index)[2] == len(self.route) - 1):
            return (state_index, self.calculate_terminal_reward(state_index), True)

        has_charger = self.get_waypoint_from_index(self.get_state_from_index(state_index)[2]).is_charger

        if action == NavigationAction.charging.value:
            if has_charger:
                return self.charge(state_index)
            else:
                return (state_index, -1000, False)
        else:
            return self.drive(state_index)


    def charge(self, state_index):
        """ Compute the next state and reward after charging in the passed in state. """
        done = False
        current_state = self.get_state_from_index(state_index)
        current_waypoint = self.get_waypoint_from_index(current_state[2])

        new_time = current_state[0] + 1
        new_batt = self.calculate_battery_level_after_charging(current_state[1], current_waypoint.charge_rate)
        new_loc = current_state[2]

        reward = self.calculate_charging_reward(new_batt, current_waypoint.charge_rate, current_waypoint.charge_price)

        if new_batt >= self.B:
            done = True
            new_batt = self.B - 1
        if new_time > self.T:
            done = True
            new_time = self.T - 1

        return (state_index, reward, done) if done else (self.get_index_from_state([new_time, new_batt, new_loc]), reward, done)

    def drive(self, state_index):
        """  Compute the next state and reward after driving in the passed in state. """
        state = self.states[state_index]
        next_location = self.route[state[2] + 1]
        
        new_battery_level = state[1] + next_location.energy_to_node
        new_time = state[0] + next_location.time_from_previous_node
        done = False
        reward = 0
        if new_battery_level < 1:
            new_battery_level =  0
            reward -= 100
            done = True
        else:
            reward = self.calculate_driving_reward(new_battery_level)

        if new_time >= self.T:
            new_time = self.T - 1
            reward -= 100
            done = True
        
        return (self.get_index_from_state(state), reward, done) if done else (self.get_index_from_state([new_time, new_battery_level, next_location.id]), reward, done)

    def calculate_battery_level_after_charging(self, battery_level, charge_rate):
        """ Calculates the battery level after being on a charger for 15 minutes. 
        For the initial project, the value of 1.6 kwh (40kwh for a 1 hour charge) charge average 
        will be used. The modeled function loosly represents real chargers, that slow down 
        once the battery nears capacity. """
        if battery_level < self.B * .80:
            new_battery_level = int(Decimal(battery_level + charge_rate).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
        else:
            new_battery_level = battery_level + int(Decimal((1/3.2) * (pow((battery_level - 80)/4, 2) + 40))
                .quantize(Decimal('0'), rounding=ROUND_HALF_UP))

        return new_battery_level

    def calculate_charging_reward(self, battery_level, charge_rate, charger_price):
        """ Calculates the reward for charging a battery to a given level. 
            If the battery level is below the max, the reward is the negative
            price for a 15 minute charge. Otherwise the reward is -100. 
        """
        return -(charge_rate * charger_price) if battery_level < self.B else -100

    def calculate_driving_reward(self, battery_state):
        """ Calculates the reward for driving a certain distance. 
        The reward is computed using the final battery state. If the state is above 20%, return 0. 
        Other wise return a negative reward. If the state is 0, return -100. """
        return 0 if ((battery_state/self.B)*100) >  self.B * (1/2) else -(pow((1/5) * ((battery_state/self.B)*100) - 10, 2))

    def calculate_battery_level_from_distance_traveled(self, current_battery_level, distance):
        """ Calculates the battery lost over the given distance and returns the new battery level. """
        battery_consumed = distance / self.average_mpkhw
        return int(Decimal(current_battery_level - battery_consumed).quantize(Decimal('0'), rounding=ROUND_HALF_UP))

    def calculate_new_time_after_distance(self, current_time, distance):
        """ Calculates the time to travel the given distance. """
        time_to_travel = self.round_to_nearest_quarter_hour(distance / 1.08)
        new_time = current_time + int((time_to_travel / 60) * 4)
        return new_time

    def round_to_nearest_quarter_hour(self, t):
        """ Round the given time t to the nearest quater hour for enumeration. """
        return 15 * int(Decimal(t/15).quantize(Decimal('0'), ROUND_HALF_UP))

    def calculate_distance_and_time_between_points(self, point_1, point_2):
        """ Calculates the distance traveled between two lat/long points using the geopu library.
        This will be replaced by calculating the distance between intersections using OSRM on the server.
        The latter step is very involved for this simple demonstration. """
        distance = self.route_machine.get_road_distance_and_between_points(point_1, point_2)
        return distance/ METERS_TO_MILES
        

