# Pseudo-Filesystem 

## File System contents Table Legend:

Each [`TarEntry`](src/api/layerslayer/parser.py:17) field corresponds to tar archive header data:

### Object Info per layer 
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | File/directory path within the layer (e.g., `etc/passwd`) |
| `size` | int | File size in bytes (0 for directories/symlinks) |
| `typeflag` | string | Tar entry type character (see below) |
| `is_dir` | bool | True if directory (typeflag `5` or name ends with `/`) |
| `mode` | string | Unix permission string like `drwxr-xr-x` or `-rw-r--r--` |
| `uid` | int | Owner user ID (often 0 for root) |
| `gid` | int | Owner group ID |
| `mtime` | string | Modification time formatted as `YYYY-MM-DD HH:MM` |
| `linkname` | string | Symlink target path (empty if not a symlink) |
| `is_symlink` | bool | True if symbolic link (typeflag `2`) |

**Typeflag values** (from [`_mode_to_string()`](src/api/layerslayer/parser.py:47)):

| Typeflag | Meaning |
|----------|---------|
| `0` or `\x00` | Regular file |
| `5` | Directory |
| `2` | Symbolic link |
| `1` | Hard link |
| `3` | Character device |
| `4` | Block device |
| `6` | FIFO/pipe |
| `7` | Contiguous file |

---

## Problem Statement 1 - Confusing Name "name"

The name "name" is too ambiguous, and is factually inacurate.

As it is now:

```json
  {
    "name": "app/app.war",
    "size": 33852552,
    "typeflag": "0",
    "is_dir": false,
    "mode": "-rw-r--r--",
    "uid": 0,
    "gid": 0,
    "mtime": "2025-12-15 09:49",
    "linkname": "",
    "is_symlink": false
  }
```

### The way it SHOULD be:

```json
  {
    "layer_object_name": "app.war",  # more concise
    "layer_object_parent_dir": "/app/" # this allows us to better filter the objects that we print at a given time.
    "layer_object_path": "/app/app.war",    # Must be full path to object
    "size": 33852552,
    "typeflag": "0",
    "is_dir": false,
    "mode": "-rw-r--r--",
    "uid": 0,
    "gid": 0,
    "mtime": "2025-12-15 09:49",
    "linkname": "",
    "is_symlink": false
  }
```

## Problem Statement 2 - Object data does not include the layer number from which it was obtained

The app **does not log the layer number** that the data is retrieved from.
 - This means that when the objects are displayed as a unified layers view (AKA peek has been run on each layer and then colletively they can all be printed as one container image)
 - OCI images use overlayfs, which overlays layers atop another, with the higher numbered layers contents' superceding previous layers in the event where there's a conflicy/collision.

 Example of problem: 

 Let's say /home/ubuntu/file.txt contsins "TRUE" on layer 1:

 ```bash
 cat /home/ubuntu/file.txt
 TRUE
 ```
 and then let's also say that on layer 2, the file says "FALSE":

 ```bash
 cat /home/ubuntu/file.txt
 FALSE
 ```

 Print all laters at once would mean that the file only ever displays "FALSE" because it's clobbered.

 ### Suggested Soluition - Both with Style differences
 the insipration prpject, dagdotdev, solves this problem by printing both layers in order, but the layers that have been overruled are represented with a strikethrough. 

 ### Example: (pseudo-code)


 `print_layers(all):`
    ~~/home/ubuntu/file.txt\:TRUE~~
    /home/ubuntu/file.txt\:FALSE

## Probelem Statement 3 - No OS Tracking per layer

If we track the OS of the layer we can construct a "pseudo-filesystem" that emulates the output of directory listings for:

    - Linux `ls -la`
    - windows `dir /w`


running `ls la /`
Because we do not, we currently just print out all file info indiscriminately.


