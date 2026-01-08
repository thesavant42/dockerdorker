## Refactor the layout of the app, update references
1. Refactor the app layout so that it matches the layout described below.

### Root 
- /app.py is in the workspace root still
    - main entry point for the app
### App folder
- /app/ - subdirectory to contain the majority of the application.

#### app/database/    
- /app/database/ - TODO: Migrate DB code from `app\modules\carve\src`
- TODO" FIX src/ and database sharing: a copy of `app\modules\carve\src` needed to be in this directory so that `app\modules\carve\carve-file-from-layer.py` could run at all; 
    - `app\modules\carve\src` needs to be refactored for shared database among *all* modules.

## MODULES: app\modules\

### (dockerhub) Search
- `app\modules\search\search-docker-hub.py` 
- returns a list of repositories, based on a keyword. 
- sorts newest first, these then feed into the "enumeration modules".

## app\modules\enumerate
- list repository tags
- list repository tags' associated container layers list, displays layer's sha256 digest
    - this feeds into the file carving module

### app\modules\list
- once we have layer digest info, we can list the files in the layer, for every layer.
    - this is used to download copies of files
    - used to construct simulated terminal layout to view files/filesystem info

### app\modules\carve
- `app\modules\carve\carve-file-from-layer.py`
- This module extracts files from SOCI layer files        
    - More info: `app\modules\carve\README-carve-file.md`
- TODO: Give saved files their own subfolders

## Simulated Terminal 
- `plans\to-do\plan-pseudo-tty-filesystem-formatting\virtualtermnal.md`
- `plans\to-do\plan-pseudo-tty-filesystem-formatting\screenshots`
    - screen shots of the desired output of the file listing
- `plans\to-do\plan-pseudo-tty-filesystem-formatting\raw-text-output\krafton-jungle.files.txt`
    - Raw output from `app\modules\search\search-docker-hub.py`