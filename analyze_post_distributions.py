# coding: utf-8
import pandas as pd
import time
import matplotlib.pyplot as plt

dfs = [pd.read_csv("results/gf0/gf0.csv"), pd.read_csv("results/gf1/gf1.csv")]

for i, df in enumerate(dfs):
    df['Time'] = pd.to_datetime(df['Timestamp'],unit='s')
    df['Time'] = df.Time.dt.tz_localize('UTC').dt.tz_convert('Asia/Singapore')

    df['DoW'] = df['Time'].dt.dayofweek
    df['Hour'] = df['Time'].dt.hour

    day_lst = {0:'Monday',1: 'Tuesday',2:'Wednesday',3:'Thursday',4:'Friday',5:'Saturday',6:'Sunday'}
    df.replace({'DoW':day_lst})

    day = ["Monday", "Tuesday", "Wednesday",'Thursday','Friday','Saturday','Sunday']
    df.groupby(['DoW']).count()['Timestamp'].plot(kind = "bar",title='Posting time distribution by Day of the Week (Monday = 0, Sunday = 6) - {}'.format(i))
    plt.show()

    df.groupby(['Hour']).count()['Timestamp'].plot(kind = "bar",title='Posting time distribution by Hour of the Day - {}'.format(i))
    plt.show()
