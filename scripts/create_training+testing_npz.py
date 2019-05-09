import pandas as pd, os, urllib.request
from ast import literal_eval
import time

from PIL import Image
import numpy as np
import random

from shutil import copyfile

import scipy.misc

wdir = "/Users/ngpnhu/Desktop/ETH"


# #### 1. Get labels and facial images from LabelBox
LB_data = pd.read_csv(os.path.join(wdir,"LB_labels_2804.csv")) #download LB labels, named after the download date

#process only images which have been labelled
LB_data = LB_data[LB_data["Label"]!="Skip"]
LB_data.reset_index(inplace=True)

lst = []
for i in range(0,len(LB_data)):
    name = LB_data["ID"][i]+".jpg"
    link = LB_data["Labeled Data"][i]
    label = literal_eval(LB_data["Label"][i])
    if len(label.keys())==3:
        ethnicity = label["ethnicity"]
        gender = label["gender"]
        age = label["age"]
        lst.append([name,link,ethnicity,gender,age])

lst = pd.DataFrame(lst,columns=["Name","Link","Ethnicity","Gender","Age"])

#download all images into a folder
dir_images = os.path.join(wdir,"LB_data_2804")
if not os.path.isdir(dir_images):
    os.makedirs(dir_images)

for i in range(0,len(lst)):
    link = lst['Link'][i]
    name = lst['Name'][i]
    try:
        urllib.request.urlretrieve(link, os.path.join(dir_images,name))
    except:
        continue


# #### 2. Create distinct facial ID for each image using Face++ 
### Note: this step was not run to create the current version of training/testing data due to inefficiency in establishing stable connection to Face++
img_lst = sorted([x for x in os.listdir(dir_images) if x.endswith('jpg')])

label = []
for img in img_lst:
    call = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/detect" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "image_file=@'+ dir_images+'/'+img+'" -F "return_landmark=0" -F "return_attributes=gender,age,ethnicity"'
    label.append([img,os.popen(call).read()])
    time.sleep(2)

facepp_data = []
for data in label:
    name = data[0]
    if data[1] != "":
        face_data = literal_eval(data[1])
        if 'faces' in face_data.keys():
            n = len(face_data['faces'])
            if n > 0:
                for i in range(0,min(n,5)):
                    facepp_data.append([name,face_data['faces'][i]['face_token']])

df = pd.DataFrame(facepp_data, columns=['Name','Face_token'])

final_df = pd.merge(df,lst,on="Name",how="left")

#face set detail
fs_name = "ETH_"
outer_id = "15"
##create new faceset if necessary
#os.popen('curl -X POST "https://api-us.faceplusplus.com/facepp/v3/faceset/create" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "display_name='+fs_name+'" -F "outer_id='+outer_id+'"').read()


## Search for matches and add face to faceset
##create function for this
lst1 = []
match = []
for i in range(0,len(df)):
    f_token = df['Face_token'][i]
    #search whether this face already exists in the faceset
    call ='curl -X POST "https://api-us.faceplusplus.com/facepp/v3/search" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+f_token+'" -F "outer_id=15"'
    msg = literal_eval(os.popen(call).read())
    #lst.append(msg)
    time.sleep(1)
    if "error_message" in msg.keys() and msg["error_message"]=="EMPTY_FACESET": #if faceset if empty
        #add face to faceset
        call2 = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/faceset/addface" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "outer_id=15" -F "face_tokens='+f_token+'"'
        lst1.append(os.popen(call2).read())
    elif "results" in msg.keys(): #retrieve matching faces
        call1 = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/faceset/addface" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "outer_id=15" -F "face_tokens='+f_token+'"'
        res = literal_eval(os.popen(call1).read()) 
        #record matching face
        lst1.append([i,msg['results'][0]['user_id'],msg['results'][0]['confidence'],msg['results'][0]['face_token']])
    time.sleep(1)

lst1 = pd.DataFrame(lst1,columns=["Id",'User_id_match',"Confidence",'Face_token_match'])

lst1["Face_token"] = 0
for i in range(0,len(lst1)):    
    idx = lst1.iloc[i]['Id']
    lst1.loc[i,'Face_token'] = df.iloc[idx]['Face_token']

#create function for this
for i in range(0,len(lst1)):
    curr = lst1.iloc[i]['Face_token']
    match = lst1.iloc[i]['Face_token_match']
    
    #1. If the highest matching face has confidence < 80 => declare non-match 
            #=> assign this face a unique user_id
    if lst1.iloc[i]['Confidence'] < 80:
        call3 ='curl -X POST "https://api-us.faceplusplus.com/facepp/v3/face/setuserid" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+curr+'" -F "user_id='+curr+'"'
        msg = os.popen(call3).read()
        lst1.loc[i,'User_id'] = curr
        time.sleep(1)
    
    #2. If confidence > 80, declare match => assign this face with unique ID of the match
    else:
        #if user id is empty then start filling in
        if lst1.iloc[i]['User_id_match']=="":
            #Retrieve id of the highest match
            call1 = 'curl -X POST "https://api-us.faceplusplus.com/facepp/v3/face/getdetail" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+match+'"'
            msg = literal_eval(os.popen(call1).read())
            time.sleep(1)
            if "user_id" in msg.keys():
                user_id = msg["user_id"]
                #If even the duplicated face_token do not have a unique user_id, assign 1
                if user_id == '':
                    call2 ='curl -X POST "https://api-us.faceplusplus.com/facepp/v3/face/setuserid" -F "api_key=WcfwQJC2Uz5usfGJKpdb_uKkWkhvV893" -F "api_secret=xkVAIQuL5xgI-pG1dAIxb--d1umTIg9j" -F "face_token='+curr+'" -F "user_id='+curr+'"'
                    msg = os.popen(call2).read()
                    lst1.loc[i,'User_id'] = match
                else:
                    lst1.loc[i,'User_id'] = user_id
                time.sleep(1)
        else:
            lst1.loc[i,'User_id'] = lst1.iloc[i]['User_id_match']

lst1.to_csv(os.path.join(wdir,"processed_labels"))

combined_df = pd.merge(df,lst1,on="Face_token")

combined_df.drop_duplicates('Face_token', inplace = True)


# #### 3. Combine data labelled from different projects

LB_1904 = pd.read_csv(os.path.join(wdir,"LB_labels_1904.csv"))
LB_2204 = pd.read_csv(os.path.join(wdir,"LB_labels_2204.csv"))
LB_2604 = pd.read_csv(os.path.join(wdir,"LB_labels_2604.csv"))
LB_2804 = pd.read_csv(os.path.join(wdir,"LB_labels_2804.csv"))

##check all images are there
lst_1904 = []
img_1904_lst = sorted([x for x in os.listdir(os.path.join(wdir,"LB_data_1904")) if x.endswith('jpg')])

for i in range(0,len(LB_1904)):
    if '.'.join([LB_1904["ID"][i],'jpg']) in img_1904_lst:
        lst_1904.append(LB_1904.loc[i])
                       
lst_2204 = []
img_2204_lst = sorted([x for x in os.listdir(os.path.join(wdir,"LB_data_2204")) if x.endswith('jpg')])

for i in range(0,len(LB_2204)):
    if '.'.join([LB_2204["ID"][i],'jpg']) in img_2204_lst:
        lst_2204.append(LB_2204.loc[i])

lst_2604 = []
img_2604_lst = sorted([x for x in os.listdir(os.path.join(wdir,"LB_data_2604")) if x.endswith('jpg')])

for i in range(0,len(LB_2604)):
    if '.'.join([LB_2604["ID"][i],'jpg']) in img_2604_lst:
        lst_2604.append(LB_2604.loc[i])
        
lst_2804 = []
img_2804_lst = sorted([x for x in os.listdir(os.path.join(wdir,"LB_data_2804")) if x.endswith('jpg')])

for i in range(0,len(LB_2804)):
    if '.'.join([LB_2804["ID"][i],'jpg']) in img_2804_lst:
        lst_2804.append(LB_2804.loc[i])


LB_total = lst_1904+lst_2204+lst_2604+lst_2804 #combine all csv
LB_total = pd.DataFrame(LB_total,columns=LB_1904.columns)
LB_total.reset_index(inplace=True)

lst = []
for i in range(0,len(LB_total)):
    name = LB_total["ID"][i]+".jpg"
    link = LB_total["Labeled Data"][i]
    label = literal_eval(LB_total["Label"][i])
    if len(label.keys())==3:
        ethnicity = label["ethnicity"]
        gender = label["gender"]
        age = label["age"]
        lst.append([name,link,ethnicity,gender,age])

lst = pd.DataFrame(lst,columns=["Name","Link","Ethnicity","Gender","Age"])

new_dir = os.path.join(wdir,"unique_faces")
## manually move all files with detected faces to unique_faces folder


########## randomly split into training and testing data
training_dir = os.path.join(new_dir,"training")
testing_dir = os.path.join(new_dir,"testing")

if not os.path.isdir(training_dir):
    os.makedirs(training_dir)
    

if not os.path.isdir(testing_dir):
    os.makedirs(testing_dir)

training_label = []
testing_label = []

#separate into 12 groups [gender,age,ethnicity] : female young indian, female old indian etc
labels = []
for i in range(0,len(lst)):
    ### filter by ethnicity
    eth = lst["Ethnicity"][i]
    gender = lst["Gender"][i]
    age = lst["Age"][i]
    
    if age == "young":
        if gender =="female":
            if eth =="asian":
                labels.append([i,[0,0,0]])
            elif eth == "white":
                labels.append([i,[0,0,1]])
            elif eth =="indian":
                labels.append([i,[0,0,2]])
        elif gender =="male":
            if eth =="asian":
                labels.append([i,[1,0,0]])
            elif eth == "white":
                labels.append([i,[1,0,1]])
            elif eth =="indian":
                labels.append([i,[1,0,2]])
    elif age =="old":
        if gender =="female":
            if eth =="asian":
                labels.append([i,[0,1,0]])
            elif eth == "white":
                labels.append([i,[0,1,1]])
            elif eth =="indian":
                labels.append([i,[0,1,2]])
        elif gender =="male":
            if eth =="asian":
                labels.append([i,[1,1,0]])
            elif eth == "white":
                labels.append([i,[1,1,1]])
            elif eth =="indian":
                labels.append([i,[1,1,2]])

count_000 = 250 # set the number of observations from each category to be included in training data 
count_010 = 250
count_100 = 250
count_110 = 250

count_001 = 250 
count_011 = 250 
count_101 = 250
count_111 = 250

count_002 = 250
count_012 = 250
count_102 = 250
count_112 = 250

for i in range(0,len(lst)):
    if (labels[i][1][0]==0 and labels[i][1][1]==0 and labels[i][1][2]==0):
        if count_000 >=1:
            training_label.append(labels[i])
            count_000-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==0 and labels[i][1][1]==1 and labels[i][1][2]==0):
        if count_010 >=1:
            training_label.append(labels[i])
            count_010-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==1 and labels[i][1][1]==0 and labels[i][1][2]==0):
        if count_100 >=1:
            training_label.append(labels[i])
            count_100-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==1 and  labels[i][1][1]==1 and labels[i][1][2]==0):
        if count_110 >=1:
            training_label.append(labels[i])
            count_110-=1
        else: 
            testing_label.append(labels[i])
            
    
    if (labels[i][1][0]==0 and labels[i][1][1]==0 and labels[i][1][2]==1):
        if count_001 >=1:
            training_label.append(labels[i])
            count_001-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==0 and labels[i][1][1]==1 and labels[i][1][2]==1):
        if count_011 >=1:
            training_label.append(labels[i])
            count_011-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==1 and labels[i][1][1]==0 and labels[i][1][2]==1):
        if count_101 >=1:
            training_label.append(labels[i])
            count_101-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==1 and  labels[i][1][1]==1 and labels[i][1][2]==1):
        if count_111 >=1:
            training_label.append(labels[i])
            count_111-=1
        else: 
            testing_label.append(labels[i])
            
            
    elif (labels[i][1][0]==0 and  labels[i][1][1]==0 and labels[i][1][2]==2):
        if count_002 >=1:
            training_label.append(labels[i])
            count_002-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==0 and  labels[i][1][1]==1 and  labels[i][1][2]==2):
        if count_012 >=1:
            training_label.append(labels[i])
            count_012-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==1 and  labels[i][1][1]==0 and labels[i][1][2]==2):
        if count_102 >=1:
            training_label.append(labels[i])
            count_102-=1
        else: 
            testing_label.append(labels[i])
    elif (labels[i][1][0]==1 and labels[i][1][1]==1 and  labels[i][1][2]==2):
        if count_112 >=1:
            training_label.append(labels[i])
            count_112-=1
        else: 
            testing_label.append(labels[i])

### add to respective folder
for i in range(0,len(training_label)):
    idx = training_label[i][0]
    name = lst["Name"][idx]
    label = training_label[i][1]
    copyfile(os.path.join(new_dir,name),os.path.join(training_dir,name))
    training_label[i] = [name,label]

### add to respective folder
for i in range(0,len(testing_label)):
    idx = testing_label[i][0]
    name = lst["Name"][idx]
    label = testing_label[i][1]
    copyfile(os.path.join(new_dir,name),os.path.join(testing_dir,name))
    testing_label[i] = [name,label]

    
X_train = np.empty((0,218,178,3),dtype=np.uint8)
X_test = np.empty((0,218,178,3),dtype=np.uint8)

Y_train = np.empty((0,3),dtype=np.uint8)
Y_test = np.empty((0,3),dtype=np.uint8)

training_lst = sorted([x for x in os.listdir(training_dir) if x.endswith('jpg')])
for file in training_lst:
    image_file_name = os.path.join(training_dir, file)
    for i in training_label:
        if file == i[0]:
            label = i[1]
            
    if ".jpg" in image_file_name:
        img = np.asarray(Image.open(image_file_name))
        img1 =scipy.misc.imresize(img, (218, 178,3))
        im2arr = img1.reshape(1,218,178,3)
        X_train = np.append(X_train, im2arr, axis=0)

        label_arr = np.array(label,dtype=np.uint8)
        label_arr = label_arr.reshape(1,3) 
        Y_train = np.append(Y_train, label_arr, axis=0)
        #print(file)


testing_lst = sorted([x for x in os.listdir(testing_dir) if x.endswith('jpg')])
for file in testing_lst:
    image_file_name = os.path.join(testing_dir, file)
    for i in testing_label:
        if file == i[0]:
            label = i[1]
            
    if ".jpg" in image_file_name:
        img = np.asarray(Image.open(image_file_name))
        img1 =scipy.misc.imresize(img, (218, 178,3))
        im2arr = img1.reshape(1,218,178,3)
        X_test = np.append(X_test, im2arr, axis=0)

        label_arr = np.array(label,dtype=np.uint8)
        label_arr = label_arr.reshape(1,3) 
        Y_test = np.append(Y_test, label_arr, axis=0)


np.savez(os.path.join(wdir,"data_0205.npz"), x_train=X_train, y_train=Y_train,x_test=X_test,y_test=Y_test)

##sanity check
data = np.load("/Users/ngpnhu/Desktop/ETH/data_0205.npz")
Y_test[499]
img = Image.fromarray(X_test[499], 'RGB')
img.show()
