import pubchempy as pcp
import pandas as pd
import requests
import json


def get_sid_set(sources):
    """
    Compile all the SID's which appear inside the Chemical Vendors or Legacy
    Depositors entries in a pubchem JSON file. From my current understanding
    SID is a unique entry that identifies a product+manufacturer. There should
    be no duplicates. Therefore we assert that this is the case.
    """
    sid_list = []
    for source_dict in sources:
        sid = source_dict['SID']
        sid_list.append(sid)
    sid_set = set(sid_list)

    assert len(sid_set) == len(sid_set), "Duplicate SID detected"
    return sid_set


def get_current_vendors(request_dict):

    categories = request_dict['SourceCategories']['Categories']
    vendor_present = False
    legacy_present = False
    for cat_item in categories:
        category = cat_item['Category']
        sources = cat_item['Sources']
        if category == 'Chemical Vendors':
            vendor_present = True
            vendor_set = get_sid_set(sources)
        elif category == 'Legacy Depositors':
            legacy_present = True
            legacy_set = get_sid_set(sources)

    # Check if at least chemical vendors or legacy depositors is present.
    if vendor_present is False and legacy_present is False:
        return set([])

    current_vendors = vendor_set-legacy_set

    return current_vendors


def vendor_status(dataframe):
    vendor_status = []
    for i, row in dataframe.iterrows():
        cid = str(row['HBA_cid'])
        target_url = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/'\
            'categories/compound/' + cid + '/JSON'
        request = requests.get(target_url)
        request_dict = request.json()
        # At this point you have the target URL and have put it in a
        # dictionary. Now the game is to look at different possible cases, i.e.
        # look at different cid's and find ones which have and don't have
        # vendors. It appears that even if a chemical does not have a vendor,
        # old sources will appear inside the 'Chemical Vendors' dictionary.
        # However, one could filter out non-current sources by checking whether
        # that product also appears in 'Legacy depositors'
        current_vendors = get_current_vendors(request_dict)
        if len(current_vendors) == 0:
            has_current_vendors = False
        else:
            has_current_vendors = True
        vendor_status.append(has_current_vendors)

    dataframe['Vendor Status'] = vendor_status
    return dataframe
