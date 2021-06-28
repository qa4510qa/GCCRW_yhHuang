# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 12:13:10 2019
This file contain the functions for historical data analysis.
The "Stat" dictionary will contain all the analyzed information for later weather generation.
 
@author: Philip
"""
import pandas as pd 
import numpy as np
from scipy.stats import expon, gamma, weibull_min, norm
from numpy.linalg import inv, lstsq
import matplotlib.pyplot as plt
from MultiWG.WG_General import PreProcess, ToPickle, SaveFig
from MultiWG.WG_StatTest import PdistBIC, PdistTest, KSTestCDFPlot, NormalTest

#%% P HisAnalysis
def SelectPdist(Setting, Stat, Stn):
    if Setting["P_Distribution"] == "Auto":
        StatPdistTest = Stat[Stn]["StatPdistTest"].copy()
        StatPdistTest[StatPdistTest == "Reject"] = np.nan
        DistRank = StatPdistTest.count().reset_index(name='count').sort_values(['count'], ascending=False).reset_index()["index"]        
        # SearchDist
        def SearchDist(DistRank, m):
            for dist in DistRank[1:]:
                if StatPdistTest.loc[m, dist] == "Pass":
                    return dist
            return DistRank[0]
                
        SelectedDist = [DistRank[0]]*12
        for i, v in enumerate(list(StatPdistTest[DistRank[0]] != "Pass")):
            if v:
                SelectedDist[i] = SearchDist(DistRank, i+1)
        Stat[Stn]["MonthlyStat"]["SelectedDist"] = SelectedDist
    else:
        StatPdistTest = Stat[Stn]["StatPdistTest"].copy()
        if Setting["P_Distribution"] not in list(StatPdistTest):
            print("The chosen distribution is not supported in the program.")
            input()
            quit()
        SelectedDist = [Setting["P_Distribution"]]*12
        Stat[Stn]["MonthlyStat"]["SelectedDist"] = SelectedDist
    return Stat

def HisPAnalysis(Wth_obv, Setting, Stat):
    # Calculate Precipitation Parameters    
    def HisPAnalysis_Stn(Wth_obv, Setting, Stat, Stn):
        P_Threshold = Setting["P_Threshold"]
        Data = {"P": Wth_obv[Stn]["PP01"],    # P is the original observed data
                "Pw": Wth_obv[Stn]["PP01"]}
        PrepDF = pd.DataFrame(Data)
        
        # Prepare data for estimate prep occurance (Nan will remain Nan)
        PrepDF["Pw"][PrepDF["Pw"] > P_Threshold] = 1    # Wet day = 1
        PrepDF["Pw"][PrepDF["Pw"] <= P_Threshold] = 0    # Wet day = 1
        PrepDF["Pd"] = 1 - PrepDF["Pw"]     # Dry day = 1
        # Calculate consecutive wet day
        pp = list(PrepDF["Pw"])
        PrepDF["PP"] = [pp[-1]] + pp[0:-1]  
        PrepDF["PP"] = PrepDF["PP"] + PrepDF["Pw"]
        
        # Estimate parameters for each month
        Pw = []; Pwd = []; Pww = []
        Pexpon = []; Pgamma = []; Pweibull = []; Plognorm = []
        for m in range(12):
            PrepDF_m = PrepDF[PrepDF.index.month==(m+1)]
            
            # Prep Occurance            
            Sum = PrepDF_m.sum() # Default drop nan
            Nan = PrepDF_m.isnull().sum()
            TotalNum = PrepDF_m.shape[0]-Nan["P"]

            frq = PrepDF_m["PP"].value_counts() # Default drop nan
            Pw.append( Sum["Pw"]/TotalNum )
            Pww.append( frq[2]/Sum["Pw"] )
            Pwd.append( 1-frq[0]/Sum["Pd"] ) # 1-Pdd
        
            # Prep Amount (Using MLE as default method in scipy "fit")
            # Eliminate all nan but include all other value no matter below or above the dry day wet day threshold.
            PrepDF_m_P = PrepDF_m[PrepDF_m["P"]>0]["P"]  
            PrepDF_m_logP = np.log(PrepDF_m_P)
            Pexpon.append(expon.fit(PrepDF_m_P,floc = 0)) # return( loc, scale ) lambda = 1/mean = scale + loc
            Pgamma.append(gamma.fit(PrepDF_m_P,floc = 0)) # return( shape, loc, scale)
            Pweibull.append(weibull_min.fit(PrepDF_m_P, floc = 0)) # return( shape, loc, scale)
            
            # Coef = weibull_min.fit(PrepDF_m_P, floc = 0)
            # x = np.linspace(min(PrepDF_m_P), max(PrepDF_m_P), 1000)
            # plt.hist(PrepDF_m_P, bins = 100,normed=True,alpha = 0.5)
            # plt.plot(x, weibull_min.pdf(x, Coef[0],Coef[1],Coef[2]))
            # plt.show()
            
            Plognorm.append(norm.fit(PrepDF_m_logP, loc=0, scale=1))   # return( mu, sig)
              
        Data = {"Pw":Pw,"Pwd":Pwd,"Pww":Pww,
                "exp":Pexpon,"gamma":Pgamma,
                "weibull":Pweibull, "lognorm":Plognorm}
        MonthlyStat = pd.DataFrame(Data, columns = Data.keys(), index = np.arange(1,13))
        Stat[Stn]["MonthlyStat"] = MonthlyStat
        Stat[Stn]["PrepDF"] = PrepDF
        return Stat
    # For all Stn
    # # 可以改平行運算!!
    Stns = Setting["StnID"]
    for s in Stns:
        Stat = HisPAnalysis_Stn(Wth_obv, Setting, Stat, s)
        Stat_Stn = Stat[s]
        StatPdistTest, StatPdistPvalue = PdistTest(Stat_Stn, Method = "kstest", alpha = 0.05)
        StatPdistBIC = PdistBIC(Stat_Stn)  
        Stat[s]["StatPdistTest"] = StatPdistTest
        Stat[s]["StatPdistPvalue"] = StatPdistPvalue
        Stat[s]["StatPdistBIC"] = StatPdistBIC
        if Setting["Plot"]["KSTestCDFPlot"]:
            KSTestCDFPlot(Stat_Stn, s, Setting)
        Stat = SelectPdist(Setting, Stat, s)
    return Stat
#%% T HisAnalysis
# Output the daily avg & std and fourier coef     
def DailyMuSig(Tw, Td, Setting):
    Var = Setting["Var"].copy(); Var.remove('PP01')
    plot = Setting["Plot"]["FourierDailyTFit"]
    FourierOrder = Setting["FourierOrder"]
    # Interpolation func is to interpolate daily statistic when nan or low sample size
    def Interpolation(orgdata,nalist):
        if len(nalist)>0:   # If any nan exist
            nData = np.array(list(orgdata)[354:364]+list(orgdata)+list(orgdata)[0:10])
            for i in nalist:
                i = int(i)
                # Average over 21 days (10 before & 10 after)
                orgdata[i] = np.nanmean(nData[i:i+20+1]) 
        return orgdata
    
    def Fourier(data, order = 2, Plot = False, name = None):
        # Fit 365 data points which are averaged across the provided period 
        #least-squares solution to a linear matrix equation
        x = np.arange(1,365+1); T = 365/(2*np.pi)
        if order == 2:
            X = np.array([np.ones(x.shape[0]), np.sin(x/T), np.cos(x/T), np.sin(2*x/T), np.cos(2*x/T)]).T
            c = lstsq(X, data)[0]
            # C = [C0 D1 D2 C1 C2]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)
            C = [c[0], np.arctan(c[2]/c[1]), np.arctan(c[4]/c[3])]
            C.append(c[1]/np.cos(C[1])); C.append(c[3]/np.cos(C[2]))
            
        elif order == 3:
            X = np.array([np.ones(x.shape[0]), np.sin(x/T), np.cos(x/T), np.sin(2*x/T), np.cos(2*x/T), np.sin(3*x/T), np.cos(3*x/T)]).T
            c = lstsq(X, data)[0]
            # C = [C0 D1 D2 D3 C1 C2 C3]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)+C3*sin(3*t/T+D3)
            C = [c[0], np.arctan(c[2]/c[1]), np.arctan(c[4]/c[3]), np.arctan(c[6]/c[5])]
            C.append(c[1]/np.cos(C[1])); C.append(c[3]/np.cos(C[2])), C.append(c[5]/np.cos(C[3]))
            
        elif order == 4:
            X = np.array([np.ones(x.shape[0]), np.sin(x/T), np.cos(x/T), np.sin(2*x/T), np.cos(2*x/T), np.sin(3*x/T), np.cos(3*x/T), np.sin(4*x/T), np.cos(4*x/T)]).T
            c = lstsq(X, data)[0]
            # C = [C0 D1 D2 D3 D4 C1 C2 C3 C4]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)+C3*sin(3*t/T+D3)+C4*sin(4*t/T+D4)
            C = [c[0], np.arctan(c[2]/c[1]), np.arctan(c[4]/c[3]), np.arctan(c[6]/c[5]), np.arctan(c[8]/c[7])]
            C.append(c[1]/np.cos(C[1])); C.append(c[3]/np.cos(C[2])), C.append(c[5]/np.cos(C[3])), C.append(c[7]/np.cos(C[4]))
        
  
        # Plot the result
        if Plot:
            if order == 2:
                Y = C[0]+C[3]*np.sin(x/T+C[1])+C[4]*np.sin(2*x/T+C[2])
            elif order == 3:
                Y = C[0]+C[4]*np.sin(x/T+C[1])+C[5]*np.sin(2*x/T+C[2])+C[6]*np.sin(3*x/T+C[3])
            elif order == 4:
                Y = C[0]+C[5]*np.sin(x/T+C[1])+C[6]*np.sin(2*x/T+C[2])+C[7]*np.sin(3*x/T+C[3])+C[8]*np.sin(4*x/T+C[4])
            plt.figure()
            plt.plot(x, data, 'o', label='Origin', markersize=3)
            plt.plot(x, Y, 'r', label='Fitted')
            plt.title('Fourier seasonal trend: '+name)
            plt.xlabel("Day")
            plt.legend();
            SaveFig(plt, 'Fourier seasonal trend_'+name, Setting)
            plt.show()
        return C
    
    TFourierData = {}; TFourierCoef = {}
    for v in Var:
        # Wet 
        Tmat_w = np.reshape(np.array(Tw[v]),(-1,365))   
        Tw_avg = np.nanmean(Tmat_w, axis=0)
        nalist = np.argwhere(np.isnan(Tw_avg))  # list out nan loc
        TFourierData[v+"_w_avg"] = Interpolation(Tw_avg, nalist)
        TFourierCoef[v+"_w_avg"] = Fourier(TFourierData[v+"_w_avg"], order = FourierOrder, Plot = plot, name = v+"_w_avg")
        Tw_std = np.nanstd(Tmat_w, axis=0)
        nonzero = np.argwhere( np.count_nonzero(~np.isnan(Tmat_w), axis=0)<3 )  # Data number < 3
        nalist = np.argwhere(np.isnan(Tw_std)) # list out nan loc ( no data )
        nalist = np.concatenate((nonzero, nalist), axis=0)
        TFourierData[v+"_w_std"] = Interpolation(Tw_std,nalist)
        TFourierCoef[v+"_w_std"] = Fourier(TFourierData[v+"_w_std"], order = FourierOrder, Plot = plot, name = v+"_w_std")

        # Dry
        Tmat_d = np.reshape(np.array(Td[v]),(-1,365))   
        Td_avg = np.nanmean(Tmat_d, axis=0)
        nalist = np.argwhere(np.isnan(Td_avg))  # list out nan loc
        TFourierData[v+"_d_avg"] = Interpolation(Td_avg, nalist)
        TFourierCoef[v+"_d_avg"] = Fourier(TFourierData[v+"_d_avg"], order = FourierOrder, Plot = plot, name = v+"_d_avg")
        Td_std = np.nanstd(Tmat_d, axis=0)
        nonzero = np.argwhere( np.count_nonzero(~np.isnan(Tmat_d), axis=0)<3 )  # Data number < 3
        nalist = np.argwhere(np.isnan(Td_std)) # list out nan loc ( no data )
        nalist = np.concatenate((nonzero, nalist), axis=0)
        TFourierData[v+"_d_std"] = Interpolation(Td_std,nalist)
        TFourierCoef[v+"_d_std"] = Fourier(TFourierData[v+"_d_std"], order = FourierOrder, Plot = plot, name = v+"_d_std")        
    return [TFourierData, TFourierCoef]

    
def Residual(Tw, Td, TFourierCoef, Setting):
    Var = Setting["Var"].copy(); Var.remove('PP01')
    FourierOrder = Setting["FourierOrder"]
    #Tw = Tw.copy(); Td = Td.copy()
    WthObvYear = int(len(Tw)/365)
    # Form mu & sig array
    x = np.array(list(np.arange(1,365+1))*WthObvYear)
    def FourierFuncValue(C, x, order):
        T = 365/(2*np.pi)
        # C = [C0 D1 D2 C1 C2]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)
        if order == 2:
            Y = C[0]+C[3]*np.sin(x/T+C[1])+C[4]*np.sin(2*x/T+C[2])
        elif order == 3:
            Y = C[0]+C[4]*np.sin(x/T+C[1])+C[5]*np.sin(2*x/T+C[2])+C[6]*np.sin(3*x/T+C[3])
        elif order == 4:
            Y = C[0]+C[5]*np.sin(x/T+C[1])+C[6]*np.sin(2*x/T+C[2])+C[7]*np.sin(3*x/T+C[3])+C[8]*np.sin(4*x/T+C[4])
        return Y
    
    Residuals = pd.DataFrame()
    for v in Var:
        # Wet
        Mu_w = FourierFuncValue(TFourierCoef[v+"_w_avg"], x, FourierOrder)
        Sig_w = FourierFuncValue(TFourierCoef[v+"_w_std"], x, FourierOrder)
        Res_w = (Tw[v]-Mu_w)/Sig_w
        Res_w = Res_w.fillna(0)
        # Dry
        Mu_d = FourierFuncValue(TFourierCoef[v+"_d_avg"], x, FourierOrder)
        Sig_d = FourierFuncValue(TFourierCoef[v+"_d_std"], x, FourierOrder)
        Res_d = (Td[v]-Mu_d)/Sig_d  
        Res_d = Res_d.fillna(0)
        # Combine to Res
        Residuals[v] = Res_w + Res_d
    print("\nMu:\n",Residuals.mean(),"\nSig:\n",Residuals.std(),"\n")        
    return Residuals


def CoefAB(Res, Method = "Cov"):
    def M0M1(Res, Method = "Cov"):
        # We apply corr instead of cov 
        Res = Res.reset_index(drop=True)
        if Method == "Cov":
            M0 = Res.cov(); M0 = np.array(M0)   # Automatically ignore nan value 
        elif Method == "Corr":
            M0 = Res.corr(); M0 = np.array(M0)   # Automatically ignore nan value 
        # Deal with dimension problem
        if M0.ndim > 1:             
            np.fill_diagonal(M0,1)      # Force diagonal to 1
        else:
            M0.resize((1,1))
        lag = 1                         # Now we only consider time lag 1
        lagDf = Res[lag:].reset_index(drop=True); lagDf.columns = [v+"_"+str(lag) for v in list(lagDf)]
        Res_lag = pd.concat([Res[:-lag].reset_index(drop=True),lagDf],axis = 1)
        if Method == "Cov":
            M1 = Res_lag.cov().loc[list(Res),list(lagDf)]   # Take upright corner
        elif Method == "Corr":
            M1 = Res_lag.corr().loc[list(Res),list(lagDf)]   # Take upright corner
        return M0,M1
    M0, M1 = M0M1(Res, Method)
    A = np.dot(M1,inv(M0))
    C = M0-np.dot(np.dot(M1,inv(M0)),np.transpose(M1))
    D,V = np.linalg.eig(C)  # D: eigenvalue should be positive since cov = positive definit 
                            # sometime the observe data is not correct 
    print("C:(symmetric)\n",C)
    print("D:\n",D)
    D[D<0] = 0.000001       # therefore we force D to near zero
    C = np.dot(np.dot(V,np.diag(D)),inv(V)) # update the matrix
    D,V = np.linalg.eig(C) # spectral decomposition
    B = np.dot(np.dot( V,np.diag(np.sqrt(D)) ) , inv(V) ) 
    # BB' = C, B = V sqrt(D) V^-1
    return {"A": A, "B": B}   

def FillNanPEvent(MonthlyStat, PrepDF):
    PrepDF[["Pw","Pd"]] = PrepDF[["Pw","Pd"]].fillna(0)
    for i in range(PrepDF.shape[0]):
        if np.isnan(PrepDF["P"][i]):
            rn = np.random.uniform(low = 0, high = 1, size = 1)
            if i == 0:
                if rn <= MonthlyStat.loc[PrepDF.index[i].month,"Pw"]:
                    PrepDF["Pw"][i] = 1
                else:
                    PrepDF["Pd"][i] = 1
            elif i > 0:
                if PrepDF["Pw"][i-1] == 1: # previous day is wet day
                    if rn <= MonthlyStat.loc[PrepDF.index[i].month,"Pww"]:
                        PrepDF["Pw"][6] = 1
                    else:
                        PrepDF["Pd"][i] = 1
                elif PrepDF["Pw"][i-1] == 0: # previous day is dry day
                    if rn <= MonthlyStat.loc[PrepDF.index[i].month,"Pwd"]:
                        PrepDF["Pw"][i] = 1
                    else:
                        PrepDF["Pd"][i] = 1
    return PrepDF
            
# T main Function
def HisTAnalysis(Wth_obv, Setting, Stat):
    Var = Setting["Var"].copy(); Var.remove('PP01')
    Stns = Setting["StnID"] 
    # DailyMuSig calculation      
    for s in Stns:
        # Seperate data into wet and dry
        # (However the "Pw" and "Pd" series have nan due to error in PP01 observed data)
        # Correct those error using P(P) in each month
        PrepDF = Stat[s]["PrepDF"].copy()
        MonthlyStat = Stat[s]["MonthlyStat"]
        PrepDF = FillNanPEvent(MonthlyStat, PrepDF)
        
        Tw = Wth_obv[s][Var].mul(PrepDF["Pw"], axis=0)
        Td = Wth_obv[s][Var].mul(PrepDF["Pd"], axis=0)        
        
        Tw[Tw == 0] = np.nan; Td[Td == 0] = np.nan  # Convert 0 into NA
        TFourierData, TFourierCoef = DailyMuSig(Tw, Td, Setting)
        Stat[s]["TFourierData"] = TFourierData
        Stat[s]["TFourierCoef"] = TFourierCoef
        Stat[s]["Residual"] = Residual(Tw, Td, TFourierCoef, Setting)
        Stat[s]["ResNormalTest"] = NormalTest(Stat[s]["Residual"], Stat[s], Setting)
        Stat[s]["CoefAB"] = CoefAB(Stat[s]["Residual"], Method = "Corr")
    return Stat

#%% HisAnalysis ALL        
def HisAnalysis(Wth_obv, Setting, Stat):
    Stat = HisPAnalysis(Wth_obv, Setting, Stat)
    Stat = HisTAnalysis(Wth_obv, Setting, Stat)
    print("HisAnalysis Done!")
    # Save
    ToPickle(Setting, "Stat.pickle", Stat)
    return Stat



#%% Store here
def MCplot(Wth_gen, Stat, Setting):
    Stns = Setting["StnID"]
    Wth_gen = Wth_gen.copy()
    Stat_gen = {}
    for s in Stns:
        Stat_gen[s] = {'Warning':[]}
        Wth_gen[s] = PreProcess(Wth_gen[s], Setting)
    Stat_gen = HisAnalysis(Wth_gen, Setting, Stat_gen)
    for s in Stns:    
        # Lines PLot
        MC = pd.concat([Stat[s]["MonthlyStat"][["Pw","Pwd","Pww"]],Stat_gen[s]["MonthlyStat"][["Pw","Pwd","Pww"]]], axis = 1)
        MC.columns = ['Pw', 'Pwd', 'Pww', 'Pw_sim', 'Pwd_sim', 'Pww_sim']
        # ax = MC.plot(color = ['black','black','black','red','blue','green'],
        #              style = [".--",".-.",".:",".-",".-",".-"])
        # ax.legend(ncol = 2)
        # ax.set_ylabel("Probility")
        # ax.set_xlabel("Month")    
        # ax.set_title("Markov's parameters "+s)
        # ax.set_ylim([0,1])
        # fig = ax.get_figure()
        # SaveFig(fig, "MCplot "+s, Setting)
        
        # Regression Plot
        Max = 1; Min = 0
        fig, ax = plt.subplots(nrows = 1, ncols = 3, sharex = True, sharey = True, figsize=(10, 5))
        for i, v in enumerate(['Pw', 'Pwd', 'Pww']):
            r_squared = np.corrcoef(MC[v], MC[v+"_sim"])[0,1]**2
            ax[i].scatter(x = MC[v], y = MC[v+"_sim"], color="b", s=50)
            ax[i].set_ylim([Min, Max])
            ax[i].set_xlim([Min, Max])
            # 45 degree line
            xx = np.linspace(*ax[i].get_xlim())
            ax[i].plot(xx, xx,color = 'black',linewidth =0.5,linestyle='--')
            
            ax[i].text(0.05, 0.9, '$r^2$(monthly) = %0.3f' % r_squared,
                    verticalalignment='top', horizontalalignment='left',
                    transform=ax[i].transAxes, fontsize=9)
            ax[i].set_title(v)
        fig.suptitle(s)
        fig.text(0.5, 0.04, 'Obeserved', ha='center', va='center')
        fig.text(0.06, 0.5, 'Simulated', ha='center', va='center', rotation='vertical')
        SaveFig(fig, "MCRegPlot" + "_" + s, Setting)