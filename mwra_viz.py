import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import numpy as np
from datetime import datetime

# Read the data
df = pd.read_csv('data/MWRA-DOWNCAST-2024.csv')

# Convert date strings to datetime
df['STAT_ARRIV'] = pd.to_datetime(df['STAT_ARRIV'], format='%d-%b-%Y %H:%M:%S')

# Define station categories
station_categories = {
    'Mass Bay Nearfield': ['N01', 'N02', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08', 'N09', 'N10'],
    'Mass Bay Farfield': ['F06', 'F10', 'F13', 'F15', 'F22'],
    'Boston Harbor Outlet': ['F23'],
    'Cape Cod Bay': ['F01', 'F02', 'F29']
}

# Create a category column
df['Station_Category'] = 'Other'
for category, stations in station_categories.items():
    df.loc[df['STAT_ID'].isin(stations), 'Station_Category'] = category

# Define color scheme
color_scheme = {
    'Mass Bay Nearfield': '#1f77b4',  # blue
    'Mass Bay Farfield': '#ff7f0e',   # orange
    'Boston Harbor Outlet': '#2ca02c', # green
    'Cape Cod Bay': '#d62728',        # red
    'Other': '#7f7f7f'                # gray
}

# Initialize the Dash app
app = Dash(__name__)

# Define the layout
app.layout = html.Div([
    html.H1('MWRA Data Visualization'),
    
    # Parameter selection
    html.Div([
        html.Label('Select Parameter:'),
        dcc.Dropdown(
            id='parameter-dropdown',
            options=[
                {'label': 'Temperature', 'value': 'TEMP'},
                {'label': 'Conductivity', 'value': 'CONDTVY'},
                {'label': 'Salinity', 'value': 'SAL'},
                {'label': 'Dissolved Oxygen', 'value': 'DISS_OXYGEN'},
                {'label': 'Oxygen Saturation', 'value': 'O2_PCT_SAT'},
                {'label': 'Chlorophyll', 'value': 'CHLA_FLU_CALIB'},
                {'label': 'pH', 'value': 'PH'}
            ],
            value='TEMP'
        )
    ], style={'width': '30%', 'margin': '20px'}),
    
    # Depth vs Parameter plot
    dcc.Graph(id='depth-parameter-plot'),
    
    # Time series plot
    dcc.Graph(id='time-series-plot')
])

# Callback for depth vs parameter plot
@app.callback(
    Output('depth-parameter-plot', 'figure'),
    Input('parameter-dropdown', 'value')
)
def update_depth_parameter_plot(parameter):
    fig = px.scatter(
        df,
        x=parameter,
        y='DEPTH',
        color='Station_Category',
        color_discrete_map=color_scheme,
        hover_data=['STAT_ID', 'STAT_ARRIV'],
        title=f'Depth vs {parameter}',
        labels={'DEPTH': 'Depth (m)', parameter: parameter}
    )
    
    # Reverse y-axis to show depth increasing downward
    fig.update_layout(yaxis_autorange='reversed')
    
    return fig

# Callback for time series plot
@app.callback(
    Output('time-series-plot', 'figure'),
    Input('parameter-dropdown', 'value')
)
def update_time_series_plot(parameter):
    # Group by date and calculate mean for each category
    daily_means = df.groupby(['STAT_ARRIV', 'Station_Category'])[parameter].mean().reset_index()
    
    fig = px.line(
        daily_means,
        x='STAT_ARRIV',
        y=parameter,
        color='Station_Category',
        color_discrete_map=color_scheme,
        title=f'{parameter} Over Time',
        labels={'STAT_ARRIV': 'Date', parameter: parameter}
    )
    
    return fig

if __name__ == '__main__':
    app.run(debug=True) 