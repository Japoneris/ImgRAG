# Structured Navigation with st.navigation()

**Date:** 2026-02-16

## Overview

Updated the Streamlit app to use the modern `st.navigation()` API for better navigation with organized sections and cleaner UI.

## Changes

### Before
- Used default Streamlit page navigation (automatic from file structure)
- Pages appeared in alphabetical/numerical order in sidebar
- No grouping or organization of pages
- App.py contained the home page content directly

### After
- Uses `st.navigation()` with structured sections
- Pages organized into logical groups:
  - **Main**: Home/overview
  - **Search & Browse**: Upload, Search, Hash Search
  - **Database Management**: All management tools
- Cleaner navigation UI with icons
- Home page separated into `pages/00_Home.py`

## Implementation

### New Structure

```python
pg = st.navigation({
    "Main": [
        st.Page("pages/00_Home.py", title="Home", icon="🏠"),
    ],
    "Search & Browse": [
        st.Page("pages/1_Upload.py", title="Upload Images", icon="⬆️"),
        st.Page("pages/2_Search.py", title="Search Images", icon="🔍"),
        st.Page("pages/3_Hash_Search.py", title="Hash Search", icon="#️⃣"),
    ],
    "Database Management": [
        st.Page("pages/4_Index_Management.py", title="Management Hub", icon="⚙️"),
        st.Page("pages/5_Ingest_Images.py", title="Ingest Images", icon="📂"),
        st.Page("pages/6_Rebuild_Index.py", title="Rebuild Index", icon="🔄"),
        st.Page("pages/7_Database_Status.py", title="Database Status", icon="📊"),
        st.Page("pages/8_Remove_Images.py", title="Remove Images", icon="🗑️"),
    ],
})

pg.run()
```

### Page Structure

```
app/
├── app.py (navigation definition)
└── pages/
    ├── 00_Home.py (system status & overview)
    ├── 1_Upload.py
    ├── 2_Search.py
    ├── 3_Hash_Search.py
    ├── 4_Index_Management.py
    ├── 5_Ingest_Images.py
    ├── 6_Rebuild_Index.py
    ├── 7_Database_Status.py
    └── 8_Remove_Images.py
```

## Benefits

1. **Better Organization**: Pages grouped by functionality
2. **Cleaner UI**: Modern navigation with sections and icons
3. **Improved UX**: Users can quickly find related functionality
4. **Maintainability**: Easy to reorganize or add new pages
5. **Consistency**: Icons and titles defined in one central location
6. **Flexibility**: Can easily add more sections or reorder pages

## Navigation Sections

### Main
- **Home**: System overview, status, and welcome page

### Search & Browse
- **Upload Images**: Add new images to database
- **Search Images**: Vector similarity search
- **Hash Search**: Look up images by SHA-256 hash

### Database Management
- **Management Hub**: Central navigation for all management tools
- **Ingest Images**: Batch import from folders or config files
- **Rebuild Index**: Recreate hash→filepath mappings
- **Database Status**: View statistics and coverage analysis
- **Remove Images**: Selectively delete from databases

## Files Modified

- ✨ Created: `app/pages/00_Home.py` (moved content from app.py)
- ✏️ Updated: `app/app.py` (now uses st.navigation())

## Cache Management

The cache reload button remains in the sidebar and is accessible from all pages, allowing users to refresh cached data after CLI updates or index rebuilds.

## Future Enhancements

Potential improvements:
- Add user preferences/settings section
- Add admin/advanced tools section
- Add help/documentation section
- Support dynamic navigation based on user roles
