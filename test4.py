import pandas as pd
from datetime import datetime, timedelta
import time
from ipywidgets import HTML
from ipyleaflet import Map, Marker, Popup, Polyline, basemaps, AwesomeIcon
from IPython.display import display, clear_output

# Load the necessary GTFS data files
data_path = r"C:\Users\TULPAR\JupyterLab Projects\dataset"
stops = pd.read_csv(f"{data_path}/stops.txt")
routes = pd.read_csv(f"{data_path}/routes.txt")
trips = pd.read_csv(f"{data_path}/trips.txt")
stop_times = pd.read_csv(f"{data_path}/stop_times.txt")
calendar = pd.read_csv(f"{data_path}/calendar.txt")

# Helper function to convert time strings to HH:MM:SS format
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

# Apply the time conversion
stop_times['arrival_time'] = stop_times['arrival_time'].apply(convert_time)
stop_times['departure_time'] = stop_times['departure_time'].apply(convert_time)
stop_times = stop_times.dropna(subset=['arrival_time', 'departure_time'])

# Define the interval in seconds for updates
update_interval = 30  # 30 seconds

def get_time_input(prompt):
    while True:
        try:
            time_str = input(prompt)
            time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
            return time_str
        except ValueError:
            print("Invalid time format. Please enter time in HH:MM:SS format.")

# Function to get the service IDs for a given date
def get_service_ids_for_date(date):
    day_index = date.weekday()
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_column = days[day_index]
    service_ids = calendar[calendar[day_column] == 1]['service_id'].tolist()
    return service_ids

def add_stop_markers(stops, map):
    for stop in stops.itertuples():
        marker = Marker(location=[stop.stop_lat, stop.stop_lon], draggable=False)
        popup_content = HTML()
        popup_content.value = f"Stop: {stop.stop_name}, Stop Number: {stop.stop_id}"
        popup = Popup(
            location=[stop.stop_lat, stop.stop_lon],
            child=popup_content,
            close_button=False,
            auto_close=False,
            close_on_escape_key=False
        )
        marker.popup = popup
        map.add_layer(marker)
    return map

def create_lines(shapes, map):
    shape_locations = []
    for shape in shapes.itertuples():
        shape_locations.append([shape.shape_pt_lat, shape.shape_pt_lon])
    
    if len(shape_locations) > 1:
        polyline = Polyline(
            locations=shape_locations,
            color="red",
            fill=False,
            weight=2,
            opacity=1,
            dash_array='5 ,5'
        )
        map.add_layer(polyline)
    
    return map

def create_bus_markers(buses):
    icon = AwesomeIcon(name='bus', marker_color='red', icon_color='white')
    marker = Marker(icon=icon, location=[buses['stop_lat'], buses['stop_lon']], draggable=False)
    popup_content = HTML()
    popup_content.value = f"Route Name: {buses['route_short_name']}, Trip ID: {buses['trip_id']}, Stop Name: {buses['stop_name']}, Arrival Time: {buses['arrival_time']}"
    popup = Popup(
        location=[buses['stop_lat'], buses['stop_lon']],
        child=popup_content,
        close_button=False,
        auto_close=False,
        close_on_escape_key=False
    )
    marker.popup = popup
    return marker

# Function to get the buses at the current time
def get_buses_at_time(target_time_str, service_ids):
    # Filter the stop_times DataFrame for the target time
    filtered_stop_times = stop_times[
        (stop_times['arrival_time'] == target_time_str) | 
        (stop_times['departure_time'] == target_time_str)
    ]
    
    if filtered_stop_times.empty:
        return pd.DataFrame()

    # Merge with trips to filter by the given service IDs
    filtered_stop_times = pd.merge(filtered_stop_times, trips, on='trip_id', how='left')
    filtered_stop_times = filtered_stop_times[filtered_stop_times['service_id'].isin(service_ids)]
    
    if filtered_stop_times.empty:
        return pd.DataFrame()

    # Merge with routes and stops to get detailed bus information
    merged_df = pd.merge(filtered_stop_times, routes, on='route_id', how='left')
    merged_df = pd.merge(merged_df, stops, on='stop_id', how='left')
    
    return merged_df

# Function to print bus information
def print_bus_info(buses):
    if buses.empty:
        print("No buses found for the current time.")
    else:
        print("Route short names of current buses:")
        for _, row in buses.iterrows():
            print(f"Route: {row['route_short_name']}, Trip ID: {row['trip_id']}, "
                  f"Stop: {row['stop_name']}, Arrival Time: {row['arrival_time']}, "
                  f"Departure Time: {row['departure_time']}, "
                  f"Service ID: {row['service_id']}, Stop Sequence: {row['stop_sequence']}")

# Start the dynamic updating service
def dynamic_update_service(start_time_str, end_time_str):
    # Initialize start and end datetime
    today_date = datetime.now().date()
    start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
    end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()
    
    start_datetime = datetime.combine(today_date, start_time)
    end_datetime = datetime.combine(today_date, end_time)
    
    # If end time is before start time, assume it is on the next day
    if end_time < start_time:
        end_datetime += timedelta(days=1)

    current_datetime = start_datetime
    previous_bus_state = {}
    markers = {}

    while current_datetime <= end_datetime:
        current_time_str = current_datetime.strftime('%H:%M:%S')
        print(f"\nCurrent Time: {current_time_str}")

        # Get service IDs for the current date
        current_service_ids = get_service_ids_for_date(current_datetime.date())
        
        buses = get_buses_at_time(current_time_str, current_service_ids)
        
        # Check if buses dataframe is empty, if so, keep the previous state
        if buses.empty:
            print("No new bus data available, retaining previous state.")
        else:
            print_bus_info(buses)
        
            current_bus_state = {row['trip_id']: (row['stop_id'], row['stop_sequence']) for _, row in buses.iterrows()}
        
            for trip_id, (stop_id, stop_sequence) in current_bus_state.items():
                if trip_id in previous_bus_state:
                    if previous_bus_state[trip_id][0] != stop_id:
                        print(f"Trip ID {trip_id} has changed stop from {previous_bus_state[trip_id][0]} to {stop_id}")
                        # Remove the old marker
                        map.remove_layer(markers[trip_id])
                        # Create a new marker
                        new_marker = create_bus_markers(buses[buses['trip_id'] == trip_id].iloc[0])
                        map.add_layer(new_marker)
                        markers[trip_id] = new_marker
                else:
                    print(f"Trip ID {trip_id} is at stop {stop_id} for the first time")
                    # Create a new marker for the first time
                    new_marker = create_bus_markers(buses[buses['trip_id'] == trip_id].iloc[0])
                    map.add_layer(new_marker)
                    markers[trip_id] = new_marker

            # Update previous_bus_state with the current state for the next iteration
            previous_bus_state.update(current_bus_state)
        
        # Remove buses that have completed their stop sequence
        for trip_id in list(previous_bus_state.keys()):
            if trip_id not in current_bus_state:
                del previous_bus_state[trip_id]
                # Remove the old marker
                map.remove_layer(markers[trip_id])
                del markers[trip_id]
                print(f"Trip ID {trip_id} has completed its stop sequence and has been removed.")

        current_datetime += timedelta(seconds=update_interval)
        time.sleep(30)  # Reduce sleep time for faster testing

# Initialize the map
m = Map(center=(0, 0), zoom=2, basemap=basemaps.OpenStreetMap.Mapnik)

# Run the dynamic updating service with the specified start and end times
start_time_str = get_time_input("Enter start time (HH:MM:SS): ")
end_time_str = get_time_input("Enter end time (HH:MM:SS): ")
dynamic_update_service(start_time_str, end_time_str)
