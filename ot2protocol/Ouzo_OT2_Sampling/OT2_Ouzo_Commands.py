def run(protocol, experiment_dict, sample_volumes, transfer_volume = False, n_transfer_plates = 0):
    """A function which uses a protocol object from the OT2 API V2 module which along with calculated and rearranged volumes will produce commands for the OT2. Additionally, information regarding the wells, slot and labware in use will be returned for use in information storage. Volume argument must be rearranged component wise (i.e. a total of n component lists should be fed). Volumes will be compared to available pipette's volume restriction and will be selected to optimize the number of commands. Returning of pipette tips is built in for when pipettes needs to be switched but will eventually switch back. """
    api_level = '2.0'
    
    metadata = {
    'protocolName': experiment_dict['Protocol Version'],
    'author': experiment_dict['Experimenter'],
    'description': experiment_dict['Project Tag'],
    'apiLevel': api_level}

    protocol.home()

    sample_plate = protocol.load_labware(experiment_dict['OT2 Sample Labware'], experiment_dict['OT2 Sample Labware Slot'])
    sample_plate_rows = [well for row in sample_plate.rows() for well in row] # allows for use of row ordering rather than default column ordering
    
    
    if len(sample_volumes)>len(sample_plate_rows):
        raise ValueError('Too many sample for single sample plate') 
           
    component_volume_lists = [] # reordering sample list into component wise list to iterate over for pipetting
    for i in range(len(sample_volumes[0])): 
        component_volumes = []
        for sample in sample_volumes:
            component_volume = sample[i]
            component_volumes.append(component_volume)
        component_volume_lists.append(component_volumes)
        
    stock_plate = protocol.load_labware(experiment_dict['OT2 Stock Labware'], experiment_dict['OT2 Stock Labware Slot'])
    stock_plate_rows = [well for row in stock_plate.rows() for well in row]
    
    right_tiprack = protocol.load_labware(experiment_dict['OT2 Right Tiprack'], experiment_dict['OT2 Right Tiprack Slot'])     
    right_pipette = protocol.load_instrument(experiment_dict['OT2 Right Pipette'], 'right', tip_racks = [right_tiprack])    
    right_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Clearance (mm)'] 

    left_tiprack = protocol.load_labware(experiment_dict['OT2 Left Tiprack'], experiment_dict['OT2 Left Tiprack Slot']) 
    left_pipette = protocol.load_instrument(experiment_dict['OT2 Left Pipette'], 'left', tip_racks = [left_tiprack])
    left_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Clearance (mm)']

    pipette_1 = left_pipette # the number one slot is always reserved for the volume limited case
    tiprack_1 = left_tiprack 
    pipette_1_tiprack_counter = [] # used to keep track of the number of times specfic tiprack has been used as opposed to just how many times tipracks have been used as currently tiprack position = iteration number of stocks.
    
    pipette_2 = right_pipette
    tiprack_2 = right_tiprack
    pipette_2_tiprack_counter = []
    
    tiprack_1_rows = [well for row in tiprack_1.rows() for well in row] # creating list to grab tip position as not row order natively available
    tiprack_2_rows = [well for row in tiprack_2.rows() for well in row]
  
    info_list = []
    for stock_index, component_volume_list in enumerate(component_volume_lists):
        
        # need to use built in counter to count the number of times going through
        
        if component_volume_list[0] <= pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_1
            if len(pipette_1_tiprack_counter) == 0 : # and the len(counter_2) =
                pipette.pick_up_tip(tiprack_1_rows[0]) # everytime there is a pickup of a tip append it to the counter. 
                pipette_1_tiprack_counter.append(tiprack_1_rows[0])
            else:
                pipette.pick_up_tip(tiprack_1_rows[len(pipette_1_tiprack_counter)])
            
            
        elif component_volume_list[0] > pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_2
            if len(pipette_2_tiprack_counter) == 0 : # so no cause if pipette one already pick up three then will skip
                pipette.pick_up_tip(tiprack_2_rows[0]) # everytime there is a pickup of a tip append it to the counter. 
                pipette_2_tiprack_counter.append(tiprack_2_rows[0])
            else:
                pipette.pick_up_tip(tiprack_2_rows[len(pipette_2_tiprack_counter)])
                pipette_2_tiprack_counter.append(tiprack_2_rows[len(pipette_2_tiprack_counter)])
            
        for well_index, volume in enumerate(component_volume_list):
            info = sample_plate_rows[well_index]
            info_list.append(info)
            if volume<pipette_1.max_volume and pipette == pipette_1:
                pipette.transfer(volume, stock_plate_rows[stock_index], sample_plate_rows[well_index], new_tip = 'never') 

            elif volume>pipette_1.max_volume and pipette == pipette_2:
                pipette.transfer(volume, stock_plate_rows[stock_index], sample_plate_rows[well_index], new_tip = 'never')

            elif volume<pipette_1.max_volume and pipette == pipette_2:
                pipette.return_tip()
                pipette = pipette_1
                pipette.pick_up_tip(tiprack_1_rows[stock_index])
                pipette.transfer(volume, stock_plate_rows[stock_index], sample_plate_rows[well_index], new_tip = 'never')

            elif volume>pipette_1.max_volume and pipette == pipette_1: 
                pipette.return_tip()
                pipette = pipette_2
                pipette.pick_up_tip(tiprack_2_rows[stock_index])
                pipette.transfer(volume, stock_plate_rows[stock_index], sample_plate_rows[well_index], new_tip = 'never')
        pipette.drop_tip()
   
    
    if n_transfer_plates == 1 and transfer_volume is not False:
        transfer_dest1_labware = protocol.load_labware(experiment_dict['OT2 Destination 1 Labware'], experiment_dict['OT2 Destination 1 Slot'])
        transfer_dest1_labware_rows = [well for row in transfer_dest1_labware.rows() for well in row]
        for well_index in range(len(sample_volumes)):
             pipette.transfer(transfer_volume, sample_plate_rows[well_index], transfer_dest1_labware_rows[well_index])
     
#     if transfer_volume == 2:
#         transfer_dest1_labware =  protocol.load_labware(experiment_dict['OT2 Destination 1 Labware'], experiment_dict['OT2 Destination 1 Slot'])
#         transfer_dest2_labware =  protocol.load_labware(experiment_dict['OT2 Destination 2 Labware'], experiment_dict['OT2 Destination 2 Slot'])
        
    
    for line in protocol.commands():
        print(line)
    return info_list