import charger_database_manager as dm
import charger_objects as co

        # #Create the database and populate it.
try:
    charger_database = dm.ChargerDatabase()
    charger_file_io  = co.ChargerObjects()
    chargers = charger_file_io.get_us_charge_locations()
    charger_database.create()
    charger_database.insert(chargers)
    #charger_database.drop()
    print('Success')
except Exception as e:
    print(e)
