import ev_route_environment as ev_route_environment
import datetime
from datetime import datetime as dt
#create a new environment
time = dt.strptime('16:00', '%H:%M')
env = ev_route_environment.EvRouteEnvironment(time,150, route_from_file=True)

#create the action space
action_space = ev_route_environment.NavigationAction

#test getting the next action.
action = action_space.driving
start_state = env.initial_state
next_state,reward = env.get_next_state(start_state, action)
print(next_state.time, next_state.battery_charge, next_state.location.Title, reward)