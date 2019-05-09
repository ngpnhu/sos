

# POIS Generation & Data Collection

### The Python script can be found [here](scripts/POIS_generation+Data_collection.py).

### 1. Gather details of all locations available in Singapore from OpenStreetMap 

* Retrieve all nodes/ways/relations within Singapore boundaries:
    ```sosense
    import overpy
    api = overpy.Overpass()
    
    r1 = api.query("""[out:json][timeout:120000];area["ISO3166-1"="SG"];(node["name"](area););out body;""")
    r2 = api.query("""[out:json][timeout:120000];area["ISO3166-1"="SG"];(way["name"](area););out body;""")
    r3 = api.query("""[out:json][timeout:110000];area["ISO3166-1"="SG"];(relation["name"](area););out body;""")
    ```
    * The longer the timeout, the more data can be retrieved.
    * `"ISO3166-1"` is the tag for area name; `"SG"` is the name code for Singapore.
    * The dataframe containing details of all OSM objects, **`OSM_list_SG.csv`**, can be found [here](data/OSM_list_SG.csv).

* Generate possible location keywords:
     * Standardise the names of OSM objects to be *lower-case, hyphen-separated*.
     * Create a list of possible keywords from each OSM object name:
         * e.g East Coast Park => [east, east-coast, east-coast park].
     * Remove duplicates. The list of unique keywords can be found [here](data/others/search_lst.csv).

<br>

### 2. Get a list of Instagram location_id within Singapore using Instagram Scraper

* For each keyword, use Instagram Scraper to retrieve information on  all related locations.
    ```sosense
    instagram-scraper -u [username] -p [password] --search-location [keyword]
    ```
* Remove duplicates. Then, filter for only locations within Singapore boundaries:
    * Retrieve Singapore Shapefile [here](data/others/Singapore_AL382.shp)(containing names & shapes of 5 regions).
    * Label each location_id by:
        * (1) the Singapore region it resides in (e.g 'Central').
        * (2) empty string if it does not reside in Singapore (`""`). 
    * The dataframe of location_ids within Singapore, **`Insta_list_SG.csv`**, can be found [here](data/Insta_list_SG.csv).
  
<br>

***NOTE: Step 1 & 2 takes a long time to run; hence, only only rerun when there is a significant location update on OSM and Instagram.***

<br>

### 3. Collect all images from a specified location using Instagram Scraper:

#### 3.1 Generate polygons of specified location **(IMPORTANT)**

First, open [OSM_list_SG](data/OSM_list_SG.csv).
```sosense
OSM_lst = pd.read_csv(os.path.join(wdir,"OSM_list_SG.csv"))
```

There are many ways to do this:

* **Case #1: If you do not have a list of coordinates for polygons:** 
    * If you have **a specific location name** in mind => search for ID of corresponding OSM Way objects.
        ```sosense
        filt = OSM_lst[(OSM_lst['Object']=="way") & (OSM_lst['Name'].str.find("Botanic Garden")!=-1)] 
        ```
    * If you have **a specific types of location** in mind => search for the appropriate tags (see [this link](https://taginfo.openstreetmap.org/tags) for inspiration)
        ```sosense
        filt = OSM_lst[(OSM_lst['Object']=="way") & (OSM_lst['Tags'].str.find("'leisure': 'park'")!=-1)]
        ```
    * Return `filt` - a dataframe containing all locations of the desired type/name.
    * Retrieve the coordinates of boundary for each location in `filt` from OSM:
        ```sosense
        ID = filt["ID"][i]
        query = """[out:json];way(""" + str(ID)+""");out;"""
    
        r4 = api.query(query)  #query for the list of nodes that set the boundary
        nodes_lst = r4.ways[0].get_nodes(resolve_missing=True)
        ```
    * Create the boundary:
        ```sosense
        #Create list of Points for boundary
        point_lst = []
        if len(nodes_lst) >2:
            print(name)
            for i in range(0,len(nodes_lst)):
                pt = Point(float(nodes_lst[i].lon),float(nodes_lst[i].lat))
                point_lst.append(pt)
        
        #Create a polygon from the list of Points:
        poly = Polygon([[p.x, p.y] for p in point_lst])
        ```
* **Case #2: If you already have a list of coordinates for polygons:**
    * The coordinates are **in the form of a Shapefile** (e.g Singapore Shapefile):
        ```sosense
        import shapefile
        from shapely.geometry import Point, shape, Polygon # Point class
       
        sg_shp = shapefile.Reader("Singapore_AL382.shp")
        poly = sg_shp.shapes() # retrieve list of polygons
        ```
     * The coordinates are **a list of pairs of Float**.
        ```sosense
        for i in range(0,len(nodes_lst)):
            pt = Point(float(nodes_lst[i].lon),float(nodes_lst[i].lat))
            point_lst.append(pt)
        
        poly = Polygon([[p.x, p.y] for p in point_lst])
        ```
* Generate `poly` - the list of polygon(s) for a specified location.
* Save `poly` into Shapefile for later use. A sample file, **`BG_polygons.shp`**, can be found [here](data/BG_polygons.shp)
```sosense
polygon_df = gpd.GeoDataFrame(crs=crs, geometry=[poly])
polygon_df.to_file(os.path.join(wdir,'BG_polygons.shp'))
```

#### 3.2 Scrape Instagram images that are posted inside the polygons**

* Filter all location_id whose latitude and longitude lie inside the polygons. 
* Use `Instagram-Scraper` to retrieve photos and *a master json file* from each location_id
     ```sosense
     #to download images and videos at the same time downloading the metadata, use --media-types image,video
     #--maximum specifies that maximum number of files to be retrieved
     
     instagram-scraper -u [username] -p [password] --destination [download directory] --location [location_id] --media-metadata --media-types image --maximum 10
     ```
* From each json file,retrieve **Image_id, Insta_user_id, Download_link & Timestamp** of the photos.
* The sample dataframe containing these information, **`images_info.csv`** can be found [here](data/images_info.csv).
