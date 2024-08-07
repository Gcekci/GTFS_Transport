import time
from datetime import timedelta, datetime
import pandas as pd
from IPython.display import display
data_path = r"C:\Users\TULPAR\JupyterLab Projects\dataset"
stops = pd.read_csv(f"{data_path}/stops.txt")
routes = pd.read_csv(f"{data_path}/routes.txt")
trips = pd.read_csv(f"{data_path}/trips.txt")
stop_times = pd.read_csv(f"{data_path}/stop_times.txt")
calendar = pd.read_csv(f"{data_path}/calendar.txt")
shapes = pd.read_csv(f"{data_path}/shapes.txt")

def convert_time(time_str):
    try:
        parts = time_str.split(':')
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        if hours >= 24:
            hours -= 24
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    except ValueError as e:
        print(f"Error converting time: {time_str} - {e}")
        return None
    
stop_times['arrival_time'] = stop_times['arrival_time'].apply(convert_time)
stop_times['departure_time'] = stop_times['departure_time'].apply(convert_time)
stop_times = stop_times.dropna(subset=['arrival_time', 'departure_time'])
today_date = datetime.now().date()



start_time = datetime.strptime("10:00:00", '%H:%M:%S').time()
print('start_time: ', start_time)

end_time = datetime.strptime("10:30:00", '%H:%M:%S').time()

print(f"Simulation will run from {start_time} to {end_time}.")

start_datetime = datetime.combine(today_date, start_time)

current_datetime= start_datetime

if end_time < start_time:
    # End time is on the next day
    end_datetime = datetime.combine(today_date + timedelta(days=1), end_time)
    
else:
    end_datetime = datetime.combine(today_date, end_time)
    


def get_service_id():
    # Get the current day of the week (0=Monday, 1=Tuesday, ..., 6=Sunday)
    today_day = current_datetime.weekday()
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # Find the column corresponding to today's day
    current_day_column = days[today_day]

    # Filter the DataFrame for the current day and get the service_id
    current_service_id = calendar[calendar[current_day_column] == 1]['service_id'].iloc[0]

    return int(current_service_id)

def initialize_buses(trips, stop_times, stops, routes):
    merged_df = pd.merge(trips, stop_times, on='trip_id', how='outer')
    merged_df2 = pd.merge(merged_df, stops, on='stop_id', how='outer')
    merged_df3=pd.merge(merged_df2,stop_times, on='trip_id',how='outer')
    final_merge = pd.merge(merged_df2, routes, on='route_id', how='outer')

    buses = [{
        'service_id': trip.service_id,
        'trip_id': trip.trip_id,
        'route_id': trip.route_id,
        'current_stop_sequence': trip.stop_sequence,
        'stop_time': trip.arrival_time,
        'direction_id': trip.direction_id,
        'current_stop_id': trip.stop_id,
        'current_stop_name': trip.stop_name,
        'stop_lat': trip.stop_lat,
        'stop_lon': trip.stop_lon,
        'route_short_name': trip.route_short_name
    } for trip in final_merge.itertuples()]
    return buses
'''
def todays_buses():
    buses2=initialize_buses(trips, stop_times, stops, routes)
    print(buses2)
    servid = get_service_id()
    todaysBuses = []
    for bus in buses2:
        bus_service_id = bus['service_id']
        if bus_service_id == servid:
            todaysBuses.append(bus)
    return todaysBuses
'''

def update():
        
        global current_datetime, end_datetime 
        current_buses=[]
        while current_datetime <= end_datetime:
                print('while is operating. Current time is : ',current_datetime)
                today_service_id=get_service_id()
                print('todays service id: ',today_service_id)
                buses=initialize_buses(trips, stop_times, stops, routes)
                todaysBuses = [bus for bus in buses if bus['service_id'] == today_service_id] 

                current_buses = todaysBuses[(stop_times['arrival_time'] == current_datetime) | (stop_times['departure_time'] == current_datetime)]
                '''for bus in todaysBuses:
                     #bus_stop_time=datetime.strptime(bus['stop_time']).time()
                     bus_stop_time_str = bus['stop_time']
                     bus_stop_time = datetime.strptime(bus_stop_time_str, '%H:%M:%S').time()
                     bus_datetime = datetime.combine(today_date, bus_stop_time)
                     
                     if current_datetime<bus_datetime:
                        bus_datetime+=timedelta(days=1)
                        print('bus datetime+1: ',bus_datetime)
                     if current_datetime==bus_datetime:
                        current_buses.append(bus)
                        
                '''
                print('>>>>>>>>>>>>>>>>>>>>>>>>>>> ',current_buses)
                print('current bus amount: ',len(current_buses))
                print(current_buses)
                amount = sum(1 for bus in buses if bus['service_id'] == today_service_id)
                print('todays bus amount is: ',amount)

                        
                current_datetime=current_datetime +timedelta(seconds=30)
                time.sleep(30)


                
                
                return current_buses

update()                        
        