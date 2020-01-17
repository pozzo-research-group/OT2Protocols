def choose_pipette(volume):
    """
    This function decides which pipette to use based on the volume given.
    For this function to work, you have to have P50, P300 defined before
    hand, outside this function.
    """
    values = volume
    if values == float(0):                                  # If volume is 0, well is skipped
        pass
    elif values < float(30):                                # If volume below 30uL, P50 used not P300. Greater than 30uL P300 is used.
        instrument = P50
    else:
        instrument = P300
    return instrument

def destination_well_plate(i, well_plate_list):
    """
    This function checks if you've filled the current well plate and need
    to move to the next one. Function is written to work with 96 well plate.
    For the function to work, i is the count of all the trials.
    """
    try:
        well_number = i // 96
        well_plate = well_plate_list[well_number]
    except ValueError:
          print("You ran out of space in the well plate. You either need to add new\
          well plates, or continue new experiment from where you stopped.")
    return well_plate

def transfer_list_of_volumes(source, starting_well_plate,starting_well_number, volume_list):
    P300list = [source]
    P50list  = [source]
    P300.pick_up_tip()                                          # Picks up pipette tip for both P50 and P300 to allow to alternate
    P50.pick_up_tip()
    for well_counter, values in enumerate(volume_list):
        pipette = choose_pipette(values)
        pipette.transfer(values, stock[source], starting_well_plate(starting_well_number+well_counter).top(0.5), new_tip='never')
        #pipette.touch_tip(starting_well_plate(starting_well_number+well_counter).top(0.5))         # Touches tip to remove any droplets
        pipette.blow_out(starting_well_plate(starting_well_number+well_counter).top(0.5))
    P300.drop_tip()
    P50.drop_tip()
    return len(volume_list)

def main(reagent_pos, reagent_volume, well_plate_list, starting_position):
    i = starting_position
    total_number_of_wells_needed = len(reagent_pos)*len(reagent_volume)
    available_wells = (len(well_plate_list)+1)*96 - i - 1
    if total_number_of_wells_needed > available_wells:
        print("Total number of empty wells needed for carrying out the experiment is {},\
        greater than the available empty wells {}.".format(total_number_of_wells_needed, available_wells))
        print("Either add empty wells or remove some of the combinations out from reagent_pos")
    else:
        for j in range(len(reagent_pos)):
            Q = reagent_pos[j][0]
            H = reagent_pos[j][1]
            starting_well_plate = destination_well_plate(i, well_plate_list)
            starting_well_number = i % 96
            # need another number to go from target well in to ending
            transfer_list_of_volumes(Q, starting_well_plate,starting_well_number, reagent_volume[0])
            moves = transfer_list_of_volumes(H, starting_well_plate,starting_well_number, reagent_volume[1])
            i += moves
    return
