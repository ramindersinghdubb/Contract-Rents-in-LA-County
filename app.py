# Libraries
from dash import dcc, html, Dash
from dash.dependencies import Output, Input
import dash_bootstrap_components as dbc
import feffery_markdown_components as fmc

from utils.app_setup import (
    YEAR_PLACE_OPTIONS,
    PLACE_YEAR_OPTIONS,
    ALL_YEARS,
    footer_string,
    geodata_map, geodata_plot
)

# -- -- --
# Folders
# -- -- --
data_folder = "data/"
mastergeometries_folder = f"{data_folder}/mastergeometries/"
masterfiles_folder = f"{data_folder}/masterfiles/"


# -- -- --
# Colors
# -- -- --
Cream_color = '#FAE8E0'
SnowWhite_color = '#F5FEFD'
AlabasterWhite_color = '#FEF9F3'
LightBrown_color = '#F7F2EE'
Rose_color = '#FF7F7F'
MaroonRed_color = '#800000'
SinopiaRed_color = '#C0451C'
Teal_color = '#2A9D8F'
ObsidianBlack_color = '#020403'
CherryRed_color = '#E3242B'


# -- --
# App
# -- --
app = Dash(__name__,
           external_stylesheets=[dbc.themes.SIMPLEX, "assets/style.css"])
server = app.server
app.title = 'Contract Rents in Los Angeles County'


app.layout = dbc.Container([
    # Title
    html.Div([html.B("Rents in Los Angeles County")],
             style = {'display': 'block',
                'color': MaroonRed_color,
                'margin': '0.2em 0',
                'padding': '0px 0px 0px 0px', # Numbers represent spacing for the top, right, bottom, and left (in that order)
                'font-family': 'Trebuchet MS, sans-serif',
                'font-size': '220.0%'}
            ),
    
    # Subtitle
    html.Div([
        html.P(f"Median, 25th Percentile, and 75th Percentile Contract Rents for Census Tracts across Cities and Census-Designated Places in Los Angeles County, {min(ALL_YEARS)} to max{(ALL_YEARS)}")
    ], style = {'display': 'block',
                'color': ObsidianBlack_color,
                'margin': '-0.5em 0',
                'padding': '0px 0px 0px 0px',
                'font-family': 'Trebuchet MS, sans-serif',
                'font-size': '105.0%'
               }
            ),
    
    # Horizontal line rule
    html.Div([html.Hr()],
             style = {'display': 'block',
                'height': '1px',
                'border': 0,
                'margin': '-0.9em 0',
                'padding': 0
               }
            ),
    # Labels for dropdowns (discarded)
    
    # Dropdowns
    html.Div([
        html.Div([
            dcc.Dropdown(id          = 'place-dropdown',
                         placeholder = 'Select a place',
                         options     = YEAR_PLACE_OPTIONS[2023],
                         value       = 'LongBeach',
                         clearable   = False
                        )
        ], style = {'display': 'inline-block',
                    'margin': '0 0',
                    'padding': '0px 15px 0px 0px',
                    'width': '22.5%'
                   }
                ),
        html.Div([
            dcc.Dropdown(id          = 'year-dropdown',
                         placeholder = 'Select a year',
                         options     = PLACE_YEAR_OPTIONS['LongBeach'],
                         value       = 2023,
                         clearable   = False
                        )
        ], style = {'display': 'inline-block',
                    'margin': '0 0',
                    'padding': '30px 15px 0px 0px',
                    'width': '12.5%',
                   }
                ),
        html.Div([
            dcc.Dropdown(id='census-tract-dropdown',
                         placeholder = 'Click on a census tract in the map',
                         clearable=True
                        )
        ], style = {'display': 'inline-block',
                    'padding': '0px 30px 0px 0px',
                    'margin': '0 0',
                    'width': '30.0%'
                   }
                ),
    ]
            ),
    # Map and plot
    html.Div([
            dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(children = [html.B("Median Contract Rents"), " in ", html.B(id="map-title1"), " by Census Tract, ", html.B(id="map-title2")],
                                   style = {'background-color': MaroonRed_color,
                                            'color': '#FFFFFF'}
                                  ),
                    dbc.CardBody([geodata_map],
                                 style = {'background-color': AlabasterWhite_color}
                                )
                ])
            ]),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(children = html.B(id = "plot-title"),
                                   style = {'background-color': Teal_color,
                                            'color': '#FFFFFF'}
                                  ),
                    dbc.CardBody([geodata_plot],
                                 style = {'background-color': AlabasterWhite_color}
                                )
                ])
            ])
        ], align='center', justify='center'
               )
    ], style = {
                'padding': '10px 0px 20px 0px',
               }
            ),
    # Footer
    html.Div([
        fmc.FefferyMarkdown(markdownStr    = footer_string,
                            renderHtml     = True,
                            style          = {'background': LightBrown_color,
                                              'margin-top': '1em'
                                             }
                           )
    ]
            ),
    # Data
    dcc.Store( id = 'MASTERFILE' ),
    dcc.Store( id = 'LAT-LON' ),
    dcc.Store( id = 'YEAR_PLACE_OPTIONS', data = YEAR_PLACE_OPTIONS ),
    dcc.Store( id = 'PLACE_YEAR_OPTIONS', data = PLACE_YEAR_OPTIONS ),

], style = {'background-color': LightBrown_color, "padding": "0px 0px 20px 0px",})



# ------------ CALLBACKS ------------ #
#
# Data:
#  year value -> masterfile data
#  year value -> lat/lon center point data
#  
# Dropdowns:
#  year value -> place options
#  place value -> year options
#  place options, year options, map ClickData -> census tract options
#  click data -> census tract value
#
# Titles:
#  place value, year value -> map title
#  place value, census tract value -> plot title
#
# Graphs:
#  place value, year value, census tract value -> map
#  place value, census tract value -> plot
#
# ----------------------------------- #

# -- -- -- --
# Data
# -- -- -- --

# Masterfile
app.clientside_callback(
    """
    async function(selected_year) {
        const url = `https://raw.githubusercontent.com/ramindersinghdubb/Contract-Rents-in-LA-County/refs/heads/main/data/masterfiles/${selected_year}_masterfile.json`;
        const response = await fetch(url);
        const data = await response.json();
        return data;
    }
    """,
    Output('MASTERFILE', 'data'),
    Input('year-dropdown', 'value')
)

# Latitudinal/longitudinal center points
app.clientside_callback(
    """
    async function(selected_year) {
        const url = `https://raw.githubusercontent.com/ramindersinghdubb/Contract-Rents-in-LA-County/refs/heads/main/data/lat_lon_center_points/${selected_year}_latlon_center_points.json`;
        const response = await fetch(url);
        const data = await response.json();
        return data;
    }
    """,
    Output('LAT-LON', 'data'),
    Input('year-dropdown', 'value')
)


# -- -- -- --
# Dropdowns
# -- -- -- --

# Place dropdown options
app.clientside_callback(
    """
    function(selected_year, YEAR_PLACE_OPTIONS) {
        return YEAR_PLACE_OPTIONS[selected_year]
    }
    """,
    Output('place-dropdown', 'options'),
    [Input('year-dropdown', 'value'),
     Input('YEAR_PLACE_OPTIONS', 'data')
    ]
)

# Year dropdown options
app.clientside_callback(
    """
    function(selected_place, PLACE_YEAR_OPTIONS) {
        return PLACE_YEAR_OPTIONS[selected_place]
    }
    """,
    Output('year-dropdown', 'options'),
    [Input('place-dropdown', 'value'),
     Input('PLACE_YEAR_OPTIONS', 'data')
    ]
)

# Census tract options
app.clientside_callback(
    """
    function(selected_place, MASTERFILE) {
        var selected_place = `${selected_place}`;
        var options = MASTERFILE.filter(x => x['ABBREV_NAME'] === selected_place);
        var tract_options = options.map(item => { return item.TRACT });
        return tract_options
    }
    """,
    Output('census-tract-dropdown', 'options'),
    [Input('place-dropdown', 'value'),
     Input('MASTERFILE', 'data')
    ]
)



# Census tract value based on click data
app.clientside_callback(
    """
    function(clickData) {
        return clickData['points']['0']['customdata']
    }
    """,
    Output('census-tract-dropdown', 'value'),
    Input('chloropleth_map', 'clickData')
)



# -- -- -- --
# Titles
# -- -- -- --


# Map title
app.clientside_callback(
    """
    function(selected_place, selected_year, MASTERFILE) {
        var selected_place = `${selected_place}`;
        var selected_year = `${selected_year}`;

        var my_array = MASTERFILE.filter(item => item['ABBREV_NAME'] === selected_place);
        var city_array = my_array.map(({CITY}) => CITY);
        var selected_city = city_array[0];
        return [selected_city, selected_year];
    }
    """,
    [Output('map-title1', 'children'),
     Output('map-title2', 'children')
    ],
    [Input('place-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('MASTERFILE', 'data')
    ]
)


# Plot title
app.clientside_callback(
    """
    function(selected_place, selected_tract, MASTERFILE) {
        if (selected_tract == undefined){
            return "Please click on a tract.";
        } else {
            var my_array = MASTERFILE.filter(item => item['ABBREV_NAME'] === selected_place);
            var city_array = my_array.map(({CITY}) => CITY);
            var selected_city = city_array[0];
            return `${selected_city}, ${selected_tract}`;
        }
    }
    """,
    Output('plot-title', 'children'),
    [Input('place-dropdown', 'value'),
     Input('census-tract-dropdown', 'value'),
     Input('MASTERFILE', 'data')
    ]
)


# -- -- --
# Graphs
# -- -- --

# Choropleth map
app.clientside_callback(
    """
    function(selected_place, selected_year, selected_tract, MASTERFILE, LAT_LON){
        var selected_place = `${selected_place}`;
        var selected_year = Number(selected_year);
        var my_array = MASTERFILE.filter(item => item['ABBREV_NAME'] === selected_place);
        
        var url_path = `https://raw.githubusercontent.com/ramindersinghdubb/Contract-Rents-in-LA-County/refs/heads/main/data/mastergeometries/${selected_year}_mastergeometry.geojson`;
        
        var locations_array = my_array.map( ({GEO_ID}) => GEO_ID);
        var z_array = my_array.map( ({B25058_001E}) => B25058_001E);
        var customdata_array = my_array.map( ({TRACT}) => TRACT);
        
        var lat_lon_array = LAT_LON.filter(item => item['ABBREV_NAME'] === selected_place);
        var lon_array = lat_lon_array.map( ({LON_CENTER}) => LON_CENTER);
        const lon_center = parseFloat(lon_array[0]);

        var lat_array = lat_lon_array.map( ({LAT_CENTER}) => LAT_CENTER);
        const lat_center = parseFloat(lon_array[0]);

        var strings = my_array.map(function(item) {
            return "<b style='font-size:16px;'>" + item['TRACT'] + "</b><br>" + item['CITY'] + "<br><br>"
            + "Median Contract Rent (" + item['YEAR'] + "): <br><b style='color:#800000; font-size:14px;'>" + item['Median'] + "</b> <br><br>"
            + "25th Percentile Contract Rent (" + item['YEAR'] + "): <br><b style='color:#B22222; font-size:14px;'>" + item['25th'] + "</b> <br><br>"
            + "75th Percentile Contract Rent (" + item['YEAR'] + "): <br><b style='color:#B22222; font-size:14px;'>" + item['75th'] + "</b> <br><br><extra></extra>";
            });
    
    
    
        var main_data = [{
            'type': 'choroplethmap',
            'customdata': customdata_array,
            'geojson': url_path,
            'locations': locations_array,
            'featureidkey': 'properties.GEO_ID',
            'colorscale': 'YlOrRd',
            'reversescale': true,
            'z': z_array,
            'zmin': 0, 'zmax': 3500,
            'marker': {'line': {'color': '#020403', 'width': 1.75}, 'opacity': 0.4},
            'text': strings,
            'colorbar': {'outlinewidth': 2,
                         'ticklabelposition': 'outside bottom',
                         'tickprefix': '$',
                         'title': {'font': {'color': '#020403', 'weight': 500}, 'text': 'Median Contract<br>Rents ($)'}},
            'hoverlabel': {'bgcolor': '#FAFAFA', 'bordercolor': '#BEBEBE', 'font': {'color': '#020403'}},
            'hovertemplate': '%{text}'
        }];
    
        var layout = {
            'autosize': true,
            'hoverlabel': {'align': 'left'},
            'map': {'center': {'lat': lat_center, 'lon': lon_center}, 'style': 'streets', 'zoom': 10},
            'margin': {'b': 0, 'l': 0, 'r': 0, 't': 0},
            'paper_bgcolor': '#FEF9F3',
            'plot_bgcolor': '#FEF9F3',
        };
        if (selected_tract != undefined){
            var aux_array = my_array.filter(item => item['TRACT'] === selected_tract);
            var aux_locations_array = aux_array.map( ({GEO_ID}) => GEO_ID);
            var aux_z_array = aux_array.map( ({dummy}) => dummy);
        
            var data_aux = {
                'type': 'choroplethmap',
                'geojson': url_path,
                'locations': aux_locations_array,
                'featureidkey': 'properties.GEO_ID',
                'colorscale': [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
                'showscale': false,
                'z': aux_z_array,
                'zmin': 0, 'zmax': 1,
                'marker': {'line': {'color': '#04D9FF', 'width': 4}},
                'hoverinfo': 'skip',
            }
            main_data.push(data_aux);
        }

        return {'data': main_data, 'layout': layout}
    }
    """,
    Output('chloropleth_map', 'figure'),
    [Input('place-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('census-tract-dropdown', 'value'),
     Input('MASTERFILE', 'data'),
     Input('LAT-LON', 'data'),
    ]
)

# Plot
app.clientside_callback(
    """
    function(selected_place, selected_tract, MASTERFILE){
        if (selected_tract != undefined){
            var selected_place = `${selected_place}`;
            var selected_tract = `${selected_tract}`;
            var my_array = MASTERFILE.filter(item => item['ABBREV_NAME'] === selected_place && item['TRACT'] === selected_tract);
            
            var x_array = my_array.map( ({YEAR}) => YEAR);
            var y_array = my_array.map( ({B25058_001E}) => B25058_001E);
    
            var customdata_array = my_array.map( ({TRACT}) => TRACT);
    
            var strings = my_array.map(function(item) {
                return "<b style='font-size:16px;'>" + item['YEAR'] + "</b><br>" + item['TRACT'] + ", " + item['CITY'] + " <br><br>" +
                "Median Contract Rent: <br><b style='color:#800000; font-size:14px;'>" + item['Median'] + "</b> <br><br>" +
                "25th Percentile Contract Rent: <br><b style='color:#B22222; font-size:14px;'>" + item['25th'] + "</b> <br><br>" +
                "75th Percentile Contract Rent: <br><b style='color:#B22222; font-size:14px;'>" + item['75th'] + "</b> <br><br><extra></extra>";
                });
        
        
        
            var data = [{
                'type': 'scatter',
                'x': x_array,
                'y': y_array,
                'mode': 'lines+markers',
                'line': {'color': '#800000'},
                'marker': {'size': 10, 'line': {'width': 2, 'color': '#F5FBFF'}},
                'text': strings,
                'hoverlabel': {'bgcolor': '#FAFAFA', 'bordercolor': '#BEBEBE', 'font': {'color': '#020403'}},
                'hovertemplate': '%{text}'
            }];
        
            var layout = {
                'font': {'color': '#020403'},
                'hoverlabel': {'align': 'left'},
                'margin': {'b': 40, 't': 40, 'r': 20},
                'autosize': true,
                'uirevision': true,
                'paper_bgcolor': '#FEF9F3',
                'plot_bgcolor': '#FEF9F3',
                'title': {'text': `Median Contract Rents, ${Math.min(...x_array)} to ${Math.max(...x_array)}`, 'x': 0.05},
                'xaxis': {'title': {'text': 'Year', 'ticklabelstandoff': 10}, 'showgrid': false, 'tickvals': x_array},
                'yaxis': {'title': {'text': 'Median Contract Rents ($)', 'standoff': 15}, 'tickprefix': '$', 'gridcolor': '#E0E0E0', 'ticklabelstandoff': 5},
            };
            
            return {'data': data, 'layout': layout};
        }
    }
    """,
    Output('rent_plot', 'figure'),
    [Input('place-dropdown', 'value'),
     Input('census-tract-dropdown', 'value'),
     Input('MASTERFILE', 'data')
    ]
)




# Execute the app
if __name__ == '__main__':
    app.run(debug=False)
