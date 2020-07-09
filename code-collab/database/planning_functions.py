"""
The purpose of this python file, is to evaluate the samples generated during
setup, by taking into account:

1. Maximum solubility.
1.1 Obtained from a stock information file.
2. Minimum pipette volume.
2.1 Obtained from experiment specification excel sheet.
Output an excel sheet with suggested stock concentrations which can be edited
by the user.
 """

import csv
import pandas as pd
import numpy as np
import ast
import setup_functions


def get_min_volume(plan_dict):
    opentrons.robot.reset()
    left_pipette = pipette_dict[plan_dict['Left pipette']]
    right_pipette = pipette_dict[plan_dict['Right pipette']]
    left_min = left_pipette(mount="left").min_volume
    right_min = right_pipette(mount="right").min_volume
    min_volume = min(left_min, right_min)
    return min_volume


def get_solubility_df(plan_dict, filepath, sheet_name, chemical_db_df):
    """
    Get solubility data from a simple excel sheet that contains relevant
    solubility data. This should be the maximum concentration of the component
    that is feasible to prepare as a stock.
    """
    solubility_df = pd.read_excel(filepath, sheet_name=sheet_name)
    component_names = plan_dict['Component names']
    solubility_df = solubility_df[solubility_df[
        'Component 1 Abbreviation'].isin(component_names)]

    molarity_list = []
    volf_list = []
    for i, row in solubility_df.iterrows():
        conc = row['Component 1 Maximum g/L']
        name = row['Component 1 Abbreviation']
        component_df = chemical_db_df[chemical_db_df[
            'Chemical Abbreviation'] == name]
        molarity = setup_functions.concconvert(conc, 'mgpermL', component_df,
                                               'molarity')
        volf = setup_functions.concconvert(conc, 'mgpermL', component_df,
                                           'volf')
        molarity_list.append(molarity)
        volf_list.append(volf)

    solubility_df['Component 1 molarity'] = molarity_list
    solubility_df['Component 1 vol. f.'] = volf_list
    return solubility_df
