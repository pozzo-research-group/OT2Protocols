import matplotlib.pyplot as plt

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

def graph_canidates(experiment_dict, unfiltered_samples, filtered_samples, xlim = [0,1], ylim = [0,1]):
    wtf_unfiltered_rearranged = rearrange(unfiltered_samples)
    wtf_filtered_rearranged = rearrange(filtered_samples)

    marker_size = 20

    component_names = experiment_dict['Component Shorthand Names']
    
    x_index = experiment_dict['Component Graphing X Index']
    x_component_name = component_names[x_index]

    y_index = experiment_dict['Component Graphing Y Index']
    y_component_name = component_names[y_index]
    

    # Plot all canidates
    plt.scatter(wtf_unfiltered_rearranged[x_index], 
                wtf_unfiltered_rearranged[y_index], 
                marker_size, alpha = 0.6, marker = 'x', color = 'b')

    # Plot samples actually made 
    plt.scatter(wtf_filtered_rearranged[x_index], # could automate by looking at the experiment names
                wtf_filtered_rearranged[y_index], 
                marker_size, alpha = 0.5, marker = 'o', color = 'r')


    plt.xlabel(x_component_name + ' wtf')
    plt.ylabel(y_component_name + ' wtf')
    
    completing_component_index = len(component_names) - 1  
    other_indexes = []
    for i in range(len(component_names)):
        if i == x_index or i == y_index or i == completing_component_index:
            pass
        else:
            other_indexes.append(i)
        
    component_units = experiment_dict['Component Concentration Unit']
    component_concentrations = experiment_dict['Component Concentrations [min, max, n]']
    
    text = []
    for index in other_indexes: 
        component_unit = component_units[index]
        component_concentration = component_concentrations[index][0]
        component_name = component_names[index]
        string = component_name + ' ' + component_unit + ' ' + str(component_concentration)
        text.append(string)
    
    text.append('Remaining component = ' + component_names[completing_component_index])
    text_newline = '\n'.join(text) 

    plt.annotate(text_newline, xy=(1.05, 0.85), xycoords='axes fraction')        
    plt.autoscale(True)
    plt.show()
