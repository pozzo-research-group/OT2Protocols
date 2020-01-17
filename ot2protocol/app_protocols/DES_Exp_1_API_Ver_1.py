#Import Dependencies
from opentrons import labware, instruments, robot
################################################################################
#Importing labware
tiprack_300 = labware.load("opentrons-tiprack-300ul", '10') # 300ul tips can be used for P300 and P50 pipettes
tiprack_300_2 = labware.load("opentrons-tiprack-300ul", '11') # Second tiprack
stock = labware.load("trough-12row", '7' ) # 12 well resovoir for stocks
A_96_well= labware.load("96-flat", '8') # Using 4, 96 wellplates labeled A-D
B_96_well= labware.load("96-flat", '9')
C_96_well= labware.load("96-flat", '5')
D_96_well= labware.load("96-flat", '6')
trash = robot.fixed_trash
################################################################################
#Importing pipettes
P300 = instruments.P300_Single(
    mount='left',
    tip_racks=[tiprack_300],
    trash_container=trash
) # Volume range = 30-300uL

P50 = instruments.P50_Single(
    mount='right',
    tip_racks=[tiprack_300_2],
    trash_container=trash
) # Volume range = 5-50uL

################################################################################
#Input volumes to pipette in uL. first list is for QAS and second is for HBD
volumes = [[7.5,15.0,30.000000000000004,45.00000000000001,51.00000000000001,60.0,
75.0,81.0,90.0,99.0,105.0,119.99999999999856,135.0,150.0,165.0,180.0,195.0,
210.0,225.0,240.00000000000003,255.00000005698485,270.0,285.0,292.5],[292.5,
285.0,270.0,254.99999999999997,248.99999999999997,240.0,225.00000000000003,
219.0,210.0,201.0,195.0,180.00000000000142,165.0,150.0,135.0,120.0,105.0,90.0,
75.0,60.0,44.99999994301515,30.0,15.000000000000002,7.500000000000001]]

#Define mixtures to create. A1-A8 are positions on 12 row trough where the stocks are located.
mixtures = np.array([['A1', 'A5'], ['A1', 'A6'], ['A1', 'A7'],['A1', 'A8'], ['A2', 'A5']])

robot.home()

main(mixtures, volumes, [A_96_well, B_96_well, C_96_well, D_96_well], 0)
