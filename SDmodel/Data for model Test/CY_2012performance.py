# -*- coding: utf-8 -*-
"""
Created on Tue Sep 18 15:08:12 2018

@author: Philip
"""
import numpy as np
import pandas as pd
import os 
os.chdir(r"C:\Users\Philip\Documents\GitHub\TaoyuanSD\Data for model Test")

def Performance(Sim,Obv):
    Obv = np.array(Obv)
    Sim = np.array(Sim)
    rms = (np.nanmean((Obv-Sim)**2))**0.5   #mean_squared_error(Obv, Sim)**0.5
    r = np.nansum((Obv-np.nanmean(Obv))*((Sim-np.nanmean(Sim)))) / ( ((np.nansum((Obv-np.nanmean(Obv))**2))**0.5)*((np.nansum((Sim-np.nanmean(Sim))**2))**0.5))
            #r2_score(Sim,Obv)
    CE = 1 - np.nansum((Obv-Sim)**2)/np.nansum((Obv-np.nanmean(Obv))**2) # Nash
    CP = 1 - np.nansum((Obv[1:]-Sim[1:])**2)/np.nansum((Obv[1:]-Obv[:-1])**2)
    data = {"RMSE": rms,
            "r": r,
            "CE": CE,
            "CP": CP}
    performance = pd.DataFrame(data,columns = data.keys(),index = [0])
    print(performance)
    return performance

df = pd.read_csv("CY_2012performance.csv")
Performance(np.array(df.loc[:,"Sim"]),np.array(df.loc[:,"Obv"]))
df.plot()
df2 = pd.concat([df.loc[0:123,:],df.loc[283:364,:]],axis = 0)
df2 = df2.reset_index().drop("index",axis = 1)
Performance(np.array(df2.loc[:,"Sim"]),np.array(df2.loc[:,"Obv"]))
df2.plot()

'''
CE:
    Nash–Sutcliffe efficiency can range from −∞ to 1. An efficiency of 1 (E = 1) corresponds to a perfect match of modeled discharge to the observed data. An efficiency of 0 (E = 0) indicates that the model predictions are as accurate as the mean of the observed data, whereas an efficiency less than zero (E < 0) occurs when the observed mean is a better predictor than the model or, in other words, when the residual variance (described by the numerator in the expression above), is larger than the data variance (described by the denominator). Essentially, the closer the model efficiency is to 1, the more accurate the model is.  ~wiki
    
CP:
    Coefficient of persistence (Kitadinis and Bras, 1980; Corradini et al., 1986) is used to compare the model performance against a simple model using the observed value of the previous day as the prediction for the current day. 
The coefficient of persistence compare the predictions of the model with the predictions obtained by assuming that the process is a Wiener process (variance increasing linearly with time), in which case, the best estimate for the future is given by the latest measurement (Kitadinis and Bras, 1980). 
    Persistence model efficiency is a normalized model evaluation statistic that quantifies the relative magnitude of the residual variance (noise) to the variance of the errors obtained by the use of a simple persistence model (Moriasi et al., 2007).
    CP ranges from 0 to 1, with CP = 1 being the optimal value and it should be larger than 0.0 to indicate a minimally acceptable model performance.
    
'''