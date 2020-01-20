#Class: Components
#Purpose: Ease calling of chemical properties.


class Component:
    """Initialize your components to make calling of chemical properties easier"""
    def __init__(self,mw, density = 1, name = 'unnamed'):
#         Initialize properties of component. If density is unknown will default to 1 g/mL
        self.mw =float(mw)#component molecular weight (g/mol)
        self.density = float(density) #component density at 298.15 K, in g/mL
        self.name = str(name)

water = Component(18.01528,density = 0.997, name = 'water')
ethanol = Component(46.07, density = 0.79,name = 'ethanol')

pfh = Component(338.04, density = 1.67, name = 'pfh')
dlpc = Component(622.845, name = 'dlpc')
dmpc = Component(677.93, name = 'dmpc')
dppc = Component(734.04,name ='dppc')
dspc = Component(790.145, name ='dspc')
dspe_peg2000 = Component(2805.5, name = 'dspe_peg2000')
cholesterol = Component(386.654, name = 'cholesterol')
sodiumdodecylsulfate = Component(288.372, name = 'sodiumdodecylsulfate')
five_cb = Component(249.356, name = 'five_cb')

# oleic_acid = Component(282.47, name ="oleic_acid")
# dodecanoic_acid = Component(200.32,name = "dodecanoic_acid")
# octanoic_acid = Component(144.21, name ="octanoic_acid")
# geranic_acid = Component(168.23, name ="geranic_acid")
# candelilla_wax = Component(name ="candelilla_wax")
# light_mineral_oil = Component(425.363,name = "light_mineral_oil")
# heavy_mineral_oil = Component(452.363,name = "heavy_mineral_oil")