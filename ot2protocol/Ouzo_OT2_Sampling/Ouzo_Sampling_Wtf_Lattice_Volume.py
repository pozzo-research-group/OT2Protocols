#!/usr/bin/env python
# coding: utf-8

# In[10]:


import numpy as np
import pandas as pd
from opentrons import simulate, execute, protocol_api
import os
import csv
import ast
import matplotlib.pyplot as plt # not on OT2 jupyter notebook, so would need to install using jupyter terminal way as follows:
# import sys
# !{sys.executable} -m pip install numpy


# In[11]:


def get_experiment_plan(filepath):
    """
    Parse a .csv file to create a dictionary of instructions.
    """
    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        plan_dict = {}
        for i, row in enumerate(reader):
            assert len(row) == 2
            plan_dict[row[0]] = ast.literal_eval(row[1])

    return plan_dict


# In[74]:


def sample_sum_filter(sample_list):
    "Filters list of sample candidates on the basis of summation to 1, if less than 1 completes by adding remaining element to end of array"
    filtered_samples = []
    for sample in sample_list:
        concentration_sum = sum(sample)
        if concentration_sum <= 1:
            filler_conc = 1 - concentration_sum
            filled_sample = np.append(sample, filler_conc)
            filtered_samples.append(filled_sample)     
    return np.asarray(filtered_samples)


# In[77]:


def generate_candidate_lattice_concentrations(component_dict):
    component_list = component_dict['Component Shorthand Names']
    component_concs_list = component_dict['Component Concentrations [min, max, n]'] # assumes all the same units that have the potential to sum to 1 (only volf and wtf
    component_conc_type_list = component_dict['Component Concentration Unit']
    component_conc_dict = {}
    conc_range_list = []
    spacing_type = component_dict['Component Spacing']

    for conc_range in component_concs_list:
        if spacing_type == "linear":
            conc_range_list.append(np.linspace(*conc_range))
        elif spacing_type == "log":
            # To do:
            # Handle cases where concentration = 0
            conc_range_list.append(np.logspace(*conc_range))
        else:
            type_list = ["linear", "log"]
            assert spacing_type in type_list, "spacing_type was not specified in the experiment plan, or the the rquested method is not implemented."
            
    # Create ever combination of concentrations with meshgrid.
    conc_grid = np.meshgrid(*conc_range_list)
    for i in range(len(conc_grid)):
        # Create concentration entry in dictionary,
        # key:value = component name: flattened list of concentrations
        component_name = component_list[i]
        component_conc_dict[component_name] = conc_grid[i].ravel()
    concentration_df = pd.DataFrame.from_dict(component_conc_dict)
    assert len(component_list) != len(component_concs_list), "The provided"         "experimental instructions are overspecified."

    concentration_array = concentration_df.values
    filtered_concentration_array = sample_sum_filter(concentration_array)
    return filtered_concentration_array


# In[78]:


def dict_creator(root_dict, common_string):
    string_len = len(common_string)
    new_dict = {}
    for key in root_dict:
        if key[0:string_len] == common_string:
                new_dict[key] = root_dict[key]
    return new_dict


# In[79]:


def stocks_dict_gen(experiment_dict):
    stock_dict = {}
    for key in experiment_dict:
        if key[0:5] == 'Stock':
            stock_dict[key] = experiment_dict[key]
    return stock_dict


# In[80]:


def ethanol_wtf_water_to_density(ethanol_wtf):    
    ethanol_wtfs = np.asarray([x for x in range(101)])/100
    ethanol_water_densities = np.asarray([0.99804, 0.99636, 0.99453, 0.99275, 0.99103, 0.98938, 0.9878, 0.98627, 0.98478 , 0.98331 , 0.98187, 0.98047, 0.9791, 0.97775, 0.97643, 0.97514, 0.97387, 0.97259, 0.97129, 0.96997, 0.96864, 0.96729, 0.96592, 0.96453, 0.96312, 0.96168, 0.9602, 0.95867, 0.9571, 0.95548, 0.95382, 0.95212, 0.95038, 0.9486, 0.94679 ,0.94494, 0.94306, 0.94114, 0.93919, 0.9372, 0.93518, 0.93314, 0.93107, 0.92897, 0.92685, 0.92472, 0.92257, 0.92041, 0.91823, 0.91604, 0.91384, 0.9116, 0.90936, 0.90711, 0.90485, 0.90258, 0.90031, 0.89803, 0.89574, 0.89344, 0.89113, 0.88882, 0.8865, 0.88417, 0.88183, 0.87948, 0.87713, 0.87477, 0.87241, 0.87004, 0.86766, 0.86527, 0.86287, 0.86047, 0.85806, 0.85564, 0.85322, 0.85079, 0.84835, 0.8459, 0.84344, 0.84096, 0.83848, 0.83599, 0.83348, 0.83095, 0.8284, 0.82583, 0.82323, 0.82062, 0.81797, 0.81529, 0.81257, 0.80983, 0.80705, 0.80424, 0.80138, 0.79846, 0.79547, 0.79243, 0.78934])   # another way is to use only wtf or state the molarity is calculated as sums of the volumes and not the final volume 
    coeffs = np.polyfit(ethanol_wtfs, ethanol_water_densities,4)
    fit = np.polyval(coeffs, ethanol_wtf)
#     plt.plot(ethanol_wtf, ethanol_water_densities)
#     plt.plot(ethanol_wtf, fit)
    return fit


# In[81]:


def mg_per_mL_to_molarity(mg_per_mL, mw):
    molarity = mg_per_mL/mw
    return(molarity)


# In[82]:


def calculate_volumes(total_sample_mass, sample_list, component_dict, stock_dict): # all in mL
    # For use in indexing, all under the assumtion the # of completed concentrations = the numbero of component infos
    """Given stock and component information alongside sample canidates will provide volume for OT2 in uL"""
    component_names = component_dict['Component Shorthand Names']
    component_units = component_dict['Component Concentration Unit']
    component_densities = component_dict['Component Density (g/mL)']
    component_mws = component_dict['Component MW (g/mol)']
    component_sol_densities = component_dict['Component Solution vol to wt density (g/mL)']
    stock_names = stock_dict['Stock Names']
    stock_concentrations = stock_dict['Stock Concentration']
    stock_concentrations_units = stock_dict['Stock Concentration Units']
    stock_components_list = stock_dict['Stock Components']

    # At the moment, hardcoded order of the component_index 
    sample_stock_volumes = []
    for sample in sample_list: 
        ethanol_index = len(sample)-2 # The common component like ethanol at the moment will be the LAST excel input component
        total_ethanol_wtf = sample[ethanol_index]
        total_ethanol_mass = total_sample_mass*total_ethanol_wtf
        total_ethanol_volume = total_ethanol_mass*ethanol_wtf_water_to_density(total_ethanol_wtf)
        stock_volumes = []
        component_volumes = []

        for i, component_conc in enumerate(sample):
            component_stock_conc = stock_dict['Stock Concentration'][i]
            if i <= (ethanol_index-1): # lipid and oils (where combination of wtf and molarity)
                stock_unit = stock_concentrations_units[i] # could probably just do everything in wtf even the stocks
                if  stock_unit == 'molarity':
                    component_mw = component_mws[i]
                    component_mass = component_conc*total_sample_mass
                    component_volume = 0
                    component_moles = component_mass/component_mw
                    component_stock_volume = component_moles*1000/component_stock_conc # in mL
                if stock_unit == 'wtf':
                    stock_density = stock_dict['Stock Appx Density (g/mL)'][i]
                    component_density = component_dict['Component Density (g/mL)']
                    component_mass = component_conc*total_sample_mass
                    component_volume = component_mass/component_density # in mL
                    component_volumes.append(component_volume)
                    component_stock_mass = component_mass/component_stock_conc #?? oh because a solution
                    component_stock_volume = component_stock_mass/stock_density # in mL

                stock_volumes.append(component_stock_volume)

            elif i == ethanol_index: # pure ethanol the leftover, only issue is that again is hard coded, but good since introduces priroity inherently
                ethanol_volume_added = np.sum(stock_volumes)-np.sum(component_volumes) # accounting for oil
                component_stock_volume = total_ethanol_volume - ethanol_volume_added
                stock_volumes.append(component_stock_volume)

            elif i == len(sample)-1: # water (wtf stock and wtf component)
                component_mass = component_conc*total_sample_mass
                component_stock_volume = component_mass/stock_density # mL
                stock_volumes.append(component_stock_volume)

            else: 
                print(i, len(sample), 'something went wrong')

        sample_stock_volumes.append(np.asarray(stock_volumes)*1000)
    return np.asarray(sample_stock_volumes)

def volume_filter(min_volume, max_volume, volume_sample_canidates): 
    """Removes any sample volume canidates which do not meet pipette miniumum or maximum working volumes. Current pipetting working volumes are limited to only a minimum of 30uL)"""
    samples = []
    for sample in volume_sample_canidates:
        sample_volumes_filtered = []
        for volume in sample:
            if volume >= min_volume and volume <= max_volume:
                sample_volumes_filtered.append(volume)
        samples.append(sample_volumes_filtered)
    
    final_samples = []
    for sample in samples:
        if len(volume_sample_canidates[0]) == len(sample):
            final_samples.append(np.asarray(sample))
    return np.asarray(final_samples)

def rearrange_volumes(sample_volumes):
    component_volumes_rearranged = []
    for i in range(len(sample_volumes[0])): 
        component_volumes = []
        for sample in sample_volumes:
            component_volume = sample[i]
            component_volumes.append(component_volume)
        component_volumes_rearranged.append(component_volumes)
    return component_volumes_rearranged  