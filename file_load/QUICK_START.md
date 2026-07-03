# Youth Data Import - Quick Start Guide

## Files Created

All files are in `file_load/` directory:

| File | Purpose |
|------|---------|
| `extract_from_pdf.py` | Extract youth data from YM Members.pdf and YW Directory.pdf |
| `load_youth_data.py` | Load youth data into the API |
| `loader_config.py` | Configuration settings (API URL, retry logic, etc.) |
| `youth_data.json` | Youth data file (auto-generated, user-editable) |
| `youth_import_schema.json` | Data schema documentation |
| `loader.log` | Detailed operation log |
| `README.md` | Complete usage documentation |
| `QUICK_START.md` | This file |

## Step-by-Step Usage

### Step 1: Extract Data from PDFs (ALREADY DONE)

Data has been extracted from the PDFs:
- ✓ YM Members.pdf: 19 males extracted
- ✓ YW Directory.pdf: 21 females extracted  
- ✓ youth_data.json: 40 entries created

**Total: 40 youth loaded into youth_data.json**

To re-extract if PDFs change:
```bash
python extract_from_pdf.py
```

### Step 2: Review Extracted Data

Open `youth_data.json` - each entry contains:

**Phase 1 Fields (Extracted):**
- `first_name`, `last_name`, `group`, `gender`, `age`
- `email` (if available in PDF)
- `birth_date` (if available in PDF, ISO format)

**Phase 2 Fields (Placeholder values):**
All entries have these fields set to **"missing"** for you to populate later:
- `permission_code`
- `parent_guardian` (name, phone, email, relationship)
- `medical` (conditions, medications, allergies, dietary_restrictions, limitations, accommodations)
- `emergency_contact` (name, phone)
- `signature` (signed_by, signature_image_base64)
- `signed_at`

Edit "missing" values as you collect the data.

### Step 3: Validate Data (Dry Run)
```bash
python load_youth_data.py --dry-run
```

This validates all 40 entries and shows what would be loaded WITHOUT making changes.

**Output shows:**
- 40 youth entries validated
- Each would be loaded to the API
- No data actually written
- Final summary: 40 loaded, 0 skipped, 0 failed

### Step 4: Load Data into System
```bash
python load_youth_data.py
```

This loads all 40 youth into the system via the API endpoint.

**Prerequisites:**
- API must be running: `python ../api_base/main.py`
- Default API URL: `http://localhost:5000`

**Output shows:**
- Progress for each youth loaded (40 total)
- Summary with success count
- Any errors or duplicates

## Sample Test Data

**40 youth extracted from PDFs:**

Males (19):
- 10 in Priest group (age 16+)
- 9 in Teacher group (age <16)
- Examples: Cole Cahoon (17), Landon Erekson (16), Will Rudder (15)

Females (21):
- All in YW group
- Examples: Paige DeVoe (12), Elisabeth Todd (12), Camille Taylor (14)

## Grouping Rules (Auto-Applied)

The extraction script automatically assigns groups:

```
Males 16+ → Priest
Males <16 → Teacher
Females (any age) → YW
```

Groups can be manually adjusted in `youth_data.json` before loading.

## Configuration

Edit `loader_config.py` to change:
- **API_BASE_URL**: API endpoint (default: http://localhost:5000)
- **DRY_RUN**: Enable dry-run by default (default: False)
- **SKIP_ON_DUPLICATE**: Skip existing usernames (default: True)
- **VERBOSE**: Show detailed progress (default: True)

Or set environment variable:
```bash
export YOUTH_API_URL="http://api.example.com:5000"
python load_youth_data.py
```

## Troubleshooting

### "Cannot connect to API"
```bash
# Make sure API is running:
cd ../api_base
python main.py
```

Then in another terminal:
```bash
cd file_load
python load_youth_data.py
```

### "JSON validation error"
Verify JSON syntax:
```bash
python -m json.tool youth_data.json
```

Fix any missing commas, quotes, or brackets.

### "Duplicate username" errors (re-running)
This is normal and expected. The script skips duplicates by default.

To load new data: edit `youth_data.json` first, then run the loader.

## Log Files

Check `loader.log` for detailed debugging:
```bash
# View entire log
type loader.log

# View last 20 lines
Get-Content loader.log -Tail 20
```

## Next Steps

1. ✅ Run: `python extract_from_pdf.py`
2. ✅ Review: Open `youth_data.json`
3. ✅ Validate: `python load_youth_data.py --dry-run`
4. ✅ Load: `python load_youth_data.py`
5. 📋 Future: Phase 2 - Add medical/permission data

## Need Help?

- **Extraction issues?** Check [README.md](README.md) → Common Issues section
- **API problems?** Ensure API is running and reachable
- **Data questions?** See `youth_import_schema.json` for complete field documentation
- **Loader errors?** Check `loader.log` for detailed messages
