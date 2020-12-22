import numpy as np
import pandas as pd
from opentrons import simulate, execute, protocol_api
import os
import csv
import ast
import datetime
from pytz import timezone
import csv

"""Common terms/info: 
    wtf = weight fraction
    2D list or nested list = [[a,b,c], [e,f,g]]
    
    Unless otherwise stated:
    - The order of list or array should be assumed to match that of its naming list or arrays. For example if stock_concentrations = [0.1, 0.5, 1] with stock_names = [A, B, C], stock_unit = ['wtf', 'wtf', 'wtf'] then stock A = 1 wtf, B = 0.5 wtf and so on.
    - Volumes are defaulted to microliters (default unit of opentrons) 
    

    
    Other notes: 
       - Currently each component has its own respective stock that only has most one solvent. Working on modifying the component logic to allow for automatic search of components and match them with respective stock, issue I can already see arising is when one component is present in more than one stock how to assign proirity. 
    
    """

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
    "Filters 2D list or nested list of sample wtf candidates on the basis of summation to 1, if the summation is less than 1 it completes by adding remainder as an element to the end of the array, while if more than one it removes entry completely."
    filtered_samples = []
    for sample in sample_list:
        concentration_sum = sum(sample)
        if concentration_sum <= 1:
            filler_conc = 1 - concentration_sum
            filled_sample = np.append(sample, filler_conc)
            filtered_samples.append(filled_sample)     
    return np.asarray(filtered_samples)

def generate_candidate_lattice_concentrations(experiment_csv_dict, filter_one = True):
    """Given the complete csv dictionary of instruction, uses the n component linspaces of equivalent concentration units which summmation equal one (i.e. volf or wtf). The number of linspaces used are to equal the total number of components - 1. Once a 2D list of component concentration candidates are generated the canidates (of length total # of components - 1) are subsequently filtered/completed by sample_sum_filter. All entry additions follow the order of linspaces from the experiment_csv_dict."""
    
    # Calling information from csv 
    component_name_list = experiment_csv_dict['Component Shorthand Names']
    component_conc_linspaces_list = experiment_csv_dict['Component Concentrations [min, max, n]']
    component_conc_type_list = experiment_csv_dict['Component Concentration Unit']
    component_spacing_type = experiment_csv_dict['Component Spacing']
 
    conc_range_list = [] # will hold flattened linspaces 
    for conc_linspace in component_conc_linspaces_list:
        if component_spacing_type == "linear":
            conc_range_list.append(np.linspace(*conc_linspace))
        elif component_spacing_type == "log": # allows for cases where conc is 0? 
            conc_range_list.append(np.logspace(*conc_linspace))
        else:
            type_list = ["linear", "log"]
            assert spacing_type in type_list, "spacing_type was not specified in the experiment plan, or the the rquested method is not implemented."
        
    conc_grid = np.meshgrid(*conc_range_list) # Create every combination of the flattened linspaces with meshgrid.
    
    component_conc_dict = {}
    for i in range(len(conc_grid)): 
        component_name = component_name_list[i]
        component_conc_dict[component_name] = conc_grid[i].ravel()
    concentration_df = pd.DataFrame.from_dict(component_conc_dict)
    assert len(component_name_list) != len(component_conc_linspaces_list), "The provided experimental instructions are overspecified."

    concentration_array = concentration_df.values
    
    if filter_one == False:
        concentration_array = concentration_array
    else: 
        concentration_array = sample_sum_filter(concentration_array)
        
    return concentration_array

# need to add catchers here when filtering- so in reality just the sum thing 
def generate_candidate_lattice_stocks(experiment_csv_dict):
    """Mirror of function generate_candidate_lattice_concentrations expect for the case of looking through multiple stocks and creating combinations of stock concentrations from the csv provided stock concentration linspaces. The major diffierences is the lack of optional 0 concentration handling and unity filter as the concentrations of stocks are independent from on another unlike the concentrations of a components in a singular sample. Returns a 2D array of stock concnetration combinations. Again 1D order is order of stock name and linspace."""
    
    stock_name_list = experiment_csv_dict['Stock Names']
    stock_concs_linspaces_list = experiment_csv_dict['Stock Search Concentrations [min, max, n]']
    stock_conc_type_list = experiment_csv_dict['Stock Concentration Units']
    
    stock_ranges_list = []

    for stock_range in stock_concs_linspaces_list:
        stock_ranges_list.append(np.linspace(*stock_range))
        
    conc_grid = np.meshgrid(*stock_ranges_list)
    
    stock_conc_dict = {}
    for i in range(len(conc_grid)): 
        stock_name = stock_name_list[i]
        stock_conc_dict[stock_name] = conc_grid[i].ravel()
    stock_concentration_df = pd.DataFrame.from_dict(stock_conc_dict)

    stock_concentration_array = stock_concentration_df.values # MOD: is this an actual array? change to np.asarray and test

    return stock_concentration_array

def prepare_stock_search(stock_canidates, experiment_csv_dict, wtf_sample_canidates, min_instrument_vol, max_instrument_vol):
    """
    Used to create a dictionary containing volume and fractional concnetration (currently only wtf and not volf notation wise) of sample canidates which are based on a groups of stock canidates. Also provides useful information in the stock_text_list entry like which stock combination was used and the number of samples possible with the specfic stock combination and concentration canidates. Essentially this runs through the process of creating a bunch of plausible cases given the single component canidates with the each of the previously created stock combination canidates. 
    
    Stock_canidates is a 2D array of stock_canidates provided from generate_candidate_lattice_stocks
    wtf_sample_canidates is the 2D array of wtf_canidates provided from generate_candidate_lattice
    max/min_instrument_vol is the max/min volume to be used by current instrumentation (this will change with instrumentation)
    
    """
    
    stock_names = experiment_csv_dict['Stock Names']
    stock_units = experiment_csv_dict['Stock Concentration Units']
    
    filtered_wtf_list = []
    filtered_volumes_list = []
    stock_text_list = []
    
    for stock_canidate in stock_canidates:
        
        volume_canidates = calculate_ouzo_volumes(wtf_sample_canidates, experiment_csv_dict, stock_searching=True, stock_searching_concentration=stock_canidate) # note the searching option here is important as we want to use a stock candiate from the stock_canidates_list rather than from the csv directly. ATM once you make your actual stocks you will need to go into the csv and change the "Stock Final Concentrations", it is not an input in a python cell as it needs to recorded down somewhere permanent like the csv instructions. 
        
        filtered_wtf_samples, filtered_volumes_samples, min_sample_volume, max_sample_volume = filter_samples(wtf_sample_canidates, volume_canidates, min_instrument_vol, max_instrument_vol)
        
        filtered_wtf_list.append(filtered_wtf_samples)
        filtered_volumes_list.append(filtered_volumes_samples)
        
        stock_text = ['', 'Stock Information']
        
        for i, stock_name in enumerate(stock_names): # adding information on which stock was used
            additional_stock_text = stock_name + ' ' + str(stock_canidate[i]) + ' ' + stock_units[i]
            stock_text.append(additional_stock_text) 
        
        # adding information of what resulted from using this specfic stock
        stock_text.append('Number of samples = ' + str(len(filtered_wtf_samples)))
        stock_text.append('Miniumum Sample Volume =' + str(min_sample_volume) + 'uL')
        stock_text.append('Maximum Sample Volume =' + str(min_sample_volume) + 'uL')
        stock_text_list.append(stock_text)
    
    prepare_stock_dict = {'stocks_wtf_lists': filtered_wtf_list, 
                          'stocks_volumes_lists': filtered_volumes_list, 
                          'stock_text_info': stock_text_list}
  
    return prepare_stock_dict


def ethanol_wtf_water_to_density(ethanol_wtf): # MOD 
    """Converts wtf of ethanol in a binary mixture with water to density using a polyfit of 4. The results are mainly used in the calculation of volume from a weight fraction. UPDATE: need to cite or create potential user entry."""
    
    # Current information pulled from NIST T = @ 25C
    ethanol_wtfs = np.asarray([x for x in range(101)])/100
    ethanol_water_densities = np.asarray([0.99804, 0.99636, 0.99453, 0.99275, 0.99103, 0.98938, 0.9878, 0.98627, 0.98478 , 0.98331 , 0.98187, 0.98047, 0.9791, 0.97775, 0.97643, 0.97514, 0.97387, 0.97259, 0.97129, 0.96997, 0.96864, 0.96729, 0.96592, 0.96453, 0.96312, 0.96168, 0.9602, 0.95867, 0.9571, 0.95548, 0.95382, 0.95212, 0.95038, 0.9486, 0.94679 ,0.94494, 0.94306, 0.94114, 0.93919, 0.9372, 0.93518, 0.93314, 0.93107, 0.92897, 0.92685, 0.92472, 0.92257, 0.92041, 0.91823, 0.91604, 0.91384, 0.9116, 0.90936, 0.90711, 0.90485, 0.90258, 0.90031, 0.89803, 0.89574, 0.89344, 0.89113, 0.88882, 0.8865, 0.88417, 0.88183, 0.87948, 0.87713, 0.87477, 0.87241, 0.87004, 0.86766, 0.86527, 0.86287, 0.86047, 0.85806, 0.85564, 0.85322, 0.85079, 0.84835, 0.8459, 0.84344, 0.84096, 0.83848, 0.83599, 0.83348, 0.83095, 0.8284, 0.82583, 0.82323, 0.82062, 0.81797, 0.81529, 0.81257, 0.80983, 0.80705, 0.80424, 0.80138, 0.79846, 0.79547, 0.79243, 0.78934])   # another way is to use only wtf or state the molarity is calculated as sums of the volumes and not the final volume 
    coeffs = np.polyfit(ethanol_wtfs, ethanol_water_densities,4)
    fit = np.polyval(coeffs, ethanol_wtf)
    return fit


########### Stopped here in updating documentation, other task: create a csv templete explaining each variables and the format on how it should be input, fix the issue of order of operations, fix the ability to only restrict some component/stocks from having an upper limit of volume, add the the ability to use mutliple stocks to create more dilute/more possible samples. 

# def mg_per_mL_to_molarity(mg_per_mL, mw):
#     molarity = mg_per_mL/mw
#     return(molarity)

def add_blank_sample(sample_wtfs, sample_volumes, blank_total_volume, blank_component_wtfs):
    """Allows for the addition of a blank sample at the end of both the concentration and volume arrays that one has selected for experimentation, returns both arrays. Blank units and order of components assumed to the same as those of other samples. Blank total volume left as non-csv-dependent input as this could change with the selected stock conidate/experiment conditions and is up to the user to decide which is the most appropiate.
    
    CSV Information: 
    - blank_component_wtfs = 'Blank Component Concentrations (wtfs)' 
   """
    
    blank_component_volumes = []
    for component_composition in blank_component_wtfs:
        volume = component_composition*blank_total_volume
        blank_component_volumes.append(volume)
    blank_wtfs_array = np.asarray([blank_component_wtfs])
    blank_volume_array = np.asarray([blank_component_volumes])
    blank_and_sample_wtfs = np.concatenate((sample_wtfs, blank_wtfs_array))
    blank_and_sample_volumes = np.concatenate((sample_volumes, blank_volume_array))
    return blank_and_sample_wtfs, blank_and_sample_volumes
    

    
# when calculating volumes need to add "catchers" to allow user to be informed of why search/exe failed (not enough of component b, volume to small etc..)    
def calculate_ouzo_volumes(sample_canidate_list, experiment_csv_dict, stock_searching = False, stock_searching_concentration = None):
    """Given the concentration information along with stock information either directly from the csv or inputted manually (stock searching) will calculate the required volume for each stock to create a given sample. All order is preserved in terms of the samples position in the new volume list and the stock positions. For example: 
    - selected_stock_concentration = [0.1, 0.3]
    - selected_sample_concentrations = [[0.02, 0.20], [0.05, 0.87]]
    - output = [[volume of 0.1 stock, volume of 0.3 stock], [volume of 0.1 stock, volume of 0.3 stock]] 
    ! should change notation to stock_volumes instead of sample volumes makes it confusion 
    
    All intermediate calculation volumes are assumed to in milliliters unless stated otherwise. <- check and label these as not clear
    
    """
    
    total_sample_mass = experiment_csv_dict['Sample Mass (g)']
    component_names = experiment_csv_dict['Component Shorthand Names']
    component_units = experiment_csv_dict['Component Concentration Unit']
    component_densities = experiment_csv_dict['Component Density (g/mL)']
    component_mws = experiment_csv_dict['Component MW (g/mol)']
    component_sol_densities = experiment_csv_dict['Component Solution vol to wt density (g/mL)']
    stock_names = experiment_csv_dict['Stock Names']
    
    if stock_searching == True:
        stock_concentrations = stock_searching_concentration
    else: 
        stock_concentrations = experiment_csv_dict['Stock Final Concentrations']
        
    stock_concentrations_units = experiment_csv_dict['Stock Concentration Units']
    stock_components_list = experiment_csv_dict['Stock Components']
    good_solvent_index = len(component_names)-2 

    sample_stock_volumes = []
    for sample in sample_canidate_list: 
        total_good_solvent_wtf = sample[good_solvent_index]
        total_good_solvent_mass = total_sample_mass*total_good_solvent_wtf
        total_good_solvent_volume = total_good_solvent_mass*ethanol_wtf_water_to_density(total_good_solvent_wtf) # why is volume being used, should not everything be in mass then at the end just converted. 
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
                    stock_density = experiment_csv_dict['Stock Appx Density (g/mL)'][i]
                    component_density = experiment_csv_dict['Component Density (g/mL)']
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
                
def check_volumes(sample, min_instrument_vol, max_instrument_vol = None):
    """Checks a 1D array (in this case the stock volumes of one sample) to see if it contains any volumes outside of the provided min/max of the instrumentation. The only case allowed outside of these min/max bounds is the case of the instrument pipetting no volume or zero volume. For use in case of wanting to limit the amount of steps in sample creation or adhering to OT2 pipette restrictions.
    
    Used as an intermediate step when filtering large amount of samples through the function - filter_samples. 
    
    """

    checker = []
    for vol in sample:
        if vol >= min_instrument_vol and vol <= max_instrument_vol or vol==0: # zero added in the case of no volume
            checker.append(1)
        else:
            checker.append(0)
    if sum(checker) == len(sample):
        return True
    else:
        return False

def filter_samples(wtf_samples_canidates, volume_sample_canidates, min_vol, max_vol):
    """Filters samples based on volume restriction and matches up with previously created wtf sample canidates, 
    returning an updated list of wtf canidates AND volume canidates"""
    
    filtered_volumes = []
    filtered_wtf = []
    filtered_out = [] # optional just add an append in an else statement
    
    for sample_wtfs, sample_vols in zip(wtf_samples_canidates, volume_sample_canidates):
        if check_volumes(sample_vols, min_vol, max_vol) == True: # could say samples_vols[:-1], essentially two checks at once, check from sample_vols[:-1] if min_vol, max_vol =optional - change in funtion, and also if samples_vols[-1] 
            filtered_volumes.append(sample_vols)
            filtered_wtf.append(sample_wtfs)
    
    volume_checking_list = [sum(volume) for volume in filtered_volumes]
    min_sample_volume = min(volume_checking_list)
    max_sample_volume = max(volume_checking_list)
    

    return (filtered_wtf, filtered_volumes, min_sample_volume, max_sample_volume)
    
def rearrange(sample_volumes):
    """Rearranges sample information to group samples based on position in sublist. [[a1,b1,c1],[a2,b2,c2]] => [[a1,a2],[b1,b2],[c1,c2]]. This is used in order to prepare stock volumes to be use in Opentrons volume commmands
    
    
    """
    component_volumes_rearranged = []
    for i in range(len(sample_volumes[0])): 
        component_volumes = []
        for sample in sample_volumes:
            component_volume = sample[i]
            component_volumes.append(component_volume)
        component_volumes_rearranged.append(component_volumes)
    return component_volumes_rearranged 

def experiment_sample_dict(experiment_plan_path, min_input_volume, max_input_volume, filter_sum_one = True): 
    """A wrapper for functions required to create ouzo samples, where final information is presented in returned dictionary. EXPLAIN THE WALKTHROUGH OF THIS STEP BY STEP ALLOWING SOMEONE TO FOLLOW  """
    experiment_plan_dict = get_experiment_plan(experiment_plan_path)
    wtf_sample_canidates = generate_candidate_lattice_concentrations(experiment_plan_dict, filter_one=filter_sum_one)
    volume_sample_canidates = calculate_ouzo_volumes(wtf_sample_canidates, experiment_plan_dict)
    
    # now filter volume min no max for all but water, but min and max for water - but should not have to input volume should just be based on pipettes
    
    filtered_wtf_samples, filtered_volume_samples, min_sample_volume, max_sample_volume = filter_samples(wtf_sample_canidates, volume_sample_canidates, min_input_volume, max_input_volume)
    
    experiment_info_dict = {'experiment_plan_dict': experiment_plan_dict,
                           'wtf_sample_canidates': wtf_sample_canidates,
                           'volume_sample_canidates': volume_sample_canidates,
                           'filtered_wtf_samples': filtered_wtf_samples,
                           'filtered_volume_samples': filtered_volume_samples, 
                           'Minimum Sample volume (uL)': min_sample_volume, 
                           'Maximum Sample volume (uL)': max_sample_volume}
    return experiment_info_dict


# WHAT IS THIS???
def calculate_stock_volumes(experiment_csv_dict, sample_volumes):
    rearranged_by_component_volumes = rearrange(sample_volumes)
    summed_stock_volumes = [sum(stock_volumes) for stock_volumes in rearranged_by_component_volumes]
    stock_names = experiment_csv_dict['Stock Names']
    stock_concentrations = experiment_csv_dict['Stock Final Concentrations']
    stock_units = experiment_csv_dict['Stock Concentration Units']
    
    
    for i in range(len(summed_stock_volumes)):
        string = str(summed_stock_volumes[i]/1000) + ' mL of ' + stock_names[i] + ' w/ conc of ' + str(stock_concentrations[i]) + ' ' + stock_units[i]
        print(string)
                   
def selected_down(array, lower_index, upper_index):
    array = array[lower_index:upper_index]
    return array

def create_csv(destination, info_list, wtf_samples, experiment_csv_dict):  
    """Creates a CSV which contains sample information in addition tieing a unique ID to the row of information. Each row in the created csv corresponds to one sample and the unique ID contains date and well information. Information is gathered from the printed commands of the OT2 either when executing or simulating. Given the type of execution in current code, this only supports the case of consecutive sample making (i.e. samples made in well order, with no skipping of wells)."""
    
    time = str(datetime.datetime.now(timezone('US/Pacific')).date()) # should be embaded once you run
    component_names = experiment_csv_dict['Component Shorthand Names']
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
        UID = time + "_" +experiment_csv_dict['Component Shorthand Names'][experiment_csv_dict['Component Graphing X Index']]+ "_" + experiment_csv_dict['Component Shorthand Names'][experiment_csv_dict['Component Graphing Y Index']] + "_" + well
        csv_entry = [UID] + component_wtfs.tolist() + [slot] + [labware] + [well]
        csv_entries.append(csv_entry)

    with open(destination, 'w', newline='',encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile, delimiter = ",")
        csvwriter.writerow(complete_header)
        csvwriter.writerow(complete_experiment_header) # so what 

        for row in csv_entries:
            csvwriter.writerow(row)