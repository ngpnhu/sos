

# Creating Training and Testing Data

### The Python script can be found [here](scripts/create_training+testing_npz.py).

### A sample of the training/testing data can be found [here](data/data_10ea.npz)

First, take the following steps to secure sufficient and quality labelled faces: 
* Gather a list of locations popular to each race (Asian/ White/Indian):
    * e.g CE LA VI for Caucasians, or Banana Leaf Restaurant for Indian.
* Upload images containing faces on LabelBox.
* While labelling, skip images with large black borders to ensure quality.

The labels for each image:

* **Ethnicity**: Asian/ White/ Indian
* **Gender**: Male/ Female
* **Age**: Young (<30 years old)/ Old (>30 years old)


### 1. Get labels and facial images from LabelBox

* Retrieve only images that are labelled (ignore those skipped)
```sosense
LB_data = LB_data[LB_data["Label"]!="Skip"]
LB_data.reset_index(inplace=True)
```
* Save all attributes (Ethnicity/Age/Gender) of each image to a list:
```sosense
lst = []
for i in range(0,len(LB_data)):
    name = LB_total["ID"][i]+".jpg"
    link = LB_total["Labeled Data"][i]
    label = literal_eval(LB_total["Label"][i])
    if len(label.keys())==3:
        ethnicity = label["ethnicity"]
        gender = label["gender"]
        age = label["age"]
        lst.append([name,link,ethnicity,gender,age])
lst = pd.DataFrame(lst,columns=["Name","Link","Ethnicity","Gender","Age"])
```
* Download all images from the list into a local directory
```sosense
#download all images into a folder
dir_images = os.path.join(wdir,"LB_data")
if not os.path.isdir(dir_images):
    os.makedirs(dir_images)

for i in range(0,len(lst)):
    link = lst['Link'][i]
    name = lst['Name'][i]
    try:
        urllib.request.urlretrieve(link, os.path.join(dir_images,name))
    except:
        continue
```

### 2. Create distinct facial ID for each image using Face++ 
Detailed instruction can be found in the [Facial Recognition and Profiling using Face++](Facial_detection_Face++.md) documentation.

### 3. Split images into training and testing set
* Create two empty folders for training and testing data. We will move the images to their respective folders later.
```sosense
training_dir = os.path.join(new_dir,"training")
testing_dir = os.path.join(new_dir,"testing")

if not os.path.isdir(training_dir):
    os.makedirs(training_dir)
if not os.path.isdir(testing_dir):
    os.makedirs(testing_dir)
```
* Create two empty lists to contain the names of image for training and testing data.
```sosense
training_label = []
testing_label = []
```
* Since we will ultimately save the data in Numpy array, reconstruct the label.
    * 0 represents Female, 1 represents Male.
    * 0 represents Young, 1 represents Old.
    * 0 represents Asian, 1 represents White, 2 represents Indian.
    * e.g [0,1,2] indicates a female, young, Indian face.
    
    ```sosense
    #separate into 12 groups [gender,age,ethnicity] : female young indian, female old indian etc
    labels = [] 
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
                
            #... so on
    ```
    * We have 12 label groups in total (3 Ethnicity * 2 Gender * 2 Age)

* To create an unbiased datasets, we should aim to include in the testing data 1000 images each for each Ethnicity, 1500 images for each Gender and Age group. This works out to about 250 images for each label group.
    * Add up to 250 images from each category to the list of each testing data. For example:
    ```sosense
    count_000 = 250
    for i in range(0,len(lst)):
    if (labels[i][1][0]==0 and labels[i][1][1]==0 and labels[i][1][2]==0):
        if count_000 >=1:
            training_label.append(labels[i])
            count_000-=1
        else: 
            testing_label.append(labels[i])
    ```
    
* After allocating all images to the respective `training_label` and `testing_label` lists, copy them into the appropriate folders.
```sosense
### add to respective folder
for i in range(0,len(training_label)):
    idx = training_label[i][0]
    name = lst["Name"][idx]
    label = training_label[i][1]
    copyfile(os.path.join(new_dir,name),os.path.join(training_dir,name))
    training_label[i] = [name,label]
```
* Create empty numpy arrays of desired shape (e.g (218,178,3) for images; (3) for labels) to store the images.
```sosense
X_train = np.empty((0,218,178,3),dtype=np.uint8)
X_test = np.empty((0,218,178,3),dtype=np.uint8)

Y_train = np.empty((0,3),dtype=np.uint8)
Y_test = np.empty((0,3),dtype=np.uint8)
```
* Add data to array:
```sosense
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
 ```
 * Save the data to .npz format. Double check to make sure labels are correct.
 ```sosense
 np.savez(os.path.join(wdir,"data_0205.npz"), x_train=X_train, y_train=Y_train,x_test=X_test,y_test=Y_test)

##sanity check
data = np.load("/Users/ngpnhu/Desktop/ETH/data_0205.npz")
Y_test[499]
img = Image.fromarray(X_test[499], 'RGB')
img.show()
 ```

