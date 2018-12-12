import json
import polyline
import folium
import requests
import os
import webbrowser
import collections
import charger_database_manager
import charger_objects as co

class Router:
    def __init__(self):
        self.request_string = 'http://router.project-osrm.org/route/v1/driving/{0},{1};{2},{3}?overview=full&steps=true'
        self.charger_database = charger_database_manager.ChargerDatabase()
        self.route_filepath = 'data/route.txt'
        self.nearest_chargers_file = 'data/nearest_charger.json'
    
    def get_route(self, start, end):
        print('Getting route...')
        url_request = self.request_string.format(start[0], start[1], end[0], end[1])
        r = requests.get(url_request)
        c = r.content 
        my_json = c.decode('utf8').replace("'", '"')
        print('Route recieved.')
        # Load the JSON to a Python list & dump it back out as formatted JSON
        data = json.loads(my_json)
        self.save_to_file(data)
        return self.build_route(data)

    def get_road_distance_and_between_points(self, point1, point2):
        request = 'http://router.project-osrm.org/route/v1/driving/{0},{1};{2},{3}?overview=simplified'.format(point1[1], point1[0], point2[1], point2[0])
        r = requests.get(request)
        c = r.content 
        my_json = c.decode('utf8').replace("'", '"')
        data = json.loads(my_json)
        route = data["routes"][0]
        leg = route["legs"][0]
        distance = float(leg["distance"])
        return distance


    def draw_route(self, coordinates, charge_points):
        # Create the map and add the line
        print('Drawing route')
        m = folium.Map(location=[41.9, -97.3], zoom_start=4)
        my_PolyLine=folium.PolyLine(locations=coordinates,weight=5)
        m.add_child(my_PolyLine)

        for point in charge_points:
            folium.Marker(location=[point.lat, point.lon], popup=point.Title).add_to(m)

        filepath = 'data/map.html'
        m.save(filepath)
        webbrowser.open(filepath)

    def save_to_file(self,data):
        print('saving to file')
        with open(self.route_filepath, 'w') as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))

        print('route saved to ',self.route_filepath)

    def get_route_from_file(self):
        print('Loading route...')

        with open(self.route_filepath, 'r') as f:
        # Load the JSON to a Python list & dump it back out as formatted JSON
            data = json.loads(f.read())

        return self.build_route(data)

    def build_route(self, data):
        route = data["routes"][0]
        print('building route')
        #get the intersections along the route
        intersections = self.get_intersections(route)


        return {'route':polyline.decode(route['geometry']),'intersections':intersections}

    def get_intersections(self, data):
        intersections = []
        for l in data['legs']:
            for s in l['steps']:
                for i in s['intersections']:
                    location = i['location']
                    intersections.append([location[1], location[0]])

        return intersections


    def get_nearest_chargers(self, route):
        print('Getting nearest chargers')
        nearest_chargers_dict = {}
        nearest_chargers = []
        #i = 0
        for waypoint in route['intersections']:
            data = self.charger_database.get_nearest_chargers(waypoint)

            for row in data:
                if row['id'] in nearest_chargers_dict.keys():
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

                nearest_chargers_dict[addressInfo.ID] = addressInfo
                nearest_chargers.append(addressInfo)
                #i += 1

        self.save_nearest_chargers(nearest_chargers)
        return nearest_chargers
        
    def save_nearest_chargers(self, nearest_chargers):
        with open(self.nearest_chargers_file, 'w') as f:
            f.write(json.dumps(nearest_chargers, default=co.to_json, indent=4, sort_keys=False))

    def get_nearest_chargers_from_file(self):
        with open(self.nearest_chargers_file, 'r') as f:
            data = json.loads( f.read())
            addresses = []
            for c in data:
                addresses.append(co.address_decoder(c))

        return addresses