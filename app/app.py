from flask import Flask, render_template, jsonify, request, url_for
from datetime import datetime
import pandas as pd
import numpy as np
import json
import plotly
import os
import datetime
from netCDF4 import Dataset
import timezonefinder, pytz
import plotly.express as px
from geopy.geocoders import Nominatim


def fixVarName(varName):
	newVarName = str(varName[1:-1])

	newVarName = str(newVarName).replace(' ','').replace(':','_').replace('.','D').replace('-','M')

	return newVarName

############ globals
#outDir = '/home/sumer/my_project_dir/ncep/'
#updated_data_available_file = '/home/sumer/weather/weather-forecast/updated_data_available.txt'

outDir = os.getenv('outDir')
updated_data_available_file = os.getenv('updated_data_available_file')

list_of_ncfiles = [x for x in os.listdir(outDir) if x.endswith('.nc')]
list_of_ncfiles.sort()
time_dim = len(list_of_ncfiles)

"""
varDict = {'TMP_2maboveground': 'Air Temp [C] (2 m above surface)',
		   'TSOIL_0D1M0D4mbelowground':'Soil Temperature [C] - 0.1-0.4 m below ground',
		   'SOILW_0D1M0D4mbelowground':'Volumetric Soil Moisture Content [Fraction] - 0.1-0.4 m below ground',
		   'CRAIN_surface':'Rainfall Boolean [1/0]',
		  }
#varList = ['TMP_2maboveground','TSOIL_0D1M0D4mbelowground','SOILW_0D1M0D4mbelowground', 'CRAIN_surface']
"""

#Relative Humidity [%]
var1 = ':RH:2 m above ground:'

#Temperature [K]
var2 = ':TMP:2 m above ground:'

#Soil Temperature [K]
var3 = ':TSOIL:0-0.1 m below ground:'
var4 = ':TSOIL:0.1-0.4 m below ground:'
var5 = ':TSOIL:0.4-1 m below ground:'
var6 = ':TSOIL:1-2 m below ground:'

#Volumetric Soil Moisture Content [Fraction]
var7 = ':SOILW:0-0.1 m below ground:'
var8 = ':SOILW:0.1-0.4 m below ground:'
var9 = ':SOILW:0.4-1 m below ground:'
var10 = ':SOILW:1-2 m below ground:'

#Specific Humidity [kg/kg]
var11 = ':SPFH:2 m above ground:'

#Dew Point Temperature [K]
var12 = ':DPT:2 m above ground:'

#Pressure Reduced to MSL [Pa]
var13 = ':PRMSL:mean sea level:'

#Pressure [Pa]
var14 = ':PRES:max wind:'

#Wind Speed (Gust) [m/s]
var15 = ':GUST:surface:'

#Total Cloud Cover [%]
var16 = ':TCDC:entire atmosphere:'

#Downward Short-Wave Radiation Flux [W/m^2]
var17 = ':DSWRF:surface:'

#Downward Long-Wave Radiation Flux [W/m^2]
var18 = ':DLWRF:surface:'

#Upward Short-Wave Radiation Flux [W/m^2]
var19 = ':USWRF:surface:'

#Upward Long-Wave Radiation Flux [W/m^2]
var20 = ':ULWRF:surface:'

#Upward Long-Wave Radiation Flux [W/m^2]
var20 = ':ULWRF:surface:'

#Soil Type [-]
var21 = ':SOTYP:surface:'

#Categorical Rain [-] (3 hr forecast)
var22 = ':CRAIN:surface:'

#Precipitation Rate [kg/m^2/s]
var23 = ':PRATE:surface:'

varStr = var1+'|'+var2+'|'+var3+'|'+var4+'|'+var5+'|'+var6+'|'+var7+'|'+var8+'|'+var9+'|'+var10+'|'+var11+'|'+var12+'|'+var13+'|'+var14+'|'+var15+'|'+var16+'|'+var17+'|'+var18+'|'+var19+'|'+var20+'|'+var21+'|'+var22+'|'+var23

###############################################
varDict = {fixVarName(var2) : 'Air Temp [C] (2 m above surface)',
		   fixVarName(var4) : 'Soil Temperature [C] - 0.1-0.4 m below ground',
		   fixVarName(var8) : 'Volumetric Soil Moisture Content [Fraction] - 0.1-0.4 m below ground',
		   fixVarName(var22) : 'Rainfall Boolean [1/0]',
		   fixVarName(var23) : 'Precipitation Rate [mm]',
		   fixVarName(var1) : 'Relative Humidity [%]',
		   fixVarName(var12) : 'Dew Point Temperature [C]',
		   fixVarName(var13) : 'Pressure Reduced to MSL [Pa]',
		   fixVarName(var14) : 'Pressure [Pa]',
		   fixVarName(var15) : 'Wind Speed (Gust) [m/s]',
		   fixVarName(var16) : 'Total Cloud Cover [%]',
		  }

varList = list(varDict.keys())


var_val3D = []
var_val4D = []
#NOTE: the variable are in opposite order var_val4D[lat, lon, forecast_time_index, 0/1/2/3, where 0=CRAIN, 1=SOILW... etc]

# updatedDtStr = list_of_ncfiles[0].split('__')[0]
# updatedDt = datetime.datetime.strptime(updatedDtStr,'%Y%m%d_%H%M%S')
# updatedDtDisplay = datetime.datetime.strftime(updatedDt, '%Y-%m-%dT%H%M%S')

#get the forecast end dt
# forecastEndDtStr = list_of_ncfiles[-1].split('__')[1].split('__')[0]
# forecastEndDt = datetime.datetime.strptime(forecastEndDtStr,'%Y%m%d_%H%M%S')
# forecastEndDtDisplay = datetime.datetime.strftime(forecastEndDt, '%Y-%m-%dT%H%M%S')

i=0
for varName in varList:
	tm_arr = []
	print('Reading data for: '+ varName)
	j=0
	for f in list_of_ncfiles:
		#f = '20211209_000000__20211212_210000__093___gfs.t00z.pgrb2.0p25.f093.grb2.nc'
		
		ncin = Dataset(outDir+f, "r")

		titleStr = varDict[varName]
		var_mat = ncin.variables[varName][:]

		if 'Temp' in titleStr:
			var_val = var_mat.squeeze() - 273.15 #convert to DegC
		elif 'Precipitation Rate' in titleStr:
			var_val = var_mat.squeeze() * 3600 #convert to mm/hr
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
	if len(df) == 0:
		return df

	tf = timezonefinder.TimezoneFinder()
	# From the lat/long, get the tz-database-style time zone name (e.g. 'America/Vancouver') or None
	timezone_str = tf.certain_timezone_at(lat=float(lat), lng=float(lon))
	timezone = pytz.timezone(timezone_str)

	df['FORECAST_DATE_LOCAL']=df.FORECAST_DATE_UTC.apply(lambda x: x + timezone.utcoffset(x))
	
	return df

def getWeatherForecastVars():
	weatherForecastVars = {}
	
	weatherForecastVars['source'] = 'United States NOAA - NOMADS Global Forecast Model'
	weatherForecastVars['variables'] = list(varDict.values())
	weatherForecastVars['updated at time [UTC]'] = 'updatedDt'
	weatherForecastVars['forecast start time [UTC]'] = 'updatedDtDisplay'
	weatherForecastVars['forecast end time [UTC]'] = 'forecastEndDtDisplay'
	weatherForecastVars['forecast type'] = 'hourly'
	weatherForecastVars['Number of time intervals'] = time_dim

	return weatherForecastVars


def get4DWeatherForecast(lon, lat):
	df_all = pd.DataFrame()
	try:
		lat = float(lat)
		lon = float(lon)

		idx=len(varList)-1
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

		try:  #try and get a location, if not, then just report on lat, lon
			geolocator = Nominatim(user_agent="myGeolocator")
			locStr = geolocator.reverse(str(lat)+","+str(lon))
			tok = locStr.address.split(' ')
			loc = ' '.join(tok[3:])
		except:
			loc='Lat='+lat+', Lon='+lon

		#Make the various graphs
		if len(localWeatherForcast_df) != 0:
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

			varName = 'Precipitation Rate [mm]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			precipGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

			varName = 'Relative Humidity [%]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			relativeHumidityGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

			varName = 'Dew Point Temperature [C]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			dewPointGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

			varName = 'Pressure Reduced to MSL [Pa]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			mslPressureGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

			varName = 'Pressure [Pa]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			pressureGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

			varName = 'Wind Speed (Gust) [m/s]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			windSpeedGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

			varName = 'Total Cloud Cover [%]'
			df = localWeatherForcast_df[['FORECAST_DATE_LOCAL',varName]]
			df.set_index(['FORECAST_DATE_LOCAL'], inplace=True, drop=True)
			fig = px.line(df, y=varName, title='Hourly Forecast for '+loc)
			cloudCoverGraph = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


	except ValueError:
		error_res['db function call error'] = 'DB function call failed for getWeatherForecast' 
		error_res['value given'] = 'lat='+str(lat)+', lon='+(str(lon))
		error_msg = jsonify(error_res)

	if len(weatherForcast_df)>0:
		if (returnType=='json'):
			res = jsonify(weatherForcast_df.to_dict(orient='records'))
		else:
			res = render_template('forecast.html', 
				airTempGraph=airTempGraph,
				soilTempGraph=soilTempGraph,
				soilMoistureGraph=soilMoistureGraph,
				rainBoolGraph=rainBoolGraph,
				precipGraph=precipGraph,
				relativeHumidityGraph=relativeHumidityGraph,
				dewPointGraph=dewPointGraph,
				mslPressureGraph=mslPressureGraph,
				pressureGraph=pressureGraph,
				windSpeedGraph=windSpeedGraph,
				cloudCoverGraph=cloudCoverGraph,
				)
	else:
		res = "{'Error': 'WeatherForecast function returned no data'}"
	return res


#main to run the app
if __name__ == '__main__':
	extra_files = [updated_data_available_file,]
	app.run(host='0.0.0.0' , port=4000, debug=True, extra_files=extra_files)
