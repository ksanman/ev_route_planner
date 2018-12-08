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

class NavigationAction(Enum):
    driving = 1
    charging = 2


class State:
    def __init__(self, time, battery_charge, location):
        #Omit this first, but this is for the terminal reward later. 
        self.time = time
        #The amount of charge in the battery at the location. 
        self.battery_charge = battery_charge
        #Index of the location in the environment list. 
        self.location = location

    def get_state(self):
        return tuple(self.time, self.battery_charge)


class EvRouteEnvironment:
    def __init__(self, end_time, battery_cap, startLocation = ['-111.8338','41.7370'], endLocation=['-109.5498','38.5733'], charger_radius=5, 
        route_from_file=False, chargers_from_file=False):
        print('Creating new environment')
        self.charger_database = db.ChargerDatabase()
        self.route_machine = router.Router()
        self.end_time = end_time
        self.battery_cap = battery_cap

        # #Create the database and populate it.
        # try:

        #     charger_file_io  = co.ChargerObjects()
        #     chargers = charger_file_io.get_us_charge_locations()
        #     #charger_database.create()
        #     #charger_database.insert(chargers)
        #     #charger_database.drop()
        # except Exception as e:
        #     print(e)

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

        # print('Getting nearest chargers')
        # i = 0
        # for waypoint in self.route_data['intersections']:
        #     data = self.charger_database.get_nearest_chargers(waypoint)

        #     for row in data:
        #         if row['id'] in self.nearest_chargers_dict.keys():
        #             continue

        #         addressInfo = co.AddressInfo(accessComments=row['accesscomments'], 
        #             addressLine1=row['addressline1'], 
        #             addressLine2=row['addressline2'],
        #             contactEmail=row['contactemail'],
        #             contactTelephone1=row['contacttelephone1'],
        #             contactTelephone2=row['contacttelephone2'],
        #             countryID=row['countryid'],
        #             distanceUnit=row['distanceunit'],
        #             ID=row['id'],
        #             lat=row['latitude'],
        #             long=row['longitude'],
        #             postcode=row['postcode'],
        #             relatedUrl=row['relatedurl'],
        #             state=row['stateorprovince'],
        #             title=row['title'],
        #             town=row['town'],
        #             distanceFromCurrentWaypoint=row['distancefromcurrentwaypoint'])

        #         self.nearest_chargers_dict[addressInfo.ID] = addressInfo
        #         i += 1

        print('Number of chargers along route: ', len(self.nearest_chargers))
        self.locations = list(range(0, len(self.nearest_chargers) - 1, 1))
        self.states = self.compute_states()
        #self.reveresed_chargers = self.reverse(self.nearest_chargers)

    def compute_states(self):
        states = []
        for stop in range(len(self.nearest_chargers)):
            for level in range(self.battery_cap):
                    states.append([stop, level])
        return states

    def get_random_state(self):
        b_states = [k for k in range(self.battery_cap)]
        s = random.sample(b_states,1)[0]
        return self.states.index([0, s])

    def reverse(self, dictionary):
        dict_items = list(dictionary.items())
        items = [item[1] for item in dict_items]
        items.reverse()
        return [s[1] for s in items]

    def display_route_in_browser(self):
        print('Displaying route.')
        self.route_machine.draw_route(self.route_data['route'], self.nearest_chargers)

    def get_next_state(self, current_state_index, action):
        done = False
        current_state = self.states[current_state_index]
        #current_waypoint_index = self.reveresed_chargers.index(current_state.location)
        current_waypoint = self.nearest_chargers[current_state[0]]
        current_waypoint_point = [current_waypoint.Latitude, current_waypoint.Longitude]

        if current_state[0] + 1 != len(self.nearest_chargers):
            #next_waypoint = self.reveresed_chargers[current_waypoint_index + 1]
            next_waypoint = self.nearest_chargers[current_state[0] + 1]
            next_waypoint_point = [next_waypoint.Latitude, next_waypoint.Longitude]
        else:
            done = True
            return self.states.index(current_state), current_state, 0, done

        distance = self.calculate_distance_between_points(current_waypoint_point, next_waypoint_point)
        new_battery = self.calculate_battery_loss(distance, action, current_state[1])
        #new_time = self.calculate_time_to_waypoint(current_state.time, distance)
        reward = self.calculate_reward(action, new_battery, new_battery - current_state[1])
        next_state = [current_state[0] + 1, new_battery]
        return self.states.index(next_state), next_state, reward, done
    
    def calculate_reward(self, action, battery_state, battery_charge_amount):
        if action == NavigationAction.driving:
            return (-1/(6 * math.pow(battery_state + 4, 3)+ 1))
        else:
	    #multiply the amount charged by $1.20 (average price of electricity
            if battery_state > 10:
                return -100
            return battery_charge_amount * 1.20

    #def calculate_time_to_waypoint(self, time, current_waypoint, next_waypoint):
    def calculate_time_to_waypoint(self, time, distance):
        time_to_travel = (distance /  45) *  60
        return time + datetime.timedelta(minutes = time_to_travel)
    
    def calculate_battery_loss(self, distance, action, current_battery):
        if action == NavigationAction.driving:
            return int(Decimal(str(current_battery - (distance / 5))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
        elif action == NavigationAction.charging & current_battery < 80:
            return current_battery + (10)
        else:
            return int(Decimal(str(current_battery + ((1/3.2) * math.pow(current_battery - 80,2) + 40))).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
            

    def calculate_distance_between_points(self, point_1, point_2):
        return geopy.distance.distance(point_1, point_2).miles

