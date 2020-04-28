class Oil_Surfacant_Mineralization:
    
    """
    Class for handling:
    Oil, vol. f
    Solvent, vol. f
    Surfactant, Molarity
    Buffering and/or reducing agent, Molarity (e.g HEPES)
    Precursor Molarity

    Volume - Volume of sample in mL, assuming negligible contribution from stabilizer, buffer, precursor
    
    Dictionaries note - all keys should simply be component name. 

    components_dict - dictionary pointing to Component objects with context specific roles
    e.g. {'hydrophobe':Component, 'organic_solvent':Component, 'solvent1':Component, 'stabilizer1':Component}

    volf_dict - dictionary which ties components to their respective volume fractions:
    e.g. {'hydrophobe':float, 'organic_solvent':float...'solvent1':None}

    stock_dict - dictionary for pointing to A1Stock objects. 
    """

    def __init__(self, volume = None, components_dict ={}, volf_dict ={}, molarity_dict = {} ,density = None, stock_dict ={}):
        self.components_dict = components_dict
        self.volf_dict = volf_dict
        self.molarity_dict = molarity_dict
        self.density = density
        self.stock_dict = stock_dict
        self.volume = float(volume)
        self.component_name_dict = {}

        #Initialize dictionaries of calculated properties below. 
        #Note assigned prefix is method for tabulating how much of a component
        #has already been accounted for by stock assignment.
        #Stock transfer is the volume of a stock that needs to be transferred. 
        self.volumes_dict = {}
        self.moles_dict = {} #Obtained by using Molarity (M) and volume of sample (mL)
        self.assigned_volumes_dict = {}
        self.assigned_moles_dict = {}
        self.assigned_stock_transfer_dict = {}
        

        #Iterate and perform calculations below
        for component_key in components_dict:
            self.assigned_volumes_dict[component_key] = 0.0
            self.assigned_moles_dict[component_key] = 0.0
            #Below was necessary because key error occurs when updating assigned volume
            #of a solvent used in a stock. i.e. we need to map 'water' : 'solvent1'
            self.component_name_dict[self.components_dict[component_key].name] = component_key
            # print(self.components_dict[component_key].name, "mapped to ", component_key)
            if component_key in self.volf_dict:
                if component_key in self.molarity_dict:
                    raise Exception("Calculations must be proceed from volf OR molarity")
                self.volumes_dict[component_key]=self.volume*self.volf_dict[component_key]
                # if 'solvent' not in component_key:
                #     self.stock_dict[component_key].wtf_to_volf()
            if component_key in self.molarity_dict:
                self.moles_dict[component_key] = self.molarity_dict[component_key]*self.volume/1000.0
                # self.stock_dict[component_key].wtf_to_molarity()
                # print(component_key, "molarity = , ", self.stock_dict[component_key].componentA_molarity)
        
        for component_key in self.stock_dict:
            if component_key in self.volf_dict and 'solvent' not in component_key:
                #Assign stock transfer volumes for samples which are handled using volume fraction - e.g. emulsified oil.
                self.assigned_stock_transfer_dict[component_key] = self.volumes_dict[component_key]/self.stock_dict[component_key].componentA_volf
                self.assigned_volumes_dict[component_key]+= self.volumes_dict[component_key]
                
                #Now account for the solvent used to transfer component
                assigned_solvent_name = self.stock_dict[component_key].solvent1.name
                assigned_solvent_name = self.component_name_dict[assigned_solvent_name]

                if type(assigned_solvent_name) is not str:
                    raise Exception("Expected assigned solvent name string to use in a dict, but got ", type(assigned_solvent_name))
                self.assigned_volumes_dict[assigned_solvent_name]+= self.volumes_dict[component_key]/self.stock_dict[component_key].solvent1_volf
            
            if component_key in self.molarity_dict:
                #Assign stock transfer volumes for samples which are handled using molarity - e.g. stablizer, precursor, buffer.
                if float(self.moles_dict[component_key]) == 0.0:
                    self.assigned_stock_transfer_dict[component_key] = 0
                else:
                    self.assigned_stock_transfer_dict[component_key] = 1000.0*self.moles_dict[component_key]/self.stock_dict[component_key].componentA_molarity
                self.assigned_moles_dict[component_key] = self.assigned_stock_transfer_dict[component_key]*self.stock_dict[component_key].componentA_molarity/1000.0

                 #Now account for the solvent used to transfer component
                assigned_solvent_name = self.stock_dict[component_key].solvent1.name
                assigned_solvent_name = self.component_name_dict[assigned_solvent_name]
                if type(assigned_solvent_name) != str:
                    raise Exception("Expected assigned solvent name string to use in a dict, but got ", type(assigned_solvent_name))
                self.assigned_volumes_dict[assigned_solvent_name]+= self.assigned_stock_transfer_dict[component_key]            
        for component_key in components_dict:
            if component_key in self.volf_dict:
                #Check for difference between desired and assigned volume. 
                # print(component_key)
                # print(self.volumes_dict)
                # print(self.assigned_volumes_dict)
                # print(self.volumes_dict[component_key] - self.assigned_volumes_dict[component_key])
                if 'solvent' in component_key:
                    missing_solvent_volume = self.volumes_dict[component_key]-self.assigned_volumes_dict[component_key]
                    self.assigned_stock_transfer_dict[component_key] = missing_solvent_volume
                    self.assigned_volumes_dict[component_key] +=missing_solvent_volume
                    # print("component_key", component_key)
                    # print("self.volumes_dict",self.volumes_dict)
                    # print("self.assigned_volumes_dict", self.assigned_volumes_dict)
                    # print("self.assigned_stock_transfer_dict", self.assigned_stock_transfer_dict)
                    # print(self.volumes_dict[component_key] - self.assigned_volumes_dict[component_key])
                    
    def transfer_ml_to_ul(self):
        """
        Convert assigned_transfer_dict from mL to uL
        """
        self.converted_transfer_dict = {}
        for component_key in self.assigned_stock_transfer_dict:
            self.converted_transfer_dict[component_key] = self.assigned_stock_transfer_dict[component_key]*1000.0