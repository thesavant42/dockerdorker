# dockerdorker

With dockerdorker you can quickly and efficiently search docker hub, investigate the results, and carve files from the container's layers, *without* the need to download and build/run the entire container just to get access to the filesystem.

## How it works:

 - By exploiting the tar.gzip file format's structure it is possible to extract a virtual "filesystem" structure without needing to download more than a few bytes of the file. This process can be repeated per layer, returning the simulated layout of the entire overlay filesystem as a text blob. 

- A review of the available files can help the user determine if its worth downloading any part of the container image, and the user can download individual files from a layer's tar.gz file.

The flow described below is the ideal state.

---

## App Usage Flow 

- [x] User starts the application: `python app.y`
- [x] Presses Ctrl+P to launch Palette, -> "search"
    - command syntax: "search acme" to search for repositories or namespaces with "acme" in the info
- [x]  [Enumerate TAGS](docs/README-enumerate.md)
    - For each repository, list all available Tags
        - [dockerhub_v2_api.py](app\core\api\dockerhub_v2_api.py) has the methods to use for this

Alternatively:
- [x]  Enumerate all Container Tags per Repoatiory
    - For each TAG, enumerate containers
    - There's a 1-to-Many relationship with Tags to Containers
    - `GET /v2/namespaces/OWNER/repositories/REPOSITORY/tags?platforms=true&page_size=NaN&page=NaN&ordering=last_updated&name=`
    - Response:
        ```json
        {"count":1,"next":null,"previous":null,"results":[{"creator":613503,"id":10278613,"images":[{"architecture":"amd64","features":"","variant":null,"digest":"sha256:46a577b81ad2ad37b99d7a809ccd21c135cbca3c6ab3b49cfcf705c54312de78","os":"linux","os_features":"","os_version":null,"size":25529703,"status":"active","last_pulled":"2026-01-09T19:20:49.733138382Z","last_pushed":"2017-11-02T07:47:36Z"}],"last_updated":"2017-11-02T07:47:35.374523Z","last_updater":613503,"last_updater_username":"ebusinessdocker","name":"latest","repository":1436233,"full_size":25529703,"v2":true,"tag_status":"active","tag_last_pulled":"2026-01-09T19:20:49.733138382Z","tag_last_pushed":"2017-11-02T07:47:35.374523Z","media_type":"application/vnd.docker.container.image.v1+json","content_type":"image"}]}
        ```
- [ ] Enumerate ALL images PER TAG:
    - `GET /v2/repositories/<OWNER>/REPOSITORY/tags/TAG/images`
        - returns Container Digests 
        ```json
        [{"architecture":"amd64","features":null,"variant":null,"digest":"sha256:46a577b81ad2ad37b99d7a809ccd21c135cbca3c6ab3b49cfcf705c54312de78","layers":[{"digest":"sha256:b56ae66c29370df48e7377c8f9baa744a3958058a766793f821dadcb144a4647","size":1991435,"instruction":"ADD file:1e87ff33d1b6765b793888cd50e01b2bd0dfe152b7dbb4048008bfc2658faea7 in / "},{"size":0,"instruction":" CMD [\"/bin/sh\"]"},{"size":0,"instruction":" LABEL maintainer:=Wang Xinguang \u003cwangxinguang@e-business.co.jp\u003e"},{"digest":"sha256:96c90ac406e93b51666023baec2ca4812b8898f1a0091d0f07f7b68e00240d93","size":4661792,"instruction":"COPY file:24069b5766fa9d99f93fc3ac09725d54bd4592b2faa0c7caff2ec2efc28d4a3e in /usr/bin/server "},{"digest":"sha256:8017ef1466bf567c49a69b20950e8c37c7757aa7fce6b84be01382c9f45da9ef","size":18876476,"instruction":"COPY dir:32f83292c89d68a54baf9312c0cda100314e2677abd71abd6a326738cbc283f1 in /asset "},{"size":0,"instruction":" ENTRYPOINT [\"/usr/bin/server\"]"},{"size":0,"instruction":" CMD [\"/usr/bin/server\"]"}],"os":"linux","os_features":null,"os_version":null,"size":25529703,"status":"active","last_pulled":"2026-01-09T19:20:49.733138382Z","last_pushed":"2017-11-02T07:47:36Z"}]
        ```
- [x] Enumerate The Repository:
    -  `GET /v2/repositories/OWNER/REPOSITORY`
    - Response:
        ```json
        {"user":"ebusinessdocker","name":"disney","namespace":"ebusinessdocker","repository_type":"image","status":1,"status_description":"active","description":"","is_private":false,"is_automated":false,"star_count":0,"pull_count":275,"last_updated":"2017-11-02T07:47:35.758489Z","last_modified":"2024-10-16T13:48:34.145251Z","date_registered":"2017-04-25T09:11:17.568035Z","collaborator_count":0,"affiliation":null,"hub_user":"ebusinessdocker","has_starred":false,"permissions":{"read":true,"write":false,"admin":false},"media_types":["application/vnd.docker.container.image.v1+json"],"content_types":["image"],"categories":[],"immutable_tags_settings":{"enabled":false,"rules":[".*"]},"storage_size":1007407794,"source":null}
        ```

--- 

### WE ARE HERE

 - [ ] Enumerate ALL image layer digests for a container
    - **Must be done AT THE CONTAINER REGISTRY!**
    - `app/modules/enumerate/list_dockerhub_container_files.py` has examples on handling auth to the registry   (line 32:60)
    - Each Tag can have many container architectures associated
        - with a unique digest for each layer
 - [ ] Extract Build Details from Registry Image Config file (ENV, ENTRYPOINT, AUTHOR, WORKINGDIR) are all some of the fields we want to highlight
 - [ ] For each layer of an image container, run a "layer-peek" using the layer slayer lib to stream the file contents with the secret gzip hacks.
    - [ ] [Peek](@docs\README-enumerate.md) each image layer until you have gathered the filesystem layout / paths for all layers.
    - [ ] [Carve](docs\README-carve-file.md) the file out of the SOCI layer image
        - `python experiments/carve-file-from-layer.py "aciliadevops/disney-local-web:latest" /etc/passwd`
        
        ```bash
        Fetching manifest for aciliadevops/disney-local-web:latest...
        Found 7 layer(s). Searching for /etc/passwd...

        Scanning layer 1/7: sha256:20043066d3d5c...
        Layer size: 29,724,688 bytes
        Downloaded: 65,536B -> Decompressed: 300,732B -> Entries: 111
        FOUND: /etc/passwd (888 bytes) at entry #111

        Done! File saved to: /etc/passwd
        Stats: Downloaded 65,536 bytes of 29,724,688 byte layer (0.2%) in 1.14s

        cat ./etc/passwd
        root:x:0:0:root:/root:/bin/bash
        daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
        bin:x:2:2:bin:/bin:/usr/sbin/nologin
        sys:x:3:3:sys:/dev:/usr/sbin/nologin
        sync:x:4:65534:sync:/bin:/bin/sync
        [...]
        ```
        - Standalone Examples
            - These are meant to be used as stand alone methods to verify functionality without the full modular framework.
            **Do not delete or modify these files.**








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
