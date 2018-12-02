import json
import polyline
import folium
import requests
import os
import webbrowser
import collections
class Router:
    def __init__(self):
        self.request_string = 'http://router.project-osrm.org/route/v1/driving/{0},{1};{2},{3}?overview=full&steps=true'
        
    
    def get_route(self, start, end,filepath):
        print('Getting route...')
        url_request = self.request_string.format(start[0], start[1], end[0], end[1])
        r = requests.get(url_request)
        c = r.content 
        my_json = c.decode('utf8').replace("'", '"')
        print('Route recieved.')
        # Load the JSON to a Python list & dump it back out as formatted JSON
        data = json.loads(my_json)
        return self.build_route(data)

    def draw_route(self, coordinates, charge_points):
        # Create the map and add the line
        print('Drawing route')
        m = folium.Map(location=[41.9, -97.3], zoom_start=4)
        my_PolyLine=folium.PolyLine(locations=coordinates,weight=5)
        m.add_child(my_PolyLine)

        for point in charge_points:
            folium.Marker(location=[point.Latitude, point.Longitude], popup=point.Title).add_to(m)

        filepath = 'data/map.html'
        m.save(filepath)
        webbrowser.open(filepath)

    def save_to_file(self,data,filename):
        print('saving to file')
        with open(filename, 'w') as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))

        print('route saved to ',filename)

    def get_route_from_file(self, filename='data/logan_to_moab.txt'):
        print('Loading route...')

        with open(filename, 'r') as f:
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
        steps = []
        intersections = []
        for l in data['legs']:
            for s in l['steps']:
                for i in s['intersections']:
                    location = i['location']
                    intersections.append([location[1], location[0]])

        return intersections