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

def getPlantCondition(crop, growthStage):
  plantCondition = {} #{[stage]:{[climateFactor]:[value]}}
  current_time = now.strftime("%H")
  if int(current_time) >= 6 and int(current_time) < 18:
    conditionItem = growthStage + "_day.csv"
  else:
    conditionItem = growthStage + "_night.csv" # get the objective condition for crop in such stage and time

  allFileList = os.listdir('./cropClimateCondition/{0}'.format(crop))
  for file in allFileList:
    if file == conditionItem: 
      plantCondition['{0}'.format(file[:-4])] = {}

  for i in plantCondition.keys():
    with open('./cropClimateCondition/{0}/{1}.csv'.format(crop ,i), newline='') as csvfile:
      rows = csv.reader(csvfile)
      for row in rows:
        print(row)
        if row[0] != '\ufeff':
          plantCondition[i][row[0]] = row[1:] 
  print('plantCondition: {0}'.format(plantCondition))
  return plantCondition

def realTimeRiskAssessment(crop, postalCode, condition):
  dataLabel = []
  climateData_realTime_outdoor = []
  climateData_realTime_indoor = []
  riskLight = {}

  try:
    climateData_realTime_outdoor = requests.get('https://agriapi.tari.gov.tw/api/CWB_ObsWeathers/observation?postalCode={0}&hours=1&projectkey={1}'.format(postalCode ,AGRi_API_ProjectKey))
    climateData_realTime_outdoor = climateData_realTime_outdoor.json()
    # Code here will only run if the request is successful
    #print('climateData_realTime_outdoor: {0}'.format(climateData_realTime_outdoor))
  except requests.exceptions.HTTPError as errh:
    print(errh)
  except requests.exceptions.ConnectionError as errc:
    print(errc)
  except requests.exceptions.Timeout as errt:
    print(errt)
  except requests.exceptions.RequestException as err:
    print(err)
  

  with open ('./indoorClimateData/indoorClimateData_scheme.txt', 'r') as indoorDataScheme:
    dataLabel = indoorDataScheme.readline().split(',')
  with open('./indoorClimateData/testdata_indoor.txt', 'r') as indoorData:
    line = indoorData.readline()
    off = -50
    while True:
      indoorData.seek(off, 2) 
      lines = indoorData.readlines() 
      if len(lines)>=2: 
        line = lines[-1] 
        break
      offs *= 2
    print(line)
  for i in plantCondition.keys():
    print(i)





    # line = indoorData.readline()
    # # timeNow = now.strftime("%Y-%m-%d %H:%M")
    # timeNow = "2021-03-08 00:04"
    # # print(timeNow[0:10])    
    # while line != '':
    #   arr = line.split(',')
    #   # print(arr[0][1:11])
    #   # print(timeNow[0:10])
    #   if arr[0][1:11] == timeNow[0:10]: # now.strftime("%Y-%m-%d")
        
    #   line = indoorData.readline()




def aWeekRiskAssessment():
  climatData_aWeekForecast = {}

  try:
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

def main():  
  crop = sys.argv[1] #[cropItem]
  timeScale = sys.argv[2] #'realTimeRiskAssessment',aWeekRiskAssessment ,'seasonalLongTermRiskAssessment', 'climateChangeRiskAssessment'
  if timeScale == 'realTime':
    postalCode = sys.argv[3] #'postalCode'
    growthStage = sys.argv[4] #'growthStageNow'
    condition = getPlantCondition(crop, growthStage)
    realTimeRiskAssessment(crop, postalCode, condition)
  elif timeScale == 'aWeekForecast':
    postalCode = sys.argv[3] #'postalCode'
    growthStage = sys.argv[4] #'growthStageNow'
    aWeekRiskAssessment()
  # elif timeScale == 'seasonalLongTerm':

  # elif timeScale == 'climateChange':


  #擷取溫室即時物聯網資料以及外部中央氣象局即時測站資料

main()