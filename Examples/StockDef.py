class Components:
    # Define Components using the component class.  
    # Expected units: mw (g/mol), density of pure material (g/mL) @25C 
    def __init__(self, name, mw, density = 1):
        self.mw = mw
        self.density = density #(g/mL) defaults to 1 g/mL if missing
        self.name = str(name)

class Stocks:
    #Define stock solutions prepared from individual components. 
    #A stock is assumed to contain no more than two components (solute + solvent)
    #Stock solutions may be pure materials if they are added as liquids. In such cases concentration should be 1
    def __init__(self, name, solute, solvent, concentration, conc_type='volfrac', ExpDensity=0):
        #ExpDensity is the experimentally measured density (if known)
        self.name = str(name)
        if conc_type == 'volfrac': 
            self.volfrac = concentration
            #Calculate concentration in mg/mL from the volume fraction
            self.mgpermL = self.volfrac*solute.density*1000
            #Calculate solute molarity 
            self.molarity = self.mgpermL/solute.mw 
            if ExpDensity == 0:
                #Estimate the density of the stock using volume-weighed densities of the mixture.
                #This estimate assumes additive volumes, which may be a poor assumption. 
                #It is best to pass an experimentally measured density for the stock solution. 
                self.density = self.volfrac*solute.density+(1-self.volfrac)*solvent.density
            else:
                #If an experimental density is passed, use this value
                self.density = ExpDensity      
            #Calculate mass fraction
            self.massfrac = (self.volfrac*solute.density)/self.density
        elif conc_type == 'massfrac':
            self.massfrac = concentration
            if ExpDensity == 0:
                #Estimate the density of the stock using mass-weighed densities of the mixture.
                #It is best to pass an experimentally measured density for the stock solution. 
                self.density = self.massfrac*solute.density+(1-self.massfrac)*solvent.density
            else:
                #If an experimental density is passed, use this value
                self.density = ExpDensity      
            #Calculate concentration in mg/mL from the volume fraction
            self.mgpermL = self.massfrac*self.density*1000
            #Calculate volume fraction  
            self.volfrac = self.mgpermL/(solute.density*1000)
            #Calculate molarity
            self.molarity = self.massfrac*self.density*1000/solute.mw
        elif conc_type == 'mgpermL':
            self.mgpermL = concentration
            #Calculate volume fraction from the mg per mL concentration
            self.volfrac = self.mgpermL/(solute.density*1000)
            if ExpDensity == 0:
                #Estimate the density of the stock using volume-weighed densities of the mixture.
                #This estimate assumes additive volumes, which may be a poor assumption. 
                #It is best to pass an experimentally measured density for the stock solution. 
                self.density = self.volfrac*solute.density+(1-self.volfrac)*solvent.density
            else:
                #If an experimental density is passed, use this value
                self.density = ExpDensity      
            #Calculate mass fraction
            self.massfrac = (self.volfrac*solute.density)/self.density
            #Calculate solute molarity 
            self.molarity = self.mgpermL/solute.mw 
        elif conc_type == 'molarity':
            self.molarity = concentration
            #Calculate solute concentration in mg per mL 
            self.mgpermL = self.molarity*solute.mw
            #Calculate volume fraction from the mg per mL concentration
            self.volfrac = self.mgpermL/(solute.density*1000)
            if ExpDensity == 0:
                #Estimate the density of the stock using volume-weighed densities of the mixture.
                #This estimate assumes additive volumes, which may be a poor assumption. 
                #It is best to pass an experimentally measured density for the stock solution. 
                self.density = self.volfrac*solute.density+(1-self.volfrac)*solvent.density
            else:
                #If an experimental density is passed, use this value
                self.density = ExpDensity      
            #Calculate mass fraction
            self.massfrac = (self.volfrac*solute.density)/self.density