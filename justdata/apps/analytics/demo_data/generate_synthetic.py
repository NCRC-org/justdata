"""
Generate Synthetic Demo Data for Analytics Dashboard

This script generates realistic-looking demo data for the analytics dashboard
to use when demonstrating features before real data is available.

Run: python generate_synthetic.py
Output: synthetic_events.json
"""

import json
import random
import uuid
from datetime import datetime, timedelta

# Sample organizations (mix of nonprofits, government, research)
ORGANIZATIONS = [
    "National Fair Housing Alliance",
    "Center for Responsible Lending",
    "California Reinvestment Coalition",
    "New Jersey Citizen Action",
    "Woodstock Institute",
    "Community Legal Services",
    "Texas Appleseed",
    "Empire Justice Center",
    "Housing Works RI",
    "Virginia Poverty Law Center",
    "Atlanta Legal Aid Society",
    "Connecticut Fair Housing Center",
    "Chicago Community Loan Fund",
    "PathStone Corporation",
    "Rural Community Assistance Corporation",
    "National Housing Law Project",
    "Local Initiatives Support Corporation",
    "Enterprise Community Partners",
    "NeighborWorks America",
    "Habitat for Humanity International",
    "Urban League of Greater Atlanta",
    "NAACP Legal Defense Fund",
    "Mexican American Legal Defense",
    "Asian Americans Advancing Justice",
    "National Consumer Law Center",
    "Consumer Financial Protection Bureau",
    "Federal Reserve Bank of Boston",
    "Federal Reserve Bank of Chicago",
    "Federal Reserve Bank of Atlanta",
    "Federal Reserve Bank of San Francisco",
    "HUD Office of Fair Housing",
    "State Attorney General - California",
    "State Attorney General - New York",
    "State Attorney General - Illinois",
    "State Attorney General - Texas",
    "University of North Carolina",
    "Georgetown University",
    "New York University",
    "MIT Urban Planning",
    "Harvard Joint Center for Housing",
    "Urban Institute",
    "Brookings Institution",
    "Pew Charitable Trusts",
    "Annie E. Casey Foundation",
    "Ford Foundation",
    "MacArthur Foundation",
    "Robert Wood Johnson Foundation",
    "Bloomberg Philanthropies",
    "JPMorgan Chase Foundation",
    "Bank of America Foundation"
]

# Sample lenders (LEIs and names)
LENDERS = [
    ("549300JMVQZN4WJ9YZ05", "Wells Fargo Bank"),
    ("4YZT6BDMGR1V7BXZPL40", "JPMorgan Chase Bank"),
    ("E57ODZWZ7FF32TWEFA76", "Bank of America"),
    ("549300FR3ML1ZVKVHJ25", "Citibank"),
    ("549300FDUPC4BMLFRD16", "U.S. Bank"),
    ("KB1H1DSPRFMYMCUFXT09", "PNC Bank"),
    ("549300XB0G4SZDXHXB40", "Truist Bank"),
    ("9DJT3UXIJIZJI4WXO774", "TD Bank"),
    ("XRVYKRW9NY0K0DO9Q942", "Capital One"),
    ("5493005JAN9Q48Q19456", "Ally Bank"),
    ("549300HZVNHP1VHFD148", "BMO Harris Bank"),
    ("549300XQTHVQYP6VED59", "Fifth Third Bank"),
    ("549300FLJABKVR1JV036", "KeyBank"),
    ("549300ML4LQTK0XRN838", "Huntington Bank"),
    ("549300NRPBM01EXEAB24", "Regions Bank"),
    ("254900HCQN1UE0E8M596", "M&T Bank"),
    ("549300GL8GCKF2MLXV35", "Citizens Bank"),
    ("549300JEFGR9H5N8I706", "Santander Bank"),
    ("549300EI2V8KNQ8PDW77", "First Republic Bank"),
    ("549300Y1N5KI0R7E5D54", "Signature Bank"),
    ("ANGGYXNX0JLX3X63JN86", "Quicken Loans/Rocket Mortgage"),
    ("549300KA7Z05L6H3Q115", "United Wholesale Mortgage"),
    ("549300XQTHVQYP6VED16", "Freedom Mortgage"),
    ("549300JRMK0JC5Z2SZ34", "loanDepot"),
    ("549300FLJABKVR1JV023", "Pennymac"),
    ("KHCYZHST6J4YNH7HQ875", "NewRez"),
    ("549300HZVNHP1VHFD120", "Mr. Cooper"),
    ("254900M9JBK5VKY72645", "Fairway Independent Mortgage")
]

# US States with populations for weighting
STATES = {
    "CA": 12, "TX": 9, "FL": 7, "NY": 6, "PA": 4, "IL": 4, "OH": 4, "GA": 3,
    "NC": 3, "MI": 3, "NJ": 3, "VA": 3, "WA": 2, "AZ": 2, "MA": 2, "TN": 2,
    "IN": 2, "MO": 2, "MD": 2, "WI": 2, "CO": 2, "MN": 2, "SC": 2, "AL": 1,
    "LA": 1, "KY": 1, "OR": 1, "OK": 1, "CT": 1, "UT": 1, "IA": 1, "NV": 1,
    "AR": 1, "MS": 1, "KS": 1, "NM": 1, "NE": 1, "WV": 1, "ID": 1, "HI": 1,
    "NH": 1, "ME": 1, "MT": 1, "RI": 1, "DE": 1, "SD": 1, "ND": 1, "AK": 1,
    "DC": 2, "VT": 1, "WY": 1
}

# Sample counties by state (FIPS codes and names)
COUNTIES = {
    "CA": [("06037", "Los Angeles County"), ("06073", "San Diego County"), ("06059", "Orange County"), ("06065", "Riverside County"), ("06071", "San Bernardino County"), ("06001", "Alameda County"), ("06085", "Santa Clara County"), ("06075", "San Francisco County")],
    "TX": [("48201", "Harris County"), ("48113", "Dallas County"), ("48029", "Bexar County"), ("48439", "Tarrant County"), ("48453", "Travis County"), ("48141", "El Paso County")],
    "FL": [("12086", "Miami-Dade County"), ("12011", "Broward County"), ("12095", "Orange County"), ("12057", "Hillsborough County"), ("12031", "Duval County"), ("12099", "Palm Beach County")],
    "NY": [("36061", "New York County"), ("36047", "Kings County"), ("36081", "Queens County"), ("36005", "Bronx County"), ("36103", "Suffolk County"), ("36059", "Nassau County")],
    "PA": [("42101", "Philadelphia County"), ("42003", "Allegheny County"), ("42091", "Montgomery County"), ("42017", "Bucks County"), ("42045", "Delaware County")],
    "IL": [("17031", "Cook County"), ("17043", "DuPage County"), ("17089", "Kane County"), ("17097", "Lake County"), ("17197", "Will County")],
    "GA": [("13121", "Fulton County"), ("13089", "DeKalb County"), ("13067", "Cobb County"), ("13135", "Gwinnett County"), ("13063", "Clayton County")],
    "NC": [("37119", "Mecklenburg County"), ("37183", "Wake County"), ("37081", "Guilford County"), ("37063", "Durham County"), ("37067", "Forsyth County")],
    "OH": [("39035", "Cuyahoga County"), ("39049", "Franklin County"), ("39061", "Hamilton County"), ("39093", "Lorain County"), ("39153", "Summit County")],
    "MI": [("26163", "Wayne County"), ("26125", "Oakland County"), ("26099", "Macomb County"), ("26081", "Kent County"), ("26161", "Washtenaw County")],
    "NJ": [("34013", "Essex County"), ("34003", "Bergen County"), ("34023", "Middlesex County"), ("34021", "Mercer County"), ("34005", "Burlington County")],
    "VA": [("51059", "Fairfax County"), ("51760", "Richmond City"), ("51810", "Virginia Beach"), ("51013", "Arlington County"), ("51107", "Loudoun County")],
    "WA": [("53033", "King County"), ("53053", "Pierce County"), ("53061", "Snohomish County"), ("53063", "Spokane County"), ("53011", "Clark County")],
    "AZ": [("04013", "Maricopa County"), ("04019", "Pima County"), ("04005", "Coconino County")],
    "MA": [("25025", "Suffolk County"), ("25017", "Middlesex County"), ("25021", "Norfolk County"), ("25013", "Hampden County")],
    "MD": [("24510", "Baltimore City"), ("24031", "Montgomery County"), ("24033", "Prince George's County"), ("24003", "Anne Arundel County")],
    "DC": [("11001", "District of Columbia")]
}

# Default counties for states not in the detailed list
DEFAULT_COUNTY = ("00000", "County")

# Event types
EVENT_TYPES = [
    "lendsight_report",
    "bizsight_report",
    "branchsight_report",
    "dataexplorer_area_report",
    "dataexplorer_lender_report"
]

# User types
USER_TYPES = ["nonprofit", "government", "research", "media", "other"]


def weighted_choice(items_with_weights):
    """Select item based on weights."""
    items = list(items_with_weights.keys())
    weights = list(items_with_weights.values())
    return random.choices(items, weights=weights, k=1)[0]


def generate_user_id():
    """Generate a realistic-looking Firebase user ID."""
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=28))


def generate_synthetic_data(
    num_users: int = 350,
    num_events: int = 3000,
    days_back: int = 180
):
    """
    Generate synthetic analytics data.

    Args:
        num_users: Number of unique users to generate
        num_events: Total number of events to generate
        days_back: How far back in time to generate events
    """

    # Generate users
    users = []
    for i in range(num_users):
        org = random.choice(ORGANIZATIONS) if random.random() > 0.3 else None
        user_type = random.choice(USER_TYPES)
        state = weighted_choice(STATES)

        user = {
            "user_id": generate_user_id(),
            "user_email": f"user{i+1}@example.org" if random.random() > 0.5 else None,
            "user_type": user_type,
            "organization_name": org,
            "state": state,
            "hubspot_contact_id": f"contact_{i+1}" if org else None,
            "hubspot_company_id": f"company_{hash(org) % 1000}" if org else None
        }
        users.append(user)

    # Generate events
    events = []
    now = datetime.utcnow()

    for _ in range(num_events):
        user = random.choice(users)
        event_type = random.choice(EVENT_TYPES)

        # Get state and county
        state = user["state"]
        if state in COUNTIES:
            county_fips, county_name = random.choice(COUNTIES[state])
        else:
            county_fips, county_name = DEFAULT_COUNTY
            county_name = f"{state} County"

        # Maybe include lender (more likely for lender-related events)
        include_lender = (
            event_type in ["lendsight_report", "dataexplorer_lender_report"]
            or random.random() > 0.7
        )

        lender_id, lender_name = random.choice(LENDERS) if include_lender else (None, None)

        # Generate timestamp (weighted toward recent)
        days_ago = int(random.expovariate(1/30))  # Exponential distribution, mean 30 days
        days_ago = min(days_ago, days_back)
        timestamp = now - timedelta(
            days=days_ago,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        event = {
            "event_id": str(uuid.uuid4()),
            "event_timestamp": timestamp.isoformat() + "Z",
            "event_name": event_type,
            "user_id": user["user_id"],
            "user_email": user["user_email"],
            "user_type": user["user_type"],
            "organization_name": user["organization_name"],
            "county_fips": county_fips,
            "county_name": county_name,
            "state": state,
            "lender_id": lender_id,
            "lender_name": lender_name,
            "hubspot_contact_id": user["hubspot_contact_id"],
            "hubspot_company_id": user["hubspot_company_id"]
        }
        events.append(event)

    # Sort events by timestamp
    events.sort(key=lambda x: x["event_timestamp"], reverse=True)

    return {
        "users": users,
        "events": events,
        "generated_at": now.isoformat() + "Z",
        "config": {
            "num_users": num_users,
            "num_events": num_events,
            "days_back": days_back
        }
    }


def main():
    """Generate and save synthetic data."""
    print("Generating synthetic analytics data...")

    data = generate_synthetic_data(
        num_users=350,
        num_events=3000,
        days_back=180
    )

    output_file = "synthetic_events.json"
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {len(data['users'])} users and {len(data['events'])} events")
    print(f"Saved to {output_file}")

    # Print some stats
    from collections import Counter
    event_types = Counter(e["event_name"] for e in data["events"])
    print("\nEvent breakdown:")
    for event_type, count in event_types.most_common():
        print(f"  {event_type}: {count}")

    states = Counter(e["state"] for e in data["events"])
    print("\nTop 10 states:")
    for state, count in states.most_common(10):
        print(f"  {state}: {count}")


if __name__ == "__main__":
    main()
