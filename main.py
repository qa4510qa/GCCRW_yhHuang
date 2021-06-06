#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
from os import listdir
import numpy as np
import pandas as pd
from pygad import GA as ga
import math
import random
import csv
from numpy.lib.function_base import append
import requests
from datetime import date, datetime
import matplotlib.pyplot as plt
from statsmodels.distributions.empirical_distribution import ECDF
import AR6_CDS_GCM

# from statsmodels.distributions.empirical_distribution import ECDF
CWB_API_Key = 'CWB-B7BC29A4-FADA-4DE6-9918-F2FA71A55F80'
AGRi_API_ProjectKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0bmFtZSI6IlNETGFiX0lvVF9Qcm9qZWN0XzIwMjEiLCJuYW1lIjoicjA4NjIyMDA1IiwiaWF0IjoxNjEzNzk5Nzk2fQ.elm1KN4D7geluaVTrv-J9OoZ9aFEOFb-juiVfUrFQTc'
now = datetime.now()
fuzzyRange = {"AirTC_Avg":1, "RH":5, "PAR_Avg":50, "VW_F_Avg":5, "WS_ms_Avg":3, "Water_Demand":0}
riskScale = ["very_low","low","slightly_low","proper","slightly_high","high","very_high"]
riskLightScale = ["red","orange","yellow","green","yellow","orange","red"]

def getHazardScale(crop, growthStage, timeScale):
  hazardScale = {} #{[stage]:{[climateFactor]:[value]}}
  if timeScale == "realTime":
    current_time = now.strftime("%H")
    if int(current_time) >= 6 and int(current_time) < 18:
      conditionItem = growthStage + "_day"
    else:
      conditionItem = growthStage + "_night" # get the objective condition for crop in such stage and time

    with open('./cropClimateCondition/{0}/{1}.csv'.format(crop ,conditionItem), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] != '\ufeff':
          hazardScale[row[0]] = row[1:] 
  elif timeScale == "aWeek":
    with open('./cropClimateCondition/{0}/{1}_day.csv'.format(crop ,growthStage), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] != '\ufeff':
          hazardScale['{0}_day'.format(row[0])] = row[1:]
    with open('./cropClimateCondition/{0}/{1}_night.csv'.format(crop ,growthStage), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        if row[0] != '\ufeff':
          hazardScale['{0}_night'.format(row[0])] = row[1:]
  elif timeScale == "seasonalLongTerm":
    hazardScale = {'AirTC_Avg_day':[], 'AirTC_Avg_night':[], 'Water_Demand':[]}
    for i in range(3): # 3 month
      with open('./cropClimateCondition/{0}/{1}_day.csv'.format(crop ,growthStage[i]), newline='') as csvfile:
        rows = csv.reader(csvfile)
        for row in rows:
          if row[0] == 'AirTC_Avg':
            hazardScale['AirTC_Avg_day'].append(row[1:])
          elif row[0] == 'Water_Demand':
            hazardScale['Water_Demand'].append(row[1:])
      with open('./cropClimateCondition/{0}/{1}_night.csv'.format(crop ,growthStage[i]), newline='') as csvfile:
        rows = csv.reader(csvfile)
        for row in rows:
          if row[0] == 'AirTC_Avg':
            hazardScale['AirTC_Avg_night'].append(row[1:])
  elif timeScale == "climateChange":
    files = listdir("./cropClimateCondition/{0}".format(crop))
    for file in files:
      if file[-3:] == 'csv':
        with open('./cropClimateCondition/{0}/{1}'.format(crop ,file), newline='') as csvfile:
          rows = csv.reader(csvfile)
          for row in rows:
            if row[0] != '\ufeff':
              hazardScale['{0}_{1}_{2}'.format( file[:file.index('_')], row[0], file[file.index('_')+1:file.index('.')])] = row[1:]
  print('{0} hazardScale: {1}\n'.format(timeScale, hazardScale))
  return hazardScale

def realTimeRiskAssessment(hazardScale):
  riskLight = {}
  
  with open ('./realTime_IoT_data/indoorClimateData/indoorClimateData_scheme.txt', 'r') as indoorDataScheme:
    dataLabel_indoor = indoorDataScheme.readline().split(',')

  with open ('./realTime_IoT_data/outdoorClimateData/outdoorClimateData_scheme.txt', 'r') as outdoorDataScheme:
    dataLabel_outdoor = outdoorDataScheme.readline().split(',')
  
  with open('./realTime_IoT_data/indoorClimateData/testdata_indoor.txt', 'rb') as indoorData:
    line_indoor = indoorData.readline()
    off = -120
    while True:
      indoorData.seek(off,2) 
      lines = indoorData.readlines() 
      if len(lines)>=2: 
        line_indoor = lines[-1].decode().split(',')
        break
      off*=2 

  with open('./realTime_IoT_data/outdoorClimateData/testdata_outdoor.txt', 'rb') as outdoorData:
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
      # print('{0}: {1}'.format(i, value))
    elif i in dataLabel_outdoor:
      value = line_outdoor[dataLabel_outdoor.index(i)]
      # print('{0}: {1}'.format(i, value))
    # print(hazardScale[i])
    for j in range(6):
      # print(hazardScale[i][j])
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
        # print('r: {0}'.format(r))
        if r>=(float(value)-(int(hazardScale[i][j])-fuzzyRange[i]))/(2*fuzzyRange[i]):
          risk[i]=riskScale[j]
        else:
          risk[i]=riskScale[j+1]
        # print('{0}: {1}'.format(i,risk[i]))
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
  # print(record[-1].split('{')[-1].replace("}",'').split(',')[4].split(':')[1].replace(" ",'').replace("\n",'').replace("'",''))
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
    # print(len(climatData_aWeekForecast))

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
  # print (rawData) # 'MinT', 'MaxT', 'RH', 'WS', 'Water_storage'
  
  indoorData = indoorClimateDataEstimation("aWeek",rawData)
  # 乾旱評估，分析水塔蓄水量變化
  with open ('./realTime_IoT_data/systemCapacityData/systemCapacityData_scheme.txt', 'r') as systemDataScheme:
    dataLabel_system = systemDataScheme.readline().split(',')

  with open('./realTime_IoT_data/systemCapacityData/testdata_systemCapacity.txt', 'rb') as systemData:
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
    # print(delta)
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
      # print(float(value))
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
      # print(hazardScaleItem)
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
          # print('r: {0}'.format(r))
          if r>=(float(value)-(float(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]))/(2*fuzzyRange[corrFactor[i]]):
            risk[i].append(riskScale[k])
          else:
            risk[i].append(riskScale[k+1])
          break
      # print('{0}: {1}'.format(i,risk[i]))
  
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
  f = open('./systemRecord/aWeek_riskLight.txt', 'a')
  f.write('{0}{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'),riskLight))
  f.close()
  return riskLight

def seasonalLongTermRiskAssessment(hazardScale, riskLight_aWeek):
  first_month = 5 # May
  num_of_days=[31,28,31,30,31,30,31,31,30,31,30,31]
  P = {"TEMP":[[20,50,30],[10,60,30],[10,50,40]], "PRCP":[[40,40,20],[30,50,20],[20,60,20]]} # May to July data update at 2021/04/30
  rawData={"date":[],"TEMP":[],"PRCP":[]}
  DataArray_month = [[],[],[]] # month,TEMP,PRCP
  IsPRCPZeroRate=[] # PRCP
  historyData=open("./historyClimateData/climateData_daily_466920.csv","r")
  line = historyData.readline()
  for line in historyData:
    if line.split(',')[1] != "":
      rawData["date"].append(line.split(',')[1])
      rawData["TEMP"].append(line.split(',')[2])
      rawData["PRCP"].append(line.split(',')[3])
  len_of_data = len(rawData["date"])
  # print(len_of_data)

  for i in range(12):
    DataArray_month[0].append(str(i+1))
    DataArray_month[1].append([])
    DataArray_month[2].append([])
  # print(DataArray_month)

  for i in range(len_of_data):
    j=int(rawData["date"][i][4:6])
    DataArray_month[1][j-1].append(rawData["TEMP"][i])
    DataArray_month[2][j-1].append(rawData["PRCP"][i])
  # print(DataArray_month)

  for i in range(12):
    count=0
    for j in range(len(DataArray_month[2][i])):
      if(DataArray_month[2][i][j]=="0"):
        count+=1
    IsPRCPZeroRate.append(round((float(count)/float(len(DataArray_month[2][i])))*1000)/1000)
  # print(IsPRCPZeroRate)

  for i in range(1,3,1):
    for j in range(12):
      while '-9999' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('-9999')
      while '-9998' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('-9998')
      while '-9997' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('-9997')
      while '0' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('0') # 沒有下雨的情況另外用isZeroRate討論
      for k in range(len(DataArray_month[i][j])):
        DataArray_month[i][j][k]=float(DataArray_month[i][j][k])
  # print(DataArray_month)
  generatedData = {"TEMP":[[],[],[]], "PRCP":[[],[],[]]} # 3 month
  mean = {"TEMP":[], "PRCP":[]} # 3 month, daily for TEMP and monthly for PRCP
  std = {"TEMP":[], "PRCP":[]} # 3 month, daily for TEMP and monthly for PRCP
  for i in range(first_month-1, first_month+2,1): # May~July
    ecdf_TEMP=ECDF(DataArray_month[1][i]) 
    ecdf_PRCP=ECDF(DataArray_month[2][i]) 

    # plt.figure()
    # plt.plot(ecdf_TEMP.x, ecdf_TEMP.y, 'ko', label="Original Noised Data_TEMP")
    # plt.legend()
    # plt.show()
    # plt.figure()
    # plt.plot(ecdf_PRCP.x, ecdf_PRCP.y, 'ko', label="Original Noised Data_PRCP")
    # plt.legend()
    # plt.show()

    for k in range(100): # generate 100 samples for each variable every month
      Climate_ratio={}
      rand_TEMP = random.random()
      if rand_TEMP<=P["TEMP"][i-4][0]:
        Climate_ratio["TEMP"]=[0,0.3]
      elif (rand_TEMP>P["TEMP"][i-4][0] and rand_TEMP<=P["TEMP"][i-4][1]):
        Climate_ratio["TEMP"]=[0.3,0.7]
      else :
        Climate_ratio["TEMP"]=[0.7,1]

      y=random.random()*(Climate_ratio["TEMP"][1]-Climate_ratio["TEMP"][0])+Climate_ratio["TEMP"][0]
      t=0
      while ecdf_TEMP.y[t]<y:
        t+=1
      generatedData["TEMP"][i-4].append(round(ecdf_TEMP.x[t]*1000)/1000)

      PRCP_month = 0
      for d in range(num_of_days[i]):
        rand_PRCP = random.random()
        if rand_PRCP<=P["PRCP"][i-4][0]:
          Climate_ratio["PRCP"]=[0,0.3]
        elif (rand_PRCP>P["PRCP"][i-4][0] and rand_PRCP<=P["PRCP"][i-4][1]):
          Climate_ratio["PRCP"]=[0.3,0.7]
        else :
          Climate_ratio["PRCP"]=[0.7,1]
      
        IsPRCPZero = random.random() # determine dry day or wet day
        if IsPRCPZero <= IsPRCPZeroRate[i]: 
          PRCP_month+=0
        else:
          y=random.random()*(Climate_ratio["PRCP"][1]-Climate_ratio["PRCP"][0])+Climate_ratio["PRCP"][0]
          t=0
          while ecdf_PRCP.y[t]<y:
            t+=1
          PRCP_month+=round(ecdf_PRCP.x[t]*1000)/1000
      generatedData["PRCP"][i-4].append(PRCP_month)

    mean["TEMP"].append(np.mean(generatedData["TEMP"][i-4]))
    std["TEMP"].append(np.std(generatedData["TEMP"][i-4],ddof=1))
    mean["PRCP"].append(np.mean(generatedData["PRCP"][i-4]))
    std["PRCP"].append(np.std(generatedData["PRCP"][i-4],ddof=1))
  # print(generatedData)
  P66_range = {'TEMP':[], 'PRCP':[], 'MN':[]}
  for i in range(3):
    P66_range['TEMP'].append([mean['TEMP'][i]-std['TEMP'][i], mean['TEMP'][i]+std['TEMP'][i]])
    P66_range['PRCP'].append([max(0,mean['PRCP'][i]-std['PRCP'][i]), mean['PRCP'][i]+std['PRCP'][i]])
    P66_range['MN'].append([first_month+i, first_month+i])

  P66_range = indoorClimateDataEstimation("seasonalLongTerm", P66_range)
  # print(P66_range) # 'TEMP', 'PRCP'
  risk = {"MinT":[],"MaxT":[],"Water_Demand":[]} # 3 month
  riskLight={"低溫":[],"高溫":[],"乾旱":[]} # 3 month
  corrFactor = {"MinT":"AirTC_Avg","MaxT":"AirTC_Avg","Water_Demand":"Water_Demand"} #climate factor and risk factor corresponding
  for i in risk.keys():
    for j in range(3):
      if i == 'MinT':
        hazardScaleItem = hazardScale["AirTC_Avg_night"][j]
        value = P66_range['TEMP'][j][0]
      elif i == 'MaxT':
        hazardScaleItem = hazardScale["AirTC_Avg_day"][j]
        value = P66_range['TEMP'][j][1]
      elif i == "Water_Demand":
        hazardScaleItem = hazardScale["Water_Demand"][j]
        t=0
        # print(ecdf_PRCP.x)
        # print(P66_range['PRCP'][j][0])
        while ecdf_PRCP.x[t]<P66_range['PRCP'][j][0]:
          t+=1
        # print(ecdf_PRCP.y[t])
        if ecdf_PRCP.y[t]>0.4:                  # 使用降雨量與歷史降雨量比教作為乾旱判斷之依據
          risk[i].append('proper')
          continue
        elif ecdf_PRCP.y[t]>0.3:
          risk[i].append('slightly_low')
          continue
        elif ecdf_PRCP.y[t]>0.2:
          risk[i].append('low')
          continue
        else:
          risk[i].append('very_low')
          continue
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
          # print('r: {0}'.format(r))
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
      elif i == "Water_Demand":
        if risk[i][j][-3:]=="igh":
          riskLight["乾旱"].append("green")
        else:
          riskLight["乾旱"].append(riskLightScale[riskScale.index(risk[i][j])])
  
  if riskLight_aWeek["乾旱"][-2] == 'orange' or riskLight_aWeek["乾旱"][-2] == 'red':
    riskLight["乾旱"][0] = riskLightScale[max(0,riskLightScale.index(riskLight["乾旱"][0])-1)]

  print('seasonalLongTerm riskLight:{0}\n'.format(riskLight))
  f = open('./systemRecord/seasonalLongTerm_riskLight.txt', 'a')
  f.write('{0}{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'),riskLight))
  f.close()
  return riskLight

def climateChangeRiskAssessment(hazardScale):
  num_of_days=[31,28,31,30,31,30,31,31,30,31,30,31]
  rawData={"date":[],"TEMP":[],"PRCP":[]}
  DataArray_month = [[],[],[],[]] # month,TEMP,PRCP,date
  monthly_PRCP = [] # monthly PRCP
  monthly_PRCP_count = []
  IsPRCPZeroRate=[] # PRCP
  historyData=open("./historyClimateData/climateData_daily_466920.csv","r")
  line = historyData.readline()
  for line in historyData:
    if line.split(',')[1] != "":
      rawData["date"].append(line.split(',')[1])
      rawData["TEMP"].append(line.split(',')[2])
      rawData["PRCP"].append(line.split(',')[3])
  len_of_data = len(rawData["date"])

  for i in range(12):
    DataArray_month[0].append(str(i+1)) # month
    DataArray_month[1].append([]) # TEMP
    DataArray_month[2].append([]) # PRCP
    DataArray_month[3].append([]) # date
    monthly_PRCP.append([])
    monthly_PRCP_count.append([])
    for j in range(20):
      monthly_PRCP_count[i].append(0)
      monthly_PRCP[i].append(0)

  for i in range(len_of_data):
    year = int(rawData["date"][i][:4])
    if year>=1996 and year<=2015:
      j=int(rawData["date"][i][4:6])
      DataArray_month[1][j-1].append(rawData["TEMP"][i])
      DataArray_month[2][j-1].append(rawData["PRCP"][i])
      DataArray_month[3][j-1].append(rawData["date"][i])
      if rawData["PRCP"][i] != '-9999' and rawData["PRCP"][i] != '-9998' and rawData["PRCP"][i] != '-9997': # dry day 一起平均
        monthly_PRCP_count[j-1][year-1996]+=1
        monthly_PRCP[j-1][year-1996]+=float(rawData["PRCP"][i])

  for i in range(12):
    for j in range(20):
      if monthly_PRCP_count[i][j] == 0:
        break
      else:
        monthly_PRCP[i][j] = monthly_PRCP[i][j]/monthly_PRCP_count[i][j]*num_of_days[i]
    while 0 in monthly_PRCP[i]:
      monthly_PRCP[i].remove(0)
  # print(monthly_PRCP)

  for i in range(12):
    count=0
    for j in range(len(DataArray_month[2][i])):
      if(DataArray_month[2][i][j]=="0"):
        count+=1
    IsPRCPZeroRate.append(round((float(count)/float(len(DataArray_month[2][i])))*1000)/1000)
  # print(IsPRCPZeroRate)

  for i in range(1,3,1):
    for j in range(12):
      while '-9999' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('-9999')
      while '-9998' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('-9998')
      while '-9997' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('-9997')
      while '0' in DataArray_month[i][j]:
        DataArray_month[i][j].remove('0') # 沒有下雨的情況另外用isZeroRate討論
      for k in range(len(DataArray_month[i][j])):
        DataArray_month[i][j][k]=float(DataArray_month[i][j][k])
  # print(DataArray_month)

  historical_mean = {"TEMP":[], "PRCP":[]} # 12 month, monthly for both
  historical_std = {"TEMP":[], "PRCP":[]}
  for i in range(12):
    historical_mean["TEMP"].append(np.mean(DataArray_month[1][i]))
    historical_std["TEMP"].append(np.std(DataArray_month[1][i],ddof=1))
    historical_mean["PRCP"].append(np.mean(monthly_PRCP[i]))
    historical_std["PRCP"].append(np.std(monthly_PRCP[i],ddof=1))

  generatedData = {
    'ssp126':{'time': [], 'TEMP': [], 'PRCP': [], 'MN': []}, 
    'ssp245':{'time': [], 'TEMP': [], 'PRCP': [], 'MN': []}, 
    'ssp585':{'time': [], 'TEMP': [], 'PRCP': [], 'MN': []}
  }
  scenarios = ['ssp126', 'ssp245', 'ssp585']
  tas = AR6_CDS_GCM.main(argv=['./climateChange_data/CMIP6/tas_Amon_HadGEM3-GC31-LL_historical_r1i1p1f3_gn_19010116-20141216.nc',[1996,2015], 'tas']) # argv = [file_path, [start_year, end_year]]
  pr = AR6_CDS_GCM.main(argv=['./climateChange_data/CMIP6/pr_Amon_HadGEM3-GC31-LL_historical_r1i1p1f3_gn_19010116-20141216.nc',[1996,2015], 'pr']).to_dict()
  tas_monthly = []
  pr_monthly = []
  for i in range(12):
    tas_monthly.append([])
    pr_monthly.append([])
  for item in tas['value'].keys():
    # print(int(tas['time'][item][5:7]))
    # print(tas['value'][item])
    tas_monthly[int(tas['time'][item][5:7])-1].append(tas['value'][item]-272.15) # 轉成攝氏溫度
  for item in pr['value'].keys():
    # print(int(tas['time'][item][5:7]))
    # print(tas['value'][item])
    pr_monthly[int(pr['time'][item][5:7])-1].append(pr['value'][item]*86400*num_of_days[int(pr['time'][item][5:7])-1]) # 轉成公釐/月
  
  baseline_mean = {"TEMP":[], "PRCP":[]} # 12 month, monthly for both
  baseline_std = {"TEMP":[], "PRCP":[]}
  for i in range(12):
    baseline_mean['TEMP'].append(np.mean(tas_monthly[i]))
    baseline_std['TEMP'].append(np.std(tas_monthly[i]))
    baseline_mean['PRCP'].append(np.mean(pr_monthly[i]))
    baseline_std['PRCP'].append(np.std(pr_monthly[i]))
  # print(baseline_mean)
  # print(baseline_std)
  # print(historical_mean)
  # print(historical_std)

  for i in scenarios:
    forecast_tas = {'time':[], 'value':[]}
    forecast_pr = {'time':[], 'value':[]}
    tas = AR6_CDS_GCM.main(argv=['./climateChange_data/CMIP6/tas_Amon_HadGEM3-GC31-LL_{0}_r1i1p1f3_gn_20150116-21001216.nc'.format(i),[2021,2060], 'tas']).to_dict()
    pr = AR6_CDS_GCM.main(argv=['./climateChange_data/CMIP6/pr_Amon_HadGEM3-GC31-LL_{0}_r1i1p1f3_gn_20150116-21001216.nc'.format(i),[2021,2160], 'pr']).to_dict()
    for item in tas['value'].keys():
      forecast_tas['time'].append(tas['time'][item])
      forecast_tas['value'].append(tas['value'][item]-272.15) # 轉成攝氏溫度
    for item in pr['value'].keys():
      forecast_pr['time'].append(pr['time'][item])
      forecast_pr['value'].append(pr['value'][item]*86400*num_of_days[int(pr['time'][item][5:7])-1]) # 轉成公釐/月
    # print(baseline_mean)
    # print(historical_mean)
    # print(forecast_tas['value'][0:12])
    # print(forecast_pr['value'][0:12])
    for j in range(480):
      generatedData[i]['time'].append(forecast_tas['time'][j])
      generatedData[i]['TEMP'].append(((forecast_tas['value'][j]-baseline_mean['TEMP'][j%12])/baseline_std['TEMP'][j%12])*historical_std['TEMP'][j%12]+historical_mean['TEMP'][j%12])
      generatedData[i]['PRCP'].append(((forecast_pr['value'][j]-baseline_mean['PRCP'][j%12])/baseline_std['PRCP'][j%12])*historical_std['PRCP'][j%12]+historical_mean['PRCP'][j%12])
      generatedData[i]['MN'].append((j%12)+1)

    for j in range(480):
      f = open('./climateChange_data/weatherGeneration_monthly_{0}.csv'.format(i), 'w')
      f.write('{0},{1},{2}\n'.format(generatedData[i]['time'][j], generatedData[i]['TEMP'][j], generatedData[i]['PRCP'][j]))
      f.close()
  # print(generatedData) # 'TEMP', 'PRCP'
  # print(hazardScale)

  generatedData = indoorClimateDataEstimation("climateChange", generatedData)

  risk = {
    'ssp126':{"MinT":[],"MaxT":[],"Water_Demand":[]},
    'ssp245':{"MinT":[],"MaxT":[],"Water_Demand":[]},
    'ssp585':{"MinT":[],"MaxT":[],"Water_Demand":[]}
  } # 480 month
  riskLight={
    'ssp126':{"低溫":[],"高溫":[],"乾旱":[]},
    'ssp245':{"低溫":[],"高溫":[],"乾旱":[]},
    'ssp585':{"低溫":[],"高溫":[],"乾旱":[]}
  } # 4 decade
  corrFactor = {"MinT":"AirTC_Avg","MaxT":"AirTC_Avg","Water_Demand":"Water_Demand"} #climate factor and risk factor corresponding
  
  ecdf_PRCP=[]
  for i in range(12):
    ecdf_PRCP.append(ECDF(DataArray_month[2][i]))
  for s in scenarios:
    for i in risk[s].keys():
      for j in range(480):
        if i == 'MinT':
          hazardScaleItem = hazardScale["nursery_AirTC_Avg_night"]
          value = generatedData[s]['TEMP'][j]
        elif i == 'MaxT':
          hazardScaleItem = hazardScale["flowering_AirTC_Avg_day"]
          value = generatedData[s]['TEMP'][j]
        elif i == "Water_Demand":
          hazardScaleItem = hazardScale["flowering_Water_Demand_day"]
          t=0
          # print(ecdf_PRCP.x)
          # print(P66_range['PRCP'][j][0])
          while ecdf_PRCP[480%12].x[t]<generatedData[s]['PRCP'][j]:
            t+=1
            if ecdf_PRCP[480%12].y[t]>0.4:
              risk[s][i].append('proper')
              break
          # print(ecdf_PRCP.y[t])
          if ecdf_PRCP[480%12].y[t]>0.4:                  # 使用降雨量與歷史降雨量比教作為乾旱判斷之依據
            risk[s][i].append('proper')
            continue
          elif ecdf_PRCP[480%12].y[t]>0.3:
            risk[s][i].append('slightly_low')
            continue
          elif ecdf_PRCP[480%12].y[t]>0.2:
            risk[s][i].append('low')
            continue
          else:
            risk[s][i].append('very_low')
            continue
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
    print('climateChange riskScale_{0}:{1}\n'.format(s,risk[s]))
    
    score = 0
    for i in risk[s]:
      for j in range(480):
        if i == "MinT":
          Hz = '低溫'
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
        elif i == "Water_Demand":
          Hz = '乾旱'
          if risk[s][i][j][-3:]=="igh":
            risk[s][i][j] = 0
          else:
            risk[s][i][j] =  -riskScale.index(risk[s][i][j])+3
        if j%120 == 119:
          # print(score)
          if score<60:
            riskLight[s][Hz].append('green')
          elif score<120:
            riskLight[s][Hz].append('yellow')
          elif score<180:
            riskLight[s][Hz].append('orange')
          else:
            riskLight[s][Hz].append('red')
          score = 0
        else:
          score+=risk[s][i][j]
  print('climateChange riskScale:{0}\n'.format(riskLight))
  f = open('./systemRecord/climateChange_riskLight.txt', 'a')
  f.write('{0}{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'),riskLight))
  f.close()
  return riskLight

def operationAssessment(timeScale,riskLight):
  operationalSuggestion={}
  operationData = open ('./operationMethod/operationMethod_{0}.csv'.format(timeScale), 'r')
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
        # print(line[0])
        for i in range(len((riskLight[line[0]]))):
          # print(riskLight[line[0]][i])
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
        # print(line[0])
        for i in range(len((riskLight[line[0]]))):
          # print(riskLight[line[0]][i])
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
          # print(line[0])
          for i in range(len((riskLight[scenario][line[0]]))):
            # print(riskLight[line[0]][i])
            if riskLight[scenario][line[0]][i] == line[-1].replace("\n",""):
              operationalSuggestion[scenario+'_'+line[0]]={
                "method":line[1],
                "risk_factor":line[2]
              }
              operationalSuggestion[scenario+'_'+line[0]]["time"] = '{0}年內面臨危害'.format((i+1)*10)
  # print('{0} operationalSuggestion:{1}\n'.format(timeScale, operationalSuggestion))
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
  

    # print(int(start_time[2:].replace(' ','').replace(':','').replace('-','').replace('"','')))
    
    # print(indoor_starter)
    # print(outdoor_starter)
    j = outdoor_starter
    indoor_data = {'TIMESTAMP': [], 'AirTC_Avg':[]}
    outdoor_data = {'TIMESTAMP': [],'AirTC_Avg':[], 'RH':[], 'WS':[], 'MN':[],'HR':[]}
    for i in range(indoor_starter,len(indoorData),1):
      # print(str(indoorData[i]).split(',')[0])
      # print(str(outdoorData[j]).split(',')[0])
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
      # print(solution)
      for i in range(1,num_of_trainingData,1):
        # print(i)
        output += ((outdoor_data['AirTC_Avg'][i]-solution[0])*solution[1]+(outdoor_data['MN'][i]-solution[2])*solution[3]-indoor_data['AirTC_Avg'][i])**2
      fitness = 1.0 / np.abs(output - desired_output)
      print(fitness)
      return fitness

    def fitness_func_2(solution, solution_idx):
      output = 0
      fitness = []
      # print(solution)
      for i in range(1,num_of_trainingData,1):
        # print(i)
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
  operationalSuggestion={}
  with open ('./inputData.txt', 'r') as inputData:
    location = inputData.readline().split(':')[1].replace("\n", "")
    crop = inputData.readline().split(':')[1].replace("\n", "")
    growthStage = inputData.readline().split(':')[1].replace("\n", "").split(',')

  realTimehazardScale = getHazardScale(crop, growthStage[0], "realTime")
  riskLight_realTime = realTimeRiskAssessment(realTimehazardScale)
  operationalSuggestion["realTime"]=operationAssessment("realTime",riskLight_realTime)
  
  aWeekhazardScale = getHazardScale(crop, growthStage[0], "aWeek")
  riskLight_aWeek = aWeekRiskAssessment(location, aWeekhazardScale, riskLight_realTime)
  operationalSuggestion["aWeek"]=operationAssessment("aWeek",riskLight_aWeek)

  seasonalLongTermhazardScale = getHazardScale(crop, growthStage, "seasonalLongTerm")
  riskLight_seasonalLongTerm = seasonalLongTermRiskAssessment(seasonalLongTermhazardScale, riskLight_aWeek)
  operationalSuggestion["seasonalLongTerm"]=operationAssessment("seasonalLongTerm",riskLight_seasonalLongTerm)

  climateChangehazardScale = getHazardScale(crop, "", "climateChange")
  riskLight_climateChange = climateChangeRiskAssessment(climateChangehazardScale)
  operationalSuggestion["climateChange"]=operationAssessment("climateChange",riskLight_climateChange)
  
  # indoorClimateDataEstimation('test',{})
  # testGA()
main()