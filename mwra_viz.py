import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import numpy as np

df = pd.read_csv('data/MWRA-DOWNCAST-2024.csv')

df['STAT_ARRIV'] = pd.to_datetime(df['STAT_ARRIV'], format='%d-%b-%Y %H:%M:%S')
df['sample_date'] = df['STAT_ARRIV'].dt.date

station_categories = {
    'Mass Bay Nearfield': [
        'N01', 'N02', 'N03', 'N04', 'N05', 'N06', 'N07', 'N08', 'N09', 'N10'],
    'Mass Bay Farfield': ['F06', 'F10', 'F13', 'F15', 'F22'],
    'Boston Harbor Outlet': ['F23'],
    'Cape Cod Bay': ['F01', 'F02', 'F29']
}

df['Station_Category'] = 'Other'
for category, stations in station_categories.items():
    df.loc[df['STAT_ID'].isin(stations), 'Station_Category'] = category

color_scheme = {
    'Mass Bay Nearfield': '#1f77b4',  # blue
    'Mass Bay Farfield': '#ff7f0e',   # orange
    'Boston Harbor Outlet': '#2ca02c',  # green
    'Cape Cod Bay': '#d62728',        # red
    'Other': '#7f7f7f'                # gray
}


def categorize_depth(depth):
    if depth <= 10:
        return 'Shallow (0-10m)', 8
    elif depth <= 20:
        return 'Mid (10-20m)', 12
    else:
        return 'Deep (>20m)', 16


def resample_by_depth(group, num_depth_samples):
    if len(group) <= num_depth_samples:
        return group
    indices = np.linspace(0, len(group) - 1, num_depth_samples, dtype=int)
    return group.sort_values('DEPTH').iloc[indices]


app = Dash(__name__)

app.layout = html.Div([
    html.H1('MWRA Data Visualization'),

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

    dcc.Graph(id='depth-parameter-plot'),

    dcc.Graph(id='time-series-plot'),

    dcc.Graph(id='param-time-depth-plot')
])


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

    fig.update_layout(yaxis_autorange='reversed')
    return fig


@app.callback(
    Output('time-series-plot', 'figure'),
    Input('parameter-dropdown', 'value')
)
def update_time_series_plot(parameter):
    daily_means = df.groupby(
        ['STAT_ARRIV', 'Station_Category'])[parameter].mean().reset_index()
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


@app.callback(
    Output('param-time-depth-plot', 'figure'),
    Input('parameter-dropdown', 'value')
)
def update_param_time_depth_plot(parameter):
    filtered_df = df.copy()
    filtered_df[['Depth_Category', 'point_size']] = pd.DataFrame(
        filtered_df['DEPTH'].apply(categorize_depth).tolist(),
        index=filtered_df.index
    )

    resampled_data = []
    for (date, station), group in filtered_df.groupby(
            ['sample_date', 'STAT_ID']):
        resampled_group = resample_by_depth(group, 10)  # Use 10 points
        resampled_data.append(resampled_group)

    resampled_df = pd.concat(resampled_data)

    resampled_df['display_date'] = resampled_df['sample_date'].apply(
        lambda x: x.strftime('%m/%d/%Y'))
    resampled_df = resampled_df.sort_values('sample_date')

    fig = go.Figure()

    for category in sorted(resampled_df['Station_Category'].unique()):
        category_data = resampled_df[
            resampled_df['Station_Category'] == category]

        for depth_cat in ['Shallow (0-10m)', 'Mid (10-20m)', 'Deep (>20m)']:
            depth_data = category_data[
                category_data['Depth_Category'] == depth_cat]
            if not depth_data.empty:
                fig.add_trace(go.Scatter(
                    x=depth_data['display_date'],
                    y=depth_data[parameter],
                    mode='markers',
                    marker=dict(
                        size=depth_data['point_size'],
                        color=color_scheme[category]
                    ),
                    name=category,
                    legendgroup=category,
                    showlegend=depth_cat == 'Shallow (0-10m)',
                    hovertemplate=(
                        'Station: %{text}<br>' +
                        'Date: %{x}<br>' +
                        f'{parameter}: %{{y}}<br>' +
                        'Depth Category: ' + depth_cat + '<br>'
                    ),
                    text=depth_data['STAT_ID']
                ))

        for station in category_data['STAT_ID'].unique():
            station_data = category_data[category_data['STAT_ID'] == station]
            for date in station_data['display_date'].unique():
                date_data = station_data[station_data['display_date'] == date]
                if len(date_data) > 1:
                    fig.add_trace(go.Scatter(
                        x=date_data['display_date'],
                        y=date_data[parameter],
                        mode='lines',
                        line=dict(
                            width=1,
                            color=color_scheme[category]
                        ),
                        name=category,
                        legendgroup=category,
                        showlegend=False,
                        hoverinfo='skip'
                    ))

    for depth_cat, size in [
            ('Shallow (0-10m)', 8),
            ('Mid (10-20m)', 12),
            ('Deep (>20m)', 16)]:
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='markers',
            marker=dict(size=size, color='gray'),
            name=depth_cat,
            legendgroup='depth',
            legendgrouptitle_text='Depth',
            showlegend=True
        ))

    fig.update_layout(
        title=f'{parameter} vs Time vs Depth',
        xaxis_title='Date',
        yaxis_title=parameter,
        showlegend=True,
        legend=dict(
            groupclick="toggleitem",
            title="Station Category"
        ),
        xaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=resampled_df['display_date'].unique()
        )
    )

    return fig


if __name__ == '__main__':
    app.run(debug=True)
