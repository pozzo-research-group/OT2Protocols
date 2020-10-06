def run(protocol, experiment_dict, component_volume_lists):
    """A function which uses a protocol object from the OT2 API V2 module which along with calculated and rearranged volumes will
    produce commands for the OT2. Additionally, information regarding the wells, slot and labware in use will be returned for use in information storage. Volume argument must be rearranged component wise (i.e. a total of n component lists should be fed). Volumes will be compared to available pipette's volume restriction and will be selected to optimize the number of commands. Returning of pipette tips is built in for when pipettes needs to be switched but will eventually switch back. """
    api_level = '2.0'
    
    metadata = {
    'protocolName': experiment_dict['Protocol Version'],
    'author': experiment_dict['Experimenter'],
    'description': experiment_dict['Project Tag'],
    'apiLevel': api_level}

    protocol.home()

    sample_plate = protocol.load_labware(experiment_dict['OT2 Sample Labware'], experiment_dict['OT2 Sample Labware Slot'])
    stock_plate = protocol.load_labware(experiment_dict['OT2 Stock Labware'], experiment_dict['OT2 Stock Labware Slot'])

    right_tiprack = protocol.load_labware(experiment_dict['OT2 Right Tiprack'], experiment_dict['OT2 Right Tiprack Slot']) 
    right_pipette = protocol.load_instrument(experiment_dict['OT2 Right Pipette'], 'right', tip_racks = [right_tiprack])
    right_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Clearance (mm)'] 

    left_tiprack = protocol.load_labware(experiment_dict['OT2 Left Tiprack'], experiment_dict['OT2 Left Tiprack Slot']) # higher working volume pipette
    left_pipette = protocol.load_instrument(experiment_dict['OT2 Left Pipette'], 'left', tip_racks = [left_tiprack])
    left_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Clearance (mm)']

    pipette_1 = right_pipette # the number one slot is always reserved for the volume limited case
    tiprack_1 = right_tiprack                          
    pipette_2 = left_pipette
    tiprack_2 = left_tiprack

    info_list = []
    for stock_index, component_volume_list in enumerate(component_volume_lists): 
        if component_volume_list[0] <= pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_1
            pipette.pick_up_tip(tiprack_1.wells()[stock_index])

        elif component_volume_list[0] > pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_2
            pipette.pick_up_tip(tiprack_2.wells()[stock_index])

        for well_index, volume in enumerate(component_volume_list):
            info = sample_plate.wells()[well_index]
            info_list.append(info)
            if volume<pipette_1.max_volume and pipette == pipette_1:
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never') 

            elif volume>pipette_1.max_volume and pipette == pipette_2:
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')

            elif volume<pipette_1.max_volume and pipette == pipette_2:
                pipette.return_tip()
                pipette = pipette_1
                pipette.pick_up_tip(tiprack_1.wells()[stock_index])
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')

            elif volume>pipette_1.max_volume and pipette == pipette_1: 
                pipette.return_tip()
                pipette = pipette_2
                pipette.pick_up_tip(tiprack_2.wells()[stock_index])
                pipette.transfer(volume, stock_plate.wells()[stock_index], sample_plate.wells()[well_index], new_tip = 'never')
        pipette.drop_tip()
    for line in protocol.commands():
        print(line)
    return info_list