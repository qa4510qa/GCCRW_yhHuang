# -*- coding: utf-8 -*-
"""
Created on Sun Aug 18 00:42:46 2019

@author: Philip
"""

import scipy
residual = Wth_obv["467571"].copy().dropna()
residual[residual["GR01"]<0]
min(residual["GR01"])

residual = Stat["467571"]["Residual"].copy()
lamb = []
mini = []
for v in ["TX01", "TX02", "TX04", "GR01"]:
    mini.append(min(residual[v])-0.001)
    x, y = scipy.stats.boxcox(residual[v]-mini[-1])
    residual[v] = x
    lamb.append(y)
residual = (residual-residual.mean())/residual.std()
for v in ["TX01", "TX02", "TX04", "GR01"]:
    print(v)
    print(scipy.stats.normaltest(residual.loc[:,v]))
residual.hist(bins =100)

residual = Stat["467571"]["Residual"].copy()
scipy.stats.shapiro(residual.iloc[1:4000,0])
scipy.stats.shapiro(residual.iloc[1:4000,1])
scipy.stats.shapiro(residual.iloc[1:4000,2])
scipy.stats.shapiro(residual.iloc[1:4000,3])
scipy.stats.shapiro(residual.iloc[1:4000,4])
scipy.stats.normaltest(residual.iloc[:,0])
scipy.stats.normaltest(residual.iloc[:,1])
scipy.stats.normaltest(residual.iloc[:,2])
scipy.stats.normaltest(residual.iloc[:,3])
scipy.stats.normaltest(residual.iloc[:,4])
residual.hist(bins =100)
residual[residual==0].count()

from statsmodels.graphics.gofplots import qqplot
qqplot(residual.iloc[:,0], line='s')
qqplot(residual.iloc[:,1], line='s')
qqplot(residual.iloc[:,2], line='s')
qqplot(residual.iloc[:,3], line='s')
qqplot(residual.iloc[:,4], line='s')
pyplot.show()

residual = Wth_obv["467571"].dropna()
scipy.stats.shapiro(residual.iloc[1:4000,0])
scipy.stats.shapiro(residual.iloc[1:4000,1])
scipy.stats.shapiro(residual.iloc[1:4000,2])
scipy.stats.shapiro(residual.iloc[1:4000,3])
scipy.stats.shapiro(residual.iloc[1:4000,4])
scipy.stats.shapiro(residual.iloc[1:4000,5])
residual.hist(bins =100)

x = scipy.stats.norm.rvs(loc=0, scale=1, size=10000)
scipy.stats.shapiro(x)
