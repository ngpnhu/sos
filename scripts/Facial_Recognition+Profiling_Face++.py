#!/usr/bin/env python
# coding: utf-8

import json, os
import pandas as pd
import subprocess
import config,time,ast

wdir = "/Users/ngpnhu/Desktop/ETH"

dir_gf = os.path.join(wdir,"results_botanic") ###make sure the photos are inside the folder

# #### 1.1 Upload to Face++ for Face Detection
img_lst = sorted([x for x in os.listdir(dir_gf) if x.endswith('jpg')])

label = []
for img in img_lst:
    call = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/detect" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "image_file=@'+ dir_gf+'/'+img+'" -F "return_landmark=0" -F "return_attributes=gender,age,ethnicity"'
    label.append([img,os.popen(call).read()])
    time.sleep(2)

facepp_data = [] #process query results to retrieve gender, ethnicity, age for each face detected
for data in label:
    name = data[0]
    if data[1] != "":
        face_data = ast.literal_eval(data[1])
        if 'faces' in face_data.keys():
            n = len(face_data['faces'])
            if n > 0:
                for i in range(0,min(n,5)):
                    facepp_data.append([name,face_data['faces'][i]['attributes']['gender']['value'],face_data['faces'][i]['attributes']['age']['value'],face_data['faces'][i]['attributes']['ethnicity']['value'],face_data['faces'][i]['face_rectangle'],face_data['faces'][i]['face_token']])

df = pd.DataFrame(facepp_data, columns=['Image_name','Gender','Age','Ethnicity',"Bounding Box",'Face_token'])
df.to_csv(os.path.join(wdir,"Face++_detection.csv"))


# #### 1.2. Add facial image to faceset (library of unique faces) 
#face set detail
face set detail
fs_name = "ETH_000"
outer_id = "1000"
##create new faceset if necessary
#os.popen('curl -X POST "https://api-us.faceplusplus.com/facepp/v3/faceset/create" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "display_name='+fs_name+'" -F "outer_id='+outer_id+'"').read()

## Search for matches and add face to faceset
lst = []
match = []
for i in range(0,len(df)):
    f_token = df['Face_token'][i]
    #search whether this face already exists in the faceset
    call ='curl -X POST "https://api-us.faceplusplus.com/facepp/v3/search" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+f_token+'" -F "outer_id=18"'
    msg = ast.literal_eval(os.popen(call).read())
    #lst.append(msg)
    time.sleep(1)
    if "error_message" in msg.keys() and msg["error_message"]=="EMPTY_FACESET": #if faceset if empty
        #add face to faceset
        call2 = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/faceset/addface" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "outer_id=18" -F "face_tokens='+f_token+'"'
        lst.append(os.popen(call2).read())
    elif "results" in msg.keys(): #retrieve matching faces
        call1 = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/faceset/addface" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "outer_id=18" -F "face_tokens='+f_token+'"'
        res = ast.literal_eval(os.popen(call1).read()) 
        #record matching face
        lst.append([i,msg['results'][0]['user_id'],msg['results'][0]['confidence'],msg['results'][0]['face_token']])
    time.sleep(1)

lst = pd.DataFrame(lst[1:len(lst)],columns=['Id','User_id_match','Confidence','Face_token_match'])
lst = lst.dropna()

lst["Face_token"] = 0 #create a colume with unique Face_token name for easy combination with df later
for i in range(0,len(lst)):    
    idx = lst.iloc[i]['Id']
    lst.loc[i,'Face_token'] = df.iloc[idx]['Face_token']

for i in range(0,len(lst)):
    curr = lst.iloc[i]['Face_token']
    match = lst.iloc[i]['Face_token_match']
    
    #1. If the highest matching face has confidence < 80 => declare non-match 
            #=> assign this face a unique user_id
    if lst.iloc[i]['Confidence'] < 80:
        call3 ='curl -X POST "https://api-us.faceplusplus.com/facepp/v3/face/setuserid" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+curr+'" -F "user_id='+curr+'"'
        msg = os.popen(call3).read()
        lst.loc[i,'Fpp_user_id'] = curr
        time.sleep(1)
    
    #2. If confidence > 80, declare match => assign this face with unique ID of the match
    else:
        #if user id is empty then start filling in
        if lst.iloc[i]['User_id_match']=="":
            #Retrieve id of the highest match
            call1 = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/face/getdetail" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+match+'"'
            msg = ast.literal_eval(os.popen(call1).read())
            time.sleep(1)
            if "user_id" in msg.keys():
                user_id = msg["user_id"]
                #If even the duplicated face_token do not have a unique user_id, assign 1
                if user_id == '':
                    call2 ='curl -X POST "https://api-us.faceplusplus.com/facepp/v3/face/setuserid" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+curr+'" -F "user_id='+curr+'"'
                    msg = os.popen(call2).read()
                    lst.loc[i,'Fpp_user_id'] = match
                else:
                    lst.loc[i,'Fpp_user_id'] = user_id
                time.sleep(1)
        else:
            lst.loc[i,'Fpp_user_id'] = lst.iloc[i]['User_id_match']


# #### 1.3. Join user_id and face_token with facial attributes in a table
combined_df = pd.merge(lst,df,on="Face_token",how="left")
combined_df = combined_df[["Face_token","Image_name","Fpp_user_id","Gender","Age","Ethnicity","Bounding Box"]]

# #### 1.4. Join Face++ dataframes with Instagram user id and timestamp
images_info = pd.read_csv(os.path.join(wdir,'images_info.csv')).drop('Unnamed: 0',axis=1)
final_df = pd.merge(combined_df,images_info,on="Image_name",how="left")
final_df.drop_duplicates('Face_token',inplace=True)
final_df.reset_index(inplace=True)
final_df = final_df[["Face_token","Image_name","Timestamp","Insta_user_id","Fpp_user_id","Gender","Age","Ethnicity","Bounding Box"]]

# #### 1.5 Add facial data to a master csv in local directory
##the goal is to save unique_user_id offline in a local directory even if it is not saved in Face++ (free account limit)
master_csv = os.path.join(wdir,"combined_facial_info.csv")

## if the master csv does not exist
if not os.path.isfile(master_csv):
    with open(master_csv, 'w') as f:
        final_df['Counter']=0
        final_df.to_csv(f, header=True)
else: ## if master csv exists, just add to existing dataframe
    curr = pd.read_csv(master_csv)
    counter=1+curr.Counter.max()
    with open(master_csv, 'a') as f:
        final_df['Counter']=counter
        final_df.to_csv(f, header=False,index=False)
