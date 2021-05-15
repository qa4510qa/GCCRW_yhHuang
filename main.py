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
riskScale = ["very_low","low","slightly_low","proper","slightly_high","high","very_high"]
riskLightScale = ["red","orange","yellow","green","yellow","orange","red"]
lightScale = ["green","yellow","orange","red"]

def getHazardScale(crop, growthStage):
  hazardScale = {} #{[stage]:{[climateFactor]:[value]}}
  current_time = now.strftime("%H")
  if int(current_time) >= 6 and int(current_time) < 18:
    conditionItem = growthStage + "_day"
  else:
    conditionItem = growthStage + "_night" # get the objective condition for crop in such stage and time

  # allFileList = os.listdir('./cropClimateCondition/{0}'.format(crop))
  # for file in allFileList:
  #   if file == conditionItem: 
  #     hazardScale['{0}'.format(file[:-4])] = {}

  # for i in hazardScale.keys():
  with open('./cropClimateCondition/{0}/{1}.csv'.format(crop ,conditionItem), newline='') as csvfile:
    rows = csv.reader(csvfile)
    for row in rows:
      print(row)
      if row[0] != '\ufeff':
        hazardScale[row[0]] = row[1:] 
  print('hazardScale: {0}'.format(hazardScale))
  return hazardScale

def realTimeRiskAssessment(crop, postalCode, hazardScale):
  dataLabel = []
  climateData_realTime = []
  riskLight = {}
  
  with open ('./indoorClimateData/indoorClimateData_scheme.txt', 'r') as indoorDataScheme:
    dataLabel_indoor = indoorDataScheme.readline().split(',')

  with open ('./outdoorClimateData/outdoorClimateData_scheme.txt', 'r') as outdoorDataScheme:
    dataLabel_outdoor = outdoorDataScheme.readline().split(',')

  with open ('./systemCapacityData/systemCapacityData_scheme.txt', 'r') as systemDataScheme:
    dataLabel_system = systemDataScheme.readline().split(',')
  
  with open('./indoorClimateData/testdata_indoor.txt', 'rb') as indoorData:
    line_indoor = indoorData.readline()
    off = -120
    while True:
      indoorData.seek(off,2) 
      lines = indoorData.readlines() 
      if len(lines)>=2: 
        line_indoor = lines[-1].decode().split(',')
        break
      off*=2 

  with open('./outdoorClimateData/testdata_outdoor.txt', 'rb') as outdoorData:
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
      print(hazardScale[i][j])
      if hazardScale[i][j]== '-':
        continue
      elif j==0 and int(hazardScale[i][j])>=float(value):
        risk[i]=riskScale[0]
        break
      elif j==5:
        risk[i]=riskScale[6]
      elif int(hazardScale[i][j])<=float(value) and int(hazardScale[i][j+1])>=float(value):
        risk[i]=riskScale[j+1]
        break
  print(risk)
  riskLight={}
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
  
  print(riskLight)
  return riskLight

def aWeekRiskAssessment(crop, postalCode, growthStage):
  climatData_aWeekForecast = {}

  try:
    #climatData_aWeekForecast = requests.get('https://agriapi.tari.gov.tw/api/CWB_ObsWeathers/observation?postalCode={0}&hours=1&projectkey={1}'.format(postalCode ,AGRi_API_ProjectKey))
    climatData_aWeekForecast = requests.get('https://agriapi.tari.gov.tw/api/CWB_PreWeathers/oneweekPredictions?postalCode={0}&eleName=T&projectkey={1}'.format(postalCode ,AGRi_API_ProjectKey))
    climatData_aWeekForecast = climatData_aWeekForecast.json()
    print(climatData_aWeekForecast)
  except requests.exceptions.HTTPError as errh:
      print(errh)
  except requests.exceptions.ConnectionError as errc:
      print(errc)
  except requests.exceptions.Timeout as errt:
      print(errt)
  except requests.exceptions.RequestException as err:
      print(err)

# def seasonalLongTermRiskAssessment(crop, timeRange):

# def climateChangeRiskAssessment(crop, timeRange):

def operationAssessment(timeScale,riskLight):
  operationalSuggestion={}
  operationData = open ('./operationMethod/operationMethod_{0}.csv'.format(timeScale), 'r')
  for line in operationData.readlines():
    print(line)
    line=line.split(',')
    if line[0] in riskLight.keys():
      print(line[-1])
      print(riskLight[line[0]])
      if riskLight[line[0]] == line[-1].replace("\n",""):
        operationalSuggestion[line[0]]={
          "method":line[1],
          "risk_factor":line[2]
        }
  return operationalSuggestion

def main():
  operationalSuggestion={}
  with open ('./inputData.txt', 'r') as inputData:
    postalCode = inputData.readline().split(':')[1].replace("\n", "")
    crop = inputData.readline().split(':')[1].replace("\n", "")
    growthStage = inputData.readline().split(':')[1].replace("\n", "")
  hazardScale = getHazardScale(crop, growthStage)
  riskLight_realTime = realTimeRiskAssessment(crop, postalCode, hazardScale)
  operationalSuggestion["realTime"]=operationAssessment("realTime",riskLight_realTime)
  aWeekRiskAssessment(crop, postalCode, growthStage)

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