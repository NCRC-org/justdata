#!/usr/bin/env python3
"""
Patch script to add individual financial contributions to weekly_update.py

Run this script once to update the weekly_update.py file:
    python patch_weekly_update.py

This adds calls to:
1. fetch_financial_pac_data() - PAC contributions from financial sector
2. fetch_individual_financial_contributions() - Personal contributions from financial execs
"""

import re
from pathlib import Path

def patch_weekly_update():
    weekly_update_path = Path(__file__).parent / 'weekly_update.py'

    if not weekly_update_path.exists():
        print(f"Error: {weekly_update_path} not found")
        return False

    content = weekly_update_path.read_text(encoding='utf-8')

    # Check if already patched
    if 'fetch_individual_financial_contributions' in content and 'self.fetch_individual_financial_contributions()' in content:
        print("Already patched!")
        return True

    # Find and update fetch_all_data method
    old_pattern = r'(self\.fetch_fec_data\(\))\s*\n(\s*def fetch_all_congress_members)'
    new_replacement = r'''\1  # Aggregate FEC data + committee IDs

        # Financial sector deep dive
        self.fetch_financial_pac_data()  # PAC contributions from financial sector
        self.fetch_individual_financial_contributions()  # Personal money from financial execs

\2'''

    new_content, count = re.subn(old_pattern, new_replacement, content)

    if count == 0:
        print("Could not find pattern to patch. Manual update needed.")
        print("\nAdd these lines after 'self.fetch_fec_data()' in fetch_all_data():")
        print("        self.fetch_financial_pac_data()")
        print("        self.fetch_individual_financial_contributions()")
        return False

    # Add import for individual contributions module if fetch method not present
    if 'def fetch_individual_financial_contributions(self):' not in new_content:
        # Add a wrapper method that calls the external module
        wrapper_method = '''
    def fetch_individual_financial_contributions(self):
        """Fetch individual contributions from financial sector executives."""
        try:
            from justdata.apps.electwatch.services.individual_contributions import enrich_officials_with_individual_contributions
            status = enrich_officials_with_individual_contributions(self.officials_data)
            self.source_status['individual_financial'] = status
        except Exception as e:
            logger.error(f"Individual financial contributions fetch failed: {e}")
            self.source_status['individual_financial'] = {'status': 'failed', 'error': str(e)}

'''
        # Find position to insert (after fetch_financial_pac_data method)
        pac_method_end = new_content.find('def fetch_congress_data(self):')
        if pac_method_end > 0:
            new_content = new_content[:pac_method_end] + wrapper_method + new_content[pac_method_end:]
        else:
            print("Could not find insertion point for wrapper method")

    weekly_update_path.write_text(new_content, encoding='utf-8')
    print(f"Successfully patched {weekly_update_path}")
    return True


if __name__ == '__main__':
    patch_weekly_update()
