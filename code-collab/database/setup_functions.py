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
        plan_dict = {}
        for i, row in enumerate(reader):
            assert len(row) == 2
            plan_dict[row[0]] = ast.literal_eval(row[1])

    return plan_dict


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


def generate_candidate_lattice_concentrations(plan_dict, chemical_db_df):
    """
    Given a experimental plan dictionary loaded from .csv,
    create a linspace array for every entry and
    obtain every possible combination using meshgrid.
    This will get fed to another function which removes impossible samples
    based on some criteria.
    """
    # Create df for each component based on position in list
    component_df_list = get_component_info(plan_dict, chemical_db_df)
    component_list = plan_dict['Component names']
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

    assert len(component_list) != len(component_concs_list), "The provided" \
        "experimental instructions are overspecified."

    # Obtaining volume fractions of all components in sample to determine
    # missing volume fraction.
    concentration_array = concentration_df.values
    volf_array = np.empty(shape=(concentration_array.shape[0],
                                 concentration_array.shape[1]+1))

    for i, component in enumerate(component_list):
        # Make use of the fact that the index position in the
        # experimentation specification is conserved between lists.
        component_df = component_df_list[i]
        conc_type = component_conc_type_list[i]
        if i != len(component_list)-1:
            concentration_vector = concentration_array[:, i]
            # All specified components case
            volf_array[:, i] = concconvert(concentration_vector, conc_type,
                                           component_df, 'volf')
        else:
            # Last component case
            volf_array[:, i] = 1.0 - np.sum(volf_array[:, :i], axis=1)
            # Drop all entries where originally unspecified vol f. is < 0,
            # i.e. the sum of the other components for this combination was
            # impossible (> 1).
            condition = volf_array[:, i] >= 0
            volf_array = volf_array[condition]

    molarity_array = np.empty(shape=(volf_array.shape))
    mgpermL_array = np.empty(shape=(volf_array.shape))

    for i, component in enumerate(component_list):
        # Create complementary mgpermL and molarity arrays for each component.
        # This can be used to further narrow down the samples that are possible
        # to make, because we can calculate how much of a stock with some
        # concentration is necessary to create each sample. The previously
        # described concentration array may have heterogeneous methods of
        # specifying the concentration. Here we will normalize them.
        component_df = component_df_list[i]
        molarity_array[:, i] = concconvert(volf_array[:, i], 'volf',
                                           component_df, 'molarity')
        mgpermL_array[:, i] = concconvert(volf_array[:, i], 'volf',
                                          component_df, 'mgpermL')

    concentration_dict = {'molarity': molarity_array, 'volf': volf_array,
                          'mgpermL': mgpermL_array}
    return concentration_dict


def concconvert(concentration_value, input_concentration,
                component_df, output_concentration):
    """
    Wrapper function for converting units. Unit definition clarification:
    density - g/mL molarity - moles/liter
    """
    def molarity_f():
        molarity = concentration_value
        mgpermL = molarity*component_mw
        volf = mgpermL/(component_density*1000)
        return molarity, mgpermL, volf

    def volf_f():
        volf = concentration_value
        mgpermL = volf*component_density*1000
        molarity = mgpermL/component_mw
        return molarity, mgpermL, volf

    def mgpermL_f():
        mgpermL = concentration_value
        volf = mgpermL/(component_density*1000)
        molarity = mgpermL/component_mw
        return molarity, mgpermL, volf

    component_mw = component_df['Molecular Weight (g/mol)'].values[0]
    component_density = component_df['Density (g/mL)'].values[0]

    # There are cases where approximating the component_density as 1.0 g/mL
    # is not a good idea. Is 1.0 chosen because water is a common solvent,
    # or ____?
    if np.isnan(component_density):
        component_density = 1.0

    unit_cases_dict = {
        "molarity": molarity_f,
        "volf": volf_f,
        "mgpermL": mgpermL_f
    }

    selected_function = unit_cases_dict[input_concentration]
    molarity, mgpermL, volf = selected_function()
    output_dict = {"volf": volf, "molarity": molarity, "mgpermL": mgpermL}

    return output_dict[output_concentration]


def get_extensive(concentration_dict, plan_dict, chemical_db_df):
    """
    Given arrays of concentrations, experimental plan containing component
    names, and a pandas dataframe containing component information (MW,
    density) - calculate moles, grams, and mL for each component in a given
    sample.
    """
    component_df_list = get_component_info(plan_dict, chemical_db_df)
    component_list = plan_dict['Component names']
    molarity_array = concentration_dict['molarity']
    sample_volume = plan_dict['Sample volume (uL)']

    def molarity_to_moles(molarity, sample_volume):
        """
        Expected units for molarity are mol/liter.
        Expected units for sample volume are uL
        Function seems overkill right now, but could be useful to implement\
        switch cases if units of sample volume are different, or if the output
        needs to have different units.
        """
        calculated_moles = molarity*(sample_volume*1e-6)
        return calculated_moles

    def moles_to_grams(moles, component_df):
        mw = component_df['Molecular Weight (g/mol)'].values[0]
        assert mw is not None, "No molecular weight entered for component" + \
            component_df['Chemical Abbreviation']
        calculated_grams = moles*mw
        return calculated_grams

    def grams_to_mL(grams, component_df):
        component_density = component_df['Density (g/mL)'].values[0]
        if np.isnan(component_density):
            print("No density input for",
                  component_df['Chemical Abbreviation'].values[0],
                  'using density = 1.0')
            component_density = 1.0
        calculated_mL = grams/component_density
        return calculated_mL

    moles = np.zeros(molarity_array.shape)
    grams = np.zeros(molarity_array.shape)
    mL = np.zeros(molarity_array.shape)

    for i, component_df in enumerate(component_df_list):
        # Loop over component_df list. Make use of index to loop over columns
        # of molarity_array.
        moles[:, i] = molarity_to_moles(molarity_array[:, i], sample_volume)
        grams[:, i] = moles_to_grams(moles[:, i], component_df)
        mL[:, i] = grams_to_mL(grams[:, i], component_df)

    output_dict = {'moles': moles, 'grams': grams, 'mL': mL}
    return output_dict
