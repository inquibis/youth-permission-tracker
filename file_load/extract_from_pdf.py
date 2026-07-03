"""
PDF Extraction Script for Youth Data
Extracts names, birth dates, and gender from YM Members.pdf and YW Directory.pdf
Applies grouping logic and outputs to youth_data.json with "missing" placeholders for required fields
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Try to import PDF libraries
try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Install with: pip install pdfplumber")
    sys.exit(1)


class YouthExtractor:
    """Extract youth data from PDFs and apply grouping logic."""
    
    def __init__(self):
        self.youth_list: List[Dict[str, Any]] = []
        self.file_load_dir = Path(__file__).parent
        self.extracted_count = 0
        self.skipped_count = 0
    
    def calculate_age_from_birthdate(self, birth_date_str: str) -> Optional[int]:
        """Calculate age from birth date string (flexible format)."""
        if not birth_date_str or not birth_date_str.strip():
            return None
        
        try:
            # Try multiple date formats
            for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    birth_date = datetime.strptime(birth_date_str.strip(), fmt)
                    today = datetime.now()
                    age = today.year - birth_date.year - (
                        (today.month, today.day) < (birth_date.month, birth_date.day)
                    )
                    return age
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def assign_group(self, gender: str, age: Optional[int] = None) -> Optional[str]:
        """
        Assign group based on gender and age.
        Males 16+: Priest
        Males <16: Teacher
        Females: YW
        """
        if not gender:
            return None
            
        gender_lower = gender.strip().lower()
        
        if gender_lower in ('m', 'male'):
            if age is None:
                return "Teacher"  # Default for males with no age
            elif age >= 16:
                return "Priest"
            else:
                return "Teacher"
        elif gender_lower in ('f', 'female', 'w', 'woman'):
            return "YW"
        else:
            return None
    
    def extract_from_ym_members(self):
        """Extract data from YM Members.pdf"""
        pdf_path = self.file_load_dir / "YM Members.pdf"
        
        if not pdf_path.exists():
            print(f"⚠️  {pdf_path.name} not found - skipping")
            return
        
        print(f"\n📖 Extracting from {pdf_path.name}...")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"   Total pages: {len(pdf.pages)}")
                page_count_total = 0
                
                for page_idx, page in enumerate(pdf.pages):
                    print(f"   Page {page_idx + 1}...", end=" ")
                    text = page.extract_text()
                    
                    if text:
                        # Extract all lines with names (format: "LastName, FirstName M Age ...")
                        entries = self._extract_names_from_text(text, gender='M')
                        page_count_total += len(entries)
                        print(f"({len(entries)} entries)")
                    else:
                        print("(no text)")
        
        except Exception as e:
            print(f"ERROR reading {pdf_path.name}: {e}")
    
    def extract_from_yw_directory(self):
        """Extract data from YW Directory.pdf"""
        pdf_path = self.file_load_dir / "YW Directory.pdf"
        
        if not pdf_path.exists():
            print(f"⚠️  {pdf_path.name} not found - skipping")
            return
        
        print(f"\n📖 Extracting from {pdf_path.name}...")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"   Total pages: {len(pdf.pages)}")
                page_count_total = 0
                
                for page_idx, page in enumerate(pdf.pages):
                    print(f"   Page {page_idx + 1}...", end=" ")
                    text = page.extract_text()
                    
                    if text:
                        # Extract all lines with names (format: "LastName, FirstName F Age ...")
                        entries = self._extract_names_from_text(text, gender='F')
                        page_count_total += len(entries)
                        print(f"({len(entries)} entries)")
                    else:
                        print("(no text)")
        
        except Exception as e:
            print(f"ERROR reading {pdf_path.name}: {e}")
    
    def _extract_names_from_text(self, text: str, gender: str) -> List[Dict[str, Any]]:
        """Extract all names from text using regex pattern matching."""
        entries = []
        
        # Pattern: "LastName, FirstName G Age ..." 
        # Example: "Cahoon, Cole M 17 Centerville UT 27ccahoon@go.dsdmail.net"
        name_pattern = r'(\w+),\s+(\w+)\s+([MF])\s+(\d+)'
        
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            match = re.search(name_pattern, line)
            if match:
                last_name = match.group(1).strip()
                first_name = match.group(2).strip()
                entry_gender = match.group(3).strip()
                age = int(match.group(4))
                
                # Skip if gender doesn't match (sometimes data has both M and F on same page)
                if entry_gender != gender:
                    continue
                
                # Assign group
                group = self.assign_group(entry_gender, age)
                if not group:
                    continue
                
                # Create youth entry with "missing" placeholders
                youth_entry = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "group": group,
                    "gender": entry_gender,
                    "age": age,
                    # API Phase 1 fields
                    # API Phase 2 fields (medical submission) - mark as "missing"
                    "permission_code": "missing",
                    "birth_date": "missing",
                    "parent_guardian": {
                        "name": "missing",
                        "phone": "missing",
                        "email": "missing",
                        "relationship": "missing"
                    },
                    "medical": {
                        "conditions": "missing",
                        "medications": "missing",
                        "allergies": "missing",
                        "dietary_restrictions": "missing",
                        "limitations": "missing",
                        "special_accommodations": "missing"
                    },
                    "emergency_contact": {
                        "name": "missing",
                        "phone": "missing"
                    },
                    "signature": {
                        "signed_by": "missing",
                        "signature_image_base64": "missing"
                    },
                    "signed_at": "missing"
                }
                
                # Try to extract email if available
                email_pattern = r'[\w\.-]+@[\w\.-]+'
                email_match = re.search(email_pattern, line)
                if email_match:
                    youth_entry["email"] = email_match.group(0)
                
                # Try to extract birth date if available (date patterns: "21 May 2009", "27 Jul 2009", "1 Dec 2009")
                date_pattern = r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})'
                date_match = re.search(date_pattern, line, re.IGNORECASE)
                if date_match:
                    day = date_match.group(1)
                    month = date_match.group(2)
                    year = date_match.group(3)
                    youth_entry["birth_date"] = f"{year}-{self._month_to_num(month):02d}-{day:0>2}"
                
                self.youth_list.append(youth_entry)
                self.extracted_count += 1
                entries.append(youth_entry)
        
        return entries
    
    @staticmethod
    def _month_to_num(month: str) -> int:
        """Convert month name to number."""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month.lower(), 1)

    
    def save_to_json(self):
        """Save extracted data to youth_data.json."""
        output_path = self.file_load_dir / "youth_data.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.youth_list, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Extraction complete!")
            print(f"   Total youth extracted: {self.extracted_count}")
            print(f"   Entries skipped: {self.skipped_count}")
            print(f"   Saved to: {output_path}")
            
            # Summary statistics
            by_group = {}
            by_gender = {}
            
            for youth in self.youth_list:
                group = youth['group']
                gender = youth['gender']
                by_group[group] = by_group.get(group, 0) + 1
                by_gender[gender] = by_gender.get(gender, 0) + 1
            
            print(f"\n   Summary by group:")
            for group in sorted(by_group.keys()):
                count = by_group[group]
                print(f"     - {group}: {count}")
            
            print(f"\n   Summary by gender:")
            for gender in sorted(by_gender.keys()):
                count = by_gender[gender]
                gender_name = "Male" if gender == "M" else "Female" if gender == "F" else gender
                print(f"     - {gender_name}: {count}")
        
        except Exception as e:
            print(f"ERROR writing JSON: {e}")
            sys.exit(1)
    
    def run(self):
        """Run the extraction process."""
        print("🚀 Starting youth data extraction from PDFs...\n")
        self.extract_from_ym_members()
        self.extract_from_yw_directory()
        
        if self.extracted_count == 0:
            print("\n❌ No youth data extracted. Please check PDF files and structure.")
            sys.exit(1)
        
        self.save_to_json()


if __name__ == "__main__":
    extractor = YouthExtractor()
    extractor.run()
