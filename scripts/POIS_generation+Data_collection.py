#!/usr/bin/env python
# coding: utf-8

import json, os
import pandas as pd
import overpy
import subprocess
import config,time
import shapefile
from shapely.geometry import Point, shape, Polygon # Point class

wdir = "/Users/ngpnhu/Desktop/ETH"


# ## Processes:
# 
# 1. Collect list of all locations in Singapore (available from OpenStreetMap)
# 2. Generate all possible name combinations using (1)
#     2.1 For each name, get a list of possible location_ids using Instagram Scraper 
#     2.2 Make sure location_id is within Singapore boundary)
# 3. To collect all images from a certain location:    
#     3.1 Get the geofence of the desired location (a polygon) 
#     3.2 Filter for location_id residing in the polygon.   
#     3.3 Query images from all location_ids in 4.2

# ### 1. Collect list of all locations in Singapore (available from OpenStreetMap)
# *Note: "ISO3166-1" is the tag for area name; "SG" is the name code for Singapore*
api = overpy.Overpass()

r1 = api.query("""[out:json][timeout:120000];area["ISO3166-1"="SG"];(node["name"](area););out body;""")
r2 = api.query("""[out:json][timeout:120000];area["ISO3166-1"="SG"];(way["name"](area););out body;""")
r3 = api.query("""[out:json][timeout:110000];area["ISO3166-1"="SG"];(relation["name"](area););out body;""")
# *Note: exhaustive list of all location objects in SG: 17431 nodes (r1), 79853 ways (r2), 1296 relations (r3)*

lst_nodes = []
for i in range(0,len(r1.get_nodes())): #extract relevant info from json file containing nodes
    node_id = r1.get_nodes()[i].id
    info = vars(r1.get_node(node_id))
    lst_nodes.append([node_id,info['tags']['name'],'node',info['attributes'],float(info['lat']),float(info['lon']),info['tags']])

lst_ways = []
for i in range(0,len(r2.get_ways())): #extract relevant info from json file containing ways
    way_id = r2.get_ways()[i].id
    info = vars(r2.get_way(way_id))
    lst_ways.append([way_id,info['tags']['name'],'way',info['attributes'],info['center_lat'],info['center_lon'],info['tags']])

lst_relations = []
for i in range(0,len(r3.get_relations())): #extract relevant info from json file containing relations
    relation_id = r3.get_relations()[i].id
    info = vars(r3.get_relation(relation_id))
    lst_relations.append([relation_id,info['tags']['name'],'way',info['attributes'],info['center_lat'],info['center_lon'],info['tags']])

lst = lst_nodes+lst_ways+lst_relations

name_lst = pd.DataFrame(lst, columns=['ID',"Name","Object","Attributes","Lat","Lon","Tags"])
name_lst.to_csv(os.path.join(wdir,"OSM_list_SG.csv"),sep=",",index=False)
# *Note: the final dataframe contains 98490 OSM objects* 


# ### 2. Generate all possible name combinations using (1)
data = pd.read_csv(os.path.join(wdir,"OSM_list_SG.csv"))

##### 2.1 create a list of separated words from poi name e.g [east, coast, park]
data['word_lst'] = data['Name'].str.split(" ")

sep = "-"
search_lst = []
for i in range(0,len(data)):# number of POIs
    #convert all words to lower case
    word_lst = [x.lower() for x in data.iloc[i,7]]
    n = len(word_lst)
    keyword_lst = []
    #generate keywords by joining the first word with the second, then the first+second with the third, so on.
    #each keyword is hyphen-separated
    for j in range (0, n):
        for k in range(j+1, n+1):
            keyword_lst.append(sep.join(word_lst[j:k]))
    search_lst = search_lst + keyword_lst

#remove duplicates
search_lst_unique = list(set(search_lst))
search_lst_unique_df = pd.DataFrame(search_lst_unique,columns=["keyword"])
search_lst_unique_df.to_csv(os.path.join(wdir,"search_lst.csv"),sep=",",index=False) 
# *Note: created a list of 549855 keywords, with 91578 unique keywords to search for in InstagramScraper*


# ### 2.2. For each name, get a list of possible location_ids using Instagram Scraper
search_lst_unique = pd.read_csv(os.path.join(wdir,"search_lst.csv"))
search_lst_unique = search_lst_unique["keyword"]

scraped_data = []

for j in range(0, len(search_lst_unique)):  
    key = search_lst_unique[j]
    result = subprocess.Popen(['instagram-scraper', '-u', 'nhubt4212', '-p', 'cubS2pup!', '--search-location',key], stdout=subprocess.PIPE).stdout.readlines()
    
    #get the output of search-location query, which typically a few options 
    if len(result) >2: #only get output result that does not contain error - the ones with error only return 2 lines
        for i in result[2:]:
            info = i.decode("utf-8").split(",")
            #latitude and longtitude are always the last 2 fields
            lon_info = info[len(info)-1].split(":")
            lat_info = info[len(info)-2].split(":")
            
            if len(lon_info)>1: #if longtitude exists
                lon = lon_info[1]
            else: #if longitude does not exists, record empty
                lon = None
                
            if len(lat_info)>1: 
                lat = lat_info[1]
            else:
                lat = None
            #location_id and name are always the first two fields
            #add '-' to make sure csv does not cut off last few digits of long int
            loc_info = info[0].split(":")
            if len(loc_info)>1:
                loc_id = loc_info[1]
            else:
                loc_id = ""
            
            name_info = info[1].split(":")
            if len(name_info)>1:
                name = name_info[1]
            else:
                name = ""
            
            lst = [name,key,loc_id,lon,lat]
            scraped_data.append(lst)
    print(j)

location_lst = pd.DataFrame(scraped_data, columns=['Location_name','Handler','Location_id','Longitude','Latitude'])
location_lst['Longitude'] = location_lst['Longitude'].str.split('\n').str[0]

#remove duplicates location_id
location_lst.drop_duplicates('Location_id', inplace = True)
location_lst.reset_index(inplace=True)

location_lst=location_lst.drop('index',axis=1)
location_lst['Location_id'] = location_lst['Location_id'].str.split('-').str[0]


# #### Make sure location_id is within Singapore boundary
#get the boundary of Singapore, by checking if Lat Long lies in Singapore geofence

#read SG shapefile
sg_shp = shapefile.Reader("/Users/ngpnhu/Desktop/ETH/SingaporepolySingapore_AL38268/Singapore_AL382.shp")
#SG shapefiles contain the shapes of 5 regions: Central, Northeast, Northwest, Southeast, Southwest
all_shapes = sg_shp.shapes()
all_records = sg_shp.records()

#create a column for label (label = any of the 5 region the lat/long of the location_id lies in)
location_lst["in_SG?"] = ""

#label
for i in range(0,len(location_lst)):
    long = location_lst.iloc[i,3]
    lat = location_lst.iloc[i,4]
    if (long is not None) & (lat is not None):
        long = float(long)
        lat = float(lat)
        point = (long,lat) # an Long,Lat tuple
        for j in range(0,len(all_shapes)):
            boundary = all_shapes[j] # get a boundary polygon 
            if Point(point).within(shape(boundary)): # make a point and see if it's in the polygon
                location_lst.iloc[i,5] = all_records[j][2] # get the second field of the corresponding record    

filtered_lst = location_lst[location_lst["in_SG?"]!=""]
filtered_lst.to_csv(os.path.join(wdir,"Insta_list_SG.csv"),sep=",",index=False)


# ### 3. To collect all images from a certain location:
# #### 3.1 Get the list of locations of interest based on OSM tags

OSM_lst = pd.read_csv(os.path.join(wdir,"OSM_list_SG.csv"))

#filter based on tags
filt = OSM_lst[(OSM_lst['Object']=="way") & (OSM_lst['Tags'].str.find("'leisure': 'park'")!=-1)]
filt = filt.reset_index()

#filter based on location names
filt = OSM_lst[(OSM_lst['Object']=="way") & (OSM_lst['Name'].str.find("Botanic Garden")!=-1)]
filt = filt.reset_index()


# #### 3.2 Get the geofence of all desired OSM locations (a polygon) 
lst = []

for i in range(0,len(filt)):
    ID = filt["ID"][i]
    name = filt["Name"][i]
    query = """[out:json];way(""" + str(ID)+""");out;"""
    r4 = api.query(query) #query for the list of nodes that set the boundary for GBTB
    nodes_lst = r4.ways[0].get_nodes(resolve_missing=True)
    ### create the points at the boundary 
    point_lst = []
    if len(nodes_lst) >2:
        print(name)
        for i in range(0,len(nodes_lst)):
            pt = Point(float(nodes_lst[i].lon),float(nodes_lst[i].lat))
            point_lst.append(pt)
        lst.append([name,ID,point_lst])


# #### 3.3 Filter for location_id residing in the polygons of OSM locations
filtered_csv = pd.read_csv(os.path.join(wdir,"Insta_list_SG.csv"),index_col=0)
poly_loc = []

for j in range(0,len(lst)):
    poly = Polygon([[p.x, p.y] for p in lst[j][2]])
    for i in range(0,len(filtered_csv)):
        long = filtered_csv.iloc[i,3]
        lat = filtered_csv.iloc[i,4]
        if (long is not None) & (lat is not None):
            long = float(long)
            lat = float(lat)
            point = (long,lat) # an Long,Lat tuple
            if Point(point).within(shape(poly)): # make a point and see if it's in the polygon
                poly_loc.append([lst[j][0],lst[j][1],lst[j][2],filtered_csv.iloc[i,2]]) # get the second field of the corresponding record 
    print(j)


# #### 3.4 Query images from all location_ids in 3.3
# retrieve the list of location_id to be downloaded

dir_gf = os.path.join(wdir,"results_botanic")
if not os.path.isdir(dir_gf):
    os.makedirs(dir_gf)

#download json files for each location_id
for i in range(0,len(poly_loc)):
    #time.sleep(5)
    location_id = str(poly_loc[i][3]).split('.')[0]
    print(location_id)
    gf = subprocess.Popen(('instagram-scraper -u nhubt4212 -p cubS2pup! --destination '+ dir_gf +' --location ' +str(location_id)+' --media-metadata --media-types none --maximum 10').split(),stdout=subprocess.PIPE).stdout.readlines()

# #### 3.5 Create a json masterfile containing: image_id, location_name, Insta_user_id, download_link, timestamp
json_lst_gf = [x for x in os.listdir(dir_gf) if x.endswith('json')]

#Find all json file in the same directory
#create a dataframe containing: image_name, metadata source file of image,location_name, Insta_user_id,download link & timestamp
data_lst_gf = []
for metadata_src_file in json_lst_gf:
    data = json.loads(open(dir_gf+ "/"+metadata_src_file).read())
    json_name = metadata_src_file.split(".")[0]
    location_name = [i[0] for i in poly_loc if str(i[3]).split('.')[0]==json_name][0]
    print(len(data['GraphImages']))
    for img in data["GraphImages"]:
        download_link = img["display_url"]
        insta_user_id = img["owner"]["id"]
        img_name = download_link.split('/')[-1].split('?')[0]
        timestamp = img["taken_at_timestamp"]
        #check if this img_id match any image already downloaded
        #if match, change the name of the downloaded image to include timestamp
        info = [img_name, location_name, insta_user_id, json_name, download_link, timestamp]
        data_lst_gf.append(info)

data_gf = pd.DataFrame(data_lst_gf, columns=['Image_name','Location_name','Insta_user_id','Metadata_src_file','Download_link','Timestamp'])
data_gf.to_csv(os.path.join(dir_gf, "images_info.csv"),sep=",")

##download images into folder
## download images into the folder
import urllib.request 

for i in range(0,len(data_gf)):
    url = data_gf['Download_link'][i]
    name = data_gf['Image_name'][i]
    print(url)
    try:
        urllib.request.urlretrieve(url, os.path.join(dir_gf,name))
    except:
        continue

