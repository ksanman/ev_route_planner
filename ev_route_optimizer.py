import ev_route_environment as ev_route_environment
import datetime
from datetime import datetime as dt
import numpy as np
import random
import test_env
import math
#create a new environment
#env = test_env.TestEnv()
env = ev_route_environment.EvRouteEnvironment(route_from_file=True, chargers_from_file=True)
times = env.T
battery_max = env.B
W = env.get_waypoint_from_index(-1).id - 1


print('Construction optimal value table')

V = np.zeros(times*battery_max*W)
for t in range(times):
    for eBatt in range(battery_max):
        s = env.get_index_from_state([t, eBatt, W])
        V[s] = env.calculate_terminal_reward(s)


i = 1
#Construct optimal values
while True:
    print ('Round {0}'.format(i))
    delta = 0
    for w in range(W-1, 0, -1):
        for t in range(times):
            for b in range(battery_max):
                s = env.get_index_from_state([t, b, w])
                v = V[s]
                best = -100
                for a in env.actions:
                    next_state, reward = env.get_instant_reward_and_next_state(s, a)
                    best = max(best, reward + V[next_state])
                V[s] = best
                err = v - V[s]
                a = abs(err)
                delta = max(delta, a)
    if delta < 0.001:
        break
    i += 1

#get the optimal policy from those values
print('Finding optimal policy')
policy = np.zeros(len(env.states))
for s in range(len(env.states)):
    possible_actions = np.zeros(len(env.actions))
    for a in range(len(env.actions)):
            next_state, reward = env.get_instant_reward_and_next_state(s, a)
            possible_actions[a] += (reward + V[next_state])
    policy[s] = np.argmax(possible_actions)

#Evaluate the policy 
average_reward = 0
for n in range(10):
    print('')
    print('test ', n)
    print('')
    state = env.get_random_state()
    total_reward = 0

    step_index = 0
    while True:
        state, reward, done = env.act(state, int(policy[state]))
        action_taken = ev_route_environment.NavigationAction(int(policy[state]))
        print('action taken: {0}'.format(action_taken.name))
        print('time: ', env.get_state_from_index(state)[0] * .25 * 60, ' minutes')
        print('battery level: ', env.get_state_from_index(state)[1])
        print('checkpoint: ', env.get_state_from_index(state)[2])
        print('')
        total_reward += reward
        step_index += 1
        if done:
            break
        average_reward += total_reward
        print('total reward:' ,total_reward)
print('Average reward: ', average_reward/10)