#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import numpy as np
import math
import random
import csv
from numpy.lib.function_base import append
import requests
from datetime import date, datetime
import matplotlib.pyplot as plt
from statsmodels.distributions.empirical_distribution import ECDF

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
  rawData = {"MinT":[],"MaxT":[],"RH":[],"WS":[],"Water_Storage":[]}
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
  # print (rawData)
  
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
  for i in range(4,7,1): # May~July
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
  P66_range = {'TEMP':[], 'PRCP':[]}
  for i in range(3):
    P66_range['TEMP'].append([mean['TEMP'][i]-std['TEMP'][i], mean['TEMP'][i]+std['TEMP'][i]])
    P66_range['PRCP'].append([max(0,mean['PRCP'][i]-std['PRCP'][i]), mean['PRCP'][i]+std['PRCP'][i]])
  
  # print(P66_range)
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

# def climateChangeRiskAssessment(crop, timeRange):

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
  # print('{0} operationalSuggestion:{1}\n'.format(timeScale, operationalSuggestion))
  f = open('./systemRecord/{}_operation.txt'.format(timeScale), 'a')
  f.write('{0}:{1}\n'.format(now.strftime('%Y-%m-%d %H:%M'), operationalSuggestion))
  f.close()
  return operationalSuggestion

def indoorClimateDataEstimation(timescale,data):
  return data


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

  # crop = sys.argv[1] #[cropItem]
  # timeScale = sys.argv[2] #'realTimeRiskAssessment',aWeekRiskAssessment ,'seasonalLongTermRiskAssessment', 'climateChangeRiskAssessment'
  # if timeScale == 'realTime':
  #   postalCode = sys.argv[3] #'postalCode'
  #   growthStage = sys.argv[4] #'growthStageNow'
    
  #   realTimeRiskAssessment(crop, postalCode, condition)
  # elif timeScale == 'aWeekForecast':
  #   postalCode = sys.argv[3] #'postalCode'
  #   growthStage = sys.argv[4] #'growthStageNow'
  #   aWeekRiskAssessment(crop, postalCode, growthStage)
  # elif timeScale == 'seasonalLongTerm':

  # elif timeScale == 'climateChange':

  #擷取溫室即時物聯網資料以及外部中央氣象局即時測站資料

main()