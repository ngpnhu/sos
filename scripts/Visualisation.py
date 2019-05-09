#!/usr/bin/env python
# coding: utf-8

import json, os
import pandas as pd
import overpy
import subprocess
import config,time
import numpy as np

from urllib.request import urlopen
from zipfile import ZipFile
from io import StringIO
import shapefile
import geopandas as gpd
from shapely.geometry import shape, Polygon, Point

import requests
import matplotlib.pyplot as plt

wdir = "/Users/ngpnhu/Desktop/ETH"

api = overpy.Overpass()

###retrieve the outline of SG map -FIXED
sg_shp = shapefile.Reader(os.path.join(wdir,"SingaporepolySingapore_AL38268/Singapore_AL382.shp"))

attributes, geometry = [], []
field_names = [field[0] for field in sg_shp.fields[1:]]  
for row in sg_shp.shapeRecords():  
    geometry.append(shape(row.shape.__geo_interface__))  
    attributes.append(dict(zip(field_names, row.record)))  

#get this from spatial_reference.org by pasting .prj content inside
proj4_string = "+proj=tmerc +lat_0=1.366666666666667 +lon_0=103.8333333333333 +k=1 +x_0=28001.642 +y_0=38744.572 +ellps=WGS84 +units=m +no_defs"
sg_frame = gpd.GeoDataFrame(data = attributes, geometry = geometry, crs = proj4_string).to_crs(epsg = 3414)


#### 1. Map of all Instagram locations in Singapore, color-coded into parks/non-parks

## list of all Instagram locations in SG
insta_csv = pd.read_csv(os.path.join(wdir,"Insta_list_SG.csv"),dtype={"Location_id":object})
insta_csv["Location_id"] = insta_csv["Location_id"].str.split(" ").str[1]
insta_csv.reset_index(inplace=True)

## list of all Instagram locations that also reside in parks in SG
loc_lst = pd.read_csv(os.path.join(wdir,"OSM_parks_SG.csv"),dtype={"Insta_location_id":object})
loc_lst["Insta_location_id"] = loc_lst["Insta_location_id"].str.split(".").str[0]

# create list of points to be drawn on map
# list of points for parks and non parks separately
# non parks first
parks = []
non_parks = []

for i in range(0,len(insta_csv)):
    long = insta_csv["Longitude"][i]
    lat = insta_csv["Latitude"][i]
    if (long is not None) & (lat is not None):
        long = float(long)
        lat = float(lat)
        pt = Point(long,lat)
        ID = insta_csv["Location_id"][i]
        if ID in list(loc_lst['Insta_location_id']):
            parks.append(pt)
        else:
            non_parks.append(pt)

ax = sg_frame.to_crs(epsg =3414).plot(color='deepskyblue',alpha=0.2, figsize=(20,15),edgecolors='grey')  
ax.set(aspect='equal', xticks=[], yticks=[])

ax.set_title('Singapore', size=15)

parks_points=gpd.GeoDataFrame(geometry = parks, crs = proj4_string).to_crs(epsg = 3414)
nonparks_points=gpd.GeoDataFrame(geometry = non_parks, crs = proj4_string).to_crs(epsg = 3414)

nonparks_points.plot(ax=ax, color = 'darkgreen' , markersize=10, alpha=0.3, edgecolors='none',categorical=True, legend=True)
parks_points.plot(ax=ax, color = 'crimson' , markersize=16, alpha=0.7, edgecolors='none', categorical=True, legend=True)

plt.savefig(os.path.join(wdir,"All_Insta_location_id_SG.png"), bbox_inches='tight')


#### 2. Bubble chart of all Instagram locations in Singapore Botanic Gardens (size = number of images posted)

BG_loc = loc_lst[loc_lst["Location_name"]=="Singapore Botanic Gardens"]
BG_loc.reset_index(inplace=True)

#get the location names, long and lat of location id within the boundaries of Botanic Gardens
BG_lst = []
for i in range(0,len(insta_csv)):
    ID = insta_csv["Location_id"][i]
    if ID in list(BG_loc['Insta_location_id']):
        BG_lst.append([insta_csv['Location_name'][i],insta_csv['Location_id'][i],insta_csv['Longitude'][i],insta_csv['Latitude'][i]])

#count the number of images per location ID
##first, create a master json
dir_gf = os.path.join(wdir,"results")
json_lst_gf = [x for x in os.listdir(dir_gf) if x.endswith('json')]

#count the number of images downloaded per location_id
sizes = []
for metadata_src_file in json_lst_gf:
    data = json.loads(open(dir_gf+ "/"+metadata_src_file).read())
    json_name = metadata_src_file.split(".")[0]
    location_name = loc_lst['Location_name'][loc_lst[loc_lst['Insta_location_id']==json_name].index]
    if data["GraphImages"] != '':
        sizes.append([json_name,len(data["GraphImages"])])

#add on to BG_list; for those ID with no image, leave size as 0
for i in range(0,len(sizes)):
    ID = sizes[i][0]
    size = sizes[i][1]
    for j in range(0,len(BG_lst)):
        if (BG_lst[j] is not None):
            if (BG_lst[j][1]==ID):
                BG_lst[j].append(size)
                
for i in range(0,len(BG_lst)):
    if (BG_lst[i] is not None):
        if len(BG_lst[i])==4:
            print(i)
            BG_lst[i].append(0)

#create a list of points from these locations
BG_points = []
names = []
ID = []
size_loc = []
for i in range(0,len(BG_lst)):
    name = BG_lst[i][0]
    long = BG_lst[i][2]
    lat = BG_lst[i][3]
    size = BG_lst[i][4]
    if (long is not None) & (lat is not None):
        long = float(long)
        lat = float(lat)
        pt = Point(long,lat)
        BG_points.append(pt)
        names.append(name)
        ID.append(i)
        size_loc.append(size)

#get the geometry of BG
ID = OSM_lst[(OSM_lst["Name"]=="Singapore Botanic Gardens") & (OSM_lst['Object']=="way")].reset_index()['ID'][0]
query = """[out:json];way(""" + str(ID)+""");out;"""
r4 = api.query(query) #query for the list of nodes that set the boundary
nodes_lst = r4.ways[0].get_nodes(resolve_missing=True)

### create the points at the boundary of BG
point_lst = []
for i in range(0,len(nodes_lst)):
    pt = Point(float(nodes_lst[i].lon),float(nodes_lst[i].lat))
    point_lst.append(pt)

#singapore epsg
crs = {'init': 'epsg:3414'}

### create and save the geofence (polygon) for BG from the points (for later use)
poly = Polygon([[p.x, p.y] for p in point_lst])
polygon_df = gpd.GeoDataFrame(crs=crs, geometry=[poly])
polygon_df.to_file(os.path.join(wdir,'BG_polygons.shp'))

### create dataframe of location_id coordinates on map
BG_ps=gpd.GeoDataFrame(geometry = BG_points, crs = proj4_string).to_crs(epsg = 3414)
##assign attributes as desired
BG_ps['ID'] = ID
BG_ps['name']= names
BG_ps['size'] = size_loc


### draw graphs
from descartes import PolygonPatch

ax = sg_frame.to_crs(epsg =3414).plot(color='deepskyblue',alpha=0.1, figsize=(30,40),edgecolors='grey') 
ax.set(aspect='equal', xticks=[], yticks=[])

miny = poly.bounds[1] - 0.0005
maxy = poly.bounds[3] + 0.0005
minx = poly.bounds[0] - 0.001
maxx = poly.bounds[2] + 0.005

ax.add_patch(PolygonPatch(poly, fc='green', ec='black', alpha=0.6, lw =2 )) #different layers
ax.axis('scaled')
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

ax.set_title('Botanic Gardens', size=30)

for x,y,label in zip(BG_ps.geometry.x, BG_ps.geometry.y, BG_ps.ID):
    ax.annotate(label,xy=(x,y),xytext=(0,0),textcoords="offset points",size=30)
    
BG_ps.plot(ax=ax, color = 'red' , markersize=(BG_ps['size']+20)*40, alpha=1, edgecolors='black',categorical=True,column='name',legend=True)
#ax.legend(BG_ps['name'])


#### 4. Census maps: Ethnicity 

#get combined facial information by Face++ and Instagram-scraper
df = pd.read_csv(os.path.join(wdir,'combined_facial_info.csv'))

#count census
asian_count = len(df.loc[df['Ethnicity']=='ASIAN'])
white_count = len(df.loc[df['Ethnicity']=='WHITE'])
black_count = len(df.loc[df['Ethnicity']=='BLACK'])
india_count = len(df.loc[df['Ethnicity']=='INDIA'])

female_count = len(df.loc[df['Gender']=='Female'])
male_count = len(df.loc[df['Gender']=='Male'])

first_bin = len(df.loc[df['Age'].between(0,20)])
second_bin = len(df.loc[df['Age'].between(21,40)])
third_bin = len(df.loc[df['Age'].between(41,60)])
fourth_bin = len(df.loc[df['Age']>=61])

census = [[asian_count, white_count, black_count, india_count],[female_count, male_count],[first_bin,second_bin,third_bin,fourth_bin]]


from numpy.random import RandomState, uniform

### Plot races
races = ['ASIAN','WHITE', 'BLACK', 'INDIA']
num_races = len(races)

list_of_point_categories=[]
for i in range(0,num_races):
	#for j in range(0,num_geofence):
	values = int(census[0][i]) #scale down the number of points to be drawn (~500 is too much for a small area)
	print(values)
	#poly = polygon_lst[j]
	points = []
	k=0
	while len(points) < values:
		s = RandomState()#(seed+k)
		random_point = Point([s.uniform(poly.bounds[0], poly.bounds[2]), s.uniform(poly.bounds[1], poly.bounds[3])])
		if poly.contains(random_point):
			points.append(random_point)
			k+=1
	ps=gpd.GeoDataFrame(geometry = points, crs = proj4_string).to_crs(epsg = 3414)
	ps['field']= races[i]
	list_of_point_categories.append(ps)

ax = sg_frame.to_crs(epsg =3414).plot(color='black',alpha=0.4, figsize=(30,40),edgecolors='grey') 
ax.set(aspect='equal', xticks=[], yticks=[])

miny = poly.bounds[1] - 0.0005
maxy = poly.bounds[3] + 0.0005
minx = poly.bounds[0] - 0.001
maxx = poly.bounds[2] + 0.005

ax.add_patch(PolygonPatch(poly, fc='green', ec='black', alpha=0.6, fill=False, lw =2 ))
ax.axis('scaled')
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

ax.set_title('Botanic Gardens - Ethnicity Distribution', size=30)
all_points=gpd.GeoDataFrame(pd.concat(list_of_point_categories))

all_points[all_points.field =='ASIAN'].plot(ax=ax, color = 'yellow' , markersize=80, alpha=0.6, edgecolors='none', 
              categorical=True, legend=True)

all_points[all_points.field =='WHITE'].plot(ax=ax, color = 'white', markersize=80, alpha=1, edgecolors='none', 
               categorical=True, legend=True)

all_points[all_points.field =='BLACK'].plot(ax=ax, color = 'black', markersize=100, alpha=1, edgecolors='none', 
              categorical=True, legend=True)

all_points[all_points.field =='INDIA'].plot(ax=ax, color = 'brown', markersize=90, alpha=1, edgecolors='none', 
              categorical=True, legend=True)

plt.savefig("Desktop/SG_BG_ethnicity.png", bbox_inches='tight')

### Plot Genders
genders = ['FEMALE','MALE']
num_genders = len(genders)

list_of_point_categories=[]
for i in range(0,num_genders):
    #for j in range(0,num_geofence):
    values = int(census[1][i]) #scale down the number of points to be drawn (~500 is too much for a small area)
    #poly = polygon_lst[j]
    points = []
    k=0
    while len(points) < values:
        s = RandomState()#(seed+k)
        random_point = Point([s.uniform(poly.bounds[0], poly.bounds[2]), s.uniform(poly.bounds[1], poly.bounds[3])])
        if poly.contains(random_point):
            points.append(random_point)
            k+=1
    ps=gpd.GeoDataFrame(geometry = points, crs = proj4_string).to_crs(epsg = 3414)
    ps['field']= genders[i]
    list_of_point_categories.append(ps)

ax = sg_frame.to_crs(epsg =3414).plot(color='black',alpha=0.4, figsize=(30,40),edgecolors='grey') 
ax.set(aspect='equal', xticks=[], yticks=[])

miny = poly.bounds[1] - 0.0005
maxy = poly.bounds[3] + 0.0005
minx = poly.bounds[0] - 0.001
maxx = poly.bounds[2] + 0.005

ax.add_patch(PolygonPatch(poly, fc='green', ec='black', alpha=0.6, fill=False, lw =2 ))
ax.axis('scaled')
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

ax.set_title('Botanic Gardens - Gender Distribution', size=30)
all_points=gpd.GeoDataFrame(pd.concat(list_of_point_categories))

all_points=gpd.GeoDataFrame(pd.concat(list_of_point_categories))
#plot points (field ='asian') first
all_points[all_points.field =='FEMALE'].plot(ax=ax, color = 'black' , markersize=100, alpha=1, edgecolors='none', 
              column='field', categorical=True, legend=True)

all_points[all_points.field =='MALE'].plot(ax=ax, color = 'yellow', markersize=100, alpha=0.5, edgecolors='none', 
              column='field', categorical=True, legend=True)

plt.savefig("Desktop/SG_BG_genders.png", bbox_inches='tight')

### Plot age
bins = ['0-20','20-40', '40-60', '60+']
num_bins = len(bins)

list_of_point_categories=[]
for i in range(0,num_bins):
    #for j in range(0,num_geofence):
    values = int(census[2][i]) #scale down the number of points to be drawn (~500 is too much for a small area)
    #poly = polygon_lst[j]
    points = []
    k=0
    while len(points) < values:
        s = RandomState()#(seed+k)
        random_point = Point([s.uniform(poly.bounds[0], poly.bounds[2]), s.uniform(poly.bounds[1], poly.bounds[3])])
        if poly.contains(random_point):
            points.append(random_point)
            k+=1
    ps=gpd.GeoDataFrame(geometry = points, crs = proj4_string).to_crs(epsg = 3414)
    ps['field']= bins[i]
    list_of_point_categories.append(ps)

ax = sg_frame.to_crs(epsg =3414).plot(color='black',alpha=0.4, figsize=(30,40),edgecolors='grey') 
ax.set(aspect='equal', xticks=[], yticks=[])

miny = poly.bounds[1] - 0.0005
maxy = poly.bounds[3] + 0.0005
minx = poly.bounds[0] - 0.001
maxx = poly.bounds[2] + 0.005

ax.add_patch(PolygonPatch(poly, fc='green', ec='black', alpha=0.6, fill=False, lw =2 ))
ax.axis('scaled')
ax.set_xlim(minx, maxx)
ax.set_ylim(miny, maxy)

ax.set_title('Botanic Gardens - Age Distribution', size=30)
all_points=gpd.GeoDataFrame(pd.concat(list_of_point_categories))

all_points[all_points.field =='0-20'].plot(ax=ax, color = 'black' , markersize=80, alpha=1, edgecolors='none', 
              categorical=True, legend=True)

all_points[all_points.field =='20-40'].plot(ax=ax, color = 'yellow', markersize=80, alpha=0.6, edgecolors='none', 
               categorical=True, legend=True)

all_points[all_points.field =='40-60'].plot(ax=ax, color = 'white', markersize=100, alpha=1, edgecolors='none', 
              categorical=True, legend=True)

all_points[all_points.field =='60+'].plot(ax=ax, color = 'red', markersize=90, alpha=1, edgecolors='none', 
              categorical=True, legend=True)

plt.savefig("Desktop/SG_BG_ages.png", bbox_inches='tight')




