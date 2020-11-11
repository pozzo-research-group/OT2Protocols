def create_samples(protocol, experiment_dict, sample_volumes, transfer = False):
    """A function which uses a protocol object from the OT2 API V2 module which along with calculated and rearranged volumes
    will produce commands for the OT2. Additionally, information regarding the wells, slot and labware in use will be returned 
    for use in information storage. Volume argument must be rearranged component wise (i.e. a total of n component lists should be fed). 
    Volumes will be compared to available pipette's volume restriction and will be selected to optimize the number of commands. 
    Returning of pipette tips is built in for when pipettes needs to be switched but will eventually switch back. """
    
    ### Initializing run according to API ###
    
    api_level = '2.0'
    
    metadata = {
    'protocolName': experiment_dict['Protocol Version'],
    'author': experiment_dict['Experimenter'],
    'description': experiment_dict['Project Tag'],
    'apiLevel': api_level}

    protocol.home()

    ### Setting up destination plates (sample plates) ### 
    
    dest_plate_names = experiment_dict['OT2 Destination Labwares']
    dest_plate_slots = experiment_dict['OT2 Destination Labware Slots']
    
    dest_plates = [] # labware objects
    for name, slot in zip(dest_plate_names, dest_plate_slots):
        dest_plate_i = protocol.load_labware(name, slot)
        dest_plates.append(dest_plate_i)
    
    dest_wells_row_order = [] # first order list of wells in order of labwares (row ordering)
    for labware in dest_plates:
        rows = [well for row in labware.rows() for well in row]
        dest_wells_row_order = dest_wells_row_order + rows

    if len(sample_volumes)>len(dest_wells_row_order):
        needed_wells = str(len(sample_volumes) - len(dest_wells_row_order))
        raise ValueError('Too many samples for given destination plates, need ' + needed_wells + ' more wells') 
           
    ### Reordering sample list into component wise list to iterate over for pipetting [[1,2,3],[1,2,3]] => [[1,1], [2,2], [3,3]] ###
    
    stock_volumes_lists = [] 
    for i in range(len(sample_volumes[0])): 
        component_volumes = []
        for sample in sample_volumes:
            component_volume = sample[i]
            component_volumes.append(component_volume)
        stock_volumes_lists.append(component_volumes)
        
    ### Setting up tipracks and pipette labware ### 
    
    right_tiprack_names = experiment_dict['OT2 Right Tipracks']
    right_tiprack_slots = experiment_dict['OT2 Right Tiprack Slots']
    
    left_tiprack_names = experiment_dict['OT2 Left Tipracks']
    left_tiprack_slots = experiment_dict['OT2 Left Tiprack Slots']
    
    right_tipracks = []
    for name, slot in zip(right_tiprack_names, right_tiprack_slots):
        right_tiprack_i = protocol.load_labware(name, slot) 
        right_tipracks.append(right_tiprack_i)
            
    left_tipracks = []
    for name, slot in zip(left_tiprack_names, left_tiprack_slots):
        left_tiprack_i = protocol.load_labware(name, slot)
        left_tipracks.append(left_tiprack_i)

    right_pipette = protocol.load_instrument(experiment_dict['OT2 Right Pipette'], 'right', tip_racks = right_tipracks)    
    right_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Dispensing Clearance (mm)'] 

    left_pipette = protocol.load_instrument(experiment_dict['OT2 Left Pipette'], 'left', tip_racks = left_tipracks)
    left_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Dispensing Clearance (mm)']
    
    ### Deciding pipette ordering for upcoming logic based commands, which require pipette_1 = lower volume constrained pipette ### 
    
    if left_pipette.max_volume < right_pipette.max_volume:
        pipette_1 = left_pipette 
        pipette_2 = right_pipette
        
    if left_pipette.max_volume > right_pipette.max_volume:
        pipette_1 = right_pipette 
        pipette_2 = left_pipette
      
    stock_plate = protocol.load_labware(experiment_dict['OT2 Stock Labware'], experiment_dict['OT2 Stock Labware Slot'])
    stock_plate_rows = [well for row in stock_plate.rows() for well in row]
    
    info_list = []
    for stock_index, stock_volumes in enumerate(stock_volumes_lists):
        if stock_volumes[0] <= pipette_1.max_volume: #initializing pipette for first stock volume in list of stock volumes
            pipette = pipette_1

        elif stock_volumes[0] > pipette_1.max_volume: #initializing pipette with tip for a component
            pipette = pipette_2
        
        pipette.pick_up_tip()
        
        for well_index, volume in enumerate(stock_volumes):
            info = dest_wells_row_order[well_index]
            info_list.append(info)
            if volume<pipette_1.max_volume and pipette == pipette_1:
                pipette.transfer(volume, stock_plate_rows[stock_index], dest_wells_row_order[well_index], new_tip = 'never') 

            elif volume>pipette_1.max_volume and pipette == pipette_2:
                pipette.transfer(volume, stock_plate_rows[stock_index], dest_wells_row_order[well_index], new_tip = 'never')

            elif volume<pipette_1.max_volume and pipette == pipette_2:
                pipette.return_tip()
                pipette = pipette_1
                pipette.pick_up_tip()
                pipette.transfer(volume, stock_plate_rows[stock_index], dest_wells_row_order[well_index], new_tip = 'never')

            elif volume>pipette_1.max_volume and pipette == pipette_1: 
                pipette.return_tip()
                pipette = pipette_2
                pipette.pick_up_tip()
                pipette.transfer(volume, stock_plate_rows[stock_index], dest_wells_row_order[well_index], new_tip = 'never')
        pipette.drop_tip()

    ### Transfer as an optional last step from sample/dest plate to another plate ### 
    
    if transfer == True:
        
        transfer_volume = experiment_dict['OT2 Dependent Transfer Volume (uL)']
        transfer_dest_labware_names = experiment_dict['OT2 Dependent Transfer Dest Labwares']
        transfer_dest_labware_slots = experiment_dict['OT2 Dependent Transfer Dest Slots']

        # Setting up list of trasnfer destination labwares in order to create final row ordered list of labware wells
        transfer_dest_labwares = []
        for name, slot in zip(transfer_dest_labware_names, transfer_dest_labware_slots):
            transfer_dest_labware = protocol.load_labware(name, slot)
            transfer_dest_labwares.append(transfer_dest_labware)
        
        transfer_dest_wells = []
        for dest_labware in transfer_dest_labwares:
            rows = [well for row in dest_labware.rows() for well in row]
            transfer_dest_wells = transfer_dest_wells + rows
            
        if len(transfer_dest_wells) < len(sample_volumes):
            raise ValueError('Not enough wells for final transfer, missing ' + str(len(sample_volumes)-len(transfer_dest_wells)) + ' number of wells')

        if pipette_1.min_volume <= transfer_volume <= pipette_1.max_volume: # allows for best specficity since higher res on volume constrained pipette
            pipette = pipette_1
    
        elif pipette_2.min_volume < transfer_volume < pipette_2.max_volume:
            pipette = pipette_2
        
        for well_index in range(len(sample_volumes)):
            pipette.transfer(transfer_volume, dest_wells_row_order[well_index], transfer_dest_wells[well_index])
                             
    for line in protocol.commands():
        print(line)
    
    return {'command info': info_list} # left as dictionary as will be able to extract more useful information in the future 

def simple_independent_transfer(protocol, experiment_dict):
    """Simple transfer protocol only referenced when wanting to transfer from plate to plate. Functional with list of plates as 
    well as single plate to plates. Remember to restart with different protocol as everything is to be reinitiliazed """
    
        ### Setting up tipracks and pipette labware ### 
    
    right_tiprack_names = experiment_dict['OT2 Right Tipracks']
    right_tiprack_slots = experiment_dict['OT2 Right Tiprack Slots']
    
    left_tiprack_names = experiment_dict['OT2 Left Tipracks']
    left_tiprack_slots = experiment_dict['OT2 Left Tiprack Slots']
    
    right_tipracks = []
    for name, slot in zip(right_tiprack_names, right_tiprack_slots):
        right_tiprack_i = protocol.load_labware(name, slot) 
        right_tipracks.append(right_tiprack_i)
            
    left_tipracks = []
    for name, slot in zip(left_tiprack_names, left_tiprack_slots):
        left_tiprack_i = protocol.load_labware(name, slot)
        left_tipracks.append(left_tiprack_i)

    right_pipette = protocol.load_instrument(experiment_dict['OT2 Right Pipette'], 'right', tip_racks = right_tipracks)    
    right_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Dispensing Clearance (mm)'] 

    left_pipette = protocol.load_instrument(experiment_dict['OT2 Left Pipette'], 'left', tip_racks = left_tipracks)
    left_pipette.well_bottom_clearance.dispense = experiment_dict['OT2 Bottom Dispensing Clearance (mm)']
    
    
    ### Deciding pipette ordering for upcoming logic based commands, which require pipette_1 = lower volume constrained pipette ### 
    
    if left_pipette.max_volume < right_pipette.max_volume:
        pipette_1 = left_pipette 
        pipette_2 = right_pipette
        
    if left_pipette.max_volume > right_pipette.max_volume:
        pipette_1 = right_pipette 
        pipette_2 = left_pipette
    
    transfer_volume = experiment_dict['OT2 Independent Transfer Volume (uL)']
    
    transfer_source_labware_names = experiment_dict['OT2 Independent Transfer Source Labwares']
    transfer_source_labware_slots = experiment_dict['OT2 Independent Transfer Source Slots']
    
    transfer_dest_labware_names = experiment_dict['OT2 Independent Transfer Dest Labwares']
    transfer_dest_labware_slots = experiment_dict['OT2 Independent Transfer Dest Slots']
    
    transfer_source_labwares = []
    for name, slot in zip(transfer_source_labware_names, transfer_source_labware_slots):
        transfer_source_labware = protocol.load_labware(name, slot)
        transfer_source_labwares.append(transfer_source_labware)
    
    transfer_dest_labwares = []
    for name, slot in zip(transfer_dest_labware_names, transfer_dest_labware_slots):
        transfer_dest_labware = protocol.load_labware(name, slot)
        transfer_dest_labwares.append(transfer_dest_labware)
    
    transfer_source_wells = []
    for source_labware in transfer_source_labwares:
        rows = [well for row in source_labware.rows() for well in row]
        transfer_source_wells = transfer_source_wells + rows
    
    transfer_dest_wells = []
    for dest_labware in transfer_dest_labwares:
        rows = [well for row in dest_labware.rows() for well in row]
        transfer_dest_wells = transfer_dest_wells + rows
    
#     transfer_source_labware = protocol.load_labware(experiment_dict['OT2 Transfer Source Labwares'], experiment_dict['OT2 Transfer Source Slot'])
    
    transfer_source_start = experiment_dict['OT2 Independent Transfer Source [Start, Stop]'][0]
    transfer_source_stop = experiment_dict['OT2 Independent Transfer Source [Start, Stop]'][1]

#     transfer_dest_labware = protocol.load_labware(experiment_dict['OT2 Transfer Dest Labwares'], experiment_dict['OT2 Transfer Dest Slot'])
    transfer_dest_start = experiment_dict['OT2 Independent Transfer Dest [Start, Stop]'][0]
    transfer_dest_stop = experiment_dict['OT2 Independent Transfer Dest [Start, Stop]'][1]
    
    if pipette_1.min_volume <= transfer_volume <= pipette_1.max_volume: # allows for best specficity since higher res on volume constrained pipette
        pipette = pipette_1
    
    elif pipette_2.min_volume < transfer_volume < pipette_2.max_volume:
        pipette = pipette_2
    
    else:
        raise ValueError('Transfer volume not appropiate for current pipettes') 
    
    for source, dest in zip(transfer_source_wells[transfer_source_start:transfer_source_stop], transfer_dest_wells[transfer_dest_start:transfer_dest_stop]):
        pipette.transfer(transfer_volume, source, dest)

    for line in protocol.commands():
        print(line)