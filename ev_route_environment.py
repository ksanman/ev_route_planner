import router
import charger_database_manager as db
import charger_objects as co
from time import time as t
import collections
import geopy.distance
import datetime
import math
from enum import Enum

class NavigationAction(Enum):
    driving = 1 
    charging = 2


class State:
    def __init__(self, time, battery_charge, location):
        self.time = time
        self.battery_charge = battery_charge
        self.location = location

    def get_state(self):
        return tuple(self.time, self.battery_charge)


class EvRouteEnvironment:
    def __init__(self, end_time, start_charge, startLocation = ['-111.8338','41.7370'], endLocation=['-109.5498','38.5733'], charger_radius=5, 
        route_from_file=False, filepath='data/logan_to_moab.txt'):
        print('Creating new environment')
        self.charger_database = db.ChargerDatabase()
        self.route_machine = router.Router()
        self.end_time = end_time
        self.start_charge = start_charge
        self.battery_cap = 100

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
            if not filepath:
                raise 'Loading a route from a file requires a file path.'
            #Get a route from a file. 
            self.route_data = self.route_machine.get_route_from_file(filepath)
        else:
            #Get a route using the api call.
            self.route_data = self.route_machine.get_route(startLocation, endLocation, filepath)

        print('route points: ', len(self.route_data['route']))
        print('intersections: ',len(self.route_data['intersections']))
        self.nearest_chargers = {}

        print('Getting nearest chargers')
        i = 0
        for waypoint in self.route_data['intersections']:
            data = self.charger_database.get_nearest_chargers(waypoint)

            for row in data:
                if row['id'] in self.nearest_chargers.keys():
                    continue

                addressInfo = co.AddressInfo(accessComments=row['accesscomments'], 
                    addressLine1=row['addressline1'], 
                    addressLine2=row['addressline2'],
                    contactEmail=row['contactemail'],
                    contactTelephone1=row['contacttelephone1'],
                    contactTelephone2=row['contacttelephone2'],
                    countryID=row['countryid'],
                    distanceUnit=row['distanceunit'],
                    ID=row['id'],
                    lat=row['latitude'],
                    long=row['longitude'],
                    postcode=row['postcode'],
                    relatedUrl=row['relatedurl'],
                    state=row['stateorprovince'],
                    title=row['title'],
                    town=row['town'],
                    distanceFromCurrentWaypoint=row['distancefromcurrentwaypoint'])

                self.nearest_chargers[addressInfo.ID] = [i, addressInfo]
                i += 1

        print('Number of chargers along route: ', len(self.nearest_chargers))
        self.reveresed_chargers = self.reverse(self.nearest_chargers)
        self.initial_state = State(self.end_time, 0, self.reveresed_chargers[0])

    def reverse(self, dictionary):
        dict_items = list(dictionary.items())
        items = [item[1] for item in dict_items]
        items.reverse()
        return [s[1] for s in items]

    def display_route_in_browser(self):
        print('Displaying route.')
        self.route_machine.draw_route(self.route_data['route'], [v[1] for v in self.nearest_chargers.values()])

    def get_next_state(self, current_state, action):
        current_waypoint_index = self.reveresed_chargers.index(current_state.location)
        current_waypoint_point = [current_state.location.Latitude, current_state.location.Longitude]

        next_waypoint = self.reveresed_chargers[current_waypoint_index + 1]
        next_waypoint_point = [next_waypoint.Latitude, next_waypoint.Longitude]

        distance = self.calculate_distance_between_points(current_waypoint_point, next_waypoint_point)
        battery_loss = self.calculate_battery_loss(distance)
        new_battery = current_state.battery_charge + battery_loss
        new_time = self.calculate_time_to_waypoint(current_state.time, distance)
        reward = self.calculate_reward(action, new_battery, battery_loss)
        return State(new_time, new_battery, next_waypoint), reward
    
    def calculate_reward(self, action, battery_state, battery_charge_amount):
        if action == NavigationAction.driving:
            return (-1/(6 * math.pow(battery_state + 4, 3)+ 1))
        else:
	    #multiply the amount charged by $1.20 (average price of electricity
            return battery_charge_amount * 1.20

    #def calculate_time_to_waypoint(self, time, current_waypoint, next_waypoint):
    def calculate_time_to_waypoint(self, time, distance):
        time_to_travel = (distance /  45) *  60
        return time + datetime.timedelta(minutes = time_to_travel)
    
    def calculate_battery_loss(self, distance):
        return distance / 5

    def calculate_distance_between_points(self, point_1, point_2):
        return geopy.distance.distance(point_1, point_2).miles

