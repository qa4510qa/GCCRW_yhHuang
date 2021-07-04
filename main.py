#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
from os import listdir
import numpy as np
import pandas as pd
from pygad import GA as ga
import math
import random
import csv
from numpy.lib.function_base import append, average
import requests
from datetime import date, datetime
import matplotlib.pyplot as plt
from statsmodels.distributions.empirical_distribution import ECDF
import AR6_CDS_GCM
import SDmodel_Sim1yr
from importlib.machinery import SourceFileLoader
import xlrd
from openpyxl import Workbook
import scipy.stats as stats
import seaborn as sns
# from statsmodels.distributions.empirical_distribution import ECDF

CWB_API_Key = 'CWB-B7BC29A4-FADA-4DE6-9918-F2FA71A55F80'
AGRi_API_ProjectKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0bmFtZSI6IlNETGFiX0lvVF9Qcm9qZWN0XzIwMjEiLCJuYW1lIjoicjA4NjIyMDA1IiwiaWF0IjoxNjEzNzk5Nzk2fQ.elm1KN4D7geluaVTrv-J9OoZ9aFEOFb-juiVfUrFQTc'
now = datetime.now()
fuzzyRange = {"AirTC_Avg":1, "RH":5, "PAR_Avg":50, "VW_F_Avg":5, "WS_ms_Avg":3, "Water_Demand":0, "Water_Storage":0, "SI":0, "DPD":0, "MCDS":0}
riskScale = ["very_low","low","slightly_low","proper","slightly_high","high","very_high"]
riskLightScale = ["red","orange","yellow","green","yellow","orange","red"]
num_of_days=[31,28,31,30,31,30,31,31,30,31,30,31]
N = [10, 10, 11, 10, 10, 8, 10, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 10, 10,
     10, 11, 10, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 10, 10, 10, 11]


def getHazardScale(crop, county, growthStage, timeScale, first_month=0):
  hazardScale = {} #{[stage]:{[climateFactor]:[value]}}
  if timeScale == "realTime":
    current_time = now.strftime("%H")
    if int(current_time) >= 6 and int(current_time) < 18:
      conditionItem = growthStage + "_day"
    else:
      conditionItem = growthStage + "_night" # get the objective condition for crop in such stage and time

    with open('./conditionData/{0}ClimateCondition/{1}.csv'.format(crop ,conditionItem), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] != '\ufeff':
          hazardScale[row[0]] = row[1:] 
  elif timeScale == "aWeek":
    with open('./conditionData/{0}ClimateCondition/{1}_day.csv'.format(crop ,growthStage), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] != '\ufeff':
          hazardScale['{0}_day'.format(row[0])] = row[1:]
    with open('./conditionData/{0}ClimateCondition/{1}_night.csv'.format(crop ,growthStage), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] != '\ufeff':
          hazardScale['{0}_night'.format(row[0])] = row[1:]
  elif timeScale == "seasonalLongTerm":
    hazardScale = {'AirTC_Avg_avg':[], 'Storage_Limit_{0}'.format(first_month):[], 'Storage_Limit_{0}'.format(first_month+1):[], 'Storage_Limit_{0}'.format(first_month+2):[]}
    for i in range(3): # 3 month
      with open('./conditionData/{0}ClimateCondition/{1}_avg.csv'.format(crop ,growthStage[i]), newline='') as csvfile:
        rows = csv.reader(csvfile)
        for row in rows:
          if row[0] == 'AirTC_Avg':
            hazardScale['AirTC_Avg_avg'].append(row[1:])
    with open('./conditionData/ShimenReservoirCondition/monthly_allTime.csv'.format(crop ,growthStage[i]), newline='') as csvfile:
        rows = csv.reader(csvfile)
        for row in rows:
          if row[0] in hazardScale.keys():
            hazardScale[row[0]] = row[1:]
  elif timeScale == "climateChange":
    hazardScale = {'nursery_AirTC_Avg_avg':[], 'flowering_AirTC_Avg_avg':[], 'SI':[], 'MCDS':[], 'DPD':[]}
    with open('./conditionData/{0}ClimateCondition/nursery_avg.csv'.format(crop), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        print(row[0])
        if row[0] == 'AirTC_Avg':
          hazardScale['nursery_AirTC_Avg_avg'] = row[1:]
    with open('./conditionData/{0}ClimateCondition/flowering_avg.csv'.format(crop), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] == 'AirTC_Avg':
          hazardScale['flowering_AirTC_Avg_avg'] = row[1:]
    with open('./conditionData/{0}WRSCondition/allTime.csv'.format(county), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] == 'SI':
          hazardScale['SI'] = row[1:]
        if row[0] == 'MCDS':
          hazardScale['MCDS'] = row[1:]
        if row[0] == 'DPD':
          hazardScale['DPD'] = row[1:]

    # files = listdir("./conditionData/{0}ClimateCondition".format(crop))
    # for file in files:
    #   if file[-3:] == 'csv':
    #     with open('./conditionData/{0}ClimateCondition/{1}'.format(crop ,file), newline='') as csvfile:
    #       rows = csv.reader(csvfile)
    #       for row in rows:
    #         if row[0] != '\ufeff':
    #           hazardScale['{0}_{1}_{2}'.format( file[:file.index('_')], row[0], file[file.index('_')+1:file.index('.')])] = row[1:]
  print('{0} hazardScale: {1}\n'.format(timeScale, hazardScale))
  return hazardScale

def realTimeRiskAssessment(hazardScale):
  riskLight = {}
  
  with open ('./climateData/realTime_IoT_data/indoorClimateData/indoorClimateData_scheme.txt', 'r') as indoorDataScheme:
    dataLabel_indoor = indoorDataScheme.readline().split(',')

  with open ('./climateData/realTime_IoT_data/outdoorClimateData/outdoorClimateData_scheme.txt', 'r') as outdoorDataScheme:
    dataLabel_outdoor = outdoorDataScheme.readline().split(',')
  
  with open('./climateData/realTime_IoT_data/indoorClimateData/testdata_indoor.txt', 'rb') as indoorData:
    line_indoor = indoorData.readline()
    off = -120
    while True:
      indoorData.seek(off,2) 
      lines = indoorData.readlines() 
      if len(lines)>=2: 
        line_indoor = lines[-1].decode().split(',')
        break
      off*=2 

  with open('./climateData/realTime_IoT_data/outdoorClimateData/testdata_outdoor.txt', 'rb') as outdoorData:
    line_outdoor = outdoorData.readline()
    off = -120
    while True:
      outdoorData.seek(off,2) 
      lines = outdoorData.readlines() 
      if len(lines)>=2: 
        line_outdoor = lines[-1].decode().split(',')
        break
      off*=2 

  risk = {}
  for i in hazardScale.keys():
    if i == 'Water_Demand': break
    elif i in dataLabel_indoor:
      value = line_indoor[dataLabel_indoor.index(i)]
    elif i in dataLabel_outdoor:
      value = line_outdoor[dataLabel_outdoor.index(i)]
    for j in range(6):
      if hazardScale[i][j]== '-':
        continue
      elif j==0 and int(hazardScale[i][j])-fuzzyRange[i]>=float(value):
        risk[i]=riskScale[0]
        break
      elif j==5 and int(hazardScale[i][j])+fuzzyRange[i]<=float(value):
        risk[i]=riskScale[6]
      elif (int(hazardScale[i][j])+fuzzyRange[i])<=float(value) and hazardScale[i][j+1]== '-':
        risk[i]=riskScale[j+1]
        break
      elif (int(hazardScale[i][j])+fuzzyRange[i])<=float(value) and (int(hazardScale[i][j+1])-fuzzyRange[i])>=float(value):
        risk[i]=riskScale[j+1]
        break
      elif float(value)>=(int(hazardScale[i][j])-fuzzyRange[i]) and float(value)<=(int(hazardScale[i][j])+fuzzyRange[i]):
        r=random.random()
        if r>=(float(value)-(int(hazardScale[i][j])-fuzzyRange[i]))/(2*fuzzyRange[i]):
          risk[i]=riskScale[j]
        else:
          risk[i]=riskScale[j+1]
        break
  print('realTime riskScale:{0}\n'.format(risk))
  riskLight={}
  if risk["WS_ms_Avg"][-3:]=="low":
    riskLight['強風']="green"
  else:
    riskLight["強風"]=riskLightScale[riskScale.index(risk["WS_ms_Avg"])]
  if risk["RH"][-3:]=="low":
    riskLight['高濕']="green"
  else:
    riskLight['高濕']=riskLightScale[riskScale.index(risk["RH"])]
  
  if risk["VW_F_Avg"][-3:]=="igh":
    riskLight['乾旱']="green"
  else:
    riskLight['乾旱']=riskLightScale[riskScale.index(risk["VW_F_Avg"])]

  if risk["AirTC_Avg"][-3:]=="low":
    riskLight["高溫"]="green"
    riskLight['低溫']=riskLightScale[riskScale.index(risk["AirTC_Avg"])]
  else:
    riskLight["低溫"]="green"
    riskLight['高溫']=riskLightScale[riskScale.index(risk["AirTC_Avg"])]
  
  record = open('./systemRecord/realTime_riskLight.txt', 'r')
  record = record.readlines()
  if riskLight['高溫']=="orange" and len(record)>=4:
    a=0
    for i in range(3): # 忍受時間設為30分鐘
      if record[-1].split('{')[-1].replace("}",'').split(',')[4].split(':')[1].replace(" ",'').replace("\n",'').replace("'",'') == "orange":
        a+=1
    if a == 3:
      riskLight['高溫']=="red"
  if riskLight['低溫']=="orange"and len(record)>=4:
    a=0
    for i in range(3): # 忍受時間設為30分鐘
      if record[-1].split('{')[-1].replace("}",'').split(',')[3].split(':')[1].replace(" ",'').replace("\n",'').replace("'",'') == "orange":
        a+=1
    if a == 3:
      riskLight['低溫']=="red"
  if (riskLight['高濕']=="orange" or riskLight['高濕']=="yellow") and len(record)>=145:
    a=0
    for i in range(144): # 忍受時間設為1天
      if record[-1].split('{')[-1].replace("}",'').split(',')[1].split(':')[1].replace(" ",'').replace("\n",'').replace("'",'') == "red":
        a+=2
      elif record[-1].split('{')[-1].replace("}",'').split(',')[1].split(':')[1].replace(" ",'').replace("\n",'').replace("'",'') == "orange":
        a+=1
      elif record[-1].split('{')[-1].replace("}",'').split(',')[1].split(':')[1].replace(" ",'').replace("\n",'').replace("'",'') == "green":
        a=0
        break
    if a >= 144:
      riskLight['高濕'] = riskLightScale[max(0,riskLightScale.index(riskLight["高濕"][0])-1)]
    
  print('realTime riskLight:{0}\n'.format(riskLight))
  f = open('./systemRecord/realTime_riskLight.csv', 'a')
  f.write('\n')
  for Hz in riskLight.keys():
    f.write('{0},{1},{2}\n'.format(now.strftime('%Y-%m-%d %H:%M'),Hz,riskLight[Hz]))
  f.close()
  f = open('./systemRecord/realTime_riskLight.txt', 'a')
  f.write('{0}{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'),riskLight))
  f.close()
  return riskLight

def aWeekRiskAssessment(location, hazardScale, riskLight_realTime):
  rawData = {"MinT":[],"MaxT":[],"RH":[],"WS":[],"Water_Storage":[],"HR":[], "MN":[]}
  riskLight={"高溫":[],"低溫":[],"高濕":[],"強風":[],"乾旱":[]}
  try:
    climatData_aWeekForecast = requests.get('https://opendata.cwb.gov.tw/api/v1/rest/datastore/{0}?locationName={1}&elementName={2}&sort={3}&Authorization={4}'.format("F-D0047-007",location,"","time",CWB_API_Key))
    #climatData_aWeekForecast = requests.get('https://agriapi.tari.gov.tw/api/CWB_PreWeathers/oneweekPredictions?postalCode={0}&eleName=MinT%2CMaxT%2CRH%2CWind&projectkey={1}'.format(postalCode ,AGRi_API_ProjectKey))
    climatData_aWeekForecast = climatData_aWeekForecast.json()["records"]["locations"][0]["location"][0]["weatherElement"] #["output"]["data"]["content"]
    climatData_aWeekForecast=list(filter(lambda x: x['elementName']=="RH" or x['elementName']=="WS" or x['elementName']=="MaxT" or x['elementName']=="MinT", climatData_aWeekForecast))

  except requests.exceptions.HTTPError as errh:
      print(errh)
  except requests.exceptions.ConnectionError as errc:
      print(errc)
  except requests.exceptions.Timeout as errt:
      print(errt)
  except requests.exceptions.RequestException as err:
      print(err)
  
  for i in climatData_aWeekForecast:
    name=i["elementName"]
    now_day = now.strftime("%m-%d")
    data=list(filter(lambda x: x['startTime'][5:10]!=now_day , i["time"]))
    for j in data:
      rawData[name].append(float(j["elementValue"][0]["value"]))
      rawData["MN"].append(int(j['endTime'][5:7]))
      rawData["HR"].append(int(j['endTime'][11:13])-6)
  
  indoorData = indoorClimateDataEstimation("aWeek",rawData)
  # 乾旱評估，分析水塔蓄水量變化
  with open ('./climateData/realTime_IoT_data/systemCapacityData/systemCapacityData_scheme.txt', 'r') as systemDataScheme:
    dataLabel_system = systemDataScheme.readline().split(',')

  with open('./climateData/realTime_IoT_data/systemCapacityData/testdata_systemCapacity.txt', 'rb') as systemData:
    line_system = systemData.readline()
    off = -120
    while True:
      systemData.seek(off,2) 
      lines = systemData.readlines() 
      if len(lines)>=14: 
        break
      off*=2 
    Number_of_Tomato_Plants = int(lines[-1].decode().split(',')[dataLabel_system.index('Number_of_Tomato_Plants')])
    Water_Storage_record = []
    delta = []
    for i in lines:
      Water_Storage_record.append(float(i.decode().split(',')[dataLabel_system.index('Water_Storage')]))
    for i in range(len(Water_Storage_record)-1):
      delta.append(Water_Storage_record[i+1]-Water_Storage_record[i])
    delta_std = np.std(delta)
    delta_avg = np.mean(delta)
    for i in delta:
      if (i-delta_avg)/delta_std >2:      # 去除一次性大量水源補注事件，outlier
        delta.remove(i)
    delta_avg = np.mean(delta)
  for i in range(7):
    indoorData["Water_Storage"].append((Water_Storage_record[-1]+i*delta_avg)/(Number_of_Tomato_Plants*3)) # 沒有入流水的情況下作物灌溉三天
    indoorData["Water_Storage"].append(0)
  risk = {"MinT":[],"MaxT":[],"RH":[],"WS":[],"Water_Storage":[]}
  for i in indoorData:
    for j in range(len(indoorData[i])):
      value = indoorData[i][j]
      corrFactor = {"MinT":"AirTC_Avg","MaxT":"AirTC_Avg","RH":"RH","WS":"WS_ms_Avg","Water_Storage":"Water_Demand"} #climate factor and risk factor corresponding
      hazardScaleItem = []
      if j%2 == 0: #day(6:00 ~ 18:00)
        if i == 'MinT' or i == 'MaxT':
          hazardScaleItem = hazardScale["AirTC_Avg_day"]
        elif i == "RH":
          hazardScaleItem = hazardScale["RH_day"]
        elif i == "WS":
          hazardScaleItem = hazardScale["WS_ms_Avg_day"]
        elif i == "Water_Storage":
          hazardScaleItem = hazardScale["Water_Demand_day"]
      else: #night(18:00 ~ 6:00)
        if i == 'MinT' or i == 'MaxT':
          hazardScaleItem = hazardScale["AirTC_Avg_night"]
        elif i == "RH":
          hazardScaleItem = hazardScale["RH_night"]
        elif i == "WS":
          hazardScaleItem = hazardScale["WS_ms_Avg_night"]
        elif i == "Water_Storage":
          hazardScaleItem = hazardScale["Water_Demand_night"]
      for k in range(6):
        if hazardScaleItem[k]== '-':
          continue
        elif k==0 and float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]>=float(value):
          risk[i].append(riskScale[0])
          break
        elif k==5 and float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]<=float(value):
          risk[i].append(riskScale[6])
        elif (float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and hazardScaleItem[k+1]== '-':
          risk[i].append(riskScale[k+1])
          break
        elif (float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and (float(hazardScaleItem[k+1])-fuzzyRange[corrFactor[i]])>=float(value):
          risk[i].append(riskScale[k+1])
          break
        elif float(value)>=(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]) and float(value)<=(float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]):
          r=random.random()
          if r>=(float(value)-(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]))/(2*fuzzyRange[corrFactor[i]]):
            risk[i].append(riskScale[k])
          else:
            risk[i].append(riskScale[k+1])
          break
  
  print('aWeek riskScale:{0}\n'.format(risk))

  for i in risk:
    for j in range(len(risk[i])):
      if i == "MinT":
        if risk[i][j][-3:]=="igh":
          riskLight["低溫"].append("green")
        else:
          riskLight["低溫"].append(riskLightScale[riskScale.index(risk[i][j])])
      elif i == "MaxT":
        if risk[i][j][-3:]=="low":
          riskLight["高溫"].append("green")
        else:
          riskLight["高溫"].append(riskLightScale[riskScale.index(risk[i][j])])
      elif i == "RH":
        if risk[i][j][-3:]=="low":
          riskLight["高濕"].append("green")
        else:
          riskLight["高濕"].append(riskLightScale[riskScale.index(risk[i][j])])
      elif i == "WS":
        if risk[i][j][-3:]=="low":
          riskLight["強風"].append("green")
        else:
          riskLight["強風"].append(riskLightScale[riskScale.index(risk[i][j])])
      elif i == "Water_Storage":
        if risk[i][j][-3:]=="igh":
          riskLight["乾旱"].append("green")
        else:
          riskLight["乾旱"].append(riskLightScale[riskScale.index(risk[i][j])])
  
  print('aWeek riskLight:{0}\n'.format(riskLight))
  f = open('./systemRecord/aWeek_riskLight.csv', 'a')
  f.write('\n')
  for Hz in riskLight.keys():
    f.write('{0},{1}'.format(now.strftime('%Y-%m-%d %H:%M'),Hz))
    for item in riskLight[Hz]:
      f.write(',{0}'.format(item))
    f.write('\n')
  f.close()
  f = open('./systemRecord/aWeek_riskLight.txt', 'a')
  f.write('{0}{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'),riskLight))
  f.close()
  return riskLight

def seasonalLongTermRiskAssessment(hazardScale, riskLight_aWeek, P, first_month, localStnID, waterResourceSystemStnID, reservoirStorageNow, waterRight):
  # rawData = {"date":[],"TEMP_local":[],"PRCP_GWLF":[], "TEMP_GWLF":[]}
  DataArray_month = [[],[],[],[]] # month, TEMP_local, PRCP_GWLF, TEMP_GWLF
  GWLFData = {"Date":[],"TEMP":[],"PRCP":[]}
  generatedData = {'TEMP':[], 'MN':[], 'water_storage':[0,0,0]}
  IsPRCPZeroRate = [] # for PRCP_GWLF only
  AR1Corr = [[],[]] # TEMP_local, TEMP_PRCP
  Climate_ratio={"TEMP_local":[],"PRCP_GWLF":[], "TEMP_GWLF":[]}
  for i in Climate_ratio.keys():
    for j in range(3):
      rand = random.random()
      if rand<=P[i][j][0]:
        Climate_ratio[i].append('B')
      elif (rand>P[i][j][0] and rand<=P[i][j][1]):
        Climate_ratio[i].append('N')
      else :
        Climate_ratio[i].append('A')

  def weib(x,n,a):
    return (a / n) * (x / n)**(a - 1) * np.exp(-(x / n)**a)

  def generatePRCPRatio():
    for i in range(1,13,1):
      historyData_WRS=open("./climateData/historyClimateData/climateData_daily_{0}.csv".format(waterResourceSystemStnID),"r")
      line_WRS = historyData_WRS.readline()
      f = open('./climateData/historyClimateData/{0}_PRCP_m_{1}.csv'.format(waterResourceSystemStnID, i),"w")
      for line in historyData_WRS:
        if line.split(',')[1] != "" and int(line.split(',')[1].split('/')[1]) == i:
          f.write('{0},{1}\n'.format(line.split(',')[1], line.split(',')[3].replace('\n','')))
      historyData_WRS.close()
      f.close()
    
    PRCPRatio = open('./climateData/historyClimateData/{0}_PRCP_coef.csv'.format(waterResourceSystemStnID),"w")
    PRCPRatio.write('month, lower_boundary, upper_boundary, P(W), P(W|W), P(W|D), B_shape, B_scale, N_shape, N_scale, A_shape, A_scale\n')
    for i in range(1,13,1): # 12 months
      data = []
      data_m = [[],[],[],[],[],[],[],[],[],[]]
      zeroRate = [0,0,0] # P(W), P(W|W), P(W|D)
      avg_m = []
      f = open('./climateData/historyClimateData/{0}_PRCP_m_{1}.csv'.format(waterResourceSystemStnID, i),"r")
      for line in f:
        data.append(float(line.split(',')[1]))
        data_m[int(line.split(',')[0].split('/')[0][2:])-8].append(float(line.split(',')[1].replace('\n',''))/10) # 轉為cm/day

      for j in range(len(data)): # 10 years
        if (data[j]) == 0.0:
          zeroRate[0]+=1
          if data[j-1] == 0.0 and j != 0:
            zeroRate[1]+=1
        elif (data[j]) != 0.0 and data[j-1] == 0.0 and j != 0:
          zeroRate[2]+=1
      zeroRate[1]=zeroRate[1]/zeroRate[0]
      zeroRate[2]=zeroRate[2]/(len(data)-zeroRate[0])
      zeroRate[0]=zeroRate[0]/len(data)

      while 0.0 in data:
        data.remove(0.0)

      for j in range(10):
        while 0.0 in data_m[j]:
          data_m[j].remove(0.0)
      
      for j in range(10): # 10 years
        avg_m.append(average(data_m[j]))
      q30 = np.percentile(avg_m, 30)
      q70 = np.percentile(avg_m, 70)
      gamma_corr = {'B':[], 'N':[], 'A':[]}
      data_1 = []
      for k in gamma_corr.keys():
        for j in range(10): # 10 years
          if k == 'B' and avg_m[j] < q30:
            data_1.extend(data_m[j][:])
          elif k == 'N' and avg_m[j] > q30 and avg_m[j] < q70 :
            data_1.extend(data_m[j][:])
          elif k == 'A' and avg_m[j] > q70:
            data_1.extend(data_m[j][:])
        scale = np.var(data_1)/np.mean(data_1)
        shape = np.mean(data_1)/scale
        gamma_corr[k] = [shape, scale]
        # data = np.random.gamma(shape, scale, 10000)
        # mean_sim = np.mean(data)
        # std_sim = np.std(data)
        # print(np.mean(data_1), mean_sim, np.std(data_1), std_sim)

      PRCPRatio.write('{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}\n'.format(i, q30, q70, zeroRate[0], zeroRate[1], zeroRate[2], gamma_corr['B'][0], gamma_corr['B'][1], gamma_corr['N'][0], gamma_corr['N'][1], gamma_corr['A'][0], gamma_corr['A'][1]))

      

    # PRCPRatio = open('./climateData/historyClimateData/{0}_PRCP_coef.csv'.format(waterResourceSystemStnID),"w")
    # PRCPRatio.write('month, lower_boundary, upper_boundary, P(W), P(W|W), P(W|D), B_shape, B_scale, N_shape, N_scale, A_shape, A_scale\n')
    # for i in range(1,13,1): # 12 months
    #   data = []
    #   data_m = [[],[],[],[],[],[],[],[],[],[]]
    #   zeroRate = [0,0,0] # P(W), P(W|W), P(W|D)
    #   avg_m = []
    #   f = open('./climateData/historyClimateData/{0}_PRCP_m_{1}.csv'.format(waterResourceSystemStnID, i),"r")
    #   for line in f:
    #     data.append(float(line.split(',')[1]))
    #     data_m[int(line.split(',')[0].split('/')[0][2:])-8].append(float(line.split(',')[1].replace('\n',''))/10) # 轉為cm/day

    #   for j in range(len(data)): # 10 years
    #     if (data[j]) == 0.0:
    #       zeroRate[0]+=1
    #       if data[j-1] == 0.0 and j != 0:
    #         zeroRate[1]+=1
    #     elif (data[j]) != 0.0 and data[j-1] == 0.0 and j != 0:
    #       zeroRate[2]+=1
    #   zeroRate[1]=zeroRate[1]/zeroRate[0]
    #   zeroRate[2]=zeroRate[2]/(len(data)-zeroRate[0])
    #   zeroRate[0]=zeroRate[0]/len(data)

    #   while 0.0 in data:
    #     data.remove(0.0)

    #   for j in range(10):
    #     while 0.0 in data_m[j]:
    #       data_m[j].remove(0.0)
      
    #   for j in range(10): # 10 years
    #     avg_m.append(average(data_m[j]))
    #   q30 = np.percentile(avg_m, 30)
    #   q70 = np.percentile(avg_m, 70)
    #   weiBull_corr = {'B':[], 'N':[], 'A':[]}
    #   data_1 = []
    #   for k in weiBull_corr.keys():
    #     for j in range(10): # 10 years
    #       if k == 'B' and avg_m[j] < q30:
    #         data_1.extend(data_m[j][1:])
    #       elif k == 'N' and avg_m[j] > q30 and avg_m[j] < q70 :
    #         data_1.extend(data_m[j][1:])
    #       elif k == 'A' and avg_m[j] > q70:
    #         data_1.extend(data_m[j][1:])
    #     # weiBull_corr[k] 
    #     shape, loc, scale = stats.weibull_min.fit(data_1, loc = 0) # shape, loc, scale
    #     # x = stats.weibull_min.rvs(shape, loc, scale, size=1000)
    #     # plt.plot(x)
    #     # plt.show()
    #     weiBull_corr[k] = [shape, scale]
    #   PRCPRatio.write('{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}\n'.format(i, q30, q70, zeroRate[0], zeroRate[1], zeroRate[2], weiBull_corr['B'][0], weiBull_corr['B'][1], weiBull_corr['N'][0], weiBull_corr['N'][1], weiBull_corr['A'][0], weiBull_corr['A'][1]))
    #   # (loc, scale) = s.exponweib.fit_loc_scale(data, 1, 1)
    #   # print loc, scale
    
  def generateTEMPCorr():
    for i in range(1,13,1):
      historyData_WRS=open("./climateData/historyClimateData/climateData_daily_{0}.csv".format(waterResourceSystemStnID),"r")
      line_WRS = historyData_WRS.readline()
      f = open('./climateData/historyClimateData/{0}_TEMP_m_{1}.csv'.format(waterResourceSystemStnID, i),"w")
      for line in historyData_WRS:
        if line.split(',')[1] != "" and int(line.split(',')[1].split('/')[1]) == i:
          f.write('{0},{1}\n'.format(line.split(',')[1], line.split(',')[2]))
      historyData_WRS.close()
      f.close()
    
    for i in range(1,13,1):
      historyData_local=open("./climateData/historyClimateData/climateData_daily_{0}.csv".format(localStnID),"r")
      line_local = historyData_local.readline()
      f = open('./climateData/historyClimateData/{0}_TEMP_m_{1}.csv'.format(localStnID, i),"w")
      for line in historyData_local:
        if line.split(',')[1] != "" and int(line.split(',')[1].split('/')[1]) == i:
          f.write('{0},{1}\n'.format(line.split(',')[1], line.split(',')[2]))
      historyData_local.close()
      f.close()

    Qvalue = open('./climateData/historyClimateData/{0}_TEMP_coef.csv'.format(waterResourceSystemStnID),"w")
    Qvalue.write('month, low_boundary, high_boundary, TEMP_avg_B, TEMP_avg_N, TEMP_avg_A, TEMP_std_B, TEMP_std_N, TEMP_std_A, TEMP_AR1_corr_B, TEMP_AR1_corr_N, TEMP_AR1_corr_A\n')
    for i in range(1,13,1): # 12 months
      data = []
      data_m = [[],[],[],[],[],[],[],[],[],[]]
      avg_m = []
      avg_m_group = [[],[],[]]
      std_group = [[],[],[]]
      avg_BNA = [] 
      std_BNA = []
      f = open('./climateData/historyClimateData/{0}_TEMP_m_{1}.csv'.format(waterResourceSystemStnID, i),"r")
      for line in f:
        data.append(float(line.split(',')[1]))
        data_m[int(line.split(',')[0].split('/')[0][2:])-8].append(float(line.split(',')[1]))
      for j in range(10): # 10 years
        avg_m.append(average(data_m[j]))
      q30 = np.percentile(avg_m, 30)
      q70 = np.percentile(avg_m, 70)
      for j in range(10): # 10 years
        if avg_m[j] < q30:
          avg_m_group[0].append(avg_m[j])
          std_group[0].extend(data_m[j])
        elif avg_m[j] > q30 and avg_m[j] < q70:
          avg_m_group[1].append(avg_m[j])
          std_group[1].extend(data_m[j])
        else:
          avg_m_group[2].append(avg_m[j])
          std_group[2].extend(data_m[j])
      for j in range(3):
        avg_BNA.append(np.mean(avg_m_group[j]))
        std_BNA.append(np.std(std_group[j]))
      AR1_corr = {'B':[], 'N':[], 'A':[]}
      data_1 = []
      data_2 = []
      avg_m_group = [] # B,N,A
      for k in AR1_corr.keys():
        for j in range(10): # 10 years
          if k == 'B' and avg_m[j] < q30:
            data_1.extend(data_m[j][1:])
            data_2.extend(data_m[j][:-1])
          elif k == 'N' and avg_m[j] > q30 and avg_m[j] < q70 :
            data_1.extend(data_m[j][1:])
            data_2.extend(data_m[j][:-1])
          elif k == 'A' and avg_m[j] > q70:
            data_1.extend(data_m[j][1:])
            data_2.extend(data_m[j][:-1])
        AR1_corr[k] = np.corrcoef(data_1, data_2)[0,1]
      Qvalue.write('{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}\n'.format(i, q30, q70, avg_BNA[0], avg_BNA[1], avg_BNA[2], std_BNA[0], std_BNA[1], std_BNA[2], AR1_corr['B'], AR1_corr['N'], AR1_corr['A']))

    Qvalue = open('./climateData/historyClimateData/{0}_TEMP_coef.csv'.format(localStnID),"w")
    Qvalue.write('month, low_boundary, high_boundary, TEMP_avg_B, TEMP_avg_N, TEMP_avg_A, TEMP_std_B, TEMP_std_N, TEMP_std_A, TEMP_AR1_corr_B, TEMP_AR1_corr_N, TEMP_AR1_corr_A\n')
    for i in range(1,13,1): # 12 months
      data = []
      data_m = [[],[],[],[],[],[],[],[],[],[]]
      avg_m = []
      avg_m_group = [[],[],[]]
      std_group = [[],[],[]]
      avg_BNA = [] 
      std_BNA = []
      f = open('./climateData/historyClimateData/{0}_TEMP_m_{1}.csv'.format(localStnID, i),"r")
      for line in f:
        data.append(float(line.split(',')[1]))
        data_m[int(line.split(',')[0].split('/')[0][2:])-8].append(float(line.split(',')[1]))
      for j in range(10): # 10 years
        avg_m.append(average(data_m[j]))
      q30 = np.percentile(avg_m, 30)
      q70 = np.percentile(avg_m, 70)
      for j in range(10): # 10 years
        if avg_m[j] < q30:
          avg_m_group[0].append(avg_m[j])
          std_group[0].extend(data_m[j])
        elif avg_m[j] > q30 and avg_m[j] < q70:
          avg_m_group[1].append(avg_m[j])
          std_group[1].extend(data_m[j])
        else:
          avg_m_group[2].append(avg_m[j])
          std_group[2].extend(data_m[j])
      for j in range(3):
        avg_BNA.append(np.mean(avg_m_group[j]))
        std_BNA.append(np.std(std_group[j]))
      AR1_corr = {'B':[], 'N':[], 'A':[]}
      data_1 = []
      data_2 = []
      avg_m_group = [] # B,N,A
      for k in AR1_corr.keys():
        for j in range(10): # 10 years
          if k == 'B' and avg_m[j] < q30:
            data_1.extend(data_m[j][1:])
            data_2.extend(data_m[j][:-1])
          elif k == 'N' and avg_m[j] > q30 and avg_m[j] < q70 :
            data_1.extend(data_m[j][1:])
            data_2.extend(data_m[j][:-1])
          elif k == 'A' and avg_m[j] > q70:
            data_1.extend(data_m[j][1:])
            data_2.extend(data_m[j][:-1])
        AR1_corr[k] = np.corrcoef(data_1, data_2)[0,1]
      Qvalue.write('{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7}, {8}, {9}, {10}, {11}\n'.format(i, q30, q70, avg_BNA[0], avg_BNA[1], avg_BNA[2], std_BNA[0], std_BNA[1], std_BNA[2], AR1_corr['B'], AR1_corr['N'], AR1_corr['A']))

  generateTEMPCorr()
  generatePRCPRatio()

  def readTEMPCoef(m, group, Stn):
    f = open('./climateData/historyClimateData/{0}_TEMP_coef.csv'.format(Stn), 'r')
    l = f.readline()
    for line in f:
      if int(line.split(',')[0]) == m:
        if group == 'B':
          value = [line.split(',')[3], line.split(',')[6], line.split(',')[9]]
        elif group == 'N':
          value = [line.split(',')[3], line.split(',')[6], line.split(',')[9]]
        elif group == 'A':
          value = [line.split(',')[3], line.split(',')[6], line.split(',')[9]]
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
          value = [line.split(',')[3], line.split(',')[4], line.split(',')[5], line.split(',')[6], line.split(',')[7]]
        elif group == 'N':
          value = [line.split(',')[3], line.split(',')[4], line.split(',')[5], line.split(',')[8], line.split(',')[9]]
        elif group == 'A':
          value = [line.split(',')[3], line.split(',')[4], line.split(',')[5], line.split(',')[10], line.split(',')[11]]
        break
    for i in range(len(value)):
      value[i] = float(value[i])
    print(value)
    return value #  P(W), P(W|W), P(W|D), shape, scale

  for i in range(3):
    coef = readTEMPCoef(i+first_month, Climate_ratio['TEMP_GWLF'][i], waterResourceSystemStnID)
    GWLFData['Date'].append('{0}/{1}/1'.format(now.strftime('%Y'),i+first_month))
    GWLFData['TEMP'].append(coef[0])
    for j in range(1,num_of_days[i+first_month],1):
      GWLFData['Date'].append('{0}/{1}/{2}'.format(now.strftime('%Y'),i+first_month,j))
      GWLFData['TEMP'].append(coef[0]+coef[2]*(GWLFData['TEMP'][j-1]-coef[0])+np.random.normal(0,1)*coef[1]*pow((1-pow(coef[2],2)),0.5))
    
  for i in range(3):
    coef = readPRCPCoef(i+first_month, Climate_ratio['PRCP_GWLF'][i], waterResourceSystemStnID)
    rand = random.random()
    if rand < coef[0]:
      GWLFData['PRCP'].append(0)
    else:
      rand = random.random()
      GWLFData['PRCP'].append(np.random.gamma(coef[3], coef[4], 1)[0]*10)
    for j in range(1,num_of_days[i+first_month],1):
      rand = random.random()
      if (GWLFData['PRCP'][j-1] == 0 and rand < coef[2]) or (GWLFData['PRCP'][j-1] != 0 and rand < coef[1]):
        GWLFData['PRCP'].append(np.random.gamma(coef[3], coef[4], 1)[0]*10)
      else:
        GWLFData['PRCP'].append(0)

  for i in range(3):
    TEMP_local=[]
    coef = readTEMPCoef(i+first_month, Climate_ratio['TEMP_local'][i], localStnID)
    TEMP_local.append(coef[0])
    for j in range(1,num_of_days[i+first_month],1):
      TEMP_local.append(coef[0]+coef[2]*(GWLFData['TEMP'][j-1]-coef[0])+np.random.normal(0,1)*coef[1]*pow((1-pow(coef[2],2)),0.5))

    generatedData['TEMP'].append([np.mean(TEMP_local)-np.std(TEMP_local), np.mean(TEMP_local)+np.std(TEMP_local)])
    generatedData['MN'].append([first_month+i, first_month+i])
  
  # print(generatedData)

  # # print(GWLFData)

  generatedData = indoorClimateDataEstimation("seasonalLongTerm", generatedData)

  GWLF_input = open('./GWLF/WthDATA/seasonalLongTerm_{0}.csv'.format(waterResourceSystemStnID), 'w')
  GWLF_input.write('Date,PP01,TX01\n')
  for i in range(len(GWLFData['Date'])):
    GWLF_input.write('{0},{1},{2}\n'.format(GWLFData['Date'][i], GWLFData['PRCP'][i], GWLFData['TEMP'][i]))
  GWLF_input.close()

  discharge = []
  GWLF = SourceFileLoader("AgriHydro-master.GWLF", "./GWLF/GWLF.py").load_module()
  GWLF.main(argv=['./GWLF', './WthDATA/seasonalLongTerm_{0}.csv'.format(waterResourceSystemStnID), './ParDATA/ShimenGWLFCalibrationPar.csv', 23.5, 0, 'y']) # ['workingDir', 'Tfilename', 'Pfilename', 'latitude', 'dz', 'Output the simulation result or not']
  f = open("./GWLF/OUTPUT_10.csv", "r")
  f_new = open("./GWLF/OUTPUT_10/seasonalLongTerm_{0}_Discharge_Shimen.csv".format(waterResourceSystemStnID), "w")
  for line in f:
    f_new.write(line)
    if '-' in line.split(',')[0]:
      discharge.append(float(line.split(',')[1].replace('\n',''))*8.64*num_of_days[int(line.split(',')[0].split('-')[1])])
  f.close()
  f_new.close()
  
  generatedData['water_storage'][0] = reservoirStorageNow
  for i in range(3):
    generatedData['water_storage'][i] = generatedData['water_storage'][i]+discharge[0+i*3]+discharge[1+i*3]+discharge[2+i*3]-waterRight[first_month-1+i]
    if i == 2: break
    generatedData['water_storage'][i+1] = generatedData['water_storage'][i]

  print(GWLFData['PRCP'])
  print(discharge)
  print(generatedData['water_storage'])

  risk = {"MinT":[],"MaxT":[],"drought":[]} # 3 month
  riskLight={"低溫":[],"高溫":[],"乾旱":[]} # 3 month
  corrFactor = {"MinT":"AirTC_Avg","MaxT":"AirTC_Avg","drought":"Water_Storage"} #climate factor and risk factor corresponding
  for i in risk.keys():
    for j in range(3):
      if i == 'MinT':
        hazardScaleItem = hazardScale["AirTC_Avg_avg"][j]
        value = generatedData['TEMP'][j][0]
      elif i == 'MaxT':
        hazardScaleItem = hazardScale["AirTC_Avg_avg"][j]
        value = generatedData['TEMP'][j][1]
      elif i == "drought":
        hazardScaleItem = hazardScale['Storage_Limit_{0}'.format(first_month+j)]
        value = generatedData['water_storage'][j]
      for k in range(6):
        if hazardScaleItem[k]== '-':
          continue
        elif k==0 and float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]>=float(value):
          risk[i].append(riskScale[0])
          break
        elif k==5 and float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]<=float(value):
          risk[i].append(riskScale[6])
        elif (float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and hazardScaleItem[k+1]== '-':
          risk[i].append(riskScale[k+1])
          break
        elif (float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and (float(hazardScaleItem[k+1])-fuzzyRange[corrFactor[i]])>=float(value):
          risk[i].append(riskScale[k+1])
          break
        elif float(value)>=(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]) and float(value)<=(float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]):
          r=random.random()
          if r>=(float(value)-(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]))/(2*fuzzyRange[corrFactor[i]]):
            risk[i].append(riskScale[k])
          else:
            risk[i].append(riskScale[k+1])
          break  
  print('seasonalLongTerm riskScale:{0}\n'.format(risk))

  for i in risk:
    for j in range(len(risk[i])):
      if i == "MinT":
        if risk[i][j][-3:]=="igh":
          riskLight["低溫"].append("green")
        else:
          riskLight["低溫"].append(riskLightScale[riskScale.index(risk[i][j])])
      elif i == "MaxT":
        if risk[i][j][-3:]=="low":
          riskLight["高溫"].append("green")
        else:
          riskLight["高溫"].append(riskLightScale[riskScale.index(risk[i][j])])
      elif i == "drought":
        if risk[i][j][-3:]=="igh":
          riskLight["乾旱"].append("green")
        else:
          riskLight["乾旱"].append(riskLightScale[riskScale.index(risk[i][j])])
  
  if riskLight_aWeek["乾旱"][-2] == 'red' and riskLightScale.index(riskLight["乾旱"][0]) >= 2: # 若一週未來最後預測為紅燈且下個月預測為綠燈或黃燈，則下個月的預測需降一級
    riskLight["乾旱"][0] = riskLightScale[max(0,riskLightScale.index(riskLight["乾旱"][0])-1)]

  print('seasonalLongTerm riskLight:{0}\n'.format(riskLight))
  f = open('./systemRecord/seasonalLongTerm_riskLight.csv', 'a')
  f.write('\n')
  for Hz in riskLight.keys():
    f.write('{0},{1},{2},{3},{4},{5}\n'.format(now.strftime('%Y-%m-%d %H:%M'),first_month-1,Hz,riskLight[Hz][0],riskLight[Hz][1],riskLight[Hz][2]))
  f.close()
  f = open('./systemRecord/seasonalLongTerm_riskLight.txt', 'a')
  f.write('{0}{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'),riskLight))
  f.close()
  return riskLight 

def climateChangeRiskAssessment(hazardScale, GCM, scenarios, variant_id, localStnID, waterResourceSystemStnID, county, reservoirName, SDInitial):
  rawData={"date":[],"TEMP":[],"PRCP":[]}
  DataArray_month = [[],[],[],[]] # month,TEMP,PRCP,date
  monthly_PRCP = [] # monthly PRCP
  monthly_PRCP_count = []
  IsPRCPZeroRate=[] # PRCP
  historical_mean = {"TEMP":[], "PRCP":[]} # 12 month, monthly for both
  historical_std = {"TEMP":[], "PRCP":[]}

  def generate_baselineData():
    with open('./MultiWG/MultiWG/Setting.Json', newline='') as jsonfile:
      data = json.load(jsonfile)
      
    with open('./MultiWG/MultiWG/Setting.Json','w', newline='') as jsonfile:
      data["StnID"] = [waterResourceSystemStnID]
      data["WthObvCsvFile"] = {
        str(waterResourceSystemStnID): "{0}.csv".format(str(waterResourceSystemStnID))
      }
      data["ClimScenCsvFile"] = {
        str(waterResourceSystemStnID): 'baseline.csv'
      }
      data["GenYear"] = 200
      json.dump(data, jsonfile)
    WG = SourceFileLoader("MultiWG.WG_SimpleRun", "./MultiWG/MultiWG/WG_SimpleRun.py").load_module()
    WG.main(argv=['./MultiWG/MultiWG','n','y']) # ['workingDir', 'multi-site or not', 'output the validation result or not']
    files = os.listdir('./MultiWG/MultiWG/OUT')
    for file in files:
      if '.csv' in file:
        f = open("./MultiWG/MultiWG/OUT/{0}".format(file), "r")
        f_new = open("./GWLF/WthDATA/baseline_{0}.csv".format(waterResourceSystemStnID), "w")
        f.readline()
        f_new.write('Date,PP01,TX01\n')
        i = 0
        for line in f:
          l = line.split(',')
          f_new.write('{0}/{1}/{2},{3},{4}\n'.format(1996+i, l[0].split('-')[1], l[0].split('-')[2], l[1], l[3].replace('\n','')))
          if l[0].split('-')[1]=='12' and l[0].split('-')[2]=='31':
            i+=1
            if i == 200:
              break
        f.close()
        f_new.close()
      print("./MultiWG/MultiWG/OUT/{0}".format(file))
      os.remove("./MultiWG/MultiWG/OUT/{0}".format(file))

    with open('./MultiWG/MultiWG/Setting.Json', newline='') as jsonfile:
      data = json.load(jsonfile)

    with open('./MultiWG/MultiWG/Setting.Json','w', newline='') as jsonfile:
      data["StnID"] = [localStnID]
      data["WthObvCsvFile"] = {
        str(localStnID): "{0}.csv".format(str(localStnID))
      }
      data["ClimScenCsvFile"] = {
        str(localStnID): 'baseline.csv'
      }
      data["GenYear"] = 200
      json.dump(data, jsonfile)
    WG = SourceFileLoader("MultiWG.WG_SimpleRun", "./MultiWG/MultiWG/WG_SimpleRun.py").load_module()
    WG.main(argv=['./MultiWG/MultiWG','n','y']) # ['workingDir', 'multi-site or not', 'output the validation result or not']
    files = os.listdir('./MultiWG/MultiWG/OUT')
    for file in files:
      if '.csv' in file:
        f = open("./MultiWG/MultiWG/OUT/{0}".format(file), "r")
        f_new = open("./climateData/climateChange_data/local_TEMP/baseline_{0}.csv".format(localStnID), "w")
        f.readline()
        f_new.write('Date,PP01,TX01\n')
        i = 0
        for line in f:
          l = line.split(',')
          f_new.write('{0}/{1}/{2},{3},{4}\n'.format(1996+i, l[0].split('-')[1], l[0].split('-')[2], l[1], l[3].replace('\n','')))
          if l[0].split('-')[1]=='12' and l[0].split('-')[2]=='31':
            i+=1
            if i == 200:
              break
        f.close()
        f_new.close()
      print("./MultiWG/MultiWG/OUT/{0}".format(file))
      os.remove("./MultiWG/MultiWG/OUT/{0}".format(file))

    GWLF = SourceFileLoader("AgriHydro-master.GWLF", "./GWLF/GWLF.py").load_module()
    GWLF.main(argv=['./GWLF', './WthDATA/baseline_{0}.csv'.format(waterResourceSystemStnID),'./ParDATA/ShimenGWLFCalibrationPar.csv', 23.5, 0, 'y']) # ['workingDir', 'Tfilename', 'Pfilename', 'latitude', 'dz', 'Output the simulation result or not']
    f = open("./GWLF/OUTPUT_10.csv", "r")
    f_new = open("./GWLF/OUTPUT_10/baseline_{0}_Discharge_Shimen.csv".format(waterResourceSystemStnID), "w")
    for line in f:
      f_new.write(line)
    f.close()
    f_new.close()

    SI_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_SI_{0}.csv'.format(county), 'w')
    SI_output.write('Year, SI_20yr_avg, SI_20yr_std\n')
    SI_output.close()
    MCDS_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_MCDS_{0}.csv'.format(county), 'w')
    MCDS_output.write('Year, MCDS_20yr_avg, MCDS_20yr_std\n')
    MCDS_output.close()
    DPD_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_DPD_{0}.csv'.format(county), 'w')
    DPD_output.write('Year, DPD_20yr_avg, DPD_20yr_std\n')
    DPD_output.close()
    SI = []
    MCDS = []
    DPD = []
    SI_20yr = 0
    # reservoir_output = open('./climateData/climateChange_data/WRS_reservoir/{0}_{1}_{2}-{3}_reservoir_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'w')
    # reservoir_output.write('Year,ShiMen Reservoir,ZhongZhuang Adjustment Reservoir,ShiMen WPP Storage Pool\n')
    # reservoir_output.close()
    discharge_data = open('./GWLF/OUTPUT_10/baseline_{0}_Discharge_Shimen.csv'.format(waterResourceSystemStnID), 'r')
    reservoir_discharge = discharge_data.readlines()
    SDInitial_1yr = SDInitial
    for yr in range(200):
      print(SDInitial_1yr)
      discharge_1yr = reservoir_discharge[yr*36+1:yr*36+36+1]
      inflow_template = xlrd.open_workbook('./SDmodel/SD_inputData/Data_inflow_template.xlsx')
      workbook = Workbook()
      inflow_newfile = workbook.active
      sheet = inflow_template.sheet_by_index(0)
      inflow_newfile.append(sheet.row_values(0))
      for l in range(1,sheet.nrows,1):
        line = sheet.row_values(l)
        line[2] = float(discharge_1yr[l-1].split(',')[1].replace('\n',''))*86400*N[l-1]
        inflow_newfile.append(line)
      workbook.save("./SDmodel/SD_inputData/Data_inflow.xlsx")
      filelist = ["./SDmodel/SD_inputData/Data_inflow.xlsx","./SDmodel/SD_inputData/Data_allocation_template.xlsx"]
      returnData = SDmodel_Sim1yr.main(argv=[SDInitial_1yr['ShiMen Reservoir'], SDInitial_1yr['ZhongZhuang Adjustment Reservoir'], SDInitial_1yr['ShiMen WPP Storage Pool'], filelist]) # ['workingDir', 'Tfilename', 'Pfilename', 'latitude', 'dz', 'Output the simulation result or not']
      print(yr)
      print(returnData)
      SDInitial_1yr['ShiMen Reservoir'] = returnData[0]
      SDInitial_1yr['ZhongZhuang Adjustment Reservoir'] = returnData[1]
      SDInitial_1yr['ShiMen WPP Storage Pool'] = returnData[2]
      SI_20yr+=returnData[3][2]
      MCDS.append(returnData[4])
      DPD.append(returnData[5])
      if yr%20 == 19:
        SI.append(SI_20yr/20)
        SI_20yr = 0
    SI_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_SI_{0}.csv'.format(county), 'a')
    SI_output.write('{0},{1},{2}\n'.format(1996,np.mean(SI),np.std(SI)))
    SI_output.close()
    MCDS_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_MCDS_{0}.csv'.format(county), 'a')
    MCDS_output.write('{0},{1},{2}\n'.format(1996,np.mean(MCDS),np.std(MCDS)))
    MCDS_output.close()
    DPD_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_DPD_{0}.csv'.format(county), 'a')
    DPD_output.write('{0},{1},{2}\n'.format(1996,np.mean(DPD),np.std(DPD)))
    DPD_output.close()
    # reservoir_output = open('./climateData/climateChange_data/WRS_reservoir/{0}_{1}_{2}-{3}_reservoir_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'a')
    # reservoir_output.write('{0},{1},{2},{3}\n'.format(2020+j*10+yr,returnData[0],returnData[1],returnData[2]))
    # reservoir_output.close()

  def generate_multiWG_para(GCM, scenarios, variant_id):
    tas = AR6_CDS_GCM.main(argv=['climateData/climateChange_data/CMIP6/tas_{0}_historical_{1}_gn_19960116-20141216.nc'.format(GCM, variant_id),[1996,2015], 'tas']).to_dict() # argv = [file_path, [start_year, end_year]]
    pr = AR6_CDS_GCM.main(argv=['climateData/climateChange_data/CMIP6/pr_{0}_historical_{1}_gn_19960116-20141216.nc'.format(GCM, variant_id),[1996,2015], 'pr']).to_dict()
    tas_monthly_baseline = []
    pr_monthly_baseline = []
    for i in range(12): # 12 month
      tas_monthly_baseline.append([])
      pr_monthly_baseline.append([])
    for item in tas['value'].keys():
      tas_monthly_baseline[int(tas['time'][item][5:7])-1].append(tas['value'][item]-272.15) # 轉成攝氏溫度
    for item in pr['value'].keys():
      pr_monthly_baseline[int(pr['time'][item][5:7])-1].append(pr['value'][item]*86400*num_of_days[int(pr['time'][item][5:7])-1]) # 轉成公釐/月
    
    baseline_mean = {"TEMP":[], "PRCP":[]} # 12 month, monthly for both
    baseline_std = {"TEMP":[], "PRCP":[]}
    forecast_mean = {} # 12 month, monthly for both
    forecast_std = {}
    TEMP_avg_delta = {}
    TEMP_std_ratio = {}
    PRCP_avg_ratio = {}
    PRCP_std_ratio = {}
    for i in range(12):
      baseline_mean['TEMP'].append(np.mean(tas_monthly_baseline[i]))
      baseline_std['TEMP'].append(np.std(tas_monthly_baseline[i]))
      baseline_mean['PRCP'].append(np.mean(pr_monthly_baseline[i]))
      baseline_std['PRCP'].append(np.std(pr_monthly_baseline[i]))

    for i in scenarios:
      tas_monthly_forecast = []
      pr_monthly_forecast = []
      forecast_mean[i] = {"TEMP":[], "PRCP":[]} 
      forecast_mean[i]["TEMP"]=[] # 12 month, 4 decade for each
      forecast_mean[i]["PRCP"]=[] # 12 month, 4 decade for each
      forecast_std[i] = {"TEMP":[], "PRCP":[]} 
      forecast_std[i]["TEMP"]=[] # 12 month, 4 decade for each
      forecast_std[i]["PRCP"]=[] # 12 month, 4 decade for each
      TEMP_avg_delta[i] = []
      TEMP_std_ratio[i] = []
      PRCP_avg_ratio[i] = []
      PRCP_std_ratio[i] = []

      for j in range(12):
        tas_monthly_forecast.append([])
        pr_monthly_forecast.append([])
        forecast_mean[i]["TEMP"].append([])
        forecast_mean[i]["PRCP"].append([])
        forecast_std[i]["TEMP"].append([])
        forecast_std[i]["PRCP"].append([]) 
        TEMP_avg_delta[i].append([]) 
        TEMP_std_ratio[i].append([]) 
        PRCP_avg_ratio[i].append([]) 
        PRCP_std_ratio[i].append([])    
      tas = AR6_CDS_GCM.main(argv=['climateData/climateChange_data/CMIP6/tas_{0}_{1}_{2}_gn_20210116-20601216.nc'.format(GCM, i, variant_id),[2021,2060], 'tas']).to_dict()
      pr = AR6_CDS_GCM.main(argv=['climateData/climateChange_data/CMIP6/pr_{0}_{1}_{2}_gn_20210116-20601216.nc'.format(GCM, i, variant_id),[2021,2160], 'pr']).to_dict()
      for item in tas['value'].keys():
        tas_monthly_forecast[int(tas['time'][item][5:7])-1].append(tas['value'][item]-272.15) # 轉成攝氏溫度
      for item in pr['value'].keys():
        pr_monthly_forecast[int(pr['time'][item][5:7])-1].append(pr['value'][item]*86400*num_of_days[int(pr['time'][item][5:7])-1]) # 轉成公釐/月
      
      for j in range(12):
        for k in range(3): # 20 years a group
          forecast_mean[i]['TEMP'][j].append(np.mean(tas_monthly_forecast[j][k*10:(k+2)*10]))
          forecast_std[i]['TEMP'][j].append(np.std(tas_monthly_forecast[j][k*10:(k+2)*10]))
          forecast_mean[i]['PRCP'][j].append(np.mean(pr_monthly_forecast[j][k*10:(k+2)*10]))
          forecast_std[i]['PRCP'][j].append(np.std(pr_monthly_forecast[j][k*10:(k+2)*10]))
          TEMP_avg_delta[i][j].append(forecast_mean[i]['TEMP'][j][k]-baseline_mean['TEMP'][j])
          TEMP_std_ratio[i][j].append(forecast_std[i]['TEMP'][j][k]/baseline_std['TEMP'][j]) 
          PRCP_avg_ratio[i][j].append(forecast_mean[i]['PRCP'][j][k]/baseline_mean['PRCP'][j]) 
          PRCP_std_ratio[i][j].append(forecast_std[i]['PRCP'][j][k]/baseline_std['PRCP'][j]) 
      
      for j in range(3):
        f = open('./MultiWG/MultiWG/DATA/{0}_{1}_{2}-{3}.csv'.format(GCM, i, 2020+j*10, 2020+(j+2)*10), 'w')
        f.write('T_avg_delta,T_std_ratio,P_avg_ratio,P_std_ratio,Pw_ratio,Pwd_ratio,Pww_ratio\n')
        for k in range(12):
          f.write('{},{},{},{},1,1,1\n'.format(TEMP_avg_delta[i][k][j],TEMP_std_ratio[i][k][j],PRCP_avg_ratio[i][k][j],PRCP_std_ratio[i][k][j]))
        f.close()
 
  def runMultiWG(GenYear, StnID, ClimScenCsvFile):
    with open('./MultiWG/MultiWG/Setting.Json', newline='') as jsonfile:
      data = json.load(jsonfile)

    with open('./MultiWG/MultiWG/Setting.Json', 'w', newline='') as jsonfile:
      data["StnID"] = [StnID]
      data["WthObvCsvFile"] = {
        str(StnID): "{0}.csv".format(str(StnID))
      }
      data["ClimScenCsvFile"] = {
        str(StnID): ClimScenCsvFile
      }
      data["GenYear"] = GenYear
      json.dump(data, jsonfile)
    WG = SourceFileLoader("MultiWG.WG_SimpleRun", "./MultiWG/MultiWG/WG_SimpleRun.py").load_module()
    WG.main(argv=['./MultiWG/MultiWG','n','y']) # ['workingDir', 'multi-site or not', 'output the validation result or not']
       
  def runGWLF():
    StnID = waterResourceSystemStnID # for drought use waterResourceSystemStnID
    for g in GCM:
      for s in scenarios[g]:
        for j in range(3):
          GWLF = SourceFileLoader("AgriHydro-master.GWLF", "./GWLF/GWLF.py").load_module()
          GWLF.main(argv=['./GWLF', './WthDATA/{0}_{1}_{2}-{3}_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, StnID),'./ParDATA/ShimenGWLFCalibrationPar.csv', 23.5, 0, 'y']) # ['workingDir', 'Tfilename', 'Pfilename', 'latitude', 'dz', 'Output the simulation result or not']
          f = open("./GWLF/OUTPUT_10.csv", "r")
          f_new = open("./GWLF/OUTPUT_10/{0}_{1}_{2}-{3}_{4}_Discharge_Shimen.csv".format(g, s, 2020+j*10, 2020+(j+2)*10, StnID), "w")
          for line in f:
            f_new.write(line)
          f.close()
          f_new.close()
  
  def generateWRS_shortage_index(g, s, j):
    SI_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_SI_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'w')
    SI_output.write('Year, SI_20yr_avg, SI_20yr_std\n')
    SI_output.close()
    MCDS_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_MCDS_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'w')
    MCDS_output.write('Year, MCDS_20yr_avg, MCDS_20yr_std\n')
    MCDS_output.close()
    DPD_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_DPD_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'w')
    DPD_output.write('Year, DPD_20yr_avg, DPD_20yr_std\n')
    DPD_output.close()
    SI = []
    MCDS = []
    DPD = []
    SI_20yr = 0
    # reservoir_output = open('./climateData/climateChange_data/WRS_reservoir/{0}_{1}_{2}-{3}_reservoir_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'w')
    # reservoir_output.write('Year,ShiMen Reservoir,ZhongZhuang Adjustment Reservoir,ShiMen WPP Storage Pool\n')
    # reservoir_output.close()
    discharge_data = open('./GWLF/OUTPUT_10/{0}_{1}_{2}-{3}_{4}_Discharge_{5}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, waterResourceSystemStnID, reservoirName), 'r')
    reservoir_discharge = discharge_data.readlines()
    SDInitial_1yr = SDInitial
    for yr in range(200):
      print(SDInitial_1yr)
      discharge_1yr = reservoir_discharge[yr*36+1:yr*36+36+1]
      inflow_template = xlrd.open_workbook('./SDmodel/SD_inputData/Data_inflow_template.xlsx')
      workbook = Workbook()
      inflow_newfile = workbook.active
      sheet = inflow_template.sheet_by_index(0)
      inflow_newfile.append(sheet.row_values(0))
      for l in range(1,sheet.nrows,1):
        line = sheet.row_values(l)
        line[2] = float(discharge_1yr[l-1].split(',')[1].replace('\n',''))*86400*N[l-1]
        inflow_newfile.append(line)
      workbook.save("./SDmodel/SD_inputData/Data_inflow.xlsx")
      filelist = ["./SDmodel/SD_inputData/Data_inflow.xlsx","./SDmodel/SD_inputData/Data_allocation_template.xlsx"]
      returnData = SDmodel_Sim1yr.main(argv=[SDInitial_1yr['ShiMen Reservoir'], SDInitial_1yr['ZhongZhuang Adjustment Reservoir'], SDInitial_1yr['ShiMen WPP Storage Pool'], filelist]) # ['workingDir', 'Tfilename', 'Pfilename', 'latitude', 'dz', 'Output the simulation result or not']
      print(g,s,j,yr)
      print(returnData)
      SDInitial_1yr['ShiMen Reservoir'] = returnData[0]
      SDInitial_1yr['ZhongZhuang Adjustment Reservoir'] = returnData[1]
      SDInitial_1yr['ShiMen WPP Storage Pool'] = returnData[2]
      SI_20yr+=returnData[3][2]
      MCDS.append(returnData[4])
      DPD.append(returnData[5])
      if yr%20 == 19:
        SI.append(SI_20yr/20)
        SI_20yr = 0
    SI_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_SI_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'a')
    SI_output.write('{0},{1},{2}\n'.format(2020+j*10,np.mean(SI),np.std(SI)))
    SI_output.close()
    MCDS_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_MCDS_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'a')
    MCDS_output.write('{0},{1},{2}\n'.format(2020+j*10,np.mean(MCDS),np.std(MCDS)))
    MCDS_output.close()
    DPD_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_DPD_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'a')
    DPD_output.write('{0},{1},{2}\n'.format(2020+j*10,np.mean(DPD),np.std(DPD)))
    DPD_output.close()
    # reservoir_output = open('./climateData/climateChange_data/WRS_reservoir/{0}_{1}_{2}-{3}_reservoir_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10, county), 'a')
    # reservoir_output.write('{0},{1},{2},{3}\n'.format(2020+j*10+yr,returnData[0],returnData[1],returnData[2]))
    # reservoir_output.close()

  def generateLocalTEMPDATA():
    StnID = localStnID # for drought use waterResourceSystemStnID
    for g in GCM:
      for s in scenarios[g]:
        for j in range(3):
          ClimScenCsvFile = '{0}_{1}_{2}-{3}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10)
          # print('{0}_{1}_{2}-{3}_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+1)*10, StnID))
          print(ClimScenCsvFile)
          runMultiWG(200, StnID, ClimScenCsvFile)
          files = os.listdir('./MultiWG/MultiWG/OUT')
          for file in files:
            if '.csv' in file:
              f = open("./MultiWG/MultiWG/OUT/{0}".format(file), "r")
              f_new = open("./climateData/climateChange_data/local_TEMP/{0}_{1}_{2}-{3}_{4}.csv".format(g, s, 2020+j*10, 2020+(j+2)*10, StnID), "w")
              f.readline()
              f_new.write('Date,PP01,TX01\n')
              i = 0
              for line in f:
                l = line.split(',')
                f_new.write('{0}/{1}/{2},{3},{4}\n'.format(2020+j*10+i, l[0].split('-')[1], l[0].split('-')[2], l[1], l[3].replace('\n','')))
                if l[0].split('-')[1]=='12' and l[0].split('-')[2]=='31':
                  i+=1
                  if i == 200:
                    break
              f.close()
              f_new.close()
            print("./MultiWG/MultiWG/OUT/{0}".format(file))
            os.remove("./MultiWG/MultiWG/OUT/{0}".format(file))
  
  def generateGWLFDATA():
    StnID = waterResourceSystemStnID # for drought use waterResourceSystemStnID
    for g in GCM:
      for s in scenarios[g]:
        for j in range(3):
          ClimScenCsvFile = '{0}_{1}_{2}-{3}.csv'.format(g, s, 2020+j*10, 2020+(j+2)*10)
          # print('{0}_{1}_{2}-{3}_{4}.csv'.format(g, s, 2020+j*10, 2020+(j+1)*10, StnID))
          print(ClimScenCsvFile)
          runMultiWG(200, StnID, ClimScenCsvFile)
          files = os.listdir('./MultiWG/MultiWG/OUT')
          for file in files:
            if '.csv' in file:
              f = open("./MultiWG/MultiWG/OUT/{0}".format(file), "r")
              f_new = open("./GWLF/WthDATA/{0}_{1}_{2}-{3}_{4}.csv".format(g, s, 2020+j*10, 2020+(j+2)*10, StnID), "w")
              f.readline()
              f_new.write('Date,PP01,TX01\n')
              i = 0
              for line in f:
                l = line.split(',')
                f_new.write('{0}/{1}/{2},{3},{4}\n'.format(2020+j*10+i, l[0].split('-')[1], l[0].split('-')[2], l[1], l[3]))
                if l[0].split('-')[1]=='12' and l[0].split('-')[2]=='31':
                  i+=1
                  if i == 200:
                    break
              f.close()
              f_new.close()
            print("./MultiWG/MultiWG/OUT/{0}".format(file))
            os.remove("./MultiWG/MultiWG/OUT/{0}".format(file))
  
  # for g in GCM:  # 產製multiWG需要的氣候變遷參數
  #   generate_multiWG_para(g, scenarios[g], variant_id[g])
  # generateLocalTEMPDATA() # for local MaxT and MinT risk
  # generateGWLFDATA()
  # runGWLF()
  
  # for g in GCM:
  #   for s in scenarios[g]:
  #     for k in range(3):
  #       generateWRS_shortage_index(g, s, k) # for WRS drought risk
  
  # generate_baselineData() # 產製基期資料

  generatedData = {}
  risk = {}
  riskLight = {}
  f_SI = open('./climateData/climateChange_data/WRS_shortage_index/SI_Taoyuan_generatedData.csv', 'w')
  f_SI.write('Model,Scenario,2020-2040,2030-2050,2040-2060\n')
  f_SI.close()
  f_MCDS = open('./climateData/climateChange_data/WRS_shortage_index/MCDS_Taoyuan_generatedData.csv', 'w')
  f_MCDS.write('Model,Scenario,2020-2040,2030-2050,2040-2060\n')
  f_MCDS.close()
  f_DPD = open('./climateData/climateChange_data/WRS_shortage_index/DPD_Taoyuan_generatedData.csv', 'w')
  f_DPD.write('Model,Scenario,2020-2040,2030-2050,2040-2060\n')
  f_DPD.close()
  f_Local_TEMP = open('./climateData/climateChange_data/local_TEMP/local_TEMP_generatedData.csv', 'w')
  f_Local_TEMP.write('Model,Scenario,Years,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec\n')
  f_Local_TEMP.close()
  f = open('./systemRecord/climateChange_riskLight.csv', 'w')
  f.write('Time,GCM,scenario,Hazard,2020-2039,2030-2049,2040-2059\n')
  f.close()

  baselineData = {'time': [], 'TEMP': [], 'MN': [], 'SI': [], 'MCDS': [], 'DPD': []} # 36 months for TEMP, time, MN, and 3 values for SI, MCDS and DPD
  for k in range(3):
    SI_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_SI_{0}.csv'.format(county), 'r')
    line = SI_output.readline()
    for line in SI_output:
      baselineData['SI'].append(float(line.split(',')[1].replace('\n','')))
    SI_output.close()
    MCDS_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_MCDS_{0}.csv'.format(county), 'r')
    line = MCDS_output.readline()
    for line in MCDS_output:
      baselineData['MCDS'].append(float(line.split(',')[1].replace('\n','')))
    MCDS_output.close()
    DPD_output = open('./climateData/climateChange_data/WRS_shortage_index/baseline_DPD_{0}.csv'.format(county), 'r')
    line = DPD_output.readline()
    for line in DPD_output:
      baselineData['DPD'].append(float(line.split(',')[1].replace('\n','')))
    DPD_output.close()
    daily_data = [[],[],[],[],[],[],[],[],[],[],[],[]] # TEMP
    TEMP_data = open("./climateData/climateChange_data/local_TEMP/baseline_{0}.csv".format(localStnID), "r")
    line = TEMP_data.readline()
    for l in range(200): # 200 years data
      for m in range(12):
        line = TEMP_data.readline()
        while int(line.replace('\n','').split(',')[0].split('/')[1]) == m+1:
          daily_data[m].append(float(line.split(',')[2]))
          line = TEMP_data.readline()
          if '/' not in line:
            break
    for m in range(12):
      baselineData['time'].append('{0}_{1}'.format(1996,m+1))
      baselineData['TEMP'].append(np.mean(daily_data[m]))
      baselineData['MN'].append(m+1)

  f_SI = open('./climateData/climateChange_data/WRS_shortage_index/SI_Taoyuan_generatedData.csv', 'w')
  f_SI.write('-,baseline,{0},{1},{2}\n'.format(baselineData['SI'][0],baselineData['SI'][0],baselineData['SI'][0]))
  f_SI.close()
  f_MCDS = open('./climateData/climateChange_data/WRS_shortage_index/MCDS_Taoyuan_generatedData.csv', 'w')
  f_MCDS.write('-,baseline,{0},{1},{2}\n'.format(baselineData['MCDS'][0],baselineData['MCDS'][0],baselineData['MCDS'][0]))
  f_MCDS.close()
  f_DPD = open('./climateData/climateChange_data/WRS_shortage_index/DPD_Taoyuan_generatedData.csv', 'w')
  f_DPD.write('-,baseline,{0},{1},{2}\n'.format(baselineData['DPD'][0],baselineData['DPD'][0],baselineData['DPD'][0]))
  f_DPD.close()
  f_Local_TEMP = open('./climateData/climateChange_data/local_TEMP/local_TEMP_generatedData.csv', 'w')
  f_Local_TEMP.write('{0},{1},{2}-{3},{4},{5},{6},{7},'.format('-','baseline','baseline','baseline',baselineData['TEMP'][0],baselineData['TEMP'][1],baselineData['TEMP'][2],baselineData['TEMP'][3]))
  f_Local_TEMP.write('{0},{1},{2},{3},{4},{5},{6},{7}\n'.format(baselineData['TEMP'][4],baselineData['TEMP'][5],baselineData['TEMP'][6],baselineData['TEMP'][7],baselineData['TEMP'][8],baselineData['TEMP'][9],baselineData['TEMP'][10],baselineData['TEMP'][11]))
  f_Local_TEMP.close()

  for g in GCM:
    generatedData['baseline'] = {'time': [], 'TEMP': [], 'MN': [], 'SI': [], 'MCDS': [], 'DPD': []} # 12 months for TEMP, time, MN, and 1 values for SI, MCDS and DPD
    generatedData['baseline']['time'] = baselineData['time']
    generatedData['baseline']['TEMP'] = baselineData['TEMP']
    generatedData['baseline']['MN'] = baselineData['MN']
    generatedData['baseline']['SI'] = baselineData['SI']
    generatedData['baseline']['MCDS'] = baselineData['MCDS']
    generatedData['baseline']['DPD'] = baselineData['DPD']
    risk['baseline'] = {"MinT":[],"MaxT":[], 'SI': [], 'MCDS': [], 'DPD': []}
    riskLight['baseline'] = {"低溫":[],"高溫":[],  'SI': [], 'MCDS': [], 'DPD': [],"乾旱":[]}
    for s in scenarios[g]:
      generatedData[s] = {'time': [], 'TEMP': [], 'MN': [], 'SI': [], 'MCDS': [], 'DPD': []} # 36 months for TEMP, time, MN, and 3 values for SI, MCDS and DPD
      risk[s] = {"MinT":[],"MaxT":[], 'SI': [], 'MCDS': [], 'DPD': []}
      riskLight[s] = {"低溫":[],"高溫":[],  'SI': [], 'MCDS': [], 'DPD': [],"乾旱":[]}
      for k in range(3): # 3 * 20years
        SI_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_SI_{4}.csv'.format(g, s, 2020+k*10, 2020+(k+2)*10, county), 'r')
        line = SI_output.readline()
        for line in SI_output:
          generatedData[s]['SI'].append(float(line.split(',')[1].replace('\n','')))
        SI_output.close()
        MCDS_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_MCDS_{4}.csv'.format(g, s, 2020+k*10, 2020+(k+2)*10, county), 'r')
        line = MCDS_output.readline()
        for line in MCDS_output:
          generatedData[s]['MCDS'].append(float(line.split(',')[1].replace('\n','')))
        MCDS_output.close()
        DPD_output = open('./climateData/climateChange_data/WRS_shortage_index/{0}_{1}_{2}-{3}_DPD_{4}.csv'.format(g, s, 2020+k*10, 2020+(k+2)*10, county), 'r')
        line = DPD_output.readline()
        for line in DPD_output:
          generatedData[s]['DPD'].append(float(line.split(',')[1].replace('\n','')))
        DPD_output.close()
        daily_data = [[],[],[],[],[],[],[],[],[],[],[],[]] # TEMP
        TEMP_data = open("./climateData/climateChange_data/local_TEMP/{0}_{1}_{2}-{3}_{4}.csv".format(g, s, 2020+k*10, 2020+(k+2)*10, localStnID), "r")
        line = TEMP_data.readline()
        for l in range(200): # 200 years data
          for m in range(12):
            line = TEMP_data.readline()
            while int(line.replace('\n','').split(',')[0].split('/')[1]) == m+1:
              daily_data[m].append(float(line.split(',')[2]))
              line = TEMP_data.readline()
              if '/' not in line:
                break
        for m in range(12):
          generatedData[s]['time'].append('{0}_{1}'.format(2020+k*10,m+1))
          generatedData[s]['TEMP'].append(np.mean(daily_data[m]))
          generatedData[s]['MN'].append(m+1)

    generatedData = indoorClimateDataEstimation("climateChange", generatedData)

    # risk = {
    #   'baseline':{"MinT":[],"MaxT":[], 'SI': [], 'MCDS': [], 'DPD': []} # 12 months *3
    #   'ssp126':{"MinT":[],"MaxT":[], 'SI': [], 'MCDS': [], 'DPD': []}, # 36 months
    #   'ssp245':{"MinT":[],"MaxT":[], 'SI': [], 'MCDS': [], 'DPD': []},
    #   'ssp585':{"MinT":[],"MaxT":[], 'SI': [], 'MCDS': [], 'DPD': []}
    # }
    # riskLight={
    #   'baseline':{"低溫":[],"高溫":[],  'SI': [], 'MCDS': [], 'DPD': [],"乾旱":[]},# 1*20years *3
    #   'ssp126':{"低溫":[],"高溫":[],  'SI': [], 'MCDS': [], 'DPD': [],"乾旱":[]},# 3*20years
    #   'ssp245':{"低溫":[],"高溫":[],  'SI': [], 'MCDS': [], 'DPD': [],"乾旱":[]},
    #   'ssp585':{"低溫":[],"高溫":[],  'SI': [], 'MCDS': [], 'DPD': [],"乾旱":[]}
    # } 

    for s in scenarios[g]:
      f_SI = open('./climateData/climateChange_data/WRS_shortage_index/SI_Taoyuan_generatedData.csv', 'a')
      f_SI.write('{0},{1},{2},{3},{4}\n'.format(g,s,generatedData[s]['SI'][0],generatedData[s]['SI'][1],generatedData[s]['SI'][2]))
      f_SI.close()
      f_MCDS = open('./climateData/climateChange_data/WRS_shortage_index/MCDS_Taoyuan_generatedData.csv', 'a')
      f_MCDS.write('{0},{1},{2},{3},{4}\n'.format(g,s,generatedData[s]['MCDS'][0],generatedData[s]['MCDS'][1],generatedData[s]['MCDS'][2]))
      f_MCDS.close()
      f_DPD = open('./climateData/climateChange_data/WRS_shortage_index/DPD_Taoyuan_generatedData.csv', 'a')
      f_DPD.write('{0},{1},{2},{3},{4}\n'.format(g,s,generatedData[s]['DPD'][0],generatedData[s]['DPD'][1],generatedData[s]['DPD'][2]))
      f_DPD.close()
      f_Local_TEMP = open('./climateData/climateChange_data/local_TEMP/local_TEMP_generatedData.csv', 'a')
      for k in range(3):
        f_Local_TEMP.write('{0},{1},{2}-{3},{4},{5},{6},{7},'.format(g,s,2020+k*10,2040+k*10,generatedData[s]['TEMP'][12*k],generatedData[s]['TEMP'][12*k+1],generatedData[s]['TEMP'][12*k+2],generatedData[s]['TEMP'][12*k+3]))
        f_Local_TEMP.write('{0},{1},{2},{3},{4},{5},{6},{7}\n'.format(generatedData[s]['TEMP'][12*k+4],generatedData[s]['TEMP'][12*k+5],generatedData[s]['TEMP'][12*k+6],generatedData[s]['TEMP'][12*k+7],generatedData[s]['TEMP'][12*k+8],generatedData[s]['TEMP'][12*k+9],generatedData[s]['TEMP'][12*k+10],generatedData[s]['TEMP'][12*k+11]))
      f_Local_TEMP.close()

    corrFactor = {"MinT":"AirTC_Avg","MaxT":"AirTC_Avg","SI":"SI", "MCDS":"MCDS", "DPD":"DPD"} #climate factor and risk factor corresponding
    def getRiskScale(s, i, value):
      for k in range(6):
        if hazardScaleItem[k]== '-':
          continue
        elif k==0 and float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]>=float(value):
          risk[s][i].append(riskScale[0])
          break
        elif k==5 and float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]<=float(value):
          risk[s][i].append(riskScale[6])
        elif (float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and hazardScaleItem[k+1]== '-':
          risk[s][i].append(riskScale[k+1])
          break
        elif (float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and (float(hazardScaleItem[k+1])-fuzzyRange[corrFactor[i]])>=float(value):
          risk[s][i].append(riskScale[k+1])
          break
        elif float(value)>=(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]) and float(value)<=(float(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]):
          r=random.random()
          # print('r: {0}'.format(r))
          if r>=(float(value)-(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]))/(2*fuzzyRange[corrFactor[i]]):
            risk[s][i].append(riskScale[k])
          else:
            risk[s][i].append(riskScale[k+1])
          break 

    for s in generatedData.keys():
      for i in risk[s].keys():
        if i == "SI":
          hazardScaleItem = hazardScale["SI"]
          for j in range(3):
            value = generatedData[s]['SI'][j]
            getRiskScale(s,i, value)
        elif i == "MCDS":
          hazardScaleItem = hazardScale["MCDS"]
          for j in range(3):
            value = generatedData[s]['MCDS'][j]
            getRiskScale(s,i, value)
        elif i == "DPD":
          hazardScaleItem = hazardScale["DPD"]
          for j in range(3):
            value = generatedData[s]['DPD'][j]
            getRiskScale(s,i, value)
        elif i == 'MinT':
          hazardScaleItem = hazardScale["nursery_AirTC_Avg_avg"]
          for j in range(36):
            value = generatedData[s]['TEMP'][j]
            getRiskScale(s,i, value)
        elif i == 'MaxT':
          hazardScaleItem = hazardScale["flowering_AirTC_Avg_avg"]
          for j in range(36):
            value = generatedData[s]['TEMP'][j]
            getRiskScale(s,i, value)
      # print('climateChange riskScale_{0}:{1}\n'.format(s,risk[s]))

      score = 0
      for i in risk[s]:
        score = 0
        for j in range(len(risk[s][i])):
          if i == "MinT":
            Hz = '低溫'
            # print(s,i,j)
            # print(generatedData[s]['TEMP'])
            # print(risk[s][i][j])
            if risk[s][i][j][-3:]=="igh":
              risk[s][i][j] = 0
            else:
              risk[s][i][j] = -riskScale.index(risk[s][i][j])+3
          elif i == "MaxT":
            Hz = '高溫'
            if risk[s][i][j][-3:]=="low":
              risk[s][i][j] = 0
            else:
              risk[s][i][j] = riskScale.index(risk[s][i][j])-3
          elif i == "SI" or i == "MCDS" or i == "DPD":
            Hz = i
            if risk[s][i][j][-3:]=="low":
              risk[s][i][j] = 0
            else:
              risk[s][i][j] = riskScale.index(risk[s][i][j])-3

          if i == "SI" or i == "MCDS" or i == "DPD":
            riskLight[s][i].append(riskLightScale[-risk[s][i][j]+3])
          elif i == "MinT" or i == "MaxT":
            if j%(int(len(risk[s][i])/3)) == int((len(risk[s][i])/3)-1):
              # print(j)
              # print(score)
              if score<8:
                riskLight[s][Hz].append('green')
              elif score<12:
                riskLight[s][Hz].append('yellow')
              elif score<16:
                riskLight[s][Hz].append('orange')
              else:
                riskLight[s][Hz].append('red')
              score = 0 
            else:
              score+=risk[s][i][j]
      for i in range(3):
        riskLight[s]['乾旱'].append(riskLightScale[min(riskLightScale.index(riskLight[s]["SI"][i]),riskLightScale.index(riskLight[s]["MCDS"][i]), riskLightScale.index(riskLight[s]["DPD"][i]))])
        if riskLight[s]["SI"][i] == riskLight[s]["MCDS"][i] == riskLight[s]["DPD"][i]:
          riskLight[s]['乾旱'][i] = riskLightScale[max(0,riskLightScale.index(riskLight[s]["SI"][i])-1)]
      print('climateChange riskLight {0}_{1}:{2}\n'.format(g,s,riskLight[s]))
      
      # f = open('./systemRecord/climateChange_riskLight.csv', 'a')
      # for Hz in riskLight[s].keys():
      #   f.write('{0},{1},{2},{3},{4},{5},{6},{7}\n'.format(now.strftime('%Y-%m-%d %H:%M'),g,s,Hz,riskLight[s][Hz][0],riskLight[s][Hz][1],riskLight[s][Hz][2],riskLight[s][Hz][3]))
      # f.close()
      # f = open('./systemRecord/climateChange_riskLight.txt', 'a')
      # f.write('{0},{1},{2},{3}\n'.format(now.strftime('%Y-%m-%d %H:%M'),g,s,riskLight[s]))
      # f.close()
  return riskLight

def operationAssessment(timeScale,riskLight):
  operationalSuggestion={}
  operationData = open ('./operationMethodData/operationMethod_{0}.csv'.format(timeScale), 'r')
  if timeScale == "realTime":
    for line in operationData.readlines():
      line=line.split(',')
      if line[0] in riskLight.keys():
        if riskLight[line[0]] == line[-1].replace("\n",""):
          operationalSuggestion[line[0]]={
            "method":line[1],
            "risk_factor":line[2]
          }
  elif timeScale == 'aWeek':
    for line in operationData.readlines():
      line=line.split(',')
      if line[0] in riskLight.keys():
        for i in range(len((riskLight[line[0]]))):
          if riskLight[line[0]][i] == line[-1].replace("\n",""):
            operationalSuggestion[line[0]]={
              "method":line[1],
              "risk_factor":line[2]
            }
            if i%2 == 0:
              operationalSuggestion[line[0]]["time"] = '{0}天後的白天面臨危害'.format(int(i/2))
            else:
              operationalSuggestion[line[0]]["time"] = '{0}天後的晚上面臨危害'.format(int((i-1)/2))
  elif timeScale == 'seasonalLongTerm':
    for line in operationData.readlines():
      line=line.split(',')
      if line[0] in riskLight.keys():
        for i in range(len((riskLight[line[0]]))):
          if riskLight[line[0]][i] == line[-1].replace("\n",""):
            operationalSuggestion[line[0]]={
              "method":line[1],
              "risk_factor":line[2]
            }
            operationalSuggestion[line[0]]["time"] = '{0}個月後面臨危害'.format(i+1)
  elif timeScale == 'climateChange':
    for line in operationData.readlines():
      line=line.split(',')
      for scenario in riskLight.keys():
        if line[0] in riskLight[scenario].keys():
          for i in range(len((riskLight[scenario][line[0]]))):
            if riskLight[scenario][line[0]][i] == line[-1].replace("\n",""):
              operationalSuggestion[scenario+'_'+line[0]]={
                "method":line[1],
                "risk_factor":line[2]
              }
              operationalSuggestion[scenario+'_'+line[0]]["time"] = '{0}年內面臨危害'.format((i+1)*10)
  print('{0} operationalSuggestion:{1}\n'.format(timeScale, operationalSuggestion))
  f = open('./systemRecord/{}_operation.txt'.format(timeScale), 'a')
  f.write('{0}:{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'), operationalSuggestion))
  f.close()
  return operationalSuggestion

def indoorClimateDataEstimation(timescale,data):
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
  climateChange_weights = {
    'TEMP':{
      'TEMP': [-4.3154551, 0.9343015],
      'MN': [3.8008508, 0.05959764]
    },
  }

  new_data = {}

  def findingWeights():
    indoorDataScheme = open('./realTime_IoT_data/indoorClimateData/indoorClimateData_scheme.txt', 'r')
    dataLabel_indoor = indoorDataScheme.readline().split(',')
    indoorDataScheme.close()
    outdoorDataScheme = open ('./realTime_IoT_data/outdoorClimateData/outdoorClimateData_scheme.txt', 'r')
    dataLabel_outdoor = outdoorDataScheme.readline().split(',')
    outdoorDataScheme.close()
    indoorData_f = open('./realTime_IoT_data/indoorClimateData/testdata_indoor.txt', 'rb')
    indoorData = indoorData_f.readlines()
    indoorData_f.close()
    outdoorData_f = open('./realTime_IoT_data/outdoorClimateData/testdata_outdoor.txt', 'rb')
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

    # start GA optimization
    desired_output = 0
    def fitness_func_1(solution, solution_idx): # for seasonalLongTerm and climateChange
      output = 0
      fitness = []
      for i in range(1,num_of_trainingData,1):
        output += ((outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['MN'][i]-solution[2])*solution[3]-indoor_data['AirTC_Avg'][i])**2
      fitness = 1.0 / np.abs(output - desired_output)
      print(fitness)
      return fitness

    def fitness_func_2(solution, solution_idx):
      output = 0
      fitness = []
      for i in range(1,num_of_trainingData,1):
        output += ((outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['HR'][i]-solution[2])*solution[3]+(outdoor_data['MN'][i]-solution[4])*solution[5]+(outdoor_data['RH'][i]-solution[6])*solution[7]+(outdoor_data['WS'][i]-solution[8])*solution[9]-indoor_data['AirTC_Avg'][i])**2
      fitness = 1.0 / np.abs(output - desired_output)
      print(fitness)
      return fitness
    fitness_function = fitness_func_2

    num_generations = 600
    num_parents_mating = 4

    sol_per_pop = 20
    num_genes = 10 # 參數數量 4 or 10

    init_range_low = -5
    init_range_high = 5

    parent_selection_type = "sss"
    keep_parents = 1

    crossover_type = "single_point"

    mutation_type = "random"
    mutation_percent_genes = 20

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

    bias_mean = 0
    # f = open('./realTime_IoT_data/data_test.csv', 'w')
    f = open('./realTime_IoT_data/data_test_2.csv', 'w')
    for i in range(num_of_trainingData, len(indoor_data['AirTC_Avg']), 1):
      # value = (outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['MN'][i]-solution[2])*solution[3]
      value_2 = (outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['HR'][i]-solution[2])*solution[3]+(outdoor_data['MN'][i]-solution[4])*solution[5]+(outdoor_data['RH'][i]-solution[6])*solution[7]+(outdoor_data['WS'][i]-solution[8])*solution[9]
      # bias = np.abs(value-indoor_data['AirTC_Avg'][i])
      bias = np.abs(value_2-indoor_data['AirTC_Avg'][i])
      bias_mean += bias**2
      # f.write('{0},{1},{2},{3},{4}\n'.format(outdoor_data['TIMESTAMP'][i], float(indoor_data['AirTC_Avg'][i]), value, bias, outdoor_data['MN'][i]))
      f.write('{0},{1},{2},{3},{4},{5},{6}.{7}\n'.format(outdoor_data['TIMESTAMP'][i], float(indoor_data['AirTC_Avg'][i]), value_2, bias, outdoor_data['HR'][i], outdoor_data['MN'][i], outdoor_data['RH'][i], outdoor_data['WS'][i]))
    f.close()

    bias_mean = (bias_mean/(len(indoor_data['AirTC_Avg'])-num_of_trainingData))**0.5
    print(bias_mean) #bias_mean_1 = 2.570,  bias_mean_2 = 2.339

  # print(data)
  
  def estimate_indoorData():
    if timescale == 'aWeek':
      for i in data.keys():
        if i in aWeek_weights.keys():
          new_data[i] = []
          for j in range(len(data[i])):
            new_data[i].append(0)
            for k in aWeek_weights[i].keys():
              new_data[i][j] += (data[k][j]-aWeek_weights[i][k][0])*aWeek_weights[i][k][1]
        elif i != 'HR' and i != 'MN': # 'HR' and 'MN' are for correction only
          new_data[i] = data[i]
    elif timescale == 'seasonalLongTerm':
      for i in data.keys():
        if i in seasonalLongTerm_weights.keys():
          new_data[i] = []
          for j in range(len(data[i])):
            new_data[i].append([])
            new_data[i][j].append(0)
            new_data[i][j].append(0)
            for k in seasonalLongTerm_weights[i].keys():
              new_data[i][j][0] += (data[k][j][0]-seasonalLongTerm_weights[i][k][0])*seasonalLongTerm_weights[i][k][1]
              new_data[i][j][1] += (data[k][j][1]-seasonalLongTerm_weights[i][k][0])*seasonalLongTerm_weights[i][k][1]
        elif i != 'MN': # 'HR' and 'MN' are for correction only
          new_data[i] = data[i]
    elif timescale == 'climateChange':
      for s  in data.keys():
        new_data[s] = {}
        for i in data[s].keys():
              if i in climateChange_weights.keys():
                new_data[s][i] = []
                for j in range(len(data[s][i])):
                  new_data[s][i].append(0)
                  for k in climateChange_weights[i].keys():
                    new_data[s][i][j] += (data[s][k][j]-climateChange_weights[i][k][0])*climateChange_weights[i][k][1]
              elif i != 'MN': # 'HR' and 'MN' are for correction only
                new_data[s][i] = data[s][i]

  # findingWeights()
  estimate_indoorData()
  return new_data

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

def main():
  operationalSuggestion = {}
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

  # realTimehazardScale = getHazardScale(crop, county, growthStage[0], "realTime")
  # riskLight_realTime = realTimeRiskAssessment(realTimehazardScale)
  # operationalSuggestion["realTime"]=operationAssessment("realTime",riskLight_realTime)
  
  # aWeekhazardScale = getHazardScale(crop, county, growthStage[0], "aWeek")
  # riskLight_aWeek = aWeekRiskAssessment(location, aWeekhazardScale, riskLight_realTime)
  # operationalSuggestion["aWeek"]=operationAssessment("aWeek",riskLight_aWeek)

  # seasonalLongTermhazardScale = getHazardScale(crop, county, growthStage, "seasonalLongTerm", first_month)
  # riskLight_seasonalLongTerm = seasonalLongTermRiskAssessment(seasonalLongTermhazardScale, riskLight_aWeek, seasonalLongTerm_P, first_month, localStnID, waterResourceSystemStnID, reservoirStorageNow, waterRight)
  # operationalSuggestion["seasonalLongTerm"]=operationAssessment("seasonalLongTerm",riskLight_seasonalLongTerm)

  climateChangehazardScale = getHazardScale(crop, county, "", "climateChange")
  riskLight_climateChange = climateChangeRiskAssessment(climateChangehazardScale, GCM, scenarios, variant_id, localStnID, waterResourceSystemStnID, county, reservoirName, SDInitial)
  operationalSuggestion["climateChange"]=operationAssessment("climateChange",riskLight_climateChange)
  
  # testGA()
main()