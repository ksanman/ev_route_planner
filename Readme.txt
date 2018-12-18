Kody Sanchez
CS5890 
Dr. Flann

Ev Trip Planner

Github: https://github.com/ksanman/ev_route_planner

How to run:
The program is made to be run with a database of all the charger locations in the US attached. 
However, I have included a mode to run the program using files containing the data instead. Although using this method will
only run 1 route. 

In the file ev_route_optimizer.py, make sure the flags route_from_file and chargers_from_file are set to true in the 
ev_route_environment.EvRouteEnvironment constructor. The program should run. 

If a postgres database is on the computer, you can populate the database with the charger locations. 
Create a new schema called 'ev'. Run the utility.py file with the database name, username, and password in the database 
constructor. This will populate the database. 

To run the program, run ev_route_optimizer.py. 