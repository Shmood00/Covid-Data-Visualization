import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Output
from dash.dependencies import Input
import requests, json
import pandas as pd
import plotly.express as px
import urllib.request
from flask_caching import Cache

#Load Dash Bootstrap package for CSS theme
#dash-bootstrap-components
external_stylesheets = [dbc.themes.BOOTSTRAP]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "COVID-19 Visualization"
app.config.suppress_callback_exceptions = True

#Configure Flask-Caching
#Holds maximum of 20 files
cache = Cache(app.server, config={
    'CACHE_TYPE':'filesystem',
    'CACHE_DIR':'cache',
    'CACHE_THRESHOLD':20
})

TIMEOUT_API = 300 #How often API data is pulled
TIMEOUT_GEO = 1800 #How often GeoJSON is read

#Funciton to retrieve COVID-19 data from API
#Data received is cached for 5 minutes
@cache.memoize(timeout=TIMEOUT_API)
def update_data():
    
    #Grab data from API
    url = requests.get("https://covid-api.com/api/reports?iso=CAN")
    url_json = url.json()

    #Changing name of Yukon Territory in API data to match GeoJSON data
    url_json['data'][15]['region']['province'] = "Yukon Territory"

    #Converting JSON data to a pandas dataframe
    return pd.json_normalize(url_json['data'])

#Get COVID-19 data for the whole world
#Data received is cahced for 5 minutes
@cache.memoize(timeout=TIMEOUT_API)
def world_data():
    url = requests.get("https://corona.lmao.ninja/v2/countries?yesterday=True")
    url_json = url.json()

    return pd.json_normalize(url_json)

#Funciton to retreive Canada GeoJSON data
#Data is stored for 30 min
@cache.memoize(timeout=TIMEOUT_GEO)
def canada_geojson():
    
    #Grab GeoJSON data of Canada
    with open("canada.geojson", "r") as f:
            canada = f.read()
    
    canada = json.loads(canada)

    return canada

#Create website navbar
navbar = dbc.NavbarSimple(
    brand="COVID-19",
    color="dark",
    dark=True,
    children=[
        dcc.Location(id='url', refresh=False),
        dbc.NavItem(dbc.NavLink("Canada", href="/")),
        dbc.NavItem(dbc.NavLink("World", href="/world")),
        html.Div(id='content') #page is rendered here?
    ]
)

#Create website layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

#Main page of website that displays Canada's COVID-19 data
main_page = html.Div(
    children=[
        navbar,
        html.Div(
            style={"padding-top":30, "padding-left":100,"padding-right":100,"padding-bottom":10,"width":"auto"},
            className="mx-auto",
            children=[
                dbc.Card([
                    dbc.CardHeader("COVID-19 Data In Canada"),
                    dbc.CardBody([
                        html.Div([
                            "Filters:",
                            dcc.Dropdown(
                                id="filter-values",
                                value="confirmed",
                                options=[
                                    {"label":"Confirmed cases", "value":"confirmed"},
                                    {"label":"Active cases", "value":"active"},
                                    {"label":"Total deaths", "value":"deaths"},
                                    {"label":"Recovered", "value":"recovered"}
                                ]
                            )
                        ]),
                        dcc.Graph(id="my-graph")  
                    ])
                ])
            ]
        )
    ]
)

#Page of website that displays the world's COVID-19 data
world_layout = html.Div(
    children=[
        navbar,
        html.Div(
            style={"padding-top":30, "padding-left":100,"padding-right":100,"padding-bottom":10, "width":"auto"},
            className="mx-auto",
            children=[
                dbc.Card([
                    dbc.CardHeader("COVID-19 Data World Wide"),
                    dbc.CardBody([
                        html.Div([
                            "Filters:",
                            dcc.Dropdown(
                                id="world-filters",
                                value="cases",
                                options=[
                                    {"label":"Confirmed cases", "value":"cases"},
                                    {"label":"Active cases", "value":"active"},
                                    {"label":"Active cases per million", "value":"activePerOneMillion"},
                                    {"label":"Cases today", "value":"todayCases"},
                                    {"label":"Cases per million", "value":"casesPerOneMillion"},
                                    {"label":"Tests", "value":"tests"},
                                    {"label":"Tests per million", "value":"testsPerOneMillion"},
                                    {"label":"Critical cases", "value":"critical"},
                                    {"label":"Critical per million", "value":"criticalPerOneMillion"},
                                    {"label":"Deaths", "value":"deaths"},
                                    {"label":"Deaths today", "value":"todayDeaths"},
                                    {"label":"Deaths per million", "value":"deathsPerOneMillion"},
                                    {"label":"Recovered", "value":"recovered"},
                                    {"label":"Recovered today", "value":"todayRecovered"},
                                    {"label":"Recovered per million", "value":"recoveredPerOneMillion"}
                                ]
                            ),
                            dcc.Graph(id="world-graph")
                            
                        ])
                    ])
                ])
            ]
        )
    ]
)

#Callback to update Canada's map when different filters are selected
@app.callback(
    Output("my-graph", "figure"),
    [Input("filter-values", "value")]
)

def update_chart(selected):
    #Load COVID-19 data from API
    dff = update_data()

    #Grab Canada GeoJSON data
    canada = canada_geojson()

    #Convert selected value to a string (used to get discrete colours for the map)
    dff[selected] = dff[selected].astype(str)

    #Create the map
    fig = px.choropleth(dff, geojson=canada,locations=dff['region.province'],
                    hover_name='region.province', hover_data={'date':True,'last_update':True,selected: True, 'region.province':False}, 
                    color=dff[selected], featureidkey='properties.name', projection='natural earth'
    )
    
    #Only show region of map that relates to what's set in locations (in this case the provinces of Canada)
    fig.update_geos(fitbounds='locations', visible=False)
    fig.update_layout(margin={"r":0,"t":20,"l":0,"b":0})

    return fig 


#Callback that updates the world map when different filters are chosen
@app.callback(
    Output("world-graph", "figure"),
    [Input("world-filters", "value")]
)
def update_world_map(selected):
    dff = world_data()

    #dff[selected] = dff[selected].astype(str)

    fig = px.choropleth(dff, locations=dff['countryInfo.iso3'],
                    hover_name='country', hover_data={'countryInfo.iso3':False, 'population':True,
                                                        'continent':True},
                    color_continuous_scale='sunset',
                    color=dff[selected], projection="orthographic")
    
    fig.update_layout(height=800)

    fig.update_geos(showocean=True, oceancolor='#66a3ff')
    
    return fig


#Display the webpages to the user
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)

def display_page(pathname):
    if pathname == "/":
        return main_page
    elif pathname == "/world":
        return world_layout


if __name__ == "__main__":
    app.run_server(threaded=True)
