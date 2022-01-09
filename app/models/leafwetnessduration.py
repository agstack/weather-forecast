"""
From https://apsjournals.apsnet.org/doi/pdfplus/10.1094/PDIS.2002.86.2.179
"""
#data is a pandas dataframe indexed by hourly data and the 
#returned dataset is a 0/1 based on this models

def get_lwd(x):
	"""
	#x is a single row of the dataframe, 
	#so invoke by data_df['LWD']=data_df.apply(f,axis=1)
	"""
    air_temperature = x['Air Temp [C] (2 m above surface)']
    dew_point = x['Dew Point Temperature [C]']
    relative_humidity = x['Relative Humidity [%]']
    wind_speed = x['Wind Speed (Gust) [m/s]']
    
    dew_point_depression = air_temperature - dew_point
    if dew_point_depression >= 3.7:
        return 0

    if wind_speed < 2.5:
        inequality_1 = (
            1.6064 * np.sqrt(air_temperature) +
            0.0036 * air_temperature ** 2 + 0.1531 * relative_humidity -
            0.4599 * wind_speed * dew_point_depression -
            0.0035 * air_temperature * relative_humidity
        ) > 14.4674
        return 1 if inequality_1 else 0

    if relative_humidity >= 87.8:
        inequality_2 = (
            0.7921 * np.sqrt(air_temperature) +
            0.0046 * relative_humidity -
            2.3889 * wind_speed -
            0.039 * air_temperature * wind_speed +
            1.0613 * wind_speed * dew_point_depression
        ) > 37
        return 1 if inequality_2 else 0
    
    return 0
