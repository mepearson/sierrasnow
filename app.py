# ----------------------------------------------------------------------------
# PYTHON LIBRARIES
# ----------------------------------------------------------------------------

# File Management
import os # Operating system library
import pathlib # file paths

# Data Cleaning and transformations
import numpy as np
import pandas as pd
import fiscalyear as fy

# Data visualization
import plotly.express as px

# Dash Framework
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ALL, MATCH

# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------

CONTENT_STYLE = {
    "padding": "2rem 1rem",
    "font-family": '"Times New Roman", Times, serif'
}

# ----------------------------------------------------------------------------
# DATA LOADING AND CLEANING
# ----------------------------------------------------------------------------

# use fiscalyear package to calculate snow year dates, start the snow year on Sept. 1.
# Example: 2017 snow year = Oct 1, 2016 - Sept 30, 2017
fy.setup_fiscal_calendar(start_month=10)

# List of Station IDs in the CDEC Snow Sensor network for the JMT
Sierra_stations_list = ['BSH', 'CBT', 'CRL', 'CWD', 'MHP', 'STL', 'SWM', 'TNY', 'TUM','UTY', 'VLC']

# Load Snow Data (2000 - 3/6/2021)
data_filepath = pathlib.Path(__file__).parent.absolute()
snow = pd.read_csv(os.path.join(data_filepath,'SWE.csv'))

# Clean up date.
# * Split DATE TIME into 2 values
# * Coerce Value column to numeric and drop NA rows to exclude missing data
# * Get columns for Day, Month and Year from the Date column
snow[['Date','Time']] = snow['DATE TIME'].str.split(expand=True)
snow['VALUE']= pd.to_numeric(snow['VALUE'], errors='coerce')
snow.dropna(subset=['Date','VALUE'])
snow['Year'] = snow.Date.str.slice(stop=4).astype('int32')
snow['Month'] = snow.Date.str.slice(start=4, stop=6).astype('int32')
snow['Day'] =snow.Date.str.slice(start=6, stop=8).astype('int32')

# Calculate snow year days for plotting using the Fiscal Year calendar
# Fiscal Year Day 1 = 9/1, so Month 1 = Sept, etc.
snow['SnowYear'] = snow.apply(lambda x: fy.FiscalDate(x['Year'],x['Month'],x['Day']).fiscal_year,axis=1)
snow['SnowMonth'] = snow.apply(lambda x: fy.FiscalDate(x['Year'],x['Month'],x['Day']).fiscal_month,axis=1)
snow['SnowDay'] = snow.apply(lambda x: fy.FiscalDate(x['Year'],x['Month'],x['Day']).fiscal_day,axis=1)

# Get subset of data to plot
plotting_columns = ['STATION_ID','VALUE','Date','SnowYear','SnowMonth','SnowDay']
plot_data = snow[plotting_columns].sort_values(by=['STATION_ID', 'SnowYear', 'SnowMonth','SnowDay'])



# ----------------------------------------------------------------------------
# DATA FOR DASH UI COMPONENTS
# ----------------------------------------------------------------------------
stations_list = snow['STATION_ID'].unique()
if stations_list is None:
    stations_list = ['Please load station data']

snowyears = sorted(snow['SnowYear'].unique(), reverse=True)
if snowyears is None:
    snowyears = ['Please load SWE data']


# Since we are plotting by Snow year dates, need to creating a
# Labeling dataframe for properly labeling the X axis
months_label = ['OCT','NOV','DEC','JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP']
months_int = [10,11,12,1,2,3,4,5,6,7,8,9]
months_day = []

for i in months_int:
  months_day.append(fy.FiscalDate(2021,i,1).fiscal_day)

# create a dictonary
months_dict = {"Label": months_label,
        "Month": months_int,
        "Fiscal_day": months_day}

months = pd.DataFrame(months_dict)

months['Fiscal_day_15'] = months['Fiscal_day'] + 14

# ----------------------------------------------------------------------------
# DATA VISUALIZATION
# ----------------------------------------------------------------------------
default_sensor = 'TUM'
default_years = [2015,2017,2018,2019,2020,2021]
def make_swe_chart(sensor, years):
    plot_df = plot_data[(plot_data['STATION_ID']==sensor) & (plot_data['SnowYear'].isin(years))]
    fig = px.line(plot_df, x="SnowDay", y="VALUE", color='SnowYear')
    fig.update_layout(xaxis=dict(title='',
                      tickvals= months['Fiscal_day'],
                      ticktext = months['Label'] + ' 1'),
                      yaxis = dict(title='SWE (inches)')
                     )
    return fig


# Fig to do: add title, move legend to horizontal, extra color for current year (maybe as it's own trace?)


# ----------------------------------------------------------------------------
# DASH APP LAYOUT
# ----------------------------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LITERA],
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}])
server = app.server


app.layout = html.Div([
    dbc.Row([
        html.H1('Sierra Snow Water Equivalent: JMT Sensors')
    ]),
    dbc.Row([
        dbc.Col([
            html.Label('Snow Sensor: '),
            html.Div([
                dcc.Dropdown(
                            id = 'dd_sensors',
                            options=[{'label': c, 'value': c}
                                                for c in stations_list],
                            value=stations_list[0]
                            )
            ]),
            # html.Div('Station metadata'),
            html.Label('Snow Years: '),
            html.Div([
                dcc.Dropdown(
                            id = 'dd_snowyears',
                            options=[{'label': c, 'value': c}
                                                for c in snowyears],
                            multi =True,
                            value=default_years
                            )
            ]),
            html.Br(),
            html.Br(),
            html.Div([
                html.P('**Very** Beta Dash APP to display snow data from the CDEC snow sensors. This site currently accesses data from 10/1/2000 to 3/6/2021.'),
                dcc.Link('CDEC website to access snow sensor APP ', href='/page-2'),
            ])
        ],md=3),
        dbc.Col([
            html.Div(id='div_chart_swe')
            # Label graph with title for Station

        ],md=9),
    ]),

], style =CONTENT_STYLE)

# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

@app.callback(
    Output('div_chart_swe','children')
    ,
    Input('dd_sensors', 'value'),
    Input('dd_snowyears', 'value'),
)
def dd_values(sensor, years):
    if sensor is None or years is None:
        dcs_children = html.H3('Please select at least one year from the dropdown')
    else:
        fig = make_swe_chart(sensor, years)
        dcs_children = dcc.Graph(id = 'chart_swe', figure = fig)
    return dcs_children
# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
