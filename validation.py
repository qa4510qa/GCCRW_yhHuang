#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from os import listdir
import numpy as np
from pygad import GA as ga
from numpy.lib.function_base import append, average
from statsmodels.distributions.empirical_distribution import ECDF
import AR6_CDS_GCM
import SDmodel_Sim1yr
from importlib.machinery import SourceFileLoader
import xlrd
from openpyxl import Workbook

def testGA():
  function_inputs = [4,-2,3.5,5,-11,-4.7]
  desired_output = 44
  def fitness_func(solution, solution_idx):
    output = np.sum(solution*function_inputs)
    fitness = 1.0 / np.abs(output - desired_output)
    return fitness
  fitness_function = fitness_func

  num_generations = 50
  num_parents_mating = 4

  sol_per_pop = 8
  num_genes = len(function_inputs)

  init_range_low = -2
  init_range_high = 5

  parent_selection_type = "sss"
  keep_parents = 1

  crossover_type = "single_point"

  mutation_type = "random"
  mutation_percent_genes = 10

  ga_instance = ga(num_generations=num_generations,
    num_parents_mating=num_parents_mating,
    fitness_func=fitness_function,
    sol_per_pop=sol_per_pop,
    num_genes=num_genes,
    init_range_low=init_range_low,
    init_range_high=init_range_high,
    parent_selection_type=parent_selection_type,
    keep_parents=keep_parents,
    crossover_type=crossover_type,
    mutation_type=mutation_type,
    mutation_percent_genes=mutation_percent_genes)

  ga_instance.run()

  solution, solution_fitness, solution_idx = ga_instance.best_solution()
  print("Parameters of the best solution : {solution}".format(solution=solution))
  print("Fitness value of the best solution = {solution_fitness}".format(solution_fitness=solution_fitness))

  prediction = np.sum(np.array(function_inputs)*solution)
  print("Predicted output based on the best solution : {prediction}".format(prediction=prediction))

def realTimeValidation(crop, county, growthStage):
  f_outdoorRecord = open('./climateData/realTime_IoT_data/outdoorClimateData/outdoorRecord.txt', 'r')
  f_indoorRecord = open('./climateData/realTime_IoT_data/indoorClimateData/indoorRecord.txt', 'r')
  lines_indoor = f_indoorRecord.readlines()
  lines_outdoor = f_outdoorRecord.readlines()
  for i in range(1440): # sim for 10 days
    print(i)
    f_outdoor = open('./climateData/realTime_IoT_data/outdoorClimateData/testdata_outdoor.txt', 'a')
    f_indoor = open('./climateData/realTime_IoT_data/indoorClimateData/testdata_indoor.txt', 'a')
    f_indoor.write(lines_indoor[i])
    f_outdoor.write(lines_outdoor[i])
    f_indoor.close()
    f_outdoor.close()
    realTimehazardScale = getHazardScale(crop, county, growthStage[0], "realTime")
    riskLight_realTime = realTimeRiskAssessment(realTimehazardScale)
    operationAssessment("realTime",riskLight_realTime)
  f_indoorRecord.close()
  f_outdoorRecord.close()  

def GWLFValidation(waterResourceSystemStnID):
  discharge = []
  GWLF = SourceFileLoader("AgriHydro-master.GWLF", "./GWLF/GWLF.py").load_module()
  GWLF.main(argv=['./GWLF', './WthDATA/historical_daily_{0}.csv'.format(waterResourceSystemStnID), './ParDATA/ShimenGWLFCalibrationPar.csv', 23.5, 0, 'y']) # ['workingDir', 'Tfilename', 'Pfilename', 'latitude', 'dz', 'Output the simulation result or not']
  
def WGENValidation(localStnID,waterResourceSystemStnID):

  def readTEMPCoef(m, group, Stn):
    f = open('./climateData/historyClimateData/{0}_TEMP_coef.csv'.format(Stn), 'r')
    l = f.readline()
    for line in f:
      if int(line.split(',')[0]) == m:
        if group == 'B':
          value = [line.split(',')[3], line.split(',')[6], line.split(',')[9]]
        elif group == 'N':
          value = [line.split(',')[4], line.split(',')[7], line.split(',')[10]]
        elif group == 'A':
          value = [line.split(',')[5], line.split(',')[8], line.split(',')[11]]
        break
    for i in range(len(value)):
      value[i] = float(value[i])
    return value # avg, std, AR1_corr

  def readPRCPCoef(m, group, Stn):
    f = open('./climateData/historyClimateData/{0}_PRCP_coef.csv'.format(Stn), 'r')
    l = f.readline()
    for line in f:
      if int(line.split(',')[0]) == m:
        if group == 'B':
          value = [line.split(',')[9], line.split(',')[10], line.split(',')[11], line.split(',')[18], line.split(',')[19]]
        elif group == 'N':
          value = [line.split(',')[12], line.split(',')[13], line.split(',')[14], line.split(',')[20], line.split(',')[21]]
        elif group == 'A':
          value = [line.split(',')[15], line.split(',')[16], line.split(',')[17], line.split(',')[22], line.split(',')[23]]
        break
    for i in range(len(value)):
      value[i] = float(value[i])
    print(value)
    return value #  P(W), P(W|W), P(W|D), shape, scale

  f = open('./WGENValidation.csv','w')
  f.write('month,B_localTEMP_avg,B_localTEMP_std,B_GWLFTEMP_avg,B_GWLFTEMP_std,B_GWLFPRCP_avg,B_GWLFPRCP_std,N_localTEMP_avg,N_localTEMP_std,N_GWLFTEMP_avg,N_GWLFTEMP_std,N_GWLFPRCP_avg,N_GWLFPRCP_std,A_localTEMP_avg,A_localTEMP_std,A_GWLFTEMP_avg,A_GWLFTEMP_std,A_GWLFPRCP_avg,A_GWLFPRCP_std\n')
  for i in range(1,13,1):
    for k in ['B','N','A']:
      data = [[],[],[]] # TEMP_local, TEMP_GWLF, PRCP_GWLF
      for m in range(100):

        GWLFData = {"Date":[],"TEMP":[],"PRCP":[]}
        TEMP_local=[]

        coef = readTEMPCoef(i, k, waterResourceSystemStnID)
        GWLFData['Date'].append('{0}/{1}/1'.format(now.strftime('%Y'),i))
        GWLFData['TEMP'].append(coef[0])
        for j in range(num_of_days[i-1]-1):
          GWLFData['Date'].append('{0}/{1}/{2}'.format(now.strftime('%Y'),i,j))
          GWLFData['TEMP'].append(coef[0]+coef[2]*(GWLFData['TEMP'][j-1]-coef[0])+np.random.normal(0,1)*coef[1]*pow((1-pow(coef[2],2)),0.5))
        
        coef = readPRCPCoef(i, k, waterResourceSystemStnID)
        GWLFData['PRCP'].extend(np.random.gamma(coef[3], coef[4], num_of_days[i-1])[:])
        # rand = random.random()
        # if rand < coef[0]:
        #   GWLFData['PRCP'].append(0)
        # else:
        #   rand = random.random()
        #   GWLFData['PRCP'].append(np.random.gamma(coef[3], coef[4], 1)[0])
        # for j in range(99):
        #   rand = random.random()
        #   if (GWLFData['PRCP'][j-1] == 0 and rand < coef[2]) or (GWLFData['PRCP'][j-1] != 0 and rand < coef[1]):
        #     GWLFData['PRCP'].append(np.random.gamma(coef[3], coef[4], 1)[0])
        #   else:
        #     GWLFData['PRCP'].append(0)

        coef = readTEMPCoef(i, k, localStnID)
        TEMP_local.append(coef[0])
        for j in range(num_of_days[i-1]-1):
          TEMP_local.append(coef[0]+coef[2]*(GWLFData['TEMP'][j-1]-coef[0])+np.random.normal(0,1)*coef[1]*pow((1-pow(coef[2],2)),0.5))
        data[0].append(np.mean(TEMP_local))
        data[1].append(np.mean(GWLFData['TEMP']))
        data[2].append(sum(GWLFData['PRCP']))

      print(i,k)
      print(np.mean(data[0]),np.std(data[0]))
      print(np.mean(data[1]),np.std(data[1]))
      print(np.mean(data[2]),np.std(data[2]))
      if k == 'B':
        f.write('{0},{1},{2},{3},{4},{5},{6},'.format(i,np.mean(data[0]),np.std(data[0]),np.mean(data[1]),np.std(data[1]),np.mean(data[2]),np.std(data[2])))
      elif k == 'N':
        f.write('{0},{1},{2},{3},{4},{5},'.format(np.mean(data[0]),np.std(data[0]),np.mean(data[1]),np.std(data[1]),np.mean(data[2]),np.std(data[2])))
      else:
        f.write('{0},{1},{2},{3},{4},{5}\n'.format(np.mean(data[0]),np.std(data[0]),np.mean(data[1]),np.std(data[1]),np.mean(data[2]),np.std(data[2])))

def MultiWGValidation():
  TEMP = [[],[],[],[],[],[],[],[],[],[],[],[]]
  PRCP = [[],[],[],[],[],[],[],[],[],[],[],[]]
  f = open('./GWLF/WthDATA/baseline_C0C460.csv', 'r')
  l = f.readline()
  for line in f:
    if '/' in line:
      m = int(line.replace('/n','').split(',')[0].split('/')[1])-1
      TEMP[m].append(float(line.replace('/n','').split(',')[2]))
      PRCP[m].append(float(line.replace('/n','').split(',')[1]))
  f_v = open('./MultiWGValidation.csv','w')
  f_v.write('month,TX01_avg,TX01_std,PP01_avg,PP01_std\n')
  for i in range(12):
    f_v.write('{0},{1},{2},{3},{4}\n'.format(i+1,np.mean(TEMP[i]),np.std(TEMP[i]),np.mean(PRCP[i]),np.std(PRCP[i])))

  TEMP = [[],[],[],[],[],[],[],[],[],[],[],[]]
  PRCP = [[],[],[],[],[],[],[],[],[],[],[],[]]
  f = open('./climateData/historyClimateData/climateData_daily_C0C460.csv', 'r')
  l = f.readline()
  for line in f:
    if '/' in line:
      m = int(line.replace('/n','').split(',')[1].split('/')[1])-1
      TEMP[m].append(float(line.replace('/n','').split(',')[2]))
      PRCP[m].append(float(line.replace('/n','').split(',')[3]))
  f_v = open('./MultiWGValidation_2.csv','w')
  f_v.write('month,TX01_avg,TX01_std,PP01_avg,PP01_std\n')
  for i in range(12):
    f_v.write('{0},{1},{2},{3},{4}\n'.format(i+1,np.mean(TEMP[i]),np.std(TEMP[i]),np.mean(PRCP[i]),np.std(PRCP[i])))

def SDValidation(SDInitial, waterResourceSystemStnID):
  MCDS = []
  SI = []
  DPD = []
  ShiMen = []
  ini_storage = [159376000, 165963000, 205501756]
  discharge_data = open('./SDmodel_validation_discharge.csv'.format(waterResourceSystemStnID), 'r')
  reservoir_discharge = discharge_data.readlines()
  SDInitial_1yr = SDInitial
  for yr in range(3): # 2010~2012
    discharge_1yr = reservoir_discharge[yr*36+1:yr*36+36+1]
    inflow_template = xlrd.open_workbook('./SDmodel/SD_inputData/Data_inflow_template.xlsx')
    workbook = Workbook()
    inflow_newfile = workbook.active
    sheet = inflow_template.sheet_by_index(0)
    inflow_newfile.append(sheet.row_values(0))
    for l in range(1,sheet.nrows,1):
      line = sheet.row_values(l)
      line[2] = float(discharge_1yr[l-1].split(',')[1].replace('\n',''))*86400
      inflow_newfile.append(line)
    workbook.save("./SDmodel/SD_inputData/Data_inflow_validation.xlsx")
    filelist = ["./SDmodel/SD_inputData/Data_inflow_validation.xlsx","./SDmodel/SD_inputData/Data_allocation_template.xlsx"]
    returnData = SDmodel_Sim1yr.main(argv=[ini_storage[yr], SDInitial_1yr['ZhongZhuang Adjustment Reservoir'], SDInitial_1yr['ShiMen WPP Storage Pool'], filelist])
    print(yr)
    SDInitial_1yr['ShiMen Reservoir'] = returnData[0]
    SDInitial_1yr['ZhongZhuang Adjustment Reservoir'] = returnData[1]
    SDInitial_1yr['ShiMen WPP Storage Pool'] = returnData[2]
    SI.append(returnData[3][2])
    MCDS.append(returnData[4])
    DPD.append(returnData[5])
    ShiMen.extend(returnData[6])
  print(ShiMen)
  f = open('./SDmodel_validation_storage.csv', 'w')
  for i in range(len(ShiMen)):
    f.write('{0}\n'.format(ShiMen[i]))

def GAValidation():
  indoorDataScheme = open('./climateData/realTime_IoT_data/indoorClimateData/indoorClimateData_scheme.txt', 'r')
  dataLabel_indoor = indoorDataScheme.readline().split(',')
  indoorDataScheme.close()
  outdoorDataScheme = open ('./climateData/realTime_IoT_data/outdoorClimateData/outdoorClimateData_scheme.txt', 'r')
  dataLabel_outdoor = outdoorDataScheme.readline().split(',')
  outdoorDataScheme.close()
  indoorData_f = open('./climateData/realTime_IoT_data/indoorClimateData/testdata_indoor.txt', 'rb')
  indoorData = indoorData_f.readlines()
  indoorData_f.close()
  outdoorData_f = open('./climateData/realTime_IoT_data/outdoorClimateData/testdata_outdoor.txt', 'rb')
  outdoorData = outdoorData_f.readlines()
  outdoorData_f.close()

  start_time = ''
  indoor_starter=0
  outdoor_starter=0
  for i in range(len(outdoorData)):
    if str(indoorData[1]).split(',')[0] == str(outdoorData[i]).split(',')[0]:
      start_time = str(outdoorData[i]).split(',')[0]
      indoor_starter = 1
      outdoor_starter = i
  if start_time == '':
    for i in range(len(indoorData)):
      if str(outdoorData[1]).split(',')[0] == str(indoorData[i]).split(',')[0]:
        start_time = str(indoorData[i]).split(',')[0]
        indoor_starter = i
        outdoor_starter = 1

  j = outdoor_starter
  indoor_data = {'TIMESTAMP': [], 'AirTC_Avg':[]}
  outdoor_data = {'TIMESTAMP': [],'AirTC_Avg':[], 'RH':[], 'WS':[], 'MN':[],'HR':[]}
  for i in range(indoor_starter,len(indoorData),1):
    if str(indoorData[i]).split(',')[0] == str(outdoorData[j]).split(',')[0]:
      if str(indoorData[i]).split(',')[dataLabel_indoor.index('AirTC_Avg')] == '"NAN"' or str(outdoorData[j]).split(',')[dataLabel_outdoor.index('AirTC_Avg')] == '"NAN"' or str(outdoorData[j]).split(',')[dataLabel_outdoor.index('RH')] == '"NAN"' or str(outdoorData[j]).split(',')[dataLabel_outdoor.index('WS_ms_Avg')] == '"NAN"':
        continue
      else:
        indoor_data['TIMESTAMP'].append(str(indoorData[i]).split(',')[dataLabel_indoor.index('TIMESTAMP')])
        indoor_data['AirTC_Avg'].append(str(indoorData[i]).split(',')[dataLabel_indoor.index('AirTC_Avg')])
        outdoor_data['TIMESTAMP'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('TIMESTAMP')])
        outdoor_data['AirTC_Avg'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('AirTC_Avg')])
        outdoor_data['RH'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('RH')])
        outdoor_data['WS'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('WS_ms_Avg')])
        outdoor_data['MN'].append(int(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('TIMESTAMP')][8:10]))
        outdoor_data['HR'].append(int(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('TIMESTAMP')][14:16]))
      if j == len(outdoorData):
        break
      j+=1
    elif int(str(indoorData[i]).split(',')[0][2:].replace(' ','').replace(':','').replace('-','').replace('"',''))<int(str(outdoorData[j]).split(',')[0][2:].replace(' ','').replace(':','').replace('-','').replace('"','')):
      continue
    else:
      while str(indoorData[i]).split(',')[0] != str(outdoorData[j]).split(',')[0]:
        j+=1
        if j == len(outdoorData):
          break
      if str(indoorData[i]).split(',')[dataLabel_indoor.index('AirTC_Avg')] == '"NAN"' or str(outdoorData[j]).split(',')[dataLabel_outdoor.index('AirTC_Avg')] == '"NAN"':
        continue
      else:
        indoor_data['TIMESTAMP'].append(str(indoorData[i]).split(',')[dataLabel_indoor.index('TIMESTAMP')])
        indoor_data['AirTC_Avg'].append(str(indoorData[i]).split(',')[dataLabel_indoor.index('AirTC_Avg')])
        outdoor_data['TIMESTAMP'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('TIMESTAMP')])
        outdoor_data['AirTC_Avg'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('AirTC_Avg')])
        outdoor_data['RH'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('RH')])
        outdoor_data['WS'].append(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('WS_ms_Avg')])
        outdoor_data['MN'].append(int(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('TIMESTAMP')][8:10]))
        outdoor_data['HR'].append(int(str(outdoorData[j]).split(',')[dataLabel_outdoor.index('TIMESTAMP')][14:16]))
      if j == len(outdoorData):
        break
      j+=1

  for i in range(len(indoor_data['AirTC_Avg'])):
    indoor_data['AirTC_Avg'][i] = float(indoor_data['AirTC_Avg'][i])
    outdoor_data['AirTC_Avg'][i] = float(outdoor_data['AirTC_Avg'][i])
    outdoor_data['RH'][i] = float(outdoor_data['RH'][i])
    outdoor_data['WS'][i] = float(outdoor_data['WS'][i])
  
  num_of_trainingData = len(indoor_data['AirTC_Avg'])-len(indoor_data['AirTC_Avg'])//5
  print(num_of_trainingData)

  aWeek_weights = {
    'MinT':{
      'MinT': [-2.21106665e-01, 1.15090587e+00],
      'HR': [-1.56657910e+01, -4.19990965e-03],
      'MN': [-7.24721046e+00, -9.09076293e-02],
      'RH':[3.02289382e+00, -2.81975878e-02],
      'WS':[-1.02510753e+01, 1.47904145e-01],
    },  
    # [-2.21106665e-01  1.15090587e+00 -1.56657910e+01 -4.19990965e-03 -7.24721046e+00 -9.09076293e-02  3.02289382e+00 -2.81975878e-02 -1.02510753e+01  1.47904145e-01]
    'MaxT':{
      'MinT': [-2.21106665e-01, 1.15090587e+00],
      'HR': [-1.56657910e+01, -4.19990965e-03],
      'MN': [-7.24721046e+00, -9.09076293e-02],
      'RH':[3.02289382e+00, -2.81975878e-02],
      'WS':[-1.02510753e+01, 1.47904145e-01],
    },
  }
  seasonalLongTerm_weights = {
    'TEMP':{
      'TEMP': [-4.3154551, 0.9343015],
      'MN': [3.8008508, 0.05959764]
    }, # [-4.3154551   0.9343015   3.8008508   0.05959764]
  }

  bias_mean = 0
  bias_0_mean = 0
  f = open('./GA_validation_1.csv', 'w')
  solution = [seasonalLongTerm_weights['TEMP']['TEMP'][0],seasonalLongTerm_weights['TEMP']['TEMP'][1],seasonalLongTerm_weights['TEMP']['MN'][0], seasonalLongTerm_weights['TEMP']['MN'][1]]
  print(solution)
  for i in range(num_of_trainingData, len(indoor_data['AirTC_Avg']), 1):
    value = (outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['MN'][i]-solution[2])*solution[3]
    bias = np.abs(value-indoor_data['AirTC_Avg'][i])
    bias_0 = np.abs(outdoor_data['AirTC_Avg'][i]-indoor_data['AirTC_Avg'][i])
    bias_mean += bias**2
    bias_0_mean += bias_0**2
    f.write('{0},{1}/{2},{3},{4},{5},{6},{7}\n'.format(outdoor_data['TIMESTAMP'][i][3:-1], outdoor_data['TIMESTAMP'][i].split('-')[0][3:7], outdoor_data['TIMESTAMP'][i].split('-')[1], outdoor_data['AirTC_Avg'][i], float(indoor_data['AirTC_Avg'][i]), value, bias, bias_0, outdoor_data['MN'][i]))
  f.close()

  bias_mean = (bias_mean/(len(indoor_data['AirTC_Avg'])-num_of_trainingData))**0.5
  bias_0_mean = (bias_0_mean/(len(indoor_data['AirTC_Avg'])-num_of_trainingData))**0.5
  print(bias_mean, bias_0_mean)
  
  f = open('./GA_validation_2.csv', 'w')
  solution = [aWeek_weights['MinT']['MinT'][0],aWeek_weights['MinT']['MinT'][1],aWeek_weights['MinT']['HR'][0],aWeek_weights['MinT']['HR'][1],aWeek_weights['MinT']['MN'][0],aWeek_weights['MinT']['MN'][1], aWeek_weights['MinT']['RH'][0],aWeek_weights['MinT']['RH'][1], aWeek_weights['MinT']['WS'][0],aWeek_weights['MinT']['WS'][1]]
  print(solution)
  for i in range(num_of_trainingData, len(indoor_data['AirTC_Avg']), 1):
    value_2 = (outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['HR'][i]-solution[2])*solution[3]+(outdoor_data['MN'][i]-solution[4])*solution[5]+(outdoor_data['RH'][i]-solution[6])*solution[7]+(outdoor_data['WS'][i]-solution[8])*solution[9]
    bias = np.abs(value_2-indoor_data['AirTC_Avg'][i])
    bias_0 = np.abs(outdoor_data['AirTC_Avg'][i]-indoor_data['AirTC_Avg'][i])
    bias_mean += bias**2
    bias_0_mean += bias_0**2
    f.write('{0},{1}/{2},{3},{4},{5},{6}.{7},{8},{9},{10}\n'.format(outdoor_data['TIMESTAMP'][i][3:-1], outdoor_data['TIMESTAMP'][i].split('-')[0][3:7], outdoor_data['TIMESTAMP'][i].split('-')[1],outdoor_data['AirTC_Avg'][i], float(indoor_data['AirTC_Avg'][i]), value_2, bias, outdoor_data['HR'][i], outdoor_data['MN'][i], outdoor_data['RH'][i], outdoor_data['WS'][i]))
  f.close()

  bias_mean = (bias_mean/(len(indoor_data['AirTC_Avg'])-num_of_trainingData))**0.5
  bias_0_mean = (bias_0_mean/(len(indoor_data['AirTC_Avg'])-num_of_trainingData))**0.5
  print(bias_mean, bias_0_mean)

seasonalLongTerm_P = {}
with open('./inputData.json', newline='') as jsonfile:
  inputData = json.load(jsonfile)
  location = inputData["location"]
  crop = inputData["cropItem"]
  growthStage = inputData["growthStage"]
  seasonalLongTerm_P["TEMP_local"] = inputData["seasonalLongTerm_P_TEMP"]
  seasonalLongTerm_P["TEMP_GWLF"] = inputData["seasonalLongTerm_P_TEMP"]
  seasonalLongTerm_P["PRCP_GWLF"] = inputData["seasonalLongTerm_P_PRCP"]
  first_month = inputData["seasonalLongTerm_first_month"]
  localStnID = inputData["localStnID"]
  waterResourceSystemStnID = inputData["waterResourceSystemStnID"]
  GCM = inputData["GCM"]
  scenarios = inputData["scenarios"]
  variant_id = inputData["variant_id"]
  county = inputData["county"]
  reservoirName = inputData["reservoirName"]
  SDInitial = inputData["SDInitial"]
  reservoirStorageNow = inputData["reservoirStorageNow"]
  waterRight = inputData["waterRight"]

testGA()
realTimeValidation(crop, county, growthStage)
GWLFValidation(waterResourceSystemStnID)
WGENValidation(localStnID,waterResourceSystemStnID)
MultiWGValidation()
SDValidation(SDInitial, waterResourceSystemStnID)
GAValidation()