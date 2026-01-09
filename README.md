# dockerdorker

With dockerdorker you can quickly and efficiently search docker hub, investigate the results, and carve files from the container's layers, *without* the need to download and build/run the entire container just to get access to the filesystem.

## How it works:

By exploiting the tar.gzip file format's structure it is possible to extract a virtual "filesystem" structure without needing to download more than a few bytes of the file. This process can be repeated per layer, returning the simulated layout of the entire overlay filesystem as a text blob. 

A review of the available files can help the user determine if its worth downloading any part of the container image, and the user can download individual files from a layer's tar.gz file.

The flow described below is the ideal state.

---

## App Usage Flow 

- [x] User starts the application:
```bash
python app.y
```
- [x] Presses Ctrl+P to launch Palette, -> "search"
    - command syntax: "search acme" to search for repositories or namespaces with "acme" in the info
- [x]  [Enumerate TAGS](docs/README-enumerate.md)
    - For each repository, list all available Tags
        - [dockerhub_v2_api.py](app\core\api\dockerhub_v2_api.py) has the methods to use for this
- [x]  Enumerate all CONTAINER Images for a selected TAG
    - For each TAG, enumerate containers
    - There's a 1-to-Many relationship with Tags to Containers
- [ ] Enumerate ALL image layer digests for a container
    - Each Tag can have many container architectures associated
        - with a unique digest for each layer
- [ ] [Peek](@docs\README-enumerate.md) each image layer until you have gathered the filesystem layout / paths for all layers.
- [ ] [Carve](docs\README-carve-file.md) the file out of the SOCI layer image

---

### STYLES 

Please review the [Code Standards](STYLES.MD) before writing any code.

---

### Prior Art / More Info

This technique is leveraged heavily by several projects:
 - dagdotdev https://github.com/jonjohnsonjr/dagdotdev (the real mvp)
 - layerslayer https://github.com/thesavant42/layerslayer
    - This project (docker-dorker) looks to integrate the lessons learned from layerslayer, and add caching, searching, navigation, and reporting.
 - yolosint https://github.com/thesavant42/yolosint
 - targz https://github.com/jonjohnsonjr/targz
  - golang utilities for working with tar.gz bundles.
