from flask import Flask, render_template, jsonify, request, url_for
from shapely.geometry import Point as Shapely_point, mapping
from geojson import Point as Geoj_point, Polygon as Geoj_polygon, Feature, FeatureCollection
from datetime import datetime
from sqlalchemy import *
import pandas as pd
import geopandas as gpd
import numpy as np
import psycopg2 as pg
import json 
import leaflet as L
from elastic_app_search import Client
from elasticsearch import Elasticsearch
from elasticapm.contrib.flask import ElasticAPM
import matplotlib.colors as cl
import h3
import h3.api.basic_int as h3int
import json
import h3pandas
import cmasher as cmr
import plotly
import plotly.express as px
from scipy.stats import percentileofscore
from scipy import stats
import plotly.graph_objects as go
import os 
import datetime
from netCDF4 import Dataset
import shapely.wkt
import folium
import ftplib
from ftplib import FTP
from pathlib import Path
from os import path, walk

import timezonefinder, pytz
import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim


############ globals
outDir = '/home/sumer/my_project_dir/ncep/'
updated_data_available_file = '/home/sumer/weather/weather-forecast/updated_data_available.txt'

#outDir = '/root/ncep/data/'
#updated_data_available_file = '/root/ncep/scripts/updated_data_available.txt'

list_of_ncfiles = [x for x in os.listdir(outDir) if x.endswith('.nc')]
list_of_ncfiles.sort()
time_dim = len(list_of_ncfiles)

varDict = {'TMP_2maboveground': 'Air Temp [C] (2 m above surface)',
		   'TSOIL_0D1M0D4mbelowground':'Soil Temperature [C] - 0.1-0.4 m below ground',
		   'SOILW_0D1M0D4mbelowground':'Volumetric Soil Moisture Content [Fraction] - 0.1-0.4 m below ground',
		   'CRAIN_surface':'Rainfall Boolean [1/0]',
		  }
#varList = ['TMP_2maboveground','TSOIL_0D1M0D4mbelowground','SOILW_0D1M0D4mbelowground', 'CRAIN_surface']
varList = list(varDict.keys())


var_val3D = []
var_val4D = []
#NOTE: the variable are in opposite order var_val4D[lat, lon, forecast_time_index, 0/1/2/3, where 0=CRAIN, 1=SOILW... etc]

updatedDtStr = list_of_ncfiles[0].split('__')[0]
updatedDt = datetime.datetime.strptime(updatedDtStr,'%Y%m%d_%H%M%S')
updatedDtDisplay = datetime.datetime.strftime(updatedDt, '%Y-%m-%dT%H%M%S')

#get the forecast end dt
forecastEndDtStr = list_of_ncfiles[-1].split('__')[1].split('__')[0]
forecastEndDt = datetime.datetime.strptime(forecastEndDtStr,'%Y%m%d_%H%M%S')
forecastEndDtDisplay = datetime.datetime.strftime(forecastEndDt, '%Y-%m-%dT%H%M%S')

i=0
for varName in varList:
	tm_arr = []
	print('Reading data for :'+varName)
	j=0
	for f in list_of_ncfiles:
		#f = '20211209_000000__20211212_210000__093___gfs.t00z.pgrb2.0p25.f093.grb2.nc'
		
		ncin = Dataset(outDir+f, "r")

		titleStr = varDict[varName]
		var_mat = ncin.variables[varName][:]

		if 'Temp' in titleStr:
			var_val = var_mat.squeeze() - 273.15 #convert to DegC
		else:
			var_val = var_mat.squeeze()
		lons = ncin.variables['longitude'][:]
		lats = ncin.variables['latitude'][:]
		tms = ncin.variables['time'][:]
		#tmstmpStr = datetime.datetime.fromtimestamp(tm.data[0]).strftime('%Y%m%d%H%M%S')

		if j>0:
			var_val3D = np.dstack((var_val3D,var_val.data))
		else:
			var_val3D = var_val.data
		tm_arr.append(tms.data[0])

		ncin.close()
		j=j+1
	if i>0:
		var_val3D_rshp = np.reshape(var_val3D , (720,1440,time_dim,1))
		var_val4D = np.append( var_val3D_rshp , var_val4D , axis = 3)
	else:
		var_val4D = np.reshape(var_val3D , (720,1440,time_dim,1))
	i=i+1

def fixToLocalTime(df,lat,lon):
	tf = timezonefinder.TimezoneFinder()
	# From the lat/long, get the tz-database-style time zone name (e.g. 'America/Vancouver') or None
	timezone_str = tf.certain_timezone_at(lat=lat, lng=lon)
	timezone = pytz.timezone(timezone_str)

	df['FORECAST_DATE_LOCAL'] = df.FORECAST_DATE_UTC + timezone.utcoffset(df.FORECAST_DATE_UTC)
	
	return df

def getWeatherForecastVars():
	weatherForecastVars = {}
	
	weatherForecastVars['source'] = 'United States NOAA - NOMADS Global Forecast Model'
	weatherForecastVars['variables'] = list(varDict.values())
	weatherForecastVars['updated at time [UTC]'] = updatedDt
	weatherForecastVars['forecast start time [UTC]'] = updatedDtDisplay
	weatherForecastVars['forecast end time [UTC]'] = forecastEndDtDisplay
	weatherForecastVars['forecast type'] = 'hourly'
	weatherForecastVars['Number of time intervals'] = time_dim

	return weatherForecastVars


def get4DWeatherForecast(lon, lat):
	df_all = pd.DataFrame()
	try:
		lat = float(lat)
		lon = float(lon)

		idx=3
		updated_dtStr = list_of_ncfiles[0].split('__')[0]
		updated_dt = datetime.datetime.strptime(updated_dtStr, '%Y%m%d_%H%M%S')

		df_all = pd.DataFrame()
		updated_dts = [updated_dt for x in range(0,len(tm_arr))]
		forecast_dts = [datetime.datetime.utcfromtimestamp(int(x)) for x in tm_arr]
		df_all['UPDATED_DATE_UTC']=updated_dts
		df_all['FORECAST_DATE_UTC']=forecast_dts

		for varName in varList:
			df = pd.DataFrame()
			#print(varName)
			#try:
			titleStr = varDict[varName]

			lon_ind = [i for i,v in enumerate(lons.data) if v >= lon][0]
			lat_ind = [i for i,v in enumerate(lats.data) if v >= lat][0]

			vv = var_val4D[lat_ind, lon_ind,:,idx]
			df[titleStr]=vv
			df_all = pd.concat([df_all, df],axis=1)
			idx=idx-1
	except Exception as e:
		print(e)

	return df_all


############

#create the app
app = Flask(__name__)
app.config['JSON_SORT_KEYS']=False

error_res = {}

#rendering the entry using any of these routes:
@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
	return render_template('index.html')

#global weather forecast implementation
@app.route('/weatherForecastVariables')
def weatherForecastVariables():
	try:
		weatherForcastVars = getWeatherForecastVars()

	except ValueError:
		error_res['db function call error'] = 'function call failed for getWeatherForecastVars' 
		error_msg = jsonify(error_res)

	return jsonify(weatherForcastVars)

#global weather forecast implementation
@app.route('/weatherForecast')
def weatherForecast():
	returnType = 'json' #default

	lat = request.args.get('lat')
	lon = request.args.get('lon')
	try:
		returnType = request.args.get('format')
	except:
		returnType = 'json'
	try:
		weatherForcast_df = get4DWeatherForecast(lon, lat)
		localWeatherForcast_df = fixToLocalTime(weatherForcast_df,lat,lon)

		geolocator = Nominatim(user_agent="myGeolocator")
		locStr = geolocator.reverse(str(lat)+","+str(lon))
		tok = locStr.address.split(' ')
		loc = ' '.join(tok[3:])

		#Make the various graphs
		varName = 'Air Temp [C] (2 m above surface)'
		df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
		df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
		fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
		airTempGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


		varName = 'Soil Temperature [C] - 0.1-0.4 m below ground'
		df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
		df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
		fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
		soilTempGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


		varName = 'Volumetric Soil Moisture Content [Fraction] - 0.1-0.4 m below ground'
		df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
		df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
		fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
		soilMoistureGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


		varName = 'Rainfall Boolean [1/0]'
		df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
		df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
		fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
		rainBoolGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


	except ValueError:
		error_res['db function call error'] = 'DB function call failed for getWeatherForecast' 
		error_res['value given'] = 'lat='+str(lat)+', lon='+(str(lon))
		error_msg = jsonify(error_res)

	if len(weatherForcast_df)>0:
		if (returnType=='json'):
			res = jsonify(weatherForcast_df.to_dict(orient='records'))
		else:
			localWeatherForcast_df = fixToLocalTime(weatherForcast_df,lat,lon)
			res = render_template('forecast.html', 
				airTempJSON=airTempGraph,
				soilTempJson=soilTempGraph,
				soilMoistureJson=soilMoistureGraph,
				rainBoolJson=rainBoolGraph
				)
	else:
		res = "{'Error': 'WeatherForecast function returned no data'}"
	return res


#main to run the app
if __name__ == '__main__':
	extra_files = [updated_data_available_file,]
	app.run(host='0.0.0.0' , port=5000, debug=True, extra_files=extra_files)
