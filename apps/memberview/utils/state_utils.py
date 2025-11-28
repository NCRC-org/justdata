"""
State utilities for mapping abbreviations to full names and getting state centers.
"""

# State abbreviation to full name mapping
# Export this so it can be imported by other modules
STATE_ABBREV_TO_NAME = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}

# Reverse mapping: full name to abbreviation
STATE_NAME_TO_ABBREV = {v: k for k, v in STATE_ABBREV_TO_NAME.items()}

# State center coordinates and zoom levels (approximate)
STATE_CENTERS = {
    'Alabama': {'lat': 32.806671, 'lng': -86.791130, 'zoom': 7},
    'Alaska': {'lat': 61.370716, 'lng': -152.404419, 'zoom': 4},
    'Arizona': {'lat': 33.729759, 'lng': -111.431221, 'zoom': 6},
    'Arkansas': {'lat': 34.969704, 'lng': -92.373123, 'zoom': 7},
    'California': {'lat': 36.116203, 'lng': -119.681564, 'zoom': 6},
    'Colorado': {'lat': 39.059811, 'lng': -105.311104, 'zoom': 6},
    'Connecticut': {'lat': 41.597782, 'lng': -72.755371, 'zoom': 8},
    'Delaware': {'lat': 39.318523, 'lng': -75.507141, 'zoom': 8},
    'District of Columbia': {'lat': 38.9072, 'lng': -77.0369, 'zoom': 11},
    'Florida': {'lat': 27.766279, 'lng': -81.686783, 'zoom': 6},
    'Georgia': {'lat': 33.040619, 'lng': -83.643074, 'zoom': 7},
    'Hawaii': {'lat': 21.094318, 'lng': -157.498337, 'zoom': 7},
    'Idaho': {'lat': 44.240459, 'lng': -114.478828, 'zoom': 6},
    'Illinois': {'lat': 40.349457, 'lng': -88.986137, 'zoom': 7},
    'Indiana': {'lat': 39.849426, 'lng': -86.258278, 'zoom': 7},
    'Iowa': {'lat': 42.011539, 'lng': -93.210526, 'zoom': 7},
    'Kansas': {'lat': 38.526600, 'lng': -96.726486, 'zoom': 7},
    'Kentucky': {'lat': 37.668140, 'lng': -84.670067, 'zoom': 7},
    'Louisiana': {'lat': 31.169546, 'lng': -91.867805, 'zoom': 7},
    'Maine': {'lat': 44.323535, 'lng': -69.765261, 'zoom': 7},
    'Maryland': {'lat': 39.063946, 'lng': -76.802101, 'zoom': 8},
    'Massachusetts': {'lat': 42.230171, 'lng': -71.530106, 'zoom': 8},
    'Michigan': {'lat': 43.326618, 'lng': -84.536095, 'zoom': 6},
    'Minnesota': {'lat': 45.694454, 'lng': -93.900192, 'zoom': 6},
    'Mississippi': {'lat': 32.741646, 'lng': -89.678696, 'zoom': 7},
    'Missouri': {'lat': 38.456085, 'lng': -92.288368, 'zoom': 7},
    'Montana': {'lat': 46.921925, 'lng': -110.454353, 'zoom': 6},
    'Nebraska': {'lat': 41.125370, 'lng': -98.268082, 'zoom': 7},
    'Nevada': {'lat': 38.313515, 'lng': -117.055374, 'zoom': 6},
    'New Hampshire': {'lat': 43.452492, 'lng': -71.563896, 'zoom': 8},
    'New Jersey': {'lat': 40.298904, 'lng': -74.521011, 'zoom': 8},
    'New Mexico': {'lat': 34.840515, 'lng': -106.248482, 'zoom': 6},
    'New York': {'lat': 42.165726, 'lng': -74.948051, 'zoom': 7},
    'North Carolina': {'lat': 35.630066, 'lng': -79.806419, 'zoom': 7},
    'North Dakota': {'lat': 47.528912, 'lng': -99.784012, 'zoom': 7},
    'Ohio': {'lat': 40.388783, 'lng': -82.764915, 'zoom': 7},
    'Oklahoma': {'lat': 35.565342, 'lng': -96.928917, 'zoom': 7},
    'Oregon': {'lat': 44.572021, 'lng': -122.070938, 'zoom': 6},
    'Pennsylvania': {'lat': 40.590752, 'lng': -77.209755, 'zoom': 7},
    'Rhode Island': {'lat': 41.680893, 'lng': -71.51178, 'zoom': 9},
    'South Carolina': {'lat': 33.856892, 'lng': -80.945007, 'zoom': 7},
    'South Dakota': {'lat': 44.299782, 'lng': -99.438828, 'zoom': 7},
    'Tennessee': {'lat': 35.747845, 'lng': -86.692345, 'zoom': 7},
    'Texas': {'lat': 31.054487, 'lng': -97.563461, 'zoom': 6},
    'Utah': {'lat': 40.150032, 'lng': -111.862434, 'zoom': 6},
    'Vermont': {'lat': 44.045876, 'lng': -72.710686, 'zoom': 8},
    'Virginia': {'lat': 37.769337, 'lng': -78.169968, 'zoom': 7},
    'Washington': {'lat': 47.400902, 'lng': -121.490494, 'zoom': 6},
    'West Virginia': {'lat': 38.491226, 'lng': -80.954453, 'zoom': 7},
    'Wisconsin': {'lat': 44.268543, 'lng': -89.616508, 'zoom': 7},
    'Wyoming': {'lat': 42.755966, 'lng': -107.302490, 'zoom': 6},
}


def get_full_state_name(state_input: str) -> str:
    """
    Converts a state abbreviation to its full name, or returns the input if it's already a full name.
    Handles case insensitivity.
    
    Args:
        state_input: State abbreviation or full name
        
    Returns:
        Full state name
    """
    if not state_input:
        return ""
    
    upper_input = state_input.upper()
    
    # If it's an abbreviation, return the full name
    if upper_input in STATE_ABBREV_TO_NAME:
        return STATE_ABBREV_TO_NAME[upper_input]
    
    # If it's a full name, return it as is (title case for consistency)
    for abbr, name in STATE_ABBREV_TO_NAME.items():
        if name.upper() == upper_input:
            return name
            
    return state_input  # Return original if no match


def normalize_state_name(state: str) -> str:
    """
    Convert state abbreviation or mixed case to full proper case name.
    
    Args:
        state: State name or abbreviation
        
    Returns:
        Full state name in proper case
    """
    if not state:
        return ''
    
    state = str(state).strip()
    
    # Check if it's an abbreviation (2 characters)
    if len(state) == 2:
        state_upper = state.upper()
        return STATE_ABBREV_TO_NAME.get(state_upper, state)
    
    # Check if it matches a full name (case-insensitive)
    state_title = state.title()
    if state_title in STATE_NAME_TO_ABBREV:
        return state_title
    
    # Try to find a match (case-insensitive)
    for full_name in STATE_NAME_TO_ABBREV.keys():
        if full_name.lower() == state.lower():
            return full_name
    
    # Return original if no match found
    return state


def get_state_center(state_name: str) -> dict:
    """
    Get center coordinates and zoom level for a state.
    
    Args:
        state_name: Full state name
        
    Returns:
        Dict with 'lat', 'lng', and 'zoom' keys, or None if not found
    """
    normalized = normalize_state_name(state_name)
    return STATE_CENTERS.get(normalized)

