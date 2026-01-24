"""
Generate synthetic analytics data for demo mode.
Creates realistic data with:
- ~100 users
- ~50 organizations
- ~1500 events
- Max 25-30 unique users per county/lender
"""

import json
import random
import uuid
from datetime import datetime, timedelta

# Configuration
NUM_USERS = 100
NUM_EVENTS = 1500
MAX_USERS_PER_ENTITY = 25

# Sample organizations (real NCRC-style orgs)
ORGANIZATIONS = [
    "National Community Reinvestment Coalition",
    "Center for Responsible Lending",
    "National Fair Housing Alliance",
    "Woodstock Institute",
    "California Reinvestment Coalition",
    "New Jersey Citizen Action",
    "Empire Justice Center",
    "Texas Appleseed",
    "National Consumer Law Center",
    "Housing Action Illinois",
    "Metropolitan St. Louis Equal Housing",
    "Fair Housing Center of Greater Boston",
    "Chicago Urban League",
    "National Housing Law Project",
    "PathStone Enterprise Center",
    "Rural Dynamics Inc",
    "NeighborWorks America",
    "Enterprise Community Partners",
    "Local Initiatives Support Corporation",
    "Habitat for Humanity",
    "Urban Institute",
    "Brookings Institution",
    "Annie E. Casey Foundation",
    "Ford Foundation",
    "MacArthur Foundation",
    "University of North Carolina",
    "MIT Urban Planning",
    "Harvard Kennedy School",
    "State Attorney General - California",
    "State Attorney General - New York",
    "State Attorney General - Texas",
    "Federal Reserve Bank - Chicago",
    "Federal Reserve Bank - Philadelphia",
    "FDIC Division of Research",
    "OCC Community Affairs",
    "HUD Office of Fair Housing",
    "CFPB Research Division",
    "Housing Works RI",
    "Florida Housing Coalition",
    "Georgia Advancing Communities Together",
]

# User types
USER_TYPES = ["member", "registered", "institutional", "government", "research", "media", "nonprofit", "other"]
USER_TYPE_WEIGHTS = [25, 20, 15, 10, 10, 5, 10, 5]

# Sample counties with FIPS codes (focusing on major metros and key states)
COUNTIES = [
    ("06037", "Los Angeles County", "CA"),
    ("06073", "San Diego County", "CA"),
    ("06075", "San Francisco County", "CA"),
    ("17031", "Cook County", "IL"),
    ("17043", "DuPage County", "IL"),
    ("36061", "New York County", "NY"),
    ("36047", "Kings County", "NY"),
    ("36081", "Queens County", "NY"),
    ("48201", "Harris County", "TX"),
    ("48113", "Dallas County", "TX"),
    ("48029", "Bexar County", "TX"),
    ("12086", "Miami-Dade County", "FL"),
    ("12011", "Broward County", "FL"),
    ("42101", "Philadelphia County", "PA"),
    ("42003", "Allegheny County", "PA"),
    ("39035", "Cuyahoga County", "OH"),
    ("39049", "Franklin County", "OH"),
    ("39093", "Lorain County", "OH"),
    ("26163", "Wayne County", "MI"),
    ("26125", "Oakland County", "MI"),
    ("24510", "Baltimore City", "MD"),
    ("24033", "Prince George's County", "MD"),
    ("51059", "Fairfax County", "VA"),
    ("11001", "District of Columbia", "DC"),
    ("13121", "Fulton County", "GA"),
    ("37119", "Mecklenburg County", "NC"),
    ("25025", "Suffolk County", "MA"),
    ("04013", "Maricopa County", "AZ"),
    ("32003", "Clark County", "NV"),
    ("53033", "King County", "WA"),
    ("41051", "Multnomah County", "OR"),
    ("08031", "Denver County", "CO"),
    ("27053", "Hennepin County", "MN"),
    ("29510", "St. Louis City", "MO"),
    ("22071", "Orleans Parish", "LA"),
    ("47157", "Shelby County", "TN"),
    ("01073", "Jefferson County", "AL"),
    ("45079", "Richland County", "SC"),
    ("10003", "New Castle County", "DE"),
    ("44007", "Providence County", "RI"),
]

# Sample lenders (real major mortgage lenders)
LENDERS = [
    ("B4TYDEB6GKMZO031MB27", "Wells Fargo"),
    ("HWUPKR0MPOU8FGXBT394", "JPMorgan Chase"),
    ("N6FXHOO1BBYMU7MJEC39", "Bank of America"),
    ("549300HZVNHP1VHFD148", "BMO Harris Bank"),
    ("9DJT3UXIJIZJI4GY2N72", "U.S. Bank"),
    ("G5GSEF7VJP5I7OUK5573", "Truist Financial"),
    ("549300FLJABKVR1JV023", "Pennymac"),
    ("5493008MFLU3MLUOB146", "loanDepot"),
    ("MP6I5ZYZBEU3UZHJUU90", "Rocket Mortgage"),
    ("E57ODZWZ7FF32TWEFA76", "Bank of America"),
    ("549300KRLOX3RL4HJP23", "Freedom Mortgage"),
    ("549300M8ZYFG0OCMTT87", "United Wholesale Mortgage"),
    ("6SHGI4ZSSLCXXQSBB395", "Citibank"),
    ("9DJT3UXIJIZJI4ITSF35", "TD Bank"),
    ("549300GKFG0RYRRQ1414", "Caliber Home Loans"),
    ("I3Q0NC3CTJ0FQPXKR SEW", "NewRez"),
    ("549300MC95COMVN2T123", "Mr. Cooper"),
    ("549300KLKRTF2MCMI852", "PNC Bank"),
    ("GJD4M5ZXDKVL8R3RP123", "Flagstar Bank"),
    ("549300MLKH5XPXOP3424", "Citizens Bank"),
]

# Apps
APPS = [
    "lendsight_report",
    "bizsight_report",
    "branchsight_report",
    "dataexplorer_area_report",
    "dataexplorer_lender_report",
]
APP_WEIGHTS = [35, 20, 15, 20, 10]


def generate_user_id():
    """Generate a Firebase-style user ID."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(chars) for _ in range(28))


def generate_users(num_users):
    """Generate user profiles."""
    users = []
    for i in range(num_users):
        user_type = random.choices(USER_TYPES, weights=USER_TYPE_WEIGHTS)[0]

        # Some users have organizations, some don't
        has_org = random.random() < 0.75
        org = random.choice(ORGANIZATIONS) if has_org else None

        # Some users have emails visible
        has_email = random.random() < 0.6

        user = {
            "user_id": generate_user_id(),
            "user_email": f"user{i+1}@example.org" if has_email else None,
            "user_type": user_type,
            "organization_name": org,
            "state": random.choice([c[2] for c in COUNTIES]),
            "hubspot_contact_id": f"contact_{i+1}" if has_org else None,
            "hubspot_company_id": f"company_{random.randint(100, 999)}" if has_org else None,
        }
        users.append(user)
    return users


def generate_events(users, num_events):
    """Generate events with realistic distribution."""
    events = []
    now = datetime.utcnow()

    # Create user "focus areas" - each user focuses on a few counties/lenders
    user_focus = {}
    for user in users:
        # Each user focuses on 1-4 counties and 1-3 lenders
        num_counties = random.randint(1, 4)
        num_lenders = random.randint(1, 3)
        user_focus[user["user_id"]] = {
            "counties": random.sample(COUNTIES, min(num_counties, len(COUNTIES))),
            "lenders": random.sample(LENDERS, min(num_lenders, len(LENDERS))),
        }

    for _ in range(num_events):
        # Pick a random user
        user = random.choice(users)
        focus = user_focus[user["user_id"]]

        # Pick from their focus areas (80% of time) or random (20%)
        if random.random() < 0.8 and focus["counties"]:
            county = random.choice(focus["counties"])
        else:
            county = random.choice(COUNTIES)

        if random.random() < 0.8 and focus["lenders"]:
            lender = random.choice(focus["lenders"])
        else:
            lender = random.choice(LENDERS)

        # Random timestamp within last 180 days
        days_ago = random.randint(0, 180)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        timestamp = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        # Pick app type
        app = random.choices(APPS, weights=APP_WEIGHTS)[0]

        # Some apps don't have lender data
        include_lender = app in ["lendsight_report", "dataexplorer_lender_report", "bizsight_report"]

        event = {
            "event_id": str(uuid.uuid4()),
            "event_timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "event_name": app,
            "user_id": user["user_id"],
            "user_email": user["user_email"],
            "user_type": user["user_type"],
            "organization_name": user["organization_name"],
            "county_fips": county[0],
            "county_name": county[1],
            "state": county[2],
            "lender_id": lender[0] if include_lender else None,
            "lender_name": lender[1] if include_lender else None,
            "hubspot_contact_id": user["hubspot_contact_id"],
            "hubspot_company_id": user["hubspot_company_id"],
        }
        events.append(event)

    # Sort events by timestamp (newest first)
    events.sort(key=lambda e: e["event_timestamp"], reverse=True)
    return events


def validate_data(users, events):
    """Validate that data meets constraints."""
    # Check max users per county
    county_users = {}
    for event in events:
        fips = event["county_fips"]
        if fips not in county_users:
            county_users[fips] = set()
        county_users[fips].add(event["user_id"])

    max_county_users = max(len(users) for users in county_users.values())
    print(f"Max users per county: {max_county_users}")

    # Check max users per lender
    lender_users = {}
    for event in events:
        if event["lender_id"]:
            lid = event["lender_id"]
            if lid not in lender_users:
                lender_users[lid] = set()
            lender_users[lid].add(event["user_id"])

    max_lender_users = max(len(users) for users in lender_users.values()) if lender_users else 0
    print(f"Max users per lender: {max_lender_users}")

    return max_county_users <= MAX_USERS_PER_ENTITY + 5  # Allow small margin


def main():
    print(f"Generating synthetic data: {NUM_USERS} users, {NUM_EVENTS} events")

    users = generate_users(NUM_USERS)
    events = generate_events(users, NUM_EVENTS)

    # Validate
    if not validate_data(users, events):
        print("Warning: Data exceeds max users per entity constraint")

    # Create output
    data = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "num_users": len(users),
        "num_events": len(events),
        "users": users,
        "events": events,
    }

    # Write to file
    output_path = __file__.replace("generate_synthetic.py", "synthetic_events.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {len(users)} users and {len(events)} events")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
