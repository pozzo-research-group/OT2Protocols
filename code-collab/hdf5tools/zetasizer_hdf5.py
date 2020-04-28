import numpy as np
import os
import glob
import h5py
import pandas as pd
import csv
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# UO = user option
# FI = final implementation
# IE = issues or errors
# NT = note/noteworthy

# would want multiple file processing

# Suggestions:
# 1. New work flow suggestion. First prompt user where to navigate to , i.e., 
# what directory do they want to look at. 
# Print all the .txt files in the folder, then user inputs name of the file
# that they want to transform into an hdf5.
# 2. New name should just be the same name as the .txt file, with new extension.
# 3. Let's have discussion on what is metadata, and how to handle it. 
# there are things that we have considered implicit, which are not, and we should
# discuss. 
# 4. Restructure this code - consider splitting it into two separate files 
# if necessary. You should not have input prompts scattered between function
# definitions.

# step 1: find zetasizer file path FI:other file types other than txt

abspath = os.path.abspath(__file__) # script abs path
dname = os.path.dirname(abspath) # dir based on script abs path 
os.chdir(dname) 
data_path = glob.glob('./*.txt') # print list of relative paths of .txt files # referencing in same working dir = ./name.extension (./ relative path to cwd) 

# step 2: initialze hdf5 file (L: any specfic user options?) (and folder?? difficult as trial name does not exist yet, but can do metadata one)

input_filename = input("Enter name of new filename \n")
file_name = input_filename + str('.hdf5')
experiment_id = input("Enter unique experiment ID \n")

print(file_name, experiment_id) # add input are these correct?
checker = input('Is this correct? y/n? \n')

if checker == 'y':
    pass
else:
    raise SystemExit(0)

root_file = h5py.File(name = file_name)

# step 3: Add unique ID to metadata of root group (file) (UO: unique experiment ID)

root_file.attrs['expid'] = experiment_id
num_root_attr = int(input('Would you like to add metadata to file? Specify Number'))
if num_root_attr>0:
    for i in range(num_root_attr):
        root_attr_name = input('name')
        root_attr_value = input('value') # will always be string give people the option of flt or int
        root_file.attrs[root_attr_name] = root_attr_value


# step 4: Add any special UO for oragnizing the file (i.e. # group trials, logic would break if implement robust naming system sample_1_trial#.) - semioptional
# RIGHT NOW ONLY FOR ONE FILE

def Pairs(data_pair):
    keys = data_pair[0]
    values = data_pair[1]

    correct_fl = []
    correct_bl = []

    for i in range(len(keys)):
        if i == len(keys)-1:
            correct_b = fuzz.ratio(keys[i],keys[i-1])
            correct_f = correct_b # as no way to go
        elif i == 0: 
            correct_f = fuzz.ratio(keys[i],keys[i+1])
            correct_b = correct_f
        else: 
            correct_f = fuzz.ratio(keys[i],keys[i+1])
            correct_b = fuzz.ratio(keys[i],keys[i-1])
        # here you could in real time make/check the cb cf cases, to make the stsp_i list
        correct_fl.append(correct_f)
        correct_bl.append(correct_b)

    # still working with first pair
    stsp_rgs = []

    for y,(key,cb,cf) in enumerate(zip(keys,correct_bl,correct_fl)):
        if cb<80 and cf>80: #start
            stsp_rgs.append(y)
        elif cf<80 and cb>80: #stop
            stsp_rgs.append(y+1)
        else:
            pass

    stsp_rgs_grpd = [stsp_rgs[i:i+2] for i in range(0,len(stsp_rgs),2)]
    return stsp_rgs_grpd
    

def back_itup(listy, ranges):
    for i,r in enumerate(reversed(ranges)): # go backwards bitch
        if i == 0:
            r_min = r[0]
            r_max = len(listy)
            replacement = listy[r_min:r_max]
            del listy[r_min:r_max]
            listy.insert(r_min,replacement)
        else:
            r_min = r[0]
            r_max = r[1]
            replacement = listy[r_min:r_max]
            del listy[r_min:r_max]
            listy.insert(r_min,replacement)
    return listy


print(data_path[0])
input()

with open(data_path[0], mode='r') as file:
    reader = csv.reader(file, delimiter=',')
    data = [row for row in reader] # writing to list, so sublist = each line

datag = [data[i:i+2] for i in range(0,len(data),2)]
print()
#data_pair = datag[0] # this is where you would add the iterator

for i,data_pair in enumerate(datag):
    k_orig = data_pair[0]
    v_orig = data_pair[1]

    indexer = k_orig
    ranges = Pairs(data_pair)

    k_u = np.asarray(back_itup(k_orig,ranges))
    v_u = np.asarray(back_itup(v_orig,ranges))

    v_enc = []
    for iter in v_u:
        if type(iter) == str:
            v_enc.append(iter.encode("ascii", "ignore"))
        elif type(iter) == list: 
            asciiList = [n.encode("ascii", "ignore") for n in iter]
            v_enc.append(asciiList)
        else:
            pass


    k_u2 = []
    for iter in k_u:
        if type(iter) == str:
            k_u2.append(iter)
        elif type(iter) == list:
            k_u2.append(iter[0])
        else:
            pass

    #print(len(v_u),len(k_u2)) here could convert to dictionaryt toi have it look for the sample name
    group = root_file.create_group(name = v_u[0])
    print('saving group'+v_u[0])

    for k,v in zip(k_u2,v_enc):
        group.create_dataset(name=k,data=v)
        print('saving dataset'+k)

input('tap enter to close')

root_file.close()














































































# step 5: take loaded txt file and select which loading environemnt (UO: delimitter type, FI: logic delimitter)


# steps 5 -8 will be alot of for loops initially but can later convert to nice function and reference


# decided to use pandas dataframe as already in same format when exported with headers.
# iloc[row] of loaded data will load a sample with same indexing of headers accessed as list(dataframe)
# if eaiser to work with the series can be converted to list(series),
# one concern is of grouping certain spectrums - how will these be grouped, which is why probably after 
# finding the index range of the similar things, series will need to converted to a list and have values extracted and packaged



# step 6: search for column titles - a good place to initialze all hdf5 groups simulatneously - NO since need to be inside the trial and waiting for trial name - try to do this step seperatley to prevent overwtting
# NT decided to keep all spectra information or repetivative info (i.e. int 1, int 2 w/ 1, 2 outputs) to one dataset.
# only needs to be done once since files loaded as one text file have the REQUIRMENT OF BEING THE SAME WORKSPACE/EXPORT TEMPLETE


# FOR EACH TRIAL - REMEMBER AT END WITH UNIQUE EXPERIMENTAL ID ANYTHING WITH THE SAME NAME EXCEPT FOR ONE TRIAL NUMBER WILL HAVE THE OPTION OF BEING GROUPED TOGETHER


# step 7: with column titles use a EXACT searching feature to search for data corresponding to column title and store in some data structure (all seperately still) like dict or list.


# step 8: once neatly stored, start to group SIMILAR aka data that belongs together - MOSTLY REFFERING TO SPECTRA - using a SIMILARITY search feature


# step 9: begin to place to the grouped data into a new entry into which every data structure. optional = delete entries used to make this grouping - could be useful who knows.
# MOST LIKELY FINAL DATA STRCUTURE WILL NEED TO 3 LEVELS DEEPS - NO NEED FOR GENERALIZING AS JUST FOR DEVELOPER. ONE FOR KEEPING TRIALS SEPERATE, ONE FOR COLUMN TITLES AND ONE FOR DATA

# step 10: once this new data structure with respective keys and values is created, create trial group using the column name and respective key = TRIAL FOLDER

# step 11: do step 11, but within trial folder, for each parameter. 


# anything else????

# step 12: close file

