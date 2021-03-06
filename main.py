# Algorithmic trading strategy using Oanda API
# import modules
from configparser import SafeConfigParser
import os
import oandapy as opy
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import seaborn as sns
sns.set()

# API access ----

# If using config file to bring in tokens/account ID

def get_config_info(filepath, section, variable):


    if os.path.isfile(filepath):
        parser = SafeConfigParser()
        parser.read(filepath)
        config_token = parser.get(section, variable)
    else:
        print("CodeError: Config file not found")

    return config_token

API_token_info = "43e890eb21da272670ba8df4f27a4d8e-72d3104edd817c256cbd205e351800fd"
account_id_info = "101-004-11425199-001"
# Access Oanda API
oanda = opy.API(environment="practice", access_token=API_token_info)


# BackTesting ---

# Data to be requested
data = oanda.get_history(instrument="EUR_USD",  # our instrument
                         start="2016-12-08",  # start data
                         end="2016-12-10",  # end date
                         granularity="M1")  # minute bars

# Place data into dataframe , requested data returned in candle format
df = pd.DataFrame(data['candles']).set_index('time')
# Index against datatime
df.index = pd.DatetimeIndex(df.index)
# display retrieved data
df.info()


# Trading strategy ---

# log of close asking price divided by close asking price +1
df['returns'] = np.log(df['closeAsk'] / df['closeAsk'].shift(1))

# empty array
cols = []

# Plot each time strategy and instrument
for momentum in [15, 30, 60, 120]:
    col = 'position_{}'.format(momentum)
    # return whether momentum positive or negative with 'np.sign'
    # mean momentum is the window size (using 'df.rolling') 
    # considered 
    df[col] = np.sign(df['returns'].rolling(momentum).mean())
    cols.append(col)

# initialise list of signals
strats = ['returns']

for col in cols:
    # window size from col names (e.g. 15, 30, etc.)
    strat = 'strategy_{}'.format(col.split('_')[1])
 
    # List created signals
    strats.append(strat)

    #FIXME: Understand this ....
    df[strat] = df[col].shift(1) * df['returns']

# drop nans, cumulative sum, take exponential of each element
# plot each of the strats + returns
df[strats].dropna().cumsum().apply(np.exp).plot()
plt.show()

# Automated Trading ---


class MomentumTrader(opy.Streamer):  # 25

    def __init__(self, momentum, *args, **kwargs):  # 26
        opy.Streamer.__init__(self, *args, **kwargs)  # 27
        self.ticks = 0  # 28
        self.position = 0  # 29
        self.df = pd.DataFrame()  # 30
        self.momentum = momentum  # 31
        self.units = 100000  # 32

    def create_order(self, side, units):  # 33
            order = oanda.create_order(config['oanda']['account_id'], 
                                       instrument='EUR_USD', units=units, side=side,
                                       type='market')  # 34
            print('\n', order)  # 35

    def on_success(self, data):  # 36
        self.ticks += 1  # 37
        print(self.ticks, end=', ')
        # appends the new tick data to the DataFrame object
        self.df = self.df.append(pd.DataFrame(data['tick'],
                                 index=[data['tick']['time']]))  # 38
        # transforms the time information to a DatetimeIndex object
        self.df.index = pd.DatetimeIndex(self.df['time'])  # 39
        # resamples the data set to a new, homogeneous interval
        dfr = self.df.resample('5s').last()  # 40
        # calculates the log returns
        dfr['returns'] = np.log(dfr['ask'] / dfr['ask'].shift(1))  # 41
        # derives the positioning according to the momentum strategy
        dfr['position'] = np.sign(dfr['returns'].rolling( 
                                      self.momentum).mean())  # 42
        if dfr['position'].ix[-1] == 1:  # 43
            # go long
            if self.position == 0:  # 44
                self.create_order('buy', self.units)  # 45
            elif self.position == -1:  # 46
                self.create_order('buy', self.units * 2)  # 47
            self.position = 1  # 48
        elif dfr['position'].ix[-1] == -1:  # 49
            # go short
            if self.position == 0:  # 50
                self.create_order('sell', self.units)  # 51
            elif self.position == 1: # 52
                self.create_order('sell', self.units * 2)  # 53
            self.position = -1  # 54
        if self.ticks == 250:  # 55
            # close out the position
            if self.position == 1:  # 56
                self.create_order('sell', self.units)  # 57
            elif self.position == -1:  # 58
                self.create_order('buy', self.units)  # 59
            self.disconnect()  # 60

mt = MomentumTrader(momentum=12, environment='practice',
                    access_token="43e890eb21da272670ba8df4f27a4d8e-72d3104edd817c256cbd205e351800fd")
mt.rates("101-004-11425199-001",
         instruments="DE30_EUR", ignore_heartbeat=True)
