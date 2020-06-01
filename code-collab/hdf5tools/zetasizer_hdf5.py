import numpy as np
import os
import glob
import h5py
import csv
from fuzzywuzzy import fuzz 
# make sure to install python-levenshtein (prevent error warning)
# Microsoft Visual C++ 14.0 is required. Get it with "Microsoft Visual C++ Build Tools" modify existing build tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Works without, see: https://stackoverflow.com/questions/53980105/string-matching-using-fuzzywuzzy-is-it-using-levenshtein-distance-or-the-ratcli
from fuzzywuzzy import process

# UO = user option
# FI = final implementation
# IE = issues or errors
# NT = note/noteworthy

# TO DO: 
# Verify if SystemExist(0) is the way to go to stop execution.
# Figure out issue with OSError not working with OSError methods.
# Create documentation to exaplain fuzzy_key_pairing function. Explain "similar" key and values.  
# Pull fuzzy_key_pairing and subgroup out of function
# Further test and try to break write_grp_dataset - issue with "group already exist", need to clear mem or give new name?
# Make it so samples are saved as own hdf5 files instead. But the nwould groups names just have a dataset within it. 
# Start writing metadata function to grab (if available) hardcoded metadata headers and corresponding keys. 
# Move over to using a module and then call functions from notebook.


def find_file_path(): # Changes cwd to based off of user input directory path and returns relative path of selected txt file.
    dir_name = input('Enter full path of working directory (no quotes) \n') 

    if os.path.exists(dir_name) is False:
        print('Provided path does not exist') 
        raise SystemExit(0)
        if os.path.isdir(dir_name) is False:
            print('Provided path is not a directory, potentially a file path\n')
            raise SystemExit(0)

    os.chdir(dir_name)

    r_file_paths = glob.glob('./*.txt') # list of relative paths of .txt files
    print('The following .txt files were found')
    for i,file_path in enumerate(r_file_paths):
        print(i, file_path)
        print()


    working_file_input = int(input("Select the appropiate file, Provide corresponding number \n")) # OR ask to type name?
    working_file_path = r_file_paths[working_file_input] 
    return working_file_path 


def create_file(file_path): # Given relative txt file path intializes + returns root hdf5 file group. 
    hdf5_file_name = os.path.splitext(file_path)[0] + str('.hdf5') #.splitext makes a tuple = (path w/out ext, .ext)

    print(hdf5_file_name)
    checker = input('Is this correct? y/n? \n')

    if checker == 'y':
        pass
    else:
        raise SystemExit(0)
   
    try:
        hdf5_file = h5py.File(name = hdf5_file_name, mode = 'w-') # change file to just file, how do I supress built in error and show custom
    except Exception as ex: # issue: although I know it is an OSError (when trying to overwrite)  for some reason when use OSError class none of its methods say an error is present.
        template = "An exception of type {0} occurred. Arguments:\n{1!r}" # currently generalized to show the user what class of Error
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        raise ex # brings up original exception, stopping execution
    return hdf5_file


def add_attr(grp_or_dataset): # Function(s) to add attributes (metadata) to specfic file/groups/database or other
    experiment_id = input("Enter unique experiment ID \n")
    grp_or_dataset.attrs['expid'] = experiment_id

    num_root_attr = int(input('Would you like to add other attributes (aka metadata) to file? Specify Number\n'))
    
    if num_root_attr>0:
        for i in range(num_root_attr):
            root_attr_name = input('name')
            root_attr_value = input('value') # will always be string give people the option of flt or int
            grp_or_dataset.attrs[root_attr_name] = root_attr_value


def fuzzy_key_pairing(data_pair): # Given a pair of keys and values returns ranges of indexes that allow for grouping of "similar" keys (i.e. intensity 1, intensity 2 etc..)
    keys = data_pair[0]
    values = data_pair[1]

    correct_fl = []
    correct_bl = []

    for i in range(len(keys)):
        if i == len(keys)-1:
            correct_b = fuzz.ratio(keys[i],keys[i-1])
            correct_f = correct_b # as no way to go back
        elif i == 0: 
            correct_f = fuzz.ratio(keys[i],keys[i+1])
            correct_b = correct_f
        else: 
            correct_f = fuzz.ratio(keys[i],keys[i+1])
            correct_b = fuzz.ratio(keys[i],keys[i-1])
        correct_fl.append(correct_f)
        correct_bl.append(correct_b)

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
    

def subgroup(listy, ranges): # given list and ranges will group into a list w/ range of corr. values and replace. ex: [1,2,3,4,5,6] w/ ranges [[3,5]] => [1,2,3,[4,5,6]]
    for i,r in enumerate(reversed(ranges)): # going backwards prevents issue of keeping track of locations once deletion occurs.
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

def pair_kv(data_file_path): # takes input of relative txt files, opens, assumes, alternating rows of key and values, groups into sublist => [[k1,v1],[k2,v2]...]
    with open(data_file_path, mode='r') as file: 
        reader = csv.reader(file, delimiter=',')
        data = [row for row in reader] 
    paired_kv_data = [data[i:i+2] for i in range(0,len(data),2)]
    return paired_kv_data



def write_grp_dataset(paired_kv_data): # Function still buggy? Takes data pairs and using fuzzy logic matches and groups "similar" keys and values then writes into groups and datasets. 

    for i,data_pair in enumerate(paired_kv_data):
        k_orig = data_pair[0]
        v_orig = data_pair[1]

        indexer = k_orig
        ranges = fuzzy_key_pairing(data_pair) # pull out??? 

        k_u = np.asarray(subgroup(k_orig,ranges))
        v_u = np.asarray(subgroup(v_orig,ranges))

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

        group = test_file.create_group(name = v_u[0])
        print('saving group'+v_u[0])

        for k,v in zip(k_u2,v_enc):
            group.create_dataset(name=k,data=v)
            print('saving dataset'+k)


##################################################################################################################################################

path1 = find_file_path() # find relative file path

test_file = create_file(path1) # intialize and return hdf5 file object here name is same as provided text file (root_groups, root group refers to the hdf5 file - explain hierarch.)

test_file_add_attr = add_attr(test_file) # adds attributes based on key and value inputs by user for any group or dataset. 

paired_data = pair_kv(path1)

write = write_grp_dataset(paired_data) 

test_file.close()