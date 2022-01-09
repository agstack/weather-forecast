"""
From https://apsjournals.apsnet.org/doi/pdfplus/10.1094/PDIS.2002.86.2.179
"""
#data is a pandas dataframe indexed by hourly data and the 
#returned dataset is a 0/1 based on this models

def get_leafwetnessduration(x):
	"""
	#x is a single row of the dataframe, 
	#so invoke by data_df['LWD']=data_df.apply(get_leafwetnessduration,axis=1)
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

"""
def get_powderymildew(x):
		ascospore_values = calculate_ascospore_stage(hourly_data, lat, lon)
		conidial_res = calculate_conidial_stage(hourly_data)

		return ascospore_values, conidial_res

def calculate_ascospore_stage(self, hourly_data, lat, lon):
	# ascospore stage
	ascospore_values = []
	# use cart sld model to classify leaf wetness hours every day
	leafwetnessmodel = CART_SLD(agls_api_key=self.agls_api_key)
	# take sections of returned data in groups of 24
	i = 0
	temp_sum = 0
	while i < len(hourly_data):
		temp_sum += self.convert_to_fahrenheit(hourly_data[i]['air_temperature'])

		if (i + 1) % 24 == 0:
			temp_avg = temp_sum / 24
			lwd = leafwetnessmodel.calculate(
				lat=lat,
				lon=lon,
				start_dt=hourly_data[i - 23]['timestamp'],
				end_dt=hourly_data[i]['timestamp']
			)
			ascospore_value = classify_ascospore(temp_avg, lwd)
			date = hourly_data[i - 1]['timestamp'].split('T')[0]
			ascospore_values.append((date, ascospore_value))

			temp_sum = 0

		i += 1

	return ascospore_values

def calculate_conidial_stage(self, hourly_data):
	if len(hourly_data) < 72:
		return "Could not compute Conidial Stage -- requires at least 3 days of data"

	def has_6_consecutive_hours(day_data):
		# see if there are 6 consecutive hours of temp between 70 and 85
		for i in range(len(day_data) - 6):
			for j in range(0, 6):
				temp = self.convert_to_fahrenheit(day_data[i + j]['air_temperature'])
				if temp < 70 or temp > 85:
					break
			return True
		return False

	def has_gt_95(day_data):
		for d in day_data:
			if self.convert_to_fahrenheit(d['air_temperature']) >= 95:
				return True
		return False

	# conidial stage
	day_acc = []
	conidial_index = 0
	conidial_start = False
	num_days = int(len(hourly_data) / 24)
	i = 0
	while i < num_days - 3:
		hourly_data_base_i = 24 * i
		# see if there are 6 consecutive hours on this day
		current_day_check = has_6_consecutive_hours(hourly_data[hourly_data_base_i:hourly_data_base_i + 24])
		if current_day_check:
			next_day_check = has_6_consecutive_hours(hourly_data[hourly_data_base_i + 24:hourly_data_base_i + 48])
			if next_day_check:
				final_day_check = has_6_consecutive_hours(hourly_data[hourly_data_base_i + 48:hourly_data_base_i + 72])
				if final_day_check:
					conidial_start = True

					conidial_start_date = hourly_data[hourly_data_base_i]['timestamp'].split('T')[0]
					conidial_next_date = hourly_data[hourly_data_base_i + 24]['timestamp'].split('T')[0]
					conidial_final_date = hourly_data[hourly_data_base_i + 48]['timestamp'].split('T')[0]

					day_acc.extend([
						(conidial_start_date, 20),
						(conidial_next_date, 40),
						(conidial_final_date, 60)
					])

					conidial_index += 60
					i += 3
					break

		i += 1

	if not conidial_start:
		return None

	for j in range(i, num_days):
		# check conditions 2 - 7
		hourly_data_base_j = 24 * j
		date = hourly_data[hourly_data_base_j]['timestamp'].split('T')[0]
		day_hours = hourly_data[hourly_data_base_j:hourly_data_base_j + 24]

		daily_increment = 0
		current_day_check = has_6_consecutive_hours(day_hours)
		if current_day_check:
			daily_increment += 20
		else:
			daily_increment -= 10

		if has_gt_95(day_hours):
			daily_increment -= 10

		if daily_increment > 20:
			daily_increment = 20
		elif daily_increment < -10:
			daily_increment = -10

		conidial_index += daily_increment

		if conidial_index < 0:
			conidial_index = 0

		if conidial_index > 100:
			conidial_index = 100

		day_acc.append((date, conidial_index))

	recommendations = {
		'low': [
			('sulfur dust', '14 days'),
			('micronized sulfur', '18 days'),
			('DMI fungicides', '21 days')
		],
		'med': [
			('sulfur dust', '10 days'),
			('micronized sulfur', '14 days'),
			('DMI fungicides', '17 days')
		],
		'high': [
			('sulfur dust', '7 days'),
			('micronized sulfur', '10 days'),
			('DMI fungicides', '14 days')
		]
	}

	if conidial_index < 45:
		recommendation = recommendations['low']
	elif 45 <= conidial_index < 55:
		recommendation = recommendations['med']
	else:
		recommendation = recommendations['high']

	return recommendation, day_acc



def classify_ascospore(temp_avg, lwd):
	"""
	#Classify ascospore treatment for a day given the average temperature
	#and hours of leaf wetness
	"""
	SAFE = 'safe'
	TREAT = 'treat'

	if temp_avg < 42 or temp_avg > 79:
		return SAFE

	def determine_treatment(threshold):
		return SAFE if lwd < threshold else TREAT

	if temp_avg < 43: return determine_treatment(40)
	if temp_avg < 44: return determine_treatment(34)
	if temp_avg < 45: return determine_treatment(30)
	if temp_avg < 46: return determine_treatment(27.3)
	if temp_avg < 47: return determine_treatment(25.3)
	if temp_avg < 48: return determine_treatment(23.3)
	if temp_avg < 50: return determine_treatment(20)
	if temp_avg < 51: return determine_treatment(19.3)
	if temp_avg < 52: return determine_treatment(18)
	if temp_avg < 53: return determine_treatment(17.3)
	if temp_avg < 54: return determine_treatment(16.7)
	if temp_avg < 56: return determine_treatment(16)
	if temp_avg < 58: return determine_treatment(14.7)
	if temp_avg < 60: return determine_treatment(14)
	if temp_avg < 62: return determine_treatment(13.3)
	if temp_avg < 63: return determine_treatment(12.7)
	if temp_avg < 76: return determine_treatment(12)
	if temp_avg < 77: return determine_treatment(12.7)
	if temp_avg < 78: return determine_treatment(14)

	# temp_avg >= 78
	return determine_treatment(17.3)

"""

	


	
