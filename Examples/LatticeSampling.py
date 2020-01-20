import numpy as np

"""Function receives an array with concentration constraints (i.e. minimum, maximum and step-size) in units of volume fraction
The function assumes that another unconstrained component will be used as 'filler' to satisfy the mixture constraint (i.e. sum vol frac =1)
It  returns an array of all the feasible samples that satisfy the mixture contraint, 
the original min/max concentration constraints and that are distributed evenly spaced as stipulated by the step sizes.
The function returns an array that is organized as follows: For a three component constrained sample, it returns
Volfrac1, Volfrac2, Volfrac3 and Volfrac_filler. 'Filler' is the component that is used to complete the
mass fractions to force them to add up to one. Each row in the return array represents a sample. Note that samples are not
inclusive of the upper limit constraint."""

def lattice_sample_list(max_min_step):
    #The number of components is equal to the number of rows of constraints that are passed
    number_components = np.shape(max_min_step)[0]
    #Use mgrid function to generate an N dimensional array with all combinatorial components according to concentration constraints 
    sample_grid = np.mgrid[[slice(row[0], row[1], row[2]) for row in max_min_step]]
    #Obtain shape of the N-Dimenaional output and convert to an array to re-shape to 2D
    grid_shape_array = np.asarray(np.shape(sample_grid))
    #The total number of samples to be prepared is the product of all elements in the array except for the first.
    #The first element of the shape array corresponds to the number of chemical constraints.
    #Total number of samples is calculated and used to re-shape the sample grid array to 2D. 
    #Here the columns represent the chemical concentrations and the rows represent each sample composition.
    totalsamples = np.int(np.prod(grid_shape_array)/grid_shape_array[0])
    sample_grid_2D = np.reshape(sample_grid,(grid_shape_array[0],totalsamples)).T
    
    filler_volfrac = 1.0-np.sum(sample_grid_2D, axis=1)
    filler_volfrac = np.reshape(filler_volfrac,(totalsamples,1))
    
    samples_w_filler = np.hstack((sample_grid_2D, filler_volfrac))
    feasible_samples = samples_w_filler[samples_w_filler.min(axis=1)>=0,:]
    
    return(feasible_samples)        