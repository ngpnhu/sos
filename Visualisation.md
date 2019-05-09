# Visualisation of Demographic Data

### Note that all legends have been manually added via PDF Preview.
### The Python script can be found [here](scripts/POIS_generation+Data_collection.py).


First, retrieve Singapore bounding box:
```sosense
sg_shp = shapefile.Reader(os.path.join(wdir,"SingaporepolySingapore_AL38268/Singapore_AL382.shp"))

attributes, geometry = [], []
field_names = [field[0] for field in sg_shp.fields[1:]]  
for row in sg_shp.shapeRecords():  
    geometry.append(shape(row.shape.__geo_interface__))  
    attributes.append(dict(zip(field_names, row.record)))  

#get this from spatial_reference.org by pasting .prj content inside
proj4_string = "+proj=tmerc +lat_0=1.366666666666667 +lon_0=103.8333333333333 +k=1 +x_0=28001.642 +y_0=38744.572 +ellps=WGS84 +units=m +no_defs"
sg_frame = gpd.GeoDataFrame(data = attributes, geometry = geometry, crs = proj4_string).to_crs(epsg = 3414)
```

### 1. Map of all Instagram locations in Singapore, color-coded into parks/non-parks 
* Retrieve list of all Instagram locations in SG [here](data/Insta_list_SG.csv)
* Retrieve list of all Instagram locations in SG that are also parks [here](data/others/OSM_parks_SG.csv)
* Create two separate lists for parks and non parks:
```sosense
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
```
* Create the map from these two lists. This drawing step is largely similar across all maps
```sosense
ax = sg_frame.to_crs(epsg =3414).plot(color='deepskyblue',alpha=0.2, figsize=(20,15),edgecolors='grey')  
ax.set(aspect='equal', xticks=[], yticks=[])

ax.set_title('Singapore', size=15)

parks_points=gpd.GeoDataFrame(geometry = parks, crs = proj4_string).to_crs(epsg = 3414)
nonparks_points=gpd.GeoDataFrame(geometry = non_parks, crs = proj4_string).to_crs(epsg = 3414)

nonparks_points.plot(ax=ax, color = 'darkgreen' , markersize=10, alpha=0.3, edgecolors='none',categorical=True, legend=True)
parks_points.plot(ax=ax, color = 'crimson' , markersize=16, alpha=0.7, edgecolors='none', categorical=True, legend=True)

plt.savefig(os.path.join(wdir,"All_Insta_location_id_SG.png"), bbox_inches='tight')
```
![All Instagram Locations in SG](https://github.com/asteentoft/sosense/blob/new_pipeline/data/visualisations/All%20Instagram%20location%20IDs%20in%20SG.png)

### 2. Bubble map of all Instagram Locations in Botanic Gardens (size = number of images posted)
* Count the number of images retrieved per location_id. 
```sosense
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
```
* Assign 0 to locations with no images retrieved.
* Create/ retrieve the shapefile of Botanic Gardens (to draw the boundary) (can be found [here](data/BG_polygons.shp)).
* Create a dataframe of coordinates and number of photos for each location_id.
```sosense
BG_ps=gpd.GeoDataFrame(geometry = BG_points, crs = proj4_string).to_crs(epsg = 3414)
##assign attributes as desired
BG_ps['ID'] = ID
BG_ps['name']= names
BG_ps['size'] = size_loc
```
* Draw the shape of Botanic Gardens on top of existing SG frames
```sosense
from descartes import PolygonPatch
ax.add_patch(PolygonPatch(BG_polygons, fc='green', ec='black', alpha=0.6, lw =2 )) #different layers
```

![All Instagram Locations in Botanic Gardens](https://github.com/asteentoft/sosense/blob/new_pipeline/data/visualisations/All%20location_ids%20in%20Botanic%20Gardens.png)

### 3. Maps of Demographic Distribution - Ethnicity/ Gender/ Age
* For each demographic attribute (Ethnicity/Gender/Age), count the observations for each unique category (e.g female/male)
```sosense
#get combined facial information by Face++ and Instagram-scraper
df = pd.read_csv(os.path.join(wdir,'combined_facial_info.csv'))

female_count = len(df.loc[df['Gender']=='Female'])
male_count = len(df.loc[df['Gender']=='Male'])
```
* For example, there are 500 female and 300 male faces detected in Botanic Gardens. Dedide on the number of points representing each category on the map, and scale accordingly.
    * 500 points will typically make the graphs too dense to read, while 100 makes it too sparse.
    * Hence, we may want to scale the number of points by half i.e 250 points for females and 150 points for males.
* Randomly create 250 points for Females and 150 for Males within the bounding box of Botanic Gardens.
```sosense
    points = []
    k=0
    while len(points) < values: #'values' refer to the number of random points to be generated e.g 250 for Females
        s = RandomState()#(seed+k)
        random_point = Point([s.uniform(poly.bounds[0], poly.bounds[2]), s.uniform(poly.bounds[1], poly.bounds[3])])
        if poly.contains(random_point):
            points.append(random_point)
            k+=1
            
    ps=gpd.GeoDataFrame(geometry = points, crs = proj4_string).to_crs(epsg = 3414)
    ps['field']= genders[i] #assign the appropriate Gender label to the points.
```
![Botanic Gardens - Gender Distribution](https://github.com/asteentoft/sosense/blob/new_pipeline/data/visualisations/Botanic%20Gardens%20-%20Gender%20Distribution.png)

* Take similar steps to produce graphs for Ethnicity and Age Distribution
![Botanic Gardens - Ethnicity Distribution](https://github.com/asteentoft/sosense/blob/new_pipeline/data/visualisations/Botanic%20Gardens%20-%20Ethnicity%20Distribution.png)
![Botanic Gardens - Age Distribution](https://github.com/asteentoft/sosense/blob/new_pipeline/data/visualisations/Botanic%20Gardens%20-%20Age%20Distribution.png)

