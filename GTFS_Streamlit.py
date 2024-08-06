import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from ipyleaflet import Map, Marker, Popup, Polyline, basemaps, AwesomeIcon
from ipywidgets.embed import embed_minimal_html
import time

# Load GTFS data
data_path = r"C:\Users\TULPAR\JupyterLab Projects\dataset"
stops = pd.read_csv(f"{data_path}/stops.txt")
routes = pd.read_csv(f"{data_path}/routes.txt")
trips = pd.read_csv(f"{data_path}/trips.txt")
stop_times = pd.read_csv(f"{data_path}/stop_times.txt")
calendar = pd.read_csv(f"{data_path}/calendar.txt")
shapes = pd.read_csv(f"{data_path}/shapes.txt")

# Function to convert the time of the data
def convert_time(time_str):
    try:
        parts = time_str.split(':')
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        if hours >= 24:
            hours -= 24
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    except ValueError as e:
        st.error(f"Error converting time: {time_str} - {e}")
        return None

# Apply the conversion to arrival_time and departure_time
stop_times['arrival_time'] = stop_times['arrival_time'].apply(convert_time)
stop_times['departure_time'] = stop_times['departure_time'].apply(convert_time)
stop_times = stop_times.dropna(subset=['arrival_time', 'departure_time'])

# Simulation parameters
today_date = datetime.now().date()
start_time = datetime.strptime("08:00:00", '%H:%M:%S').time()
end_time = datetime.strptime("10:00:00", '%H:%M:%S').time()
start_datetime = datetime.combine(today_date, start_time)
if end_time < start_time:
    end_datetime = datetime.combine(today_date + timedelta(days=1), end_time)
else:
    end_datetime = datetime.combine(today_date, end_time)

# Define the current time to use in the update function below.
current_time = start_datetime

def find_service_id(calendar, current_time):
    today = current_time.weekday() + 1
    for index in calendar.index:
        value = calendar.iloc[index, today]
        if value == 1:
            servid = calendar.iloc[index, 0]
            return servid
    return None

# Initialize the map centered on the city
center = (stops['stop_lat'].mean(), stops['stop_lon'].mean())

# Add stop markers to the map initially
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

def initialize_buses(trips, stop_times, stops, routes):
    merged_df = pd.merge(trips, stop_times, on='trip_id', how='outer')
    merged_df2 = pd.merge(merged_df, stops, on='stop_id', how='outer')
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

def todays_buses(buses, calendar, current_time):
    servid = find_service_id(calendar, current_time)
    todaysBuses = []
    for bus in buses:
        bus_service_id = bus['service_id']
        if bus_service_id == servid:
            todaysBuses.append(bus)
    return todaysBuses

def create_bus_markers(bus):
    icon = AwesomeIcon(name='bus', marker_color='red', icon_color='white')
    marker = Marker(icon=icon, location=[bus['stop_lat'], bus['stop_lon']], draggable=False)
    popup_content = HTML()
    popup_content.value = f"Route Name: {bus['route_short_name']}, Trip ID: {bus['trip_id']}, Stop Name: {bus['current_stop_name']}, Stop Number: {bus['current_stop_id']}, Stop Time: {bus['stop_time']}"
    popup = Popup(
        location=[bus['stop_lat'], bus['stop_lon']],
        child=popup_content,
        close_button=False,
        auto_close=False,
        close_on_escape_key=False
    )
    marker.popup = popup
    return marker 

def update_buses(buses, calendar, current_time, start_datetime, end_datetime, map):
    existing_markers = {}
    st.write(f"Simulation will run from {start_datetime} to {end_datetime}.")

    while current_time <= end_datetime:
        todays_buses_list = todays_buses(buses, calendar, current_time)
        st.write("Current time: ", current_time)

        new_markers = {(bus['trip_id'], bus['current_stop_sequence']): bus for bus in todays_buses_list}
        for marker_key in list(existing_markers.keys()):
            if marker_key not in new_markers:
                map.remove_layer(existing_markers[marker_key])
                del existing_markers[marker_key]

        for marker_key, bus in new_markers.items():
            if marker_key not in existing_markers:
                marker = create_bus_markers(bus)
                map.add_layer(marker)
                existing_markers[marker_key] = marker
                
            else:
                old_marker = existing_markers[marker_key]
                new_location = [bus['stop_lat'], bus['stop_lon']]
                if old_marker.location != new_location:
                    map.remove_layer(old_marker)
                    new_marker = create_bus_markers(bus)
                    map.add_layer(new_marker)
                    existing_markers[marker_key] = new_marker

        current_time = current_time + timedelta(seconds=30)
        st.write("SYSTEM IS")
        # Clear the previous output and display the map
        embed_minimal_html('map.html', views=[map], title='ipyleaflet Map')
        with open('map.html', 'r') as f:
            map_html = f.read()
        st.components.v1.html(map_html, height=600)
        time.sleep(30)

# Initialize the map
map = Map(basemap=basemaps.OpenStreetMap.Mapnik, center=center, zoom=12)
buses = initialize_buses(trips, stop_times, stops, routes)
map = add_stop_markers(stops, map)
map = create_lines(shapes, map)
# Embed the map as HTML
embed_minimal_html('map.html', views=[map], title='ipyleaflet Map')
with open('map.html', 'r') as f:
    map_html = f.read()
# Render the map in Streamlit
st.components.v1.html(map_html, height=600)
# Call the update_buses function
update_buses(buses, calendar, current_time, start_datetime, end_datetime, map)
