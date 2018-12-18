"""

Author: Kody Sanchez
Class: CS5890 - Machine Learning and Clean Energy 
Instructor: Dr. Nicholas Flann
Description: A program used to find optimal charging points on any route in Utah. 
The program uses value iteration to find an optimal policy given trip time, start and end point, 
and battery level. 

"""

import ev_route_environment as ev_route_environment
import datetime
from datetime import datetime as dt
import numpy as np
import random
import test_env
import math
from time import time

TEST_RUNS = 1

#create a new environment
env = ev_route_environment.EvRouteEnvironment(trip_time=8, extra_time = 2,endLocation=['-113.5684','37.0965'],battery_cap=40 ,route_from_file=False, chargers_from_file=False)

max_time = env.T
battery_max = env.B
last_waypoint = env.get_waypoint_from_index(-1).id - 1
actions = range(len(env.actions))

end_state_start = max_time*battery_max*last_waypoint

print('Construction optimal value table')

V = np.zeros(len(env.states))

t = time()

print('Calculating terminal V table.')

# Calculate the value of every terminal state. 

for s in range(end_state_start, len(env.states)):
    V[s] = env.calculate_terminal_reward(s)

print('time: ', time() - t)


# compute the rewards of each action for each state, but not the terminal states!
# This is used to speed up the value iteration. Instead of computing all the rewards several times, 
# compute them before hand. 
D_reward =  [[0,0.0] for _ in range(end_state_start)]
C_reward = [[0,0.0] for _ in range(end_state_start)]

print('calculating rewards for all states')
t = time()
# don't calculate a reward for the terminal stats!
for s in range(0,end_state_start):
    D_reward[s] = env.get_instant_reward_and_next_state(s, 0)
    C_reward[s] = env.get_instant_reward_and_next_state(s, 1)

print('time: ', time() - t)


print('Calculating V Table for non-terminal states')
i = 1
#Construct optimal values
while True:
    print ('Round {0}'.format(i))
    t = time()
    delta = 0
    V_copy = np.copy(V)
    for s in range(end_state_start - 1 , -1, -1):
        v = V[s]
        d = D_reward[s]
        c = C_reward[s]

        V[s] = max(d[1] + V[d[0]], c[1] + V[c[0]])
    print('time: ', time() - t)

    delta = (np.sum(np.fabs(V_copy - V)))
    print('delta: ', delta)
    if (np.sum(np.fabs(V_copy - V)) <= 0.1):
        break
    i += 1


#get the optimal policy from those values
print('Finding optimal policy')
t = time()
policy = np.zeros(len(env.states))
for s in range(len(env.states)):
    if s < end_state_start:
        d = D_reward[s]
        c = C_reward[s]
        policy[s] = np.argmax([d[1] + V[d[0]],c[1] + V[c[0]]])
    

print('time: ', time() - t)

#Evaluate the policy 
print('Evaluating policy')
average_reward = 0
for n in range(TEST_RUNS):
    state = env.get_index_from_state([0,39, 0])
    total_reward = 0

    step_index = 0
    charging_points = {}
    while True:
        # Get the optimal action. 
        action_taken = ev_route_environment.NavigationAction(int(policy[state]))

        # Act.  
        state, reward, done = env.act(state, int(policy[state]))

        # if the action is charging, add the waypoint to a list of coordinates to display once the test
        # is finished. 
        if action_taken == ev_route_environment.NavigationAction.charging:
            env.add_waypoint_charger_to_final_route(state)
            if env.get_state_from_index(state)[2] not in charging_points:
                  charging_points[env.get_state_from_index(state)[2]] = 1
            else:
                  charging_points[env.get_state_from_index(state)[2]] += 1

        total_reward += reward
        step_index += 1
        average_reward += total_reward

        if done:
            env.display_route_in_browser()
            break
    #Print the trip stats. 
    ns = env.get_state_from_index(state)
    print('Battery level: ', ns[1])
    print('Trip time: ', ns[0]*15, ' minutes') 
    for k,p in charging_points.items():
        w = env.get_waypoint_from_index(k).Title
        t = p*15
        s = 'Stop at {0} for {1} minutes.'.format(w, t)
        print(s)
        
print('Average reward: ', average_reward/TEST_RUNS)
