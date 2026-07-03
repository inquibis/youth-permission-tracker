"""
Youth Data Loader Script
Loads youth data from youth_data.json into the system via the /youth API endpoint.
"""

import json
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed. Install with: pip install requests")
    sys.exit(1)

# Import configuration
try:
    from loader_config import (
        API_ENDPOINT_YOUTH,
        DATA_FILE,
        LOG_FILE,
        MAX_RETRIES,
        RETRY_DELAY_SECONDS,
        REQUEST_TIMEOUT_SECONDS,
        BATCH_SIZE,
        SKIP_ON_DUPLICATE,
        SKIP_ON_VALIDATION_ERROR,
        SKIP_ON_API_ERROR,
        VERBOSE,
        DRY_RUN,
        REQUIRED_FIELDS,
        ALLOWED_GROUPS,
        SCHEMA_FILE
    )
except ImportError:
    print("ERROR: loader_config.py not found. Make sure it's in the same directory as this script.")
    sys.exit(1)


class YouthLoader:
    """Load youth data from JSON into the API."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.logger = self._setup_logging()
        self.youth_data: List[Dict[str, Any]] = []
        self.results = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging to file and console."""
        logger = logging.getLogger("YouthLoader")
        logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO if VERBOSE else logging.WARNING)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        # Add handlers
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def load_data_file(self) -> bool:
        """Load youth data from JSON file."""
        self.logger.info(f"Loading data from {DATA_FILE}...")
        
        try:
            if not DATA_FILE.exists():
                self.logger.error(f"Data file not found: {DATA_FILE}")
                return False
            
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                self.youth_data = json.load(f)
            
            if not isinstance(self.youth_data, list):
                self.logger.error("Data file must contain a JSON array of youth objects")
                return False
            
            self.logger.info(f"Loaded {len(self.youth_data)} youth entries")
            return True
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {DATA_FILE}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading data file: {e}")
            return False
    
    def validate_entry(self, entry: Dict[str, Any], index: int) -> bool:
        """Validate a single youth entry."""
        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in entry or not entry[field]:
                self.logger.warning(f"Entry {index}: Missing required field '{field}'")
                return False
        
        # Validate field types
        if not isinstance(entry.get("first_name"), str) or not entry["first_name"].strip():
            self.logger.warning(f"Entry {index}: Invalid first_name (must be non-empty string)")
            return False
        
        if not isinstance(entry.get("last_name"), str) or not entry["last_name"].strip():
            self.logger.warning(f"Entry {index}: Invalid last_name (must be non-empty string)")
            return False
        
        # Validate group
        group = entry.get("group", "").strip()
        if group not in ALLOWED_GROUPS:
            self.logger.warning(
                f"Entry {index}: Invalid group '{group}'. Must be one of: {', '.join(ALLOWED_GROUPS)}"
            )
            return False
        
        return True
    
    def load_youth_via_api(self, first_name: str, last_name: str, group: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Load a single youth entry via API.
        
        Returns:
            (success, user_id, error_message)
        """
        payload = {
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "group": group.strip()
        }
        
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would POST to {API_ENDPOINT_YOUTH} with: {payload}")
            return True, f"{first_name}_{last_name}_DRY_RUN", None
        
        attempt = 0
        last_error = None
        
        while attempt < MAX_RETRIES:
            try:
                response = requests.post(
                    API_ENDPOINT_YOUTH,
                    json=payload,
                    timeout=REQUEST_TIMEOUT_SECONDS
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        user_id = result.get("user_id", f"{first_name}_{last_name}")
                        self.logger.debug(f"Created youth: {user_id}")
                        return True, user_id, None
                    except json.JSONDecodeError:
                        self.logger.debug(f"Created youth (could not parse response ID)")
                        return True, f"{first_name}_{last_name}", None
                
                elif response.status_code == 409:
                    error_msg = "Duplicate username (already exists)"
                    self.logger.warning(f"{first_name} {last_name}: {error_msg}")
                    return False, None, error_msg
                
                else:
                    error_msg = f"API returned {response.status_code}: {response.text[:100]}"
                    last_error = error_msg
                    attempt += 1
                    if attempt < MAX_RETRIES:
                        self.logger.debug(f"Retry {attempt}/{MAX_RETRIES} for {first_name} {last_name}...")
                        time.sleep(RETRY_DELAY_SECONDS)
                    continue
            
            except requests.exceptions.Timeout:
                error_msg = f"API request timeout ({REQUEST_TIMEOUT_SECONDS}s)"
                last_error = error_msg
                attempt += 1
                if attempt < MAX_RETRIES:
                    self.logger.debug(f"Retry {attempt}/{MAX_RETRIES} for {first_name} {last_name}...")
                    time.sleep(RETRY_DELAY_SECONDS)
                continue
            
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Cannot connect to API: {str(e)[:50]}"
                last_error = error_msg
                attempt += 1
                if attempt < MAX_RETRIES:
                    self.logger.debug(f"Retry {attempt}/{MAX_RETRIES} for {first_name} {last_name}...")
                    time.sleep(RETRY_DELAY_SECONDS)
                continue
            
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)[:100]}"
                last_error = error_msg
                break
        
        return False, None, last_error or "Unknown error"
    
    def process_entries(self) -> bool:
        """Process all youth entries."""
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Starting to load {len(self.youth_data)} youth entries")
        self.logger.info(f"{'='*70}\n")
        
        if self.dry_run:
            self.logger.info("🔍 DRY RUN MODE - No data will be written to the API\n")
        
        self.results["total"] = len(self.youth_data)
        
        for idx, entry in enumerate(self.youth_data, 1):
            # Validate entry
            if not self.validate_entry(entry, idx):
                self.results["skipped"] += 1
                if SKIP_ON_VALIDATION_ERROR:
                    self.logger.info(f"[{idx}/{len(self.youth_data)}] SKIPPED: Validation failed")
                    continue
                else:
                    self.logger.error(f"[{idx}/{len(self.youth_data)}] FAILED: Validation failed")
                    self.results["failed"] += 1
                    self.results["errors"].append({
                        "entry": f"{entry.get('first_name')} {entry.get('last_name')}",
                        "error": "Validation failed"
                    })
                    if not SKIP_ON_API_ERROR:
                        return False
                    continue
            
            # Load via API
            first_name = entry.get("first_name", "")
            last_name = entry.get("last_name", "")
            group = entry.get("group", "")
            
            success, user_id, error = self.load_youth_via_api(first_name, last_name, group)
            
            if success:
                self.results["success"] += 1
                self.logger.info(f"[{idx}/{len(self.youth_data)}] ✓ {first_name} {last_name} (ID: {user_id})")
            else:
                # Check if it's a duplicate
                if "Duplicate" in (error or ""):
                    self.results["skipped"] += 1
                    self.logger.info(f"[{idx}/{len(self.youth_data)}] ⊘ {first_name} {last_name} - {error}")
                    if not SKIP_ON_DUPLICATE:
                        return False
                else:
                    self.results["failed"] += 1
                    self.logger.error(f"[{idx}/{len(self.youth_data)}] ✗ {first_name} {last_name} - {error}")
                    self.results["errors"].append({
                        "entry": f"{first_name} {last_name}",
                        "error": error
                    })
                    if not SKIP_ON_API_ERROR:
                        return False
            
            # Progress checkpoint
            if BATCH_SIZE > 0 and idx % BATCH_SIZE == 0:
                self.logger.info(f"   ... progress: {idx}/{len(self.youth_data)} processed")
        
        return True
    
    def print_summary(self):
        """Print summary of loading results."""
        self.logger.info(f"\n{'='*70}")
        self.logger.info("LOADING COMPLETE - SUMMARY")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"Total entries:    {self.results['total']}")
        self.logger.info(f"Loaded:           {self.results['success']}")
        self.logger.info(f"Skipped:          {self.results['skipped']}")
        self.logger.info(f"Failed:           {self.results['failed']}")
        
        if self.results['errors']:
            self.logger.info(f"\nErrors ({len(self.results['errors'])}):")
            for err in self.results['errors'][:10]:  # Show first 10
                self.logger.info(f"  - {err['entry']}: {err['error']}")
            if len(self.results['errors']) > 10:
                self.logger.info(f"  ... and {len(self.results['errors']) - 10} more")
        
        self.logger.info(f"{'='*70}\n")
        
        if self.dry_run:
            self.logger.info("✓ Dry run complete. Data was not written to the API.")
        elif self.results['failed'] == 0:
            self.logger.info("✓ All entries loaded successfully!")
        else:
            self.logger.warning(f"⚠ {self.results['failed']} entries failed. See details above.")
        
        try:
            print(f"\nResults: {self.results['success']} loaded, {self.results['skipped']} skipped, {self.results['failed']} failed")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(f"\nResults: {self.results['success']} loaded, {self.results['skipped']} skipped, {self.results['failed']} failed")
        
        print(f"Log file: {LOG_FILE}")
    
    def run(self) -> bool:
        """Run the complete loading process."""
        try:
            # Load data
            if not self.load_data_file():
                return False
            
            # Check API connectivity (unless dry run)
            if not self.dry_run:
                try:
                    self.logger.info(f"Checking API connectivity to {API_ENDPOINT_YOUTH}...")
                    response = requests.head(API_ENDPOINT_YOUTH.replace("/youth", ""), timeout=5)
                    self.logger.info(f"API is reachable")
                except Exception as e:
                    self.logger.error(f"Cannot reach API: {e}")
                    self.logger.error(f"Make sure the API is running at {API_ENDPOINT_YOUTH.split('/youth')[0]}")
                    return False
            
            # Process entries
            if not self.process_entries():
                return False
            
            # Print summary
            self.print_summary()
            
            return self.results['failed'] == 0
        
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load youth data from JSON into the youth-permission-tracker system"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate data and show what would be loaded without making API calls"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        help="Override API base URL (default: from YOUTH_API_URL env var or http://localhost:5000)"
    )
    
    args = parser.parse_args()
    
    # Override config if needed
    if args.api_url:
        import loader_config
        loader_config.API_BASE_URL = args.api_url
        loader_config.API_ENDPOINT_YOUTH = f"{args.api_url}/youth"
    
    # Run loader
    loader = YouthLoader(dry_run=args.dry_run or DRY_RUN)
    success = loader.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
