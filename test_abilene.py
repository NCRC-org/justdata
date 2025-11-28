import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    parent_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
    if parent_env.exists():
        load_dotenv(parent_env, override=False)
    load_dotenv(override=False)
except:
    pass

from apps.dataexplorer.acs_utils import get_household_income_distribution_for_geoids, get_tract_household_distributions_for_geoids
from apps.dataexplorer.mmct_utils import get_average_minority_percentage

geoid = '48441'  # Taylor County, TX (Abilene)

print("Testing Abilene, TX (GEOID5: 48441)")
print("=" * 60)

# Test 1
print("\n1. Household Income Distribution:")
h_data = get_household_income_distribution_for_geoids([geoid])
print(f"   Total Households: {h_data.get('total_households', 0):,}")
print(f"   Metro AMI: ${h_data.get('metro_ami', 0):,.0f}" if h_data.get('metro_ami') else "   Metro AMI: N/A")
dist = h_data.get('household_income_distribution', {})
if dist:
    for k, v in dist.items():
        print(f"   {k}: {v}%")
else:
    print("   No data")

# Test 2
print("\n2. Average Minority %:")
avg_min = get_average_minority_percentage([geoid], [2024])
print(f"   {avg_min:.2f}%")

# Test 3
print("\n3. Tract Income Distribution:")
t_data = get_tract_household_distributions_for_geoids([geoid], avg_min)
tract_inc = t_data.get('tract_income_distribution', {})
if tract_inc:
    for k, v in tract_inc.items():
        print(f"   {k} Tracts: {v}%")
else:
    print("   No data")

# Test 4
print("\n4. Tract Minority Distribution:")
tract_min = t_data.get('tract_minority_distribution', {})
if tract_min:
    for k, v in tract_min.items():
        print(f"   {k} Tracts: {v}%")
else:
    print("   No data")

print("\n" + "=" * 60)
print("Summary:")
print(f"  Dataset 1 (Household Income): {'✓' if dist else '✗'}")
print(f"  Dataset 2 (Tract Income): {'✓' if tract_inc else '✗'}")
print(f"  Dataset 3 (Tract Minority): {'✓' if tract_min else '✗'}")

