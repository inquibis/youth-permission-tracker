# Youth Data Editor - Quick Start

## Problem Solved ✓

The youth editor was failing to load data because the API server wasn't running. This is now fixed with:

1. **Fallback data loading**: Can load data directly from `youth_data.json` even without API
2. **Better error messages**: Clear instructions on what to do
3. **Startup helpers**: Scripts to easily start the API

## Quick Start in 3 Steps

### Step 1: Start the API Server

**Option A: PowerShell (Recommended)**
```powershell
./START_API.ps1
```

**Option B: Command Prompt**
```cmd
START_API.bat
```

**Option C: Manual**
```powershell
python run_local.py
```

The API will start on `http://localhost:5000`

### Step 2: Open the Youth Editor

Once the API is running, open in your browser:
```
http://localhost:5000/website/youth_editor.html
```

Or directly (without API, view-only):
```
file:///c:/sandbox/youth-permission-tracker/website/youth_editor.html
```

### Step 3: Search and Edit

1. Enter youth's last name (e.g., "Cahoon") or permission code (e.g., "072709")
2. Click Search
3. Edit the fields (all fields start with "missing" placeholder)
4. Draw signature in canvas
5. Click "Save Changes" (requires API running)

## What Changed

### Updated Files
- ✅ `file_load/youth_editor.html` - Now loads data with fallback
- ✅ `website/youth_editor.html` - Copy with same updates
- ✅ `file_load/youth_data.json` - Copied to website folder
- ✅ `website/youth_data.json` - Now available locally

### New Files
- ✅ `START_API.bat` - Windows batch startup script
- ✅ `START_API.ps1` - PowerShell startup script

### How It Works Now

```
┌─────────────────────────────────────────────┐
│   Youth Editor HTML Opens                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
        Try API first (/api/youth/data)
               │
         ┌─────┴─────┐
         │           │
    API OK?      No API/Error?
         │           │
       YES           ▼
         │      Fallback to
         │      youth_data.json
         │           │
         └─────┬─────┘
               │
               ▼
        Data Loaded ✓
        (Search works)
               │
               ▼
        User edits data
               │
               ▼
        Click Save
               │
         ┌─────┴─────┐
         │           │
     API OK?      No API?
         │           │
       YES           Error message:
         │       "API server required"
         ▼       "Run: python run_local.py"
      Saved! ✓
```

## Features

### ✓ Search (Works without API)
- Last name lookup
- Permission code lookup
- Combined search

### ✓ View Data (Works without API)
- All youth information displayed
- Form fields show current data
- "missing" placeholder for empty fields

### ✗ Save Changes (Requires API)
- Must start API with `python run_local.py`
- Saves to `youth_data.json`
- Captures signatures as base64 images
- Timestamps saved automatically

## Troubleshooting

### "Error loading youth data"
- **Cause**: Neither API nor local file found
- **Fix**: 
  1. Check `file_load/youth_data.json` exists
  2. Check file is in same directory as youth_editor.html
  3. For API: run `python run_local.py`

### Search works but Save fails
- **Cause**: API server not running
- **Fix**: Run `./START_API.ps1` or `python run_local.py`

### Port 5000 already in use
- **Cause**: Another service using the port
- **Fix**: 
  - Find what's using port 5000: `netstat -ano | findstr :5000`
  - Or use different port: `python run_local.py --port 8001`

### "Permission denied" on save
- **Cause**: File locked or not writable
- **Fix**: 
  1. Close other programs editing youth_data.json
  2. Check file permissions
  3. Ensure API process has write access

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| youth_editor.html | website/ | Main editor interface |
| youth_editor.html | file_load/ | Source (backup) |
| youth_data.json | file_load/ | Primary data file |
| youth_data.json | website/ | Copy for local loading |
| START_API.ps1 | root/ | PowerShell startup |
| START_API.bat | root/ | Command prompt startup |

## API Endpoints

These are now available when the API is running:

### GET /api/youth/data
Returns all youth records from `youth_data.json`

### POST /api/youth/save
Saves updated youth data back to `youth_data.json`

## Next Steps

1. **Start API**: `./START_API.ps1`
2. **Open editor**: http://localhost:5000/website/youth_editor.html
3. **Test search**: Find a youth (e.g., "Cahoon")
4. **Edit some data**: Fill in a missing field
5. **Test save**: Click "Save Changes"
6. **Verify**: Search again to confirm data persisted

## Support

If you encounter issues:
1. Check that `python run_local.py` completes without errors
2. Check that API returns data: `http://localhost:5000/api/youth/data`
3. Open browser console (F12) to see detailed error messages
4. Ensure youth_data.json is readable and writable

---

**Ready?** Run `./START_API.ps1` now!
