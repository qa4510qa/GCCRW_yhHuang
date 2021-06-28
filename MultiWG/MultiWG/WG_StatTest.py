# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 13:22:26 2019

@author: Philip
"""
import pandas as pd
import numpy as np
from scipy.stats import kstest, expon, gamma, weibull_min, norm
from statsmodels.distributions.empirical_distribution import ECDF
from scipy.stats import t, f, kruskal, normaltest
from MultiWG.WG_General import PreProcess, SaveFig
from MultiWG.WG_Multi_HisAnalysis import HisI
import matplotlib.pyplot as plt


def SpatialAutoCorrelationComparison(Setting, Stat, Wth_gen):
    Var = Setting["Var"].copy() + ["P_Occurrence"] # Add prep event variable
    rng = list(pd.date_range( pd.datetime(2019,1,1), pd.datetime(2019,12,31)))
    MultiSiteDict = Stat["MultiSiteDict"].copy()
    for s in Setting["StnID"]:
        Wth_gen[s] = PreProcess(Wth_gen[s], Setting)
    # Observation data 
    ObvI = MultiSiteDict["HisI"].copy()
    ObvI.index = rng
    ObvI_m = ObvI.groupby(ObvI.index.month).mean()
    # Re-calculate HisI for simulated data
    MultiSiteDict = HisI(MultiSiteDict, Setting, Wth_gen, ForGenWth = False)
    SimI = MultiSiteDict["HisI"].copy()
    SimI.index = rng
    SimI_m = SimI.groupby(SimI.index.month).mean()    
    
    # Plot
    for v in Var:
        if v == "PP01" or v == "P_Occurrence":
            Max = 1; Min = 0
        else:
            Max = 1; Min = round( min(np.min(ObvI[v]),np.min(SimI[v]),0.96), 2)
        r_squared_D = np.corrcoef(ObvI[v], SimI[v])[0,1]**2
        r_squared_M = np.corrcoef(ObvI_m[v], SimI_m[v])[0,1]**2
            
        fig, ax = plt.subplots()
        ax.scatter(x = ObvI[v], y = SimI[v], color="b", s=50, label = "Daily")
        ax.scatter(x = ObvI_m[v], y = SimI_m[v], color="r", s=50, label = "Monthly")
        ax.set_xlim(Min,Max); ax.set_ylim(Min,Max)
        # 45 degree line
        xx = np.linspace(*ax.get_xlim())
        ax.plot(xx, xx,color = 'black',linewidth =0.5,linestyle='--')
        ax.text(0.05, 0.8, '$r^2$(monthly) = %0.3f' % r_squared_M,
                verticalalignment='top', horizontalalignment='left',
                transform=ax.transAxes, fontsize=9)
        ax.text(0.05, 0.85, '$r^2$(daily) = %0.3f' % r_squared_D,
                verticalalignment='top', horizontalalignment='left',
                transform=ax.transAxes, fontsize=9)
        ax.legend(fontsize=9,loc = 2) 
        ax.set_title(Setting["MultiSite"]["SpatialAutoCorrIndex"] + ": " + v)
        SaveFig(fig, Setting["MultiSite"]["SpatialAutoCorrIndex"] + "_" + v, Setting)
    return None
    
# KSTest for selecting distribution for prep
def KSTestCDFPlot(Stat_Stn, Stn, Setting):
    MonthlyStat = Stat_Stn["MonthlyStat"]
    Prep = Stat_Stn["PrepDF"]["P"]
    fig, axs = plt.subplots(nrows = 4, ncols=3,sharex=True, sharey=True)
    m = 0
    for i in range(3):
        for j in range(4):
            Prep_m = Prep[Prep.index.month==(m+1)].dropna()
            Prep_m = Prep_m[Prep_m != 0]
            coef1 = MonthlyStat.loc[m+1,"exp"]
            coef2 = MonthlyStat.loc[m+1,"gamma"]
            coef3 = MonthlyStat.loc[m+1,"weibull"]
            coef4 = MonthlyStat.loc[m+1,"lognorm"]
            # Plot
            ecdf = ECDF(Prep_m)
            x = np.arange(0,max(Prep_m),0.1)
            axs[j,i].plot(x, expon(coef1[0],coef1[1]).cdf(x), label='exp', linestyle=':' )
            axs[j,i].plot(x, gamma(coef2[0],coef2[1],coef2[2]).cdf(x), label='gamma', linestyle=':' )
            axs[j,i].plot(x, weibull_min(coef3[0],coef3[1],coef3[2]).cdf(x), label='weibull', linestyle=':' )
            xlog = np.arange(min(np.log(Prep_m)),max(np.log(Prep_m)),0.1)
            axs[j,i].plot(np.exp(xlog), norm(coef4[0],coef4[1]).cdf(xlog), label='lognorm', linestyle=':' )
            axs[j,i].plot(ecdf.x, ecdf.y, label='ecdf', color = "red")
            axs[j,i].axvline(x = 130, color = "black", linestyle = "--", linewidth=1) # Definition of storm defined by CWB
            axs[j,i].set_title(str(m+1))
            axs[j,i].legend();
            m += 1
    fig.suptitle("KStest CDF "+Stn, fontsize = 16)
    # Add common axis label
    fig.text(0.5, 0.04, 'Precipitation (mm)', ha='center', fontsize = 14)
    fig.text(0.05, 0.5, 'CDF', va='center', rotation='vertical', fontsize = 14)
    fig.set_size_inches(18.5, 10.5)
    plt.tight_layout(rect=[0.06, 0.05, 0.94, 0.94]) #rect : tuple (left, bottom, right, top)
    SaveFig(fig, "KStest CDF "+Stn, Setting)
    plt.show()
    return None

def PdistTest(Stat_Stn, Method = "kstest", alpha = 0.05):
    def KSTest(data, dist, alpha = 0.05, PlotName = None):
        res = kstest(data,dist)
        if res[1] < alpha:  restxt = "Reject"
        else:               restxt = "Pass"
        # Plot
        return restxt, res[1]    

    Pexpon = []; Pgamma = []; Pweibull = []; Plognorm = []
    Pexpon2 = []; Pgamma2 = []; Pweibull2 = []; Plognorm2 = []
    MonthlyStat = Stat_Stn["MonthlyStat"]
    Prep = Stat_Stn["PrepDF"]["P"]
    
    for m in range(0,12):
        Prep_m = Prep[Prep.index.month==(m+1)]
        Prep_m = Prep_m[Prep_m > 0]
        coef1 = MonthlyStat.loc[m+1,"exp"]
        coef2 = MonthlyStat.loc[m+1,"gamma"]
        coef3 = MonthlyStat.loc[m+1,"weibull"]
        coef4 = MonthlyStat.loc[m+1,"lognorm"]
        #coef5 = MonthlyStat.loc[m,"pearson3"]
        if Method == "kstest":            
            exp = KSTest(Prep_m, expon(coef1[0],coef1[1]).cdf, alpha, "exp "+str(m+1))
            gam = KSTest(Prep_m, gamma(coef2[0],coef2[1],coef2[2]).cdf, alpha, "gamma "+str(m+1))
            wei = KSTest(Prep_m, weibull_min(coef3[0],coef3[1],coef3[2]).cdf, alpha, "weibull "+str(m+1))
            logn = KSTest(np.log(Prep_m), norm(coef4[0],coef4[1]).cdf, alpha, "lognorm "+str(m+1))
            Pexpon.append(exp[0]); Pexpon2.append(exp[1])
            Pgamma.append(gam[0]); Pgamma2.append(gam[1])
            Pweibull.append(wei[0]); Pweibull2.append(wei[1])
            Plognorm.append(logn[0]); Plognorm2.append(logn[1])
            #Ppearson3.append(KSTest(Prep_m,pearson3(coef5[0],coef5[1],coef5[2]).cdf))           
    data = {"exp":Pexpon,
            "gamma":Pgamma,
            "weibull":Pweibull,
            "lognorm":Plognorm}
    StatPdistTest = pd.DataFrame(data, columns = data.keys(), index = np.arange(1,13) )
    data2 = {"exp":Pexpon2,
            "gamma":Pgamma2,
            "weibull":Pweibull2,
            "lognorm":Plognorm2}
    StatPdistPvalue = pd.DataFrame(data2, columns = data.keys(), index = np.arange(1,13) )
    print("P distribution test result (Reject<0.05):\n",StatPdistTest)
    return [StatPdistTest, StatPdistPvalue]

# Calculate BIC value for prep distribution
# BIC lower is better 
def PdistBIC(Stat_Stn):
    def BIC(n, k, lnL):
        return np.log(n)*k-2*lnL # BIC = ln(n)k-2ln(L)
    Pexpon = []; Pgamma = []; Pweibull = []; Plognorm = []
    MonthlyStat = Stat_Stn["MonthlyStat"]
    Prep = Stat_Stn["PrepDF"]["P"]
    
    for m in range(0,12):
        Prep_m = Prep[Prep.index.month==(m+1)]
        Prep_m = Prep_m[Prep_m > 0]
        n = len(Prep_m)
        coef1 = MonthlyStat.loc[m+1,"exp"]
        coef2 = MonthlyStat.loc[m+1,"gamma"]
        coef3 = MonthlyStat.loc[m+1,"weibull"]
        coef4 = MonthlyStat.loc[m+1,"lognorm"]
        Pexpon.append(BIC(n, 1, np.sum(expon.logpdf(Prep_m, coef1[0],coef1[1])) )) 
        Pgamma.append(BIC(n, 1, np.sum(gamma.logpdf(Prep_m, coef2[0],coef2[1],coef2[2])) )) 
        Pweibull.append(BIC(n, 1, np.sum(weibull_min.logpdf(Prep_m, coef3[0],coef3[1],coef3[2])) )) 
        Plognorm.append(BIC(n, 1, np.sum(norm.logpdf(np.log(Prep_m), coef4[0],coef4[1])) ))      
    data = {"exp":Pexpon,
            "gamma":Pgamma,
            "weibull":Pweibull,
            "lognorm":Plognorm}
    StatPdistBIC = pd.DataFrame(data, columns = data.keys(), index = np.arange(1,13) )
    return StatPdistBIC

def WGFTest(Wth_gen, Wth_obv, Setting):
    Var = Setting["Var"].copy(); Var.remove('PP01')
    Stns = Setting["StnID"]
    alpha = Setting["StatTestAlpha"]["FTest"]
    # Preprocess data 
    FtestDict = {}; Wth_gen_Test = {}; Std = {}; Dof = {}
    for s in Stns:
        FtestDict[s] = {}; Std[s] = {}; Dof[s] = {}
        Wth_gen_Test[s] = PreProcess(Wth_gen[s], Setting)
        Std[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).std()
        Std[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).std()
        Dof[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).count()-1
        Dof[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).count()-1
        FtestDict[s]["Statistic"] = Std[s]["Gen"]**2/Std[s]["Obv"]**2
        FtestDict[s]["pvalue"] = pd.DataFrame(f.cdf(FtestDict[s]["Statistic"], Dof[s]["Obv"], Dof[s]["Gen"]), columns = Var, index = np.arange(1,13))
        # Turn into result based on alpha
        FtestDict[s]["TestResult"] = pd.DataFrame(index = FtestDict[s]["pvalue"].index, columns = FtestDict[s]["pvalue"].columns).fillna("Pass")
        FtestDict[s]["TestResult"][FtestDict[s]["pvalue"] < alpha/2] = "Reject_L"
        FtestDict[s]["TestResult"][FtestDict[s]["pvalue"] > 1-alpha/2] = "Reject_H"
    return FtestDict

# Validation tests
def WGTTest(Wth_gen, Wth_obv, Setting):
    Var = Setting["Var"].copy(); Var.remove('PP01')
    Stns = Setting["StnID"]
    alpha = Setting["StatTestAlpha"]["TTest"]
    # Preprocess data   
    TtestDict = {}; Wth_gen_Test = {}; Std = {}; Avg = {}; Count = {}
    for s in Stns:
        TtestDict[s] = {}; Std[s] = {}; Avg[s] = {}; Count[s] = {}
        Wth_gen_Test[s] = PreProcess(Wth_gen[s], Setting)
        Avg[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).mean()
        Avg[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).mean()
        Std[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).std()
        Std[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).std()
        Count[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).count()
        Count[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).count()
        Count[s]["Dof"] = (Std[s]["Obv"]**2/Count[s]["Obv"] + Std[s]["Gen"]**2/Count[s]["Gen"])**2/((Std[s]["Obv"]**2/Count[s]["Obv"])**2/(Count[s]["Obv"]-1)+(Std[s]["Gen"]**2/Count[s]["Gen"])**2/(Count[s]["Gen"]-1))
        Std[s]["Std_TTest"] =  (Std[s]["Obv"]**2/Count[s]["Obv"] + Std[s]["Gen"]**2/Count[s]["Gen"])**0.5       
        TtestDict[s]["Statistic"] = np.abs((Avg[s]["Obv"]-Avg[s]["Gen"])/Std[s]["Std_TTest"]) # Two tails
        TtestDict[s]["pvalue"] = pd.DataFrame(t.cdf(TtestDict[s]["Statistic"], Count[s]["Dof"]), columns = Var, index = np.arange(1,13))
        # Turn into result based on alpha
        TtestDict[s]["TestResult"] = pd.DataFrame(index = TtestDict[s]["pvalue"].index, columns = TtestDict[s]["pvalue"].columns).fillna("Pass")
        TtestDict[s]["TestResult"][TtestDict[s]["pvalue"] < alpha/2] = "Reject"
        TtestDict[s]["TestResult"][TtestDict[s]["pvalue"] > 1-alpha/2] = "Reject"
        # Plot
    return TtestDict

def MonthlyStatPlot(Wth_gen, Wth_obv, Setting):
    Var = Setting["Var"].copy(); #Var = Var+["P_Occurance"]
    Stns = Setting["StnID"]
    TtestDict = {}; Wth_gen_Test = {}; Std = {}; Avg = {}; Count = {}
       
    for s in Stns:
        TtestDict[s] = {}; Std[s] = {}; Avg[s] = {}; Count[s] = {}
        Wth_gen_Test[s] = PreProcess(Wth_gen[s], Setting)
        Avg[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).mean()
        Avg[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).mean()
        Std[s]["Obv"] = Wth_obv[s][Var].groupby(Wth_obv[s].index.month).std()
        Std[s]["Gen"] = Wth_gen_Test[s][Var].groupby(Wth_gen_Test[s].index.month).std()
        fig, axs = plt.subplots(nrows = 2, ncols = len(Var), sharex=False, sharey=False)
        for i, v in enumerate(Var):
            axs[0,i].plot(Avg[s]["Obv"][v], Avg[s]["Gen"][v], "o")
            axs[0,i].plot(axs[0,i].get_ylim(), axs[0,i].get_ylim(), color = "black", linestyle = ":", linewidth = 1)
            axs[0,i].set_title("Avg: "+v)
            axs[1,i].plot(Std[s]["Obv"][v], Std[s]["Gen"][v], "o")
            axs[1,i].plot(axs[1,i].get_ylim(), axs[1,i].get_ylim(), color = "black", linestyle = ":", linewidth = 1)
            axs[1,i].set_title("Std: "+v)
            r_squared_avg = np.corrcoef(Avg[s]["Obv"][v], Avg[s]["Gen"][v])[0,1]**2
            axs[0,i].text(0.05, 0.9, '$r^2$ = %0.3f' % r_squared_avg,
                            verticalalignment='top', horizontalalignment='left',
                            transform=axs[0,i].transAxes, fontsize=9)
            r_squared_std = np.corrcoef(Std[s]["Obv"][v], Std[s]["Gen"][v])[0,1]**2
            axs[1,i].text(0.05, 0.9, '$r^2$ = %0.3f' % r_squared_std,
                            verticalalignment='top', horizontalalignment='left',
                            transform=axs[1,i].transAxes, fontsize=9)
        fig.suptitle("Monthly Statistic Plot: " + s, fontsize = 16)
        # Add common axis label
        fig.text(0.5, 0.04, 'Observed', ha='center', fontsize = 14)
        fig.text(0.05, 0.5, 'Generated', va='center', rotation='vertical', fontsize = 14)
        fig.set_size_inches(18.5, 10.5)
        plt.tight_layout(rect=[0.06, 0.05, 0.94, 0.94]) #rect : tuple (left, bottom, right, top)
        SaveFig(fig, "MonthlyStatPlot "+s, Setting)
    return {"Avg":Avg, "Std":Std}

def Kruskal_Wallis_Test(Wth_gen, Wth_obv, Setting):
    alpha = Setting["StatTestAlpha"]["Kruskal_Wallis_Test"]
    Stns = Setting["StnID"]
    KruskalDict = {}
    for s in Stns:
        Obv = Wth_obv[s]["PP01"]; Gen = Wth_gen[s]["PP01"]
        # Remove nan in Obv series
        Obv = Obv[~Obv.isnull()]
        
        pvalue = []; statistic = []; result = ["Pass"]*12
        for m in range(12):
            Obvm = Obv[Obv.index.month == m+1]
            Genm = Gen[Gen.index.month == m+1]
            pvalue.append(kruskal(Obvm,Genm)[1])
            statistic.append(kruskal(Obvm,Genm)[0])
            if pvalue[m] < alpha:
                result[m] = "Reject"
        data = {"pvalue":pvalue,
                "statistic":statistic,
                "result": result}
        df = pd.DataFrame(data,columns = data.keys())
        KruskalDict[s] = df
    return KruskalDict

def NormalTest(residual, Stat_s, Setting):
    Var = Setting["Var"].copy(); Var.remove('PP01')  
    ResNormalTest = pd.DataFrame()  
    for v in Var:      
        res = normaltest(residual.loc[:,v])
        if res[1] < 0.05:  
            restxt = "Reject"
            Stat_s["Warning"].append("NormalTest: Normal test is rejected at "+v)
        else:               
            restxt = "Pass"
        ResNormalTest[v] = restxt
        return ResNormalTest

def RnNumHistPlot(Setting, Stat):
    Stns = Setting["StnID"]
    for s in Stns:
        fig, ax = plt.subplots()
        Rn = Stat[s]["RnNum"]
        Rn.hist(bins = 100, ax = ax) 
        fig.suptitle("Histogram of Random number used by "+s)
        fig.set_size_inches(18.5, 10.5)
        plt.tight_layout(rect=[0.06, 0.05, 0.94, 0.94])
        SaveFig(fig, "RnNumHistPlot "+s, Setting)