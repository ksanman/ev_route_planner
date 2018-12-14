import ev_route_environment as ev_route_environment
import datetime
from datetime import datetime as dt
import numpy as np
import random
import test_env
import math
from time import time
#create a new environment
#env = test_env.TestEnv()
env = ev_route_environment.EvRouteEnvironment(battery_cap=40 ,route_from_file=False, chargers_from_file=False)
#env = ev_route_environment.EvRouteEnvironment(endLocation=['-113.5684','37.0965'],battery_cap=40 ,route_from_file=False, chargers_from_file=False)

times = env.T
battery_max = env.B
W = env.get_waypoint_from_index(-1).id - 1
actions = range(len(env.actions))

end_state_start = times*battery_max*W

print('Construction optimal value table')

V = np.zeros(len(env.states))

t = time()

print('Calculating terminal V table.')

for s in range(end_state_start, len(env.states)):
    V[s] = env.calculate_terminal_reward(s)

T = [env.calculate_terminal_reward(s) for s in range(end_state_start, len(env.states))]

print('time: ', time() - t)

# for t in range(times):
#     for eBatt in range(battery_max):
#         s = env.get_index_from_state([t, eBatt, W])
#         V[s] = env.calculate_terminal_reward(s)


# compute the rewards of each action for each state.
D_reward =  [[0,0.0] for _ in range(end_state_start)]
C_reward = [[0,0.0] for _ in range(end_state_start)]

print('calculating rewards for all states')
t = time()
# don't calculate a reward for the end state!
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
    if (np.sum(np.fabs(V_copy - V)) <= 24):
        break
    i += 1

# while True:
#     print ('Round {0}'.format(i))
#     delta = 0
#     for s in range(end_state_start -1 , 0, -1):
#         v = V[s]
#         V[s] =  np.argmax([reward + V[next_state] for next_state,reward
#                 in [env.get_instant_reward_and_next_state(s, a) 
#                     for a in actions]])
#         err = v - V[s]
#         a = abs(err)
#         delta = max(delta, a)
#     if delta < 0.001:
#         break
#     i += 1

# while True:
#     print ('Round {0}'.format(i))
#     delta = 0
#     for w in range(W-1, 0, -1):
#         for t in range(times):
#             for b in range(battery_max):
#                 s = env.get_index_from_state([t, b, w])
#                 v = V[s]
#                 best = -100
#                 for a in env.actions:
#                     next_state, reward = env.get_instant_reward_and_next_state(s, a)
#                     best = max(best, reward + V[next_state])
#                 V[s] = best
#                 err = v - V[s]
#                 a = abs(err)
#                 delta = max(delta, a)
#     if delta < 0.001:
#         break
#     i += 1


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
for n in range(1):
    print('')
    print('test ', n)
    print('')
    state = env.get_index_from_state([0,39, 0])
    #state = env.get_random_state()
    total_reward = 0

    step_index = 0
    charging_points = {}
    while True:
        action_taken = ev_route_environment.NavigationAction(int(policy[state]))
       # print('Previous state:')
       # print('time: ', env.get_state_from_index(state)[0] * .25 * 60, ' minutes')
       # print('battery level: ', env.get_state_from_index(state)[1])
       # print('checkpoint: ', env.get_state_from_index(state)[2])
       # print('action taken: {0}'.format(action_taken.name))
       # print('')

        state, reward, done = env.act(state, int(policy[state]))

        if action_taken == ev_route_environment.NavigationAction.charging:
            env.add_waypoint_charger_to_final_route(state)
            if state not in charging_points:
                  charging_points[env.get_state_from_index(state)[2]] = 1
            else:
                  charging_points[env.get_state_from_index(state)[2]] += 1
       # print('New state:')
       # print('time: ', env.get_state_from_index(state)[0] * .25 * 60, ' minutes')
       # print('battery level: ', env.get_state_from_index(state)[1])
       # print('checkpoint: ', env.get_state_from_index(state)[2])
       # print('Distance Traveled: {0}'.format(env.get_waypoint_from_index(env.get_state_from_index(state)[2]).distance_from_previous_node))
       # print('Energy Used: {0}'.format(env.get_waypoint_from_index(env.get_state_from_index(state)[2]).energy_to_node))
       # print('')

        total_reward += reward
        step_index += 1
        average_reward += total_reward
       # print('total reward:' ,total_reward)
       # print('')
       # print('')

        if done:
            env.display_route_in_browser()
            break
    for k,p in charging_points.items():
        w = env.get_waypoint_from_index(env.get_state_from_index(state)[2]).Title
        t = p*4
        s = 'Stop at {0} for {1} minutes.'.format(w, t)
        print(s)
        
print('Average reward: ', average_reward)
