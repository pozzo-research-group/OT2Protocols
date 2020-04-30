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
    will consist of, return a list of dataframes of just those entries from the
    chemical database df.
    """
    component_list = plan_dict['Component names']
    selection1 = chemical_db_df['Chemical Abbreviation'].isin(component_list)
    component_df = chemical_db_df[selection1]

    component_df_list = []
    for component_name in component_list:
        selection2 = component_df['Chemical Abbreviation'] == component_name
        component_df_list.append(component_df[selection2])
    return component_df_list


def generate_candidate_samples(plan_dict, chemical_db_df):
    """
    Given a experimental plan dictionary loaded from .csv,
    create a linspace array for every entry and
    obtain every possible combination using meshgrid.
    This will get fed to another function which removes impossible samples
    based on some criteria.
    """
    component_df_list = get_component_info(plan_dict, chemical_db_df)
    component_list = plan_dict['Component names']
    # Create df for each component based on position in list
    component_concs_list = plan_dict['Concentration linspace [min, max, n]']
    component_conc_type_list = plan_dict['Concentration types']
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
    concentration_df = pd.DataFrame.from_dict(component_conc_dict)

    # At this stage, if a component has remained unspecified (e.g. water), then
    # we need to apply the mixture rule to obtain its value. Each combination
    # of concentrations needs to make use of ConcentrationManager methods to
    # calculate unspecified volume_fraction = 1-sum(all other concentrations).

    if len(component_list) == len(component_concs_list):
        # Somehow the exact concentrations of each component were specified.
        return concentration_df
    else:
        # Obtaining volume fractions of all components in sample to determine
        # missing volume fraction.
        concentration_array = concentration_df.values
        conc_man_array = np.empty(shape=(concentration_array.shape),
                                  dtype=object)
        for i in range(len(concentration_array)):
            conc_vector = concentration_array[:, i]

            conc_type = component_conc_type_list[i]
            # conc_type_vector = np.empty(shape=(concentration_array.shape[0]),
            #                             dtype=object)
            # conc_type_vector[:] = conc_type

            comp_df = component_df_list[i]
            # comp_df_vector = np.empty(shape=(concentration_array.shape[0]),
            #                           dtype=object)
            # comp_df_vector[:] = comp_df

            conc_man_array[:, i] = ConcentrationManager(conc_vector,
                                                        conc_type,
                                                        comp_df)
    return concentration_df


class ConcentrationManager:
    """
    The purpose of this class is to take the concentration value used to
    originally specify the sample, and convert it into an interoperable unit
    format.
    """

    def __init__(self, concentration_value, concentration_type, component_df):
        """
        Upon initialization, assign all known information into the
        component_df. Then, use unit_cases_dict to manage unit conversion
        scenarios and generate all possible methods of expressing sample
        concentrations.

        Unit definition clarification:
        density - g/mL
        molarity - moles/liter
        """
        print(len(concentration_value))
        self.component_df = component_df
        self.component_mw = self.component_df['Molecular Weight (g/mol)']
        self.component_density = self.component_df['Density (g/mL)'].values
        # There are cases where approximating the component_density as 1.0 g/mL
        # is not a good idea. Is 1.0 chosen because water is a common solvent,
        # or ____?
        if self.component_density == np.nan:
            self.component_density = 1.0

        unit_cases_dict = {
            "molarity": self.molarity(concentration_value),
            "volf": self.volf(concentration_value),
            "mgpermL": self.mgpermL(concentration_value)
        }
        # "massf": self.massf(concentration_value),

        # Next, convert current units to all other units.
        unit_cases_dict[concentration_type]

    def molarity(self, concentration_value):
        self.molarity = concentration_value
        self.mgpermL = self.molarity*self.component_mw
        self.volf = self.mgpermL/(self.component_density*1000)

    def volf(self, concentration_value):
        self.volf = concentration_value
        self.mgperml = self.volf*self.component_density*1000
        self.molarity = self.mgpermL/self.component_mw

    def mgpermL(self, concentration_value):
        self.mgpermL = concentration_value
        self.volf = self.mgpermL/(self.component_density*1000)
        self.molarity = self.mgpermL/self.component_mw
