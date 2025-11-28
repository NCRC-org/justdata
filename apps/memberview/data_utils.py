"""
Data utilities for loading and processing HubSpot member data.
Handles loading companies, contacts, and deals, and creating unified member views.
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import json

logger = logging.getLogger(__name__)


class MemberDataLoader:
    """Loads and processes HubSpot data for MemberView."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize data loader.
        
        Args:
            data_dir: Path to HubSpot data directory. If None, uses default location.
        """
        if data_dir is None:
            # Use C:\DREAM symbolic link to avoid apostrophe issues
            self.data_dir = Path(r"C:\DREAM") / "HubSpot" / "data"
        else:
            self.data_dir = Path(data_dir)
        
        self.companies_file = self.data_dir / "raw" / "hubspot-crm-exports-all-companies-2025-11-14.csv"
        self.contacts_file = self.data_dir / "processed" / "20251114_123115_all-contacts_processed.parquet"
        self.deals_file = self.data_dir / "processed" / "20251114_123117_all-deals_processed.parquet"
        
        self._companies_df = None
        self._contacts_df = None
        self._deals_df = None
        self._members_df = None  # Cache for filtered members
        
        # ProPublica client for Form 990 data (lazy loaded)
        self._propublica_client = None
        
        # Cache for Form 990 data (store in HubSpot data directory)
        self._form_990_cache_file = self.data_dir / "form_990_cache.json"
        self._form_990_cache = self._load_form_990_cache()
    
    def load_companies(self) -> pd.DataFrame:
        """Load companies data."""
        if self._companies_df is not None:
            return self._companies_df
        
        if not self.companies_file.exists():
            raise FileNotFoundError(f"Companies file not found: {self.companies_file}")
        
        logger.info(f"Loading companies from {self.companies_file}")
        # Use dtype=str to speed up loading and avoid type inference
        df = pd.read_csv(self.companies_file, dtype=str, low_memory=False)
        
        # Standardize column names
        df.columns = df.columns.str.strip()
        
        # Convert Record ID to string for consistent joining
        record_id_col = None
        for col in df.columns:
            if 'record id' in col.lower():
                record_id_col = col
                break
        
        if record_id_col:
            df[record_id_col] = df[record_id_col].str.strip()
        
        self._companies_df = df
        return df
    
    def load_contacts(self) -> pd.DataFrame:
        """Load contacts data."""
        if self._contacts_df is not None:
            return self._contacts_df
        
        if not self.contacts_file.exists():
            raise FileNotFoundError(f"Contacts file not found: {self.contacts_file}")
        
        logger.info(f"Loading contacts from {self.contacts_file}")
        df = pd.read_parquet(self.contacts_file)
        
        # Convert company ID to string for consistent joining
        company_id_cols = [c for c in df.columns if 'company' in c.lower() and 'id' in c.lower()]
        for col in company_id_cols:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        self._contacts_df = df
        return df
    
    def load_deals(self) -> pd.DataFrame:
        """Load deals data."""
        if self._deals_df is not None:
            return self._deals_df
        
        if not self.deals_file.exists():
            raise FileNotFoundError(f"Deals file not found: {self.deals_file}")
        
        logger.info(f"Loading deals from {self.deals_file}")
        df = pd.read_parquet(self.deals_file)
        
        # Convert company ID to string for consistent joining
        company_id_cols = [c for c in df.columns if 'company' in c.lower() and ('id' in c.lower() or 'primary' in c.lower())]
        for col in company_id_cols:
            df[col] = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        self._deals_df = df
        return df
    
    def get_members(self, status_filter: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get member companies filtered by status.
        Uses caching to avoid reprocessing on every call.
        
        Args:
            status_filter: List of statuses to include (e.g., ['CURRENT', 'GRACE PERIOD', 'LAPSED'])
                          If None, returns all members.
        
        Returns:
            DataFrame of member companies
        """
        # Load base members (cached)
        if self._members_df is None:
            companies = self.load_companies()
            
            # Find membership status column
            status_col = None
            for col in companies.columns:
                if 'membership' in col.lower() and 'status' in col.lower():
                    status_col = col
                    break
            
            if not status_col:
                logger.warning("Could not find membership status column")
                self._members_df = companies
            else:
                # Filter to members only (case-insensitive regex is faster than isin for large datasets)
                self._members_df = companies[
                    companies[status_col].astype(str).str.upper().str.contains('CURRENT|ACTIVE|GRACE|LAPSED', na=False, regex=True)
                ].copy()
                logger.info(f"Cached {len(self._members_df)} members")
        
        # Apply status filter if provided (this is fast since we're filtering a smaller dataset)
        if status_filter:
            status_col = None
            for col in self._members_df.columns:
                if 'membership' in col.lower() and 'status' in col.lower():
                    status_col = col
                    break
            
            if status_col:
                status_filter_upper = [s.upper() for s in status_filter]
                return self._members_df[
                    self._members_df[status_col].astype(str).str.upper().isin(status_filter_upper)
                ].copy()
        
        return self._members_df.copy()
    
    def get_member_with_contacts(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Get contacts associated with a company.
        
        Args:
            company_id: Company record ID
        
        Returns:
            List of contact dictionaries
        """
        contacts = self.load_contacts()
        
        # Find company association column
        company_col = None
        for col in contacts.columns:
            if 'primary_associated_company_id' in col.lower():
                company_col = col
                break
            elif 'associated_company' in col.lower() and 'id' in col.lower():
                company_col = col
                break
        
        if not company_col:
            return []
        
        # Filter contacts
        company_id_str = str(company_id).replace('.0', '').strip()
        member_contacts = contacts[contacts[company_col] == company_id_str].copy()
        
        # Convert to list of dicts
        contact_list = []
        for _, row in member_contacts.iterrows():
            # Find email column
            email_col = None
            for col in row.index:
                if col.lower() == 'email':
                    email_col = col
                    break
            
            # Find name columns
            first_name_col = None
            last_name_col = None
            for col in row.index:
                col_lower = col.lower()
                if 'first' in col_lower and 'name' in col_lower:
                    first_name_col = col
                elif 'last' in col_lower and 'name' in col_lower:
                    last_name_col = col
            
            # Find phone column
            phone_col = None
            for col in row.index:
                if 'phone' in col.lower():
                    phone_col = col
                    break
            
            email = str(row.get(email_col, '')).strip() if email_col and pd.notna(row.get(email_col)) else ''
            first_name = str(row.get(first_name_col, '')).strip() if first_name_col and pd.notna(row.get(first_name_col)) else ''
            last_name = str(row.get(last_name_col, '')).strip() if last_name_col and pd.notna(row.get(last_name_col)) else ''
            phone = str(row.get(phone_col, '')).strip() if phone_col and pd.notna(row.get(phone_col)) else ''
            
            contact_dict = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
            }
            contact_list.append(contact_dict)
        
        return contact_list
    
    def get_member_deals(self, company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get deals associated with a company.
        
        Args:
            company_id: Company record ID
            limit: Maximum number of deals to return
        
        Returns:
            List of deal dictionaries, sorted by close date (most recent first)
        """
        deals = self.load_deals()
        
        # Find company association column
        company_col = None
        exact_patterns = [
            'associated_company_ids_(primary)',
            'Associated Company IDs (Primary)',
        ]
        
        for pattern in exact_patterns:
            if pattern in deals.columns:
                company_col = pattern
                break
        
        if not company_col:
            for col in deals.columns:
                col_lower = col.lower()
                if ('associated company' in col_lower or 'company id' in col_lower) and ('primary' in col_lower or 'ids' in col_lower):
                    company_col = col
                    break
        
        if not company_col:
            return []
        
        # Filter deals
        company_id_str = str(company_id).replace('.0', '').strip()
        member_deals = deals[deals[company_col] == company_id_str].copy()
        
        # Sort by close date (most recent first)
        close_date_col = None
        for col in member_deals.columns:
            if 'close' in col.lower() and 'date' in col.lower():
                close_date_col = col
                break
        
        if close_date_col:
            member_deals = member_deals.sort_values(close_date_col, ascending=False, na_position='last')
        
        # Convert to list of dicts
        deal_list = []
        for _, row in member_deals.head(limit).iterrows():
            # Find amount column
            amount_col = None
            for col in row.index:
                if col.lower() == 'amount' or ('amount' in col.lower() and 'currency' in col.lower()):
                    amount_col = col
                    break
            
            # Get values and handle NaN
            deal_name = row.get('dealname', row.get('deal_name', ''))
            if pd.isna(deal_name):
                deal_name = ''
            
            deal_amount = row.get(amount_col, 0) if amount_col else 0
            if pd.isna(deal_amount) or (isinstance(deal_amount, float) and (deal_amount != deal_amount)):  # NaN check
                deal_amount = 0
            
            deal_stage = row.get('dealstage', row.get('deal_stage', ''))
            if pd.isna(deal_stage):
                deal_stage = ''
            
            close_date = row.get(close_date_col, '') if close_date_col else ''
            if pd.isna(close_date):
                close_date = ''
            
            deal_dict = {
                'name': str(deal_name),
                'amount': float(deal_amount) if isinstance(deal_amount, (int, float)) and deal_amount == deal_amount else 0,
                'stage': str(deal_stage),
                'close_date': str(close_date),
            }
            deal_list.append(deal_dict)
        
        return deal_list
    
    def _get_propublica_client(self):
        """Get or create ProPublica client instance."""
        if self._propublica_client is None:
            try:
                from utils.propublica_client import ProPublicaClient
                self._propublica_client = ProPublicaClient(rate_limit_delay=0.5)
            except ImportError:
                logger.warning("ProPublica client not available - Form 990 data will not be loaded")
                return None
        return self._propublica_client
    
    def _load_form_990_cache(self) -> Dict[str, Any]:
        """Load Form 990 data cache from file."""
        if self._form_990_cache_file.exists():
            try:
                with open(self._form_990_cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load Form 990 cache: {e}")
        return {}
    
    def _save_form_990_cache(self):
        """Save Form 990 data cache to file."""
        try:
            self._form_990_cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._form_990_cache_file, 'w') as f:
                json.dump(self._form_990_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save Form 990 cache: {e}")
    
    def get_form_990_data(self, company_name: str, city: Optional[str] = None, 
                          state: Optional[str] = None, ein: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get Form 990 data for a member company.
        Uses cache to avoid repeated API calls.
        
        Args:
            company_name: Company name
            city: Optional city
            state: Optional state
            ein: Optional EIN (if available)
        
        Returns:
            Dictionary with Form 990 data or None
        """
        # Create cache key
        cache_key = f"{company_name}|{city or ''}|{state or ''}|{ein or ''}".lower()
        
        # Check cache first
        if cache_key in self._form_990_cache:
            cached_data = self._form_990_cache[cache_key]
            if cached_data.get('found'):
                return cached_data
            # If cached as not found, return None (don't retry)
            return None
        
        # Get ProPublica client
        client = self._get_propublica_client()
        if not client:
            return None
        
        # Try to enrich with Form 990 data
        try:
            enriched = client.enrich_member_with_form_990(
                company_name=company_name,
                state=state,
                city=city,
                ein=ein
            )
            
            # Cache result (even if not found)
            self._form_990_cache[cache_key] = enriched
            self._save_form_990_cache()
            
            if enriched.get('found'):
                return enriched
        except Exception as e:
            logger.warning(f"Error getting Form 990 data for {company_name}: {e}")
            # Cache as not found to avoid retrying
            self._form_990_cache[cache_key] = {'found': False}
            self._save_form_990_cache()
        
        return None
    
    def load_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """
        Load pre-geocoded coordinates from file.
        
        Returns:
            Dictionary mapping "city|state" to (lat, lng) tuple
        """
        import json
        
        coords_file = self.data_dir.parent.parent / "data" / "member_coordinates.json"
        
        if coords_file.exists():
            try:
                with open(coords_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load coordinates: {e}")
        
        return {}
    
    def save_coordinates(self, coordinates: Dict[str, Any]):
        """Save coordinates cache to file."""
        import json
        from pathlib import Path
        
        coords_file = self.data_dir.parent.parent / "data" / "member_coordinates.json"
        coords_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(coords_file, 'w') as f:
                json.dump(coordinates, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save coordinates: {e}")
    
    def create_member_summary(self, company_id: str) -> Dict[str, Any]:
        """
        Create a summary view of a member with all associated data.
        
        Args:
            company_id: Company record ID
        
        Returns:
            Dictionary with member summary data
        """
        companies = self.load_companies()
        
        # Find company
        record_id_col = None
        for col in companies.columns:
            if 'record id' in col.lower():
                record_id_col = col
                break
        
        if not record_id_col:
            return {}
        
        company_id_str = str(company_id).replace('.0', '').strip()
        company_row = companies[companies[record_id_col] == company_id_str]
        
        if len(company_row) == 0:
            return {}
        
        company_row = company_row.iloc[0]
        
        # Get company name
        name_col = None
        for col in companies.columns:
            if 'company' in col.lower() and 'name' in col.lower():
                name_col = col
                break
        
        # Get status
        status_col = None
        for col in companies.columns:
            if 'membership' in col.lower() and 'status' in col.lower():
                status_col = col
                break
        
        # Get location fields
        city_col = None
        state_col = None
        for col in companies.columns:
            col_lower = col.lower()
            if col_lower == 'city':
                city_col = col
            elif ('state' in col_lower or 'region' in col_lower) and 'country' not in col_lower:
                if not state_col:  # Only set if not already found
                    state_col = col
        
        # Get contacts and deals
        contacts = self.get_member_with_contacts(company_id_str)
        deals = self.get_member_deals(company_id_str, limit=100)
        
        # Calculate totals
        total_deal_amount = sum(d.get('amount', 0) for d in deals if isinstance(d.get('amount'), (int, float)))
        
        # Get last deal
        last_deal = deals[0] if deals else None
        
        # Get company info
        company_name = company_row.get(name_col, '') if name_col else ''
        city = company_row.get(city_col, '') if city_col else ''
        state = company_row.get(state_col, '') if state_col else ''
        
        # Get Form 990 data (if available) - DISABLED
        form_990_data = None
        # if company_name:
        #     form_990_data = self.get_form_990_data(
        #         company_name=company_name,
        #         city=city if city else None,
        #         state=state if state else None
        #     )
        
        summary = {
            'id': company_id_str,
            'name': company_name,
            'status': company_row.get(status_col, '') if status_col else '',
            'city': city,
            'state': state,
            'create_date': company_row.get('Create Date', ''),
            'last_activity_date': company_row.get('Last Activity Date', ''),
            'phone': company_row.get('Phone Number', ''),
            'contacts_count': len(contacts),
            'deals_count': len(deals),
            'total_deal_amount': total_deal_amount,
            'last_deal': last_deal,
            'contacts': contacts[:10],  # Limit to 10 contacts for display
            'form_990': form_990_data,  # Include Form 990 data if found
        }
        
        return summary

