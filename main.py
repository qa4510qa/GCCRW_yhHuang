#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import numpy as np
import math
import random
import csv
import requests
from datetime import datetime

# from statsmodels.distributions.empirical_distribution import ECDF
CWB_API_Key = 'CWB-B7BC29A4-FADA-4DE6-9918-F2FA71A55F80'
AGRi_API_ProjectKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0bmFtZSI6IlNETGFiX0lvVF9Qcm9qZWN0XzIwMjEiLCJuYW1lIjoicjA4NjIyMDA1IiwiaWF0IjoxNjEzNzk5Nzk2fQ.elm1KN4D7geluaVTrv-J9OoZ9aFEOFb-juiVfUrFQTc'
now = datetime.now()
fuzzyRange = {"AirTC_Avg":1, "RH":5, "PAR_Avg":50, "VW_F_Avg":5, "WS_ms_Avg":3, "Water_Demand":10}
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
  print('{0} hazardScale: {1}\n'.format(timeScale, hazardScale))
  return hazardScale

def realTimeRiskAssessment(crop, postalCode, hazardScale):
  dataLabel = []
  climateData_realTime = []
  riskLight = {}
  
  with open ('./realTime_IoT_data/indoorClimateData/indoorClimateData_scheme.txt', 'r') as indoorDataScheme:
    dataLabel_indoor = indoorDataScheme.readline().split(',')

  with open ('./realTime_IoT_data/outdoorClimateData/outdoorClimateData_scheme.txt', 'r') as outdoorDataScheme:
    dataLabel_outdoor = outdoorDataScheme.readline().split(',')

  with open ('./realTime_IoT_data/systemCapacityData/systemCapacityData_scheme.txt', 'r') as systemDataScheme:
    dataLabel_system = systemDataScheme.readline().split(',')
  
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
    if i in dataLabel_indoor:
      value = line_indoor[dataLabel_indoor.index(i)]
      print('{0}: {1}'.format(i, value))
    elif i in dataLabel_outdoor:
      value = line_outdoor[dataLabel_outdoor.index(i)]
      print('{0}: {1}'.format(i, value))
    print(hazardScale[i])
    for j in range(6):
      # print(hazardScale[i][j])
      if hazardScale[i][j]== '-':
        continue
      elif j==0 and int(hazardScale[i][j])-fuzzyRange[i]>=float(value):
        risk[i]=riskScale[0]
        break
      elif j==5 and int(hazardScale[i][j])+fuzzyRange[i]<=float(value):
        risk[i]=riskScale[6]
      elif (int(hazardScale[i][j])+fuzzyRange[i])<=float(value) and (int(hazardScale[i][j+1])-fuzzyRange[i])>=float(value):
        risk[i]=riskScale[j+1]
        break
      elif float(value)>=(int(hazardScale[i][j])-fuzzyRange[i]) and float(value)<=(int(hazardScale[i][j])+fuzzyRange[i]):
        r=random.random()
        print('r: {0}'.format(r))
        if r>=(float(value)-(int(hazardScale[i][j])-fuzzyRange[i]))/(2*fuzzyRange[i]):
          risk[i]=riskScale[j]
        else:
          risk[i]=riskScale[j+1]
        print('{0}: {1}'.format(i,risk[i]))
        break
  print('\nrealTime riskScale:{0}'.format(risk))
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
  
  print('realTime riskLight:{0}'.format(riskLight))
  return riskLight

def aWeekRiskAssessment(crop, postalCode, growthStage, hazardScale):
  rawData = {"MinT":[],"MaxT":[],"RH":[],"WS":[]}
  riskLight={"高溫":[],"低溫":[],"高濕":[],"強風":[]}
  try:
    climatData_aWeekForecast = requests.get('https://opendata.cwb.gov.tw/api/v1/rest/datastore/{0}?locationName={1}&elementName={2}&sort={3}&Authorization={4}'.format("F-D0047-007","中壢區","","time",CWB_API_Key))
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
  print (rawData)
  
  indoorData = indoorClimateDataEstimation("aWeek",rawData)
  print(indoorData)

  risk = {"MinT":[],"MaxT":[],"RH":[],"WS":[]}
  for i in indoorData:
    for j in range(len(indoorData[i])):
      value = indoorData[i][j]
      corrFactor = {"MinT":"AirTC_Avg","MaxT":"AirTC_Avg","RH":"RH","WS":"WS_ms_Avg"} #climate factor and risk factor corresponding
      hazardScaleItem = []
      print(float(value))
      if j%2 == 0: #day(6:00 ~ 18:00)
        if i == 'MinT' or i == 'MaxT':
          hazardScaleItem = hazardScale["AirTC_Avg_day"]
        elif i == "RH":
          hazardScaleItem = hazardScale["RH_day"]
        elif i == "WS":
          hazardScaleItem = hazardScale["WS_ms_Avg_day"]
      else: #night(18:00 ~ 6:00)
        if i == 'MinT' or i == 'MaxT':
          hazardScaleItem = hazardScale["AirTC_Avg_night"]
        elif i == "RH":
          hazardScaleItem = hazardScale["RH_night"]
        elif i == "WS":
          hazardScaleItem = hazardScale["WS_ms_Avg_night"]
      print(hazardScaleItem)
      for k in range(6):
        if hazardScaleItem[k]== '-':
          continue
        elif k==0 and int(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]>=float(value):
          risk[i].append(riskScale[0])
          break
        elif k==5 and int(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]<=float(value):
          risk[i].append(riskScale[6])
        elif (int(hazardScaleItem[k])+fuzzyRange[corrFactor[i]])<=float(value) and (int(hazardScaleItem[k+1])-fuzzyRange[corrFactor[i]])>=float(value):
          risk[i].append(riskScale[k+1])
          break
        elif float(value)>=(int(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]) and float(value)<=(int(hazardScaleItem[k])+fuzzyRange[corrFactor[i]]):
          r=random.random()
          print('r: {0}'.format(r))
          if r>=(float(value)-(int(hazardScaleItem[k])-fuzzyRange[corrFactor[i]]))/(2*fuzzyRange[corrFactor[i]]):
            risk[i].append(riskScale[k])
          else:
            risk[i].append(riskScale[k+1])
          break
      print('{0}: {1}'.format(i,risk[i]))
  print('\naWeek riskScale:{0}'.format(risk))

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
  
  print('aWeek riskLight:{0}'.format(riskLight))
  return riskLight

# def seasonalLongTermRiskAssessment(crop, timeRange):

# def climateChangeRiskAssessment(crop, timeRange):

def operationAssessment(timeScale,riskLight):
  operationalSuggestion={}
  operationData = open ('./operationMethod/operationMethod_{0}.csv'.format(timeScale), 'r')
  for line in operationData.readlines():
    line=line.split(',')
    if line[0] in riskLight.keys():
      if riskLight[line[0]] == line[-1].replace("\n",""):
        operationalSuggestion[line[0]]={
          "method":line[1],
          "risk_factor":line[2]
        }
  print('{0} operationalSuggestion:{1}\n'.format(timeScale, operationalSuggestion))
  return operationalSuggestion

def indoorClimateDataEstimation(timescale,data):
  return data


def main():
  operationalSuggestion={}
  with open ('./inputData.txt', 'r') as inputData:
    postalCode = inputData.readline().split(':')[1].replace("\n", "")
    crop = inputData.readline().split(':')[1].replace("\n", "")
    growthStage = inputData.readline().split(':')[1].replace("\n", "")
  realTimehazardScale = getHazardScale(crop, growthStage, "realTime")
  riskLight_realTime = realTimeRiskAssessment(crop, postalCode, realTimehazardScale)
  operationalSuggestion["realTime"]=operationAssessment("realTime",riskLight_realTime)
  aWeekhazardScale = getHazardScale(crop, growthStage, "aWeek")
  riskLight_aWeek = aWeekRiskAssessment(crop, postalCode, growthStage, aWeekhazardScale)
  operationalSuggestion["aWeek"]=operationAssessment("aWeek",riskLight_aWeek)


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