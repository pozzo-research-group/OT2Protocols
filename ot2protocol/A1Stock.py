class A1Stock:
    '''
    A1_Stock: shorthand for stock with Component A, and 1 solvent.
    class called AB2 would consist of Components A and B, and 2 solvents. 
    Minimum information: 
    
    components_dict - dictionary pointing to Component objects: 
    e.g. {'A':Component, 'solvent1':Component}
    
    wt_f_dict - dictionary which ties components to their respective weight fractions:
    e.g. {'A':float, 'solvent1':float}
    
    density - float. By default this is solvent1.density
    
    TODO: 
    -Potential for A1_stock method which estimates density based on volume of component, 
    or A1_stock method which takes interpolates density from dataset of density and wt.f. Component:solvent
    -Function which manages volume/position of A1_stock, i.e. we can assign multiple stock and have the robot 
    switch to new stock position when necessary.
    '''
    
    def __init__(self, components_dict ={}, wt_f_dict ={}, density = None):
        self.componentA = components_dict['A']
        self.solvent1 = components_dict['solvent1']

        self.componentA_wtf = wt_f_dict['A']
        self.solvent1_wtf = wt_f_dict['solvent1']
        
        self.density = self.solvent1.density #Approximate density as density of solvent1 for now. 
    def real_init(self):
        pass
