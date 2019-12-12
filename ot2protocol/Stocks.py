class Stocks:
   def  __init__(self,
        molarity = molarity,
        composition = [],
        density = 1,
        aspiration_rate = 1):
        
        self.aspiration_rate = aspiration_rate # between 0 and 1
        self.molarity = molarity #mol/L
        self.composition = composition
        self.density = density #g/ml

# #Template:
# self = Stocks(
#     molarity = ,
#     composition = ,
#     density = ,
#     aspiration_rate =
# )

oleic_acid_2M = Stocks(
    molarity = 2,
    composition = ["oleic_acid", "ethanol"],
    density = .823,
    aspiration_rate = .8
)

dodecanoic_acid_1_3M = Stocks(
    molarity = 1.3,
    composition = ["dodecanoic_acid", "ethanol"],
    density = .803,
    aspiration_rate = .4
)

octanoic_acid_2M = Stocks(
    molarity = 2,
    composition = ["octanoic_acid", "ethanol"],
    density = .820,
    aspiration_rate = .4
)
