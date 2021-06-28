# -*- coding: utf-8 -*-

"""
Created on Fri Mar 22 13:29:23 2019
Low frequency components
Use WeaGets method + AR model
@author: Philip
"""
import numpy as np
import pandas as pd
from scipy.fftpack import fft,ifft
from MultiWG.WG_HisAnalysis import CoefAB
#from cmath import exp, pi
#def fft(x):
#    N = len(x)
#    if N <= 1: return x
#    even = fft(x[0::2])
#    odd =  fft(x[1::2])
#    T= [exp(-2j*pi*k/N)*odd[k] for k in range(N//2)]
#    return [even[k] + T[k] for k in range(N//2)] + \
#           [even[k] - T[k] for k in range(N//2)]
           
def LowFrequecy(Wth_obv, Wth_gen, Setting, Stat):
    Wth_obv = Wth_obv.copy()
    Wth_gen = Wth_gen.copy()
    Stns = Setting["StnID"]
    for s in Stns:
        Stat[s]["LowFrequency"] = {}
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
        # Precipitation
        # Monthly correction
        def P_month_gen(Monthly_obv_stn, m, mObvYear):
            Monthly_obvP_m = Monthly_obv_stn["PP01"][Monthly_obv_stn.index.month == m]
            MeanP = np.mean(Monthly_obvP_m)
            n = int(len(Monthly_obvP_m))
            if n%2 != 0:
                print("Observed years have to be even number!")   
            Cf = fft(Monthly_obvP_m)/n
            Spec = abs(Cf)  # spectrum abs(fft(Monthly_obvP_m))#
            RNPhase = np.random.uniform(low=0.0, high= 2*np.pi, size = n)
            RNPhase = [complex(0,i) for i in RNPhase] # Turn into complex form
            NewSeriesM = Spec*np.exp(RNPhase)
            # Construct symmetric => ifft back to real number!
            NewSeriesM[0] = 0#NewSeriesM[0].real
            NewSeriesM[int(n/2)] = 0#NewSeriesM[int(n/2)].real
            NewSeriesM[int(n/2)+1:] = np.flip(NewSeriesM[1:int(n/2)]).conjugate()
            NewSeriesM = MeanP + ifft(NewSeriesM).real*n
            #NewSeriesM[NewSeriesM<0] = MeanP
            NewSeriesM = np.array(list(NewSeriesM)*mObvYear)
            return NewSeriesM
    ##########################################################################
    # Don't know the funcking fft problem!!!! why different from matlab ######
        MonthlyNewSeries = {}
        MonthlyNewSeries[s] = pd.DataFrame()
        for m in range(12):
            MonthlyNewSeries[s][m+1] = P_month_gen(Monthly_obv[s], m+1, mObvYear)
        ###########################################################################
                
        def P_year_gen_all(Yearly_obv_stn, mObvYear):
            GenYear = Setting["GenYear"]
            Var = list(Yearly_obv_stn)
            Var = ["PP01"]+[i for i in Var if "TX" in i]
            Yearly_obv_stn = Yearly_obv_stn.copy()[Var]
            Std = Yearly_obv_stn.std(); 
            Mean = Yearly_obv_stn.mean(); 
            Skew = Yearly_obv_stn.skew();      
            # Tho
            lag = 1                         # Now we only consider time lag 1
            lagDf = Yearly_obv_stn[lag:].reset_index(drop=True); lagDf.columns = [v+"_"+str(lag) for v in list(lagDf)]
            Res_lag = pd.concat([Yearly_obv_stn[:-lag].reset_index(drop=True),lagDf],axis = 1)
            M1 = Res_lag.corr().loc[list(Yearly_obv_stn),list(lagDf)]
            
            # Calculate A B
            # Residue
            for v in Var:
                Yearly_obv_stn[v] = (Yearly_obv_stn[v] - Mean[v])/Std[v]
            CoefAB_y = CoefAB(Yearly_obv_stn, Method = "Cov")
    
            
            RnNum = {}; NewSeriesY = {}
            # Gen RN
            for v in Var:
                # Do skew correction to all v (or may limit to P)
                RnNum[v] = np.random.normal(0, 1, size = GenYear)
                p = M1.loc[v,v+"_"+str(lag)]
                g = (1-p**3)*Skew[v]/(1-p**2)**1.5 # Wilson-Hilferty transformation
                RnNum[v] = 2/g*(1+g*RnNum[v]/6-g**2/36)**3 - 2/g 
                RnNum = pd.DataFrame(RnNum)
                
            def AR1(CoefAB, Rn_T, Var):
                res = np.zeros((Rn_T.shape[0]+1, Rn_T.shape[1]))
                for i in range(Rn_T.shape[0]):
                    Rn = Rn_T.loc[i,:]
                    res[i+1] = np.dot(CoefAB["A"],res[i]) + np.dot(CoefAB["B"],Rn)
                res = pd.DataFrame(res, columns = Var)
                return res.loc[1:,:].reset_index(drop=True)
            
            # AR1
            NewSeriesY = AR1(CoefAB_y, RnNum, Var)
            for v in Var:
                NewSeriesY[v] = Mean[v] + NewSeriesY[v]*Std[v]
            return NewSeriesY
        
        YearlyNewSeries = {}
        Yearly_obv_stn = Yearly_obv[s]
        YearlyNewSeries[s] = P_year_gen_all(Yearly_obv_stn, mObvYear)
        
        # Update P iteratively
        def CorrectPMonthly(Wth_gen, Monthly_gen, MonthlyNewSeries ):
            Ratio = Monthly_gen[s]["PP01"]/MonthlyNewSeries[s].values.reshape(-1,1)
            a = MonthlyNewSeries[s].values.reshape(-1,1)
            for m in range(12):
                
        
        def CorrectPiter():
            
