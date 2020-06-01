#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import os
import glob
import h5py
import csv
from fuzzywuzzy import fuzz 
from fuzzywuzzy import process
from datetime import datetime

# Make it so samples are saved as own hdf5 files instead. But the nwould groups names just have a dataset within it. 
# Start writing metadata function to grab (if available) hardcoded metadata headers and corresponding keys. 


# In[2]:


def find_file_path(dir_path):
    """
    Finds the file path of files with the appropiate .txt extension
    
    Args: 
        dir_path: raw string
            Absolute path of directory where files will be searched for.

    Returns:
        working_file_path: list
            A list of absolute paths of txt files found in the provided directory.
    """

    if os.path.exists(dir_path) is False:  #checks and balances
        raise ValueError('Provided path does not exist')
        if os.path.isdir(dir_path) is False:
            raise ValueError('Provided path is not a directory, potentially a file path')

    os.chdir(dir_path)

    r_file_paths = glob.glob('./*.txt') # list of relative paths of .txt files
    
    working_file_path = [os.path.abspath(r_path) for r_path in r_file_paths]
    
    return working_file_path 


# In[3]:


def key_value_data_pairs(data_file_path): 
    """
    Given an txt file of alternating rows of key and values, groups keys list and values list in a list. 
    
    Args: 
        data_file_path: raw string
            Absolute path of txt file of interest. 
    
    Returns:
        kv_pairs: list
            List containing sublist which contain keys and values, [[k1,v1],[k2,v2]...].
    
    """
    with open(data_file_path, mode='r') as file: 
        reader = csv.reader(file, delimiter=',')
        data = [row for row in reader] 
        
    kv_pairs = [data[i:i+2] for i in range(0,len(data),2)]
    return kv_pairs


# In[4]:


def create_file(file_path, default_name = True, date_ref = True): 
    """
    Creates root hdf5 file given an absolute file path. 
    Note hdf5 will remain open when returned, to close file.close().
    Useful when wanting to keep experiments under the same Hdf5 file.
    
    Args: 
        file_path: raw string
            Absolute path of file.
            
        deafult_name: bool, optional
            Optional string that will be used as created hdf5 file name. If default_name = None
            then file will have the same name as the provided file from file_path. 
            
        date_ref: bool, optional
            if False, will block metadata addition of Year-Month-Day-Hour-Minute. Default is True. 
            
    Returns: 
        hdf5_file: File Object-Like
            A file object like hdf5 root file. 
    
    """
    if default_name is True:
        hdf5_file_name = os.path.splitext(file_path)[0] + str('.hdf5') #.splitext makes a tuple = (path w/out ext, .ext)
    elif type(default_name) == str:
        hdf5_file_name = default_name + str('.hdf5')
    else:
        raise ValueError('Data type of provide hdf5 file name must be str.')  

    hdf5_file = h5py.File(name=hdf5_file_name, mode = 'w-')
    
    if date_ref is True:
        date_info = datetime.now().strftime('%Y-%m-%d-%H-%M')
        hdf5_file.attrs['Creation Timestamp'] = date_info
        
    return hdf5_file

# In[4.1]:

def create_file_sample(name, date_ref = True): 
    """
    Creates root hdf5 file given an absolute file path. 
    Note hdf5 will remain open when returned, to close file.close().
    
    Args: 
        file_path: raw string
            Absolute path of file.
            
        deafult_name: bool, optional
            Optional string that will be used as created hdf5 file name. If default_name = None
            then file will have the same name as the provided file from file_path. 
            
        date_ref: bool, optional
            if False, will block metadata addition of Year-Month-Day-Hour-Minute. Default is True. 
            
    Returns: 
        hdf5_file: File Object-Like
            A file object like hdf5 root file. 
    
    """
    date_info = datetime.now().strftime('%Y-%m-%d-%H-%M')
    random_number = str(np.random.randint(1000))
    hdf5_file_name = name + random_number + str('.hdf5') # initially used date, but if two samples have same name and created within ms then error
    hdf5_file = h5py.File(name=hdf5_file_name, mode = 'w-')

    if date_ref is True:
        hdf5_file.attrs['Creation Timestamp'] = date_info

    return hdf5_file

# In[5]:


def fuzzy_key_pairing(str_obj_list, sesitivity_cutoff = 80): # no need for values 
    """
    Indentifies index ranges of highly-similar str objectsg. It utilizes the string matching fuzzywuzzy package to compare str objects 
    by looking at the following str object AND previous str object in provided list and assiging forward and backwards similarity scores. 
    When appropiate the function uses both similarity scores to deteremine whether adjacent elements are similar enough to be 
    grouped/included in the same index ranges returned. 
    
    Understand this is case sensitive, please VERIFY results. 
    
    Args: 
        str_obj_list: list
            List of str objects.
            
        sensitivity_cutoff: float or int
            The criteria used for determine whether similarity scores is high enough to group two or more str object. 
            The higher the cutoff the more sensitive the grouping will be. 
            
    Returns: 
        start_stop_idxs: nested list
            List containing lists of length 2, with the entries corresponding to indexes begenning and end of string matching
            in provided key list.
    
    Example:
        str_obj_list_1 = ['Size[1]','Size[2]','Size[3]','Size[4]','Intensity[1]','Intensity[2]','Intensity[3]']
        start_stop_idxs = [[0:3],[4:6]]
    
    
    """
    looking_forward_list = []
    looking_backward_list = []

    for i in range(len(str_obj_list)):
        
        if i == 0: # At beginning of list the only option is to compare forward
            correct_f = fuzz.ratio(str_obj_list[i],str_obj_list[i+1])
            correct_b = correct_f
            
        elif i == len(str_obj_list)-1:# At end of list the only option is to compare backwards
            correct_b = fuzz.ratio(str_obj_list[i],str_obj_list[i-1])
            correct_f = correct_b # as no way to go back
            
        else: # In all other cases it is possible to compare and assign forward and backward similarity scores
            correct_f = fuzz.ratio(str_obj_list[i],str_obj_list[i+1])
            correct_b = fuzz.ratio(str_obj_list[i],str_obj_list[i-1])
        
        looking_forward_list.append(correct_f)
        looking_backward_list.append(correct_b)

    start_stop_idxs = []

    for i,(forward_score,backward_score) in enumerate(zip(looking_forward_list,looking_backward_list)):
        
        if backward_score < sesitivity_cutoff and forward_score>sesitivity_cutoff: #start
            start_stop_idxs.append(i)
            
        elif forward_score < sesitivity_cutoff and backward_score>sesitivity_cutoff: #stop
            start_stop_idxs.append(i+1)
            
        else:
            pass

    start_stop_idxs = [start_stop_idxs[i:i+2] for i in range(0,len(start_stop_idxs),2)]
    start_stop_idxs[-1].append(len(str_obj_list)) # Accounts for matching ending where similarity scores are satis. until str_obj_list 
    # Potential Issue: specific cases where scores fail at beginning of list providing a one element range. In general one element ranges are problmatic. 
            
    
    return start_stop_idxs


# In[6]:


def subgroup(listy, ranges): 
    """
    Given list and index ranges will group elements into a list based on ranges. Grouped elements are not "left behind", 
    the grouping leads to deletion of any other instance of the element. 
    
    Ex: [1,2,3,4,5,6] w/ ranges [[3,5]] => [1,2,3,[4,5,6]]
    
    Args:
        listy: list
            List that will be split by corresponding ranges.
            
        ranges: list
            List containing list of len two with ranges. Sublist is to have the starting index as the first entry and the 
            ending index as the second entry.
    
    Returns:
        listy: list
            Updated list with grouped and replaced elements in accordance with provided ranges. 
    
    """
    
    for i,r in enumerate(reversed(ranges)): # Going backwards prevents issue of keeping track of locations once deletion occurs.
        
        r_min = r[0]
        r_max = r[1]
        
        replacement = listy[r_min:r_max]
        del listy[r_min:r_max]
        
        listy.insert(r_min,replacement)

    return listy
    
    # Idea: Make all elements within Listy list instead of having a combination, should remove one more step of logic? Well, gies both ways


# In[7]:


def zetasizer_csv_to_hdf5(data_file_path): # How to pass arguments that are intended for functions used in this functions. 
    
    """
    Takes key and value pairs and using fuzzy logic matches and groups "similar" keys and values then writes 
    into groups and datasets. The function is a wrapper of all other functions in this module and is able 
    to create and store information from a csv/text file to a hdf5 file given only the absolute file path. 

    At the moment the requirements to utilize this function correctly are: 
        - csv/txt file must be arranged in alternation order of row of headers and row of keys. 
        - Add any other encounted limitations.
   
    Args: 
        data_file_path: raw string
            Absolute path of txt file of interest. 
            
    Returns: 
        hdf5_file: File Object-Like
            A file object like hdf5 root file. Note: Ensure to close this file once no longer in use.
    """
    
    #hdf5_root_file = create_file(data_file_path)
    
    paired_kv_data = key_value_data_pairs(data_file_path)

    
    for i,data_pair in enumerate(paired_kv_data): # Make more general and tease out issue with encoding/decoding.
        
        k_orig = data_pair[0]
        v_orig = data_pair[1]

        indexer = k_orig
        ranges = fuzzy_key_pairing(k_orig) # Pull out?

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
        
        hdf5_file = create_file_sample(name = v_u[0]) # hard coded for sample name, make it a searchable feature
        print('Creating Root File '+v_u[0])
          
        for k,v in zip(k_u2, v_enc):
            group = hdf5_file.create_group(name = k)
            dataset = group.create_dataset(name=k,data=v)
            print('saving dataset'+k)



