#!/usr/bin/env python
# coding: utf-8

# In[2]:


from opentrons import simulate, execute, protocol_api

def run(protocol:protocol_api, experiment_dict, opentrons_dict, component_volume_lists, mode = 'simulate'):
    api_level = '2.0'
    
    metadata = {
    'protocolName': experiment_dict['Protocol Version'],
    'author': experiment_dict['Experimenter'],
    'description': experiment_dict['Project Tag'],
    'apiLevel': api_level}

    protocol.home()

    # verify if you can just add custom labware into OT2 permanatly 
    sample_plate = protocol.load_labware(opentrons_dict['OT2 Sample Labware'], opentrons_dict['OT2 Sample Labware Slot'])
    stock_plate = protocol.load_labware(opentrons_dict['OT2 Stock Labware'], opentrons_dict['OT2 Stock Labware Slot'])

    right_tiprack = protocol.load_labware(opentrons_dict['OT2 Right Tiprack'], opentrons_dict['OT2 Right Tiprack Slot']) # could call lower pipette
    right_pipette = protocol.load_instrument(opentrons_dict['OT2 Right Pipette'], 'right', tip_racks = [right_tiprack])
    right_pipette.well_bottom_clearance.dispense = opentrons_dict['OT2 Bottom Clearance (mm)'] # make well height on the excel sheet

    left_tiprack = protocol.load_labware(opentrons_dict['OT2 Left Tiprack'], opentrons_dict['OT2 Left Tiprack Slot']) # higher working volume pipette
    left_pipette = protocol.load_instrument(opentrons_dict['OT2 Left Pipette'], 'left', tip_racks = [left_tiprack])
    left_pipette.well_bottom_clearance.dispense = opentrons_dict['OT2 Bottom Clearance (mm)']

    pipette_1 = right_pipette # the number one slot is always reserved for the volume limited case
    tiprack_1 = right_tiprack                          
    pipette_2 = left_pipette
    tiprack_2 = left_tiprack

    for stock_index, component_volume_list in enumerate(component_volume_lists): # with this the right pipette is always the one with the limited volume

        if component_volume_list[0] <= pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_1
            pipette.pick_up_tip(tiprack_1.wells()[stock_index])

        elif component_volume_list[0] > pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_2
            pipette.pick_up_tip(tiprack_2.wells()[stock_index])

        for well_index, volume in enumerate(component_volume_list):
            if volume<pipette_1.max_volume and pipette == pipette_1:
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')

            elif volume>pipette_1.max_volume and pipette == pipette_2:
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')

            elif volume<pipette_1.max_volume and pipette == pipette_2:# switching from p300 to p1000
                pipette.return_tip()
                pipette = pipette_1
                pipette.pick_up_tip(tiprack_1.wells()[stock_index])
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')

            elif volume>pipette_1.max_volume and pipette == pipette_1: # switching from p300 to p1000, since volume not comtpibale with current pipette
                pipette.return_tip()
                pipette = pipette_2
                pipette.pick_up_tip(tiprack_2.wells()[stock_index])
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')
        pipette.drop_tip()
    for line in protocol.commands():
        print(line)
        # try to incorperate the use of pipette.tip_attached

