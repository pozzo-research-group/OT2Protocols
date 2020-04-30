import csv
import pandas as pd
import numpy as np
import ast
import opentrons


pipette_dict = {
    "P1000_Single": opentrons.instruments.P1000_Single,
    "P1000_Single_GEN2": opentrons.instruments.P1000_Single_GEN2,
    "P300_Single": opentrons.instruments.P300_Single,
    "P300_Single_GEN2": opentrons.instruments.P300_Single_GEN2
}


def get_stock_dfs(filepath):
    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        index_list = []
        full_list = []
        for i, row in enumerate(reader):
            if row[0] == 'Stock name':
                index_list.append(i)
            full_list.append(row)

        stock_df_dict = {}
        for i, index in enumerate(index_list):
            name = full_list[index][1]
            if i == len(index_list)-1:
                stock_info = full_list[index+1:len(full_list)]
                # This is the last entry in the list of indices
            else:
                stock_info = full_list[index+1:index_list[i+1]]

            df = pd.DataFrame(stock_info)
            df = df.rename(columns=df.iloc[0])
            df = df.drop(df.index[0])
            stock_df_dict[name] = df

    return stock_df_dict


def get_experiment_plan(filepath):
    """
    Parse a .csv file to create a dictionary of instructions.
    """

    with open(filepath, newline='') as csvfile:
        reader = csv.reader(csvfile)
        parsed_dict = {}
        for i, row in enumerate(reader):
            assert len(row) == 2
            parsed_dict[row[0]] = ast.literal_eval(row[1])

    return parsed_dict


def get_min_volume(plan_dict):
    opentrons.robot.reset()
    left_pipette = pipette_dict[plan_dict['Left pipette']]
    right_pipette = pipette_dict[plan_dict['Right pipette']]
    left_min = left_pipette(mount="left").min_volume
    right_min = right_pipette(mount="right").min_volume
    min_volume = min(left_min, right_min)


def get_component_info(plan_dict, chemical_db_df):
    """
    Given a plan_dict which contains the names of components that each sample
    will consist of, return a dataframe of just those entries from the
    chemical_inventory.
    """
    component_list = plan_dict['Component names']
    selection = chemical_db_df['Chemical Abbreviation'].isin(component_list)
    component_df = chemical_db_df[selection]
    return component_df


def generate_candidate_samples(plan_dict, chemical_db_df):
    """
    Given a experimental plan dictionary loaded from .csv,
    create a linspace array for every entry and
    obtain every possible combination using meshgrid.
    This will get fed to another function which removes impossible samples
    based on some criteria.
    """
    component_df = get_component_info(plan_dict, chemical_db_df)
    component_list = plan_dict['Component names']
    component_concs_list = plan_dict['Concentration linspace [min, max, n]']
    component_conc_dict = {}
    conc_range_list = []
    for conc_range in component_concs_list:
        conc_range_list.append(np.linspace(*conc_range))
    conc_grid = np.meshgrid(*conc_range_list)
    for i in range(len(conc_grid)):
        # Create concentration entry in dictionary,
        # key:value = component name: flattened list of concentrations
        component_name = component_list[i]
        component_conc_dict[component_name] = conc_grid[i].ravel()
    output_df = pd.DataFrame.from_dict(component_conc_dict)
    return output_df
