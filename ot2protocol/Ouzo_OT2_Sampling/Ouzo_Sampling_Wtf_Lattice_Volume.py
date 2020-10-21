import numpy as np
import pandas as pd
from opentrons import simulate, execute, protocol_api
import os
import csv
import ast
import datetime
from pytz import timezone
import csv


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

def sample_sum_filter(sample_list):
    "Filters list of sample candidates on the basis of summation to 1, if less than 1 completes by adding remaining element to end of array, while if more than one removes entry."
    filtered_samples = []
    for sample in sample_list:
        concentration_sum = sum(sample)
        if concentration_sum <= 1:
            filler_conc = 1 - concentration_sum
            filled_sample = np.append(sample, filler_conc)
            filtered_samples.append(filled_sample)     
    return np.asarray(filtered_samples)

def generate_candidate_lattice_concentrations(experiment_dict, stocks = False, filter_one = True):
    """Given n component linspaces of equivalent concentration units which summmation equal one (i.e. volf or wtf), generates an array of component concentration candidates which is subsequently filtered"""
    
    component_list = experiment_dict['Component Shorthand Names']
    component_concs_list = experiment_dict['Component Concentrations [min, max, n]']
    component_conc_type_list = experiment_dict['Component Concentration Unit']
    
    component_conc_dict = {}
    conc_range_list = []
    spacing_type = experiment_dict['Component Spacing']

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
        
    conc_grid = np.meshgrid(*conc_range_list)# Create every combination with meshgrid.
    
    for i in range(len(conc_grid)): 
        # Create concentration entry in dictionary,
        # key:value = component name: flattened list of concentrations
        component_name = component_list[i]
        component_conc_dict[component_name] = conc_grid[i].ravel()
    concentration_df = pd.DataFrame.from_dict(component_conc_dict)
    assert len(component_list) != len(component_concs_list), "The provided experimental instructions are overspecified."

    concentration_array = concentration_df.values
    
    if filter_one == False:
        concentration_array = concentration_array
    else: 
        concentration_array = sample_sum_filter(concentration_array)
        
    return concentration_array

def generate_candidate_lattice_stocks(experiment_dict):
    stock_list = experiment_dict['Stock Names']
    stock_concs_list = experiment_dict['Stock Concentration [min, max, n]']
    stock_conc_type_list = experiment_dict['Stock Concentration Units']
    stock_conc_dict = {}
    stock_ranges_list = []

    for stock_range in stock_concs_list:
        stock_ranges_list.append(np.linspace(*stock_range))

    conc_grid = np.meshgrid(*stock_ranges_list)

    for i in range(len(conc_grid)): 
        # Create concentration entry in dictionary,
        # key:value = component name: flattened list of concentrations
        stock_name = stock_list[i]
        stock_conc_dict[stock_name] = conc_grid[i].ravel()
    concentration_df = pd.DataFrame.from_dict(stock_conc_dict)

    concentration_array = concentration_df.values

    return concentration_array

def prepare_stock_search(stock_canidates, experiment_dict, wtf_sample_canidates):
    stock_names = experiment_dict['Stock Names']
    stock_units = experiment_dict['Stock Concentration Units']
    
    filtered_wtf_list = []
    stock_text_list = []
    for stock_canidate in stock_canidates:
        volume_canidates = calculate_ouzo_volumes(wtf_sample_canidates, experiment_dict, searching=True, searching_stock_concentrations=stock_canidate)
        filtered_wtf_samples, filtered_volume_samples = filter_samples(wtf_sample_canidates, volume_canidates, 30, 1000)
        filtered_wtf_list.append(filtered_wtf_samples)
        
        stock_text = ['', 'Stock Information']
        
        for i, stock_name in enumerate(stock_names):
            additional_stock_text = stock_name + ' ' + str(stock_canidate[i]) + ' ' + stock_units[i]
            stock_text.append(additional_stock_text) 
        stock_text_list.append(stock_text)

    return filtered_wtf_list, stock_text_list

def ethanol_wtf_water_to_density(ethanol_wtf):
    """Converts wtf of ethanol in a binary mixture with water to density using a polyfit of 4. The results are mainly used in the calculation of volume from a weight fraction. UPDATE: need to cite or create potential user entry."""
    ethanol_wtfs = np.asarray([x for x in range(101)])/100
    ethanol_water_densities = np.asarray([0.99804, 0.99636, 0.99453, 0.99275, 0.99103, 0.98938, 0.9878, 0.98627, 0.98478 , 0.98331 , 0.98187, 0.98047, 0.9791, 0.97775, 0.97643, 0.97514, 0.97387, 0.97259, 0.97129, 0.96997, 0.96864, 0.96729, 0.96592, 0.96453, 0.96312, 0.96168, 0.9602, 0.95867, 0.9571, 0.95548, 0.95382, 0.95212, 0.95038, 0.9486, 0.94679 ,0.94494, 0.94306, 0.94114, 0.93919, 0.9372, 0.93518, 0.93314, 0.93107, 0.92897, 0.92685, 0.92472, 0.92257, 0.92041, 0.91823, 0.91604, 0.91384, 0.9116, 0.90936, 0.90711, 0.90485, 0.90258, 0.90031, 0.89803, 0.89574, 0.89344, 0.89113, 0.88882, 0.8865, 0.88417, 0.88183, 0.87948, 0.87713, 0.87477, 0.87241, 0.87004, 0.86766, 0.86527, 0.86287, 0.86047, 0.85806, 0.85564, 0.85322, 0.85079, 0.84835, 0.8459, 0.84344, 0.84096, 0.83848, 0.83599, 0.83348, 0.83095, 0.8284, 0.82583, 0.82323, 0.82062, 0.81797, 0.81529, 0.81257, 0.80983, 0.80705, 0.80424, 0.80138, 0.79846, 0.79547, 0.79243, 0.78934])   # another way is to use only wtf or state the molarity is calculated as sums of the volumes and not the final volume 
    coeffs = np.polyfit(ethanol_wtfs, ethanol_water_densities,4)
    fit = np.polyval(coeffs, ethanol_wtf)
    return fit


def mg_per_mL_to_molarity(mg_per_mL, mw):
    molarity = mg_per_mL/mw
    return(molarity)

def average_volume(sample_volumes):
    tak = []
    for i in sample_volumes:
        tak.append(np.average(i))
    tak = np.asarray(tak)
    average_vol = np.average(tak)
    return average_vol

def add_blank(sample_wtfs, sample_volumes, blank_total_volume, blank_component_wtfs):
    blank_component_volumes = []
    for component_composition in blank_component_wtfs:
        volume = component_composition*blank_total_volume
        blank_component_volumes.append(volume)
    blank_wtfs_array = np.asarray([blank_component_wtfs])
    blank_volume_array = np.asarray([blank_component_volumes])
    blank_and_sample_wtfs = np.concatenate((sample_wtfs, blank_wtfs_array))
    blank_and_sample_volumes = np.concatenate((sample_volumes, blank_volume_array))
    return blank_and_sample_wtfs, blank_and_sample_volumes
    
    
def calculate_ouzo_volumes(sample_canidate_list, experiment_dict, searching = False, searching_stock_concentrations = None):
    """Given stock and component information alongside selected sample canidates will provide volume for OT2 in microliters. All intermediate calculation volumes are assumed to in milliliters unless stated otherwise. Component order to match order of sample concentration in sample canidate list. Additionally, assumes the good solvent for all other components is the second to last in component list and the poor solvent is last. """
    total_sample_mass = experiment_dict['Sample Mass']
    component_names = experiment_dict['Component Shorthand Names']
    component_units = experiment_dict['Component Concentration Unit']
    component_densities = experiment_dict['Component Density (g/mL)']
    component_mws = experiment_dict['Component MW (g/mol)']
    component_sol_densities = experiment_dict['Component Solution vol to wt density (g/mL)']
    stock_names = experiment_dict['Stock Names']
    
    if searching == True:
        stock_concentrations = searching_stock_concentrations
    else: 
        stock_concentrations = experiment_dict['Stock Concentration'] # OOH NO CAN DO A SINGLE ONE BUT USE THIS SPECIFIC NAMING CONVENTION
        
    stock_concentrations_units = experiment_dict['Stock Concentration Units']
    stock_components_list = experiment_dict['Stock Components']
    good_solvent_index = len(component_names)-2 

    sample_stock_volumes = []
    for sample in sample_canidate_list: 
        total_good_solvent_wtf = sample[good_solvent_index]
        total_good_solvent_mass = total_sample_mass*total_good_solvent_wtf
        total_good_solvent_volume = total_good_solvent_mass*ethanol_wtf_water_to_density(total_good_solvent_wtf)
        stock_volumes = []
        component_volumes = []

        for i, component_conc in enumerate(sample):
            component_stock_conc = stock_concentrations[i]
            if i <= (good_solvent_index-1):
                stock_unit = stock_concentrations_units[i]
                if  stock_unit == 'molarity': # currently only use case for lipids
                    component_mw = component_mws[i]
                    component_mass = component_conc*total_sample_mass
                    component_volume = 0
                    component_moles = component_mass/component_mw
                    component_stock_volume = component_moles*1000/component_stock_conc
                if stock_unit == 'wtf': # use case for everything except lipids and pure solvents
                    stock_density = experiment_dict['Stock Appx Density (g/mL)'][i]
                    component_density = experiment_dict['Component Density (g/mL)']
                    component_mass = component_conc*total_sample_mass
                    component_volume = component_mass/component_density # lipids are assumed to have 0 volume, but must account for oil. 
                    component_volumes.append(component_volume)
                    component_stock_mass = component_mass/component_stock_conc
                    component_stock_volume = component_stock_mass/stock_density #
                stock_volumes.append(component_stock_volume)

            elif i == good_solvent_index: # given good solvent index will always be second to last execution. 
                good_solvent_volume_added = np.sum(stock_volumes)-np.sum(component_volumes) 
                component_stock_volume = total_good_solvent_volume - good_solvent_volume_added
                stock_volumes.append(component_stock_volume)

            elif i == len(sample)-1: # water (wtf stock and wtf component)
                component_mass = component_conc*total_sample_mass
                component_stock_volume = component_mass/stock_density # mL
                stock_volumes.append(component_stock_volume)

            else: 
                print(i, len(sample), 'something went wrong')

        sample_stock_volumes.append(np.asarray(stock_volumes)*1000) # converted to uL
    return np.asarray(sample_stock_volumes)
                
def check_volumes(sample, min_vol, max_vol):
    "Checks a sample to see if it contains any volumes outside of the provided min/max. For use in case of wanting to limit the amount of steps in sample creation or adhering to OT2 pipette restrictions."
    checker = []
    for vol in sample:
        if vol >= min_vol and vol <= max_vol:
            checker.append(1)
        else:
            checker.append(0)
    if sum(checker) == len(sample):
        return True
    else:
        return False

def filter_samples(sample_canidates, volume_sample_canidates, min_vol, max_vol):
    """Filters samples based on volume restriction and matches up with previously created wtf sample canidates, 
    returning an updated list of wtf canidates AND volume canidates"""
    filtered_volumes = []
    filtered_wtf = []
    filtered_out = [] # optional just add an append in an else statement
    for sample_wtfs, sample_vols in zip(sample_canidates, volume_sample_canidates):
        if check_volumes(sample_vols, min_vol, max_vol) == True:
            filtered_volumes.append(sample_vols)
            filtered_wtf.append(sample_wtfs)
    
    volume_checking_list = [sum(volume) for volume in filtered_volumes]
    max_volume = max(volume_checking_list)
    min_volume = min(volume_checking_list)
    
    print('Min sample volume = ' + str(min_volume) + 'uL', 
          'Max sample volume = ' + str(max_volume) + 'uL')
    

    return (filtered_wtf, filtered_volumes)
    
def rearrange(sample_volumes):
    """Rearranges sample information to group samples based on position in sublist. [[a1,b1,c1],[a2,b2,c2]] => [[a1,a2],[b1,b2],[c1,c2]]"""
    component_volumes_rearranged = []
    for i in range(len(sample_volumes[0])): 
        component_volumes = []
        for sample in sample_volumes:
            component_volume = sample[i]
            component_volumes.append(component_volume)
        component_volumes_rearranged.append(component_volumes)
    return component_volumes_rearranged 
    
def create_csv(destination, info_list, wtf_samples, experiment_dict):  
    """Creates a CSV which contains sample information in addition tieing a unique ID to the row of information. Each row in the created csv corresponds to one sample and the unique ID contains date and well information. Information is gathered from the printed commands of the OT2 either when executing or simulating. Given the type of execution in current code, this only supports the case of consecutive sample making (i.e. samples made in well order, with no skipping of wells)."""
    
    time = str(datetime.datetime.now(timezone('US/Pacific')).date()) # should be embaded once you run
    component_names = experiment_dict['Component Shorthand Names']
    UID_header = ['UID']
    slot_header = ['Slot']
    labware_header = ['Labware']
    well_header =['Well']
    general_component_header = []
    experiment_component_header = []

    for i in range(len(component_names)):
        general_component_header.append('Component ' + str(i+1) + ' wtf')
        experiment_component_header.append(component_names[i] + ' wtf')

    complete_header = UID_header + general_component_header + slot_header + labware_header + well_header
    complete_experiment_header = UID_header + experiment_component_header + slot_header + labware_header + well_header


    wells = []
    labwares = []
    slots = []
    info_cut = info_list[0:len(wtf_samples)] #info only being used of length of number of samples
    for info in info_cut:
        str_info = str(info)
        spacing_index = []
        for i, letter in enumerate(str_info):
            if letter == ' ':
                spacing_index.append(i)
        well = str_info[0:spacing_index[0]]
        wells.append(well)
        labware = str_info[spacing_index[1]+1:spacing_index[8]]
        labwares.append(labware)
        slot = str_info[spacing_index[9]+1:]
        slots.append(slot)

    csv_entries = []
    ## Adding unique id and other information into one sublist to be fed as row into writer
    for component_wtfs, slot, labware, well in zip(wtf_samples, slots, labwares, wells):
        UID = time + "_" +experiment_dict['Component Shorthand Names'][experiment_dict['Component Graphing X Index']]+ "_" + experiment_dict['Component Shorthand Names'][experiment_dict['Component Graphing Y Index']] + "_" + well
        csv_entry = [UID] + component_wtfs.tolist() + [slot] + [labware] + [well]
        csv_entries.append(csv_entry)

    with open(destination, 'w', newline='',encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter = ",")
        csvwriter.writerow(complete_header)
        csvwriter.writerow(complete_experiment_header) # so what 

        for row in csv_entries:
            csvwriter.writerow(row)