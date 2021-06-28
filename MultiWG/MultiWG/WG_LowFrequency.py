# -*- coding: utf-8 -*-
"""
Created on Mon Mar 25 14:07:39 2019

@author: Philip
"""

# For stn
Stat[s]["LowFrequency"] = {}
Stat_Stn = 


GenYear = Setting["GenYear"]
Wth_obv_stn = Wth_obv[s]
Wth_gen_stn = Wth_gen[s]
MonthlyWth = {}; YearlyWth = {}
MonthlyWth["Obv"] = Wth_obv_stn.resample("M").mean()
MonthlyWth["Obv"]["PP01"] = Wth_obv_stn["PP01"].resample("M").sum()
YearlyWth["Obv"] = Wth_obv[s].resample("Y").mean()
YearlyWth["Obv"]["PP01"] = Wth_obv_stn["PP01"].resample("Y").sum()

# Assign datetime rng to Wth_gen
if GenYear



Monthly_obv = {}; Yearly_obv = {}
Monthly_gen = {}; Yearly_gen = {}
Monthly_obv[s] = Wth_obv[s].resample("M").mean()
Yearly_obv[s] = Wth_obv[s].resample("Y").mean() 
Monthly_gen[s] = Wth_gen[s].resample("M").mean() 
Yearly_gen[s] = Wth_gen[s].resample("Y").mean()   
# P is "Sum"
Monthly_obv[s]["PP01"] = Wth_obv[s]["PP01"].resample("M").sum()
Yearly_obv[s]["PP01"] = Wth_obv[s]["PP01"].resample("Y").sum()
Monthly_gen[s]["PP01"] = Wth_gen[s]["PP01"].resample("M").sum()
Yearly_gen[s]["PP01"] = Wth_gen[s]["PP01"].resample("Y").sum()

mObvYear = int(Setting["GenYear"]/(Wth_obv[s].shape[0]/365))