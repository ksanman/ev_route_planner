import ev_route_environment as ev_route_environment
import datetime
from datetime import datetime as dt
import numpy as np
import random
#create a new environment

time = dt.strptime('16:00', '%H:%M')
env = ev_route_environment.EvRouteEnvironment(time,100, 
    startLocation=['-111.8338', '41.7370'], endLocation=['-112.024867','41.289583'],
    charger_radius=3,route_from_file=False)

print([state for state in env.states])
print('number of states ', len(env.states))


#create the action space
action_space = ev_route_environment.NavigationAction

# #test getting the next action.
action = action_space.driving
start_state = env.get_random_state()
next_state,reward, done = env.get_next_state(start_state, action)

# Hyperparameters
# alpha = 0.1
# gamma = 0.6
# epsilon = 0.1

# # For plotting metrics
# all_epochs = []
# all_penalties = []

# for i in range(1, 100001):
#     state = env.reset()

#     epochs, penalties, reward, = 0, 0, 0
#     done = False
    
#     while not done:
#         if random.uniform(0, 1) < epsilon:
#             action = env.action_space.sample() # Explore action space
#         else:
#             action = np.argmax(q_table[state]) # Exploit learned values

#         next_state, reward, done, info = env.step(action) 
        
#         old_value = q_table[state, action]
#         next_max = np.max(q_table[next_state])
        
#         new_value = (1 - alpha) * old_value + alpha * (reward + gamma * next_max)
#         q_table[state, action] = new_value

#         if reward == -10:
#             penalties += 1

#         state = next_state
#         epochs += 1
        
#     if i % 100 == 0:
#         clear_output(wait=True)
#         print(f"Episode: {i}")

# print("Training finished.\n")