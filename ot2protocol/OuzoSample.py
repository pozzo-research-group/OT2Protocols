class OuzoSample:
    '''
    Create ouzo sample with colloidal stabilizer in Aq. phase:
    organic solvent, organic solvent + hydrophobe/oil, 
    water, water + colloidal stabilizer 
    
    components_dict - dictionary pointing to Component objects with context specific roles
    e.g. {'hydrophobe':Component, 'organic_solvent':Component, 'water':Component, 'stabilizer1':Component}
    
    wtf_dict - dictionary which ties components to their respective weight fractions:
    e.g. {'hydrophobe':float, 'organic_solvent':float...'water':None}
    
    '''
    def __init__(self, mass = None, components_dict ={}, wtf_dict ={}, density = None, stock_dict ={}):
        self.hydrophobe = components_dict['hydrophobe']
        self.organic_solvent = components_dict['organic_solvent']
        self.stabilizer1 = components_dict['stabilizer1']
        self.water = components_dict['water']
        
        self.hydrophobe_wtf = wtf_dict['hydrophobe']
        self.organic_solvent_wtf = wtf_dict['organic_solvent']
        self.stabilizer1_wtf = wtf_dict['stabilizer1']
        self.water_wtf = wtf_dict['water']
        
        self.hydrophobe_stock =stock_dict['hydrophobe'] 
        self.organic_solvent_stock =stock_dict['organic_solvent'] 
        self.stabilizer1_stock =stock_dict['stabilizer1'] 
        self.water_stock =stock_dict['water'] 
    

        self.mass = mass
        self.hydrophobe_mass = mass * self.hydrophobe_wtf
        self.organic_solvent_mass = mass * self.organic_solvent_wtf
        self.stabilizer1_mass = mass * self.stabilizer1_wtf
        self.water_mass = mass * self.water_wtf
        
        #{component, component_mass is mass of component in sample, component_stock points to stock class 
        # object associated with object, component_wtf is the wtf of this component in sample}
        self.hydrophobe_dict = {'component':self.hydrophobe,'component_mass':self.hydrophobe_mass, 
        'component_stock':self.hydrophobe_stock, 'component_wtf':self.hydrophobe_wtf}
        self.organic_solvent_dict = {'component':self.organic_solvent,
        'component_mass':self.organic_solvent_mass, 'component_stock':self.organic_solvent_stock, 'component_wtf':self.organic_solvent_wtf}
        self.stabilizer1_dict = {'component':self.stabilizer1,
        'component_mass':self.stabilizer1_mass, 'component_stock':self.stabilizer1_stock, 'component_wtf':self.stabilizer1_wtf}
        self.water_dict = {'component':self.water,
        'component_mass':self.water_mass, 'component_stock':self.water_stock, 'component_wtf':self.water_wtf}

        self.additional_water_mass = self.water_mass
        self.additional_organic_solvent_mass = self.organic_solvent_mass
        if self.hydrophobe_stock.solvent == self.organic_solvent:
            self.source_organic(self.hydrophobe_dict)
        
        if self.stabilizer1.solvent == self.water:
            self.source_aq(self.stabilizer1_dict, prestock=True)
            
    def source_aq(self,dict_to_source, prestock):
        '''
        Update dictionary that tracks paremeters associated with this component with how much water/aq stock is necessary to make sample, 
        and simultaneously track how this affects solvent volume
        '''
        component_mass = dict_to_source['component_mass']
        component_stock = dict_to_source['component_stock']
        
        total_stock_mass = component_mass/component_stock.componentA_wtf
        solvent_stock_mass = total_stock_mass-component_mass

        dict_to_source['total_stock_mass']=total_stock_mass
        dict_to_source['solvent_stock_mass']=solvent_stock_mass
        if prestock == True:
            dict_to_source['aq_prestock'] = self.make_aq_prestock(dict_to_source)
        else:
            self.additional_water_mass -= solvent_stock_mass
            raise Exception("Class not configured to move componens without prestock")
        return
    
    def source_organic(self, dict_to_source):
        '''
        Update dictionary that tracks paremeters associated with this component with how much organic stock is necessary to make sample, 
        and simultaneously track how this affects solvent volume
        '''
        component_mass = dict_to_source['component_mass']
        component_stock = dict_to_source['component_stock']
        
        total_stock_mass = component_mass/component_stock.componentA_wtf
        solvent_stock_mass = total_stock_mass-component_mass
        total_stock_volume = total_stock_mass/component_stock.density

        dict_to_source['total_stock_mass']=total_stock_mass
        dict_to_source['solvent_stock_mass']=solvent_stock_mass
        dict_to_source['total_stock_volume'] = total_stock_volume
        self.additional_organic_solvent_mass -= solvent_stock_mass
        return 

    def make_aq_prestock(self, dict_for_prestock):
        #units: 
        # prestock_volume units = uL
        # density = g/cm3 or g/mL
        # mass = g


        dead_prestock_weight = 0.2 #Hard coded value for making slight excess of prestock, so that air is not aspirated

        min_component_mass = dict_for_prestock['component_mass']
        component_stock = dict_for_prestock['component_stock']
        prestock_component_wtf = min_component_mass/self.water_mass
        
        #Minimum prestock mass is essential. This pulls the mass of component and water from sample, and combines it into a prestock
        #This prestock is then scaled up to prevent air aspiration. Additionally, this prestock mass is used to determine volume 
        #of prestock that needs to be moved in final ouzo sample making step
        min_prestock_mass = sum(min_component_mass, self.water_mass)
        scaled_prestock_mass = dead_prestock_weight + min_prestock_mass
        
        #Since we're creating more than we need, we need to draw more from master stock, than if we were adding directly to sample
        prestock_component_mass = scaled_prestock_mass*prestock_component_wtf
        total_stock_mass  = prestock_component_mass/component_stock.componentA_wtf
        solvent_stock_mass = total_stock_mass-prestock_component_mass
        additional_solvent_mass = scaled_prestock_mass-solvent_stock_mass-prestock_component_mass
        total_stock_volume = total_stock_mass/component_stock.density
        additional_solvent_volume = additional_solvent_mass/component_stock.solvent.density

        if additional_solvent_mass == (scaled_prestock_mass*(1.0 -prestock_component_wtf)):
            print("Prestock math might be ok")
        else:
            print("Warning, additional_solvent_mass to make prestock seems off=  ", additional_solvent_mass)

        #Again, wherever we see a density call we could substitute this with something smarter, like a reference to data table of density vs. weight fraction 
        prestock_volume = min_prestock_mass/self.water.density*1000 

        aq_prestock = {'prestock_component_mass':prestock_component_mass, 'prestock_component_wtf':prestock_component_wtf, 
        'total_stock_mass':total_stock_mass, 'solvent_stock_mass':solvent_stock_mass, 'additional_solvent_mass':additional_solvent_mass,
        'prestock_volume':prestock_volume, 'additional_solvent_volume':additional_solvent_volume, 'total_stock_volume':total_stock_volume}
        
        return aq_prestock



                