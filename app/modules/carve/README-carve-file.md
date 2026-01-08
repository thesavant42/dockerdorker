# Carve file from layer

- Carve a single file from an OCI image layer using incremental streaming.

**CRITICAL! NOTE: this needs to be refactored so that the entire app can utilize a shared database.**

## Summary

 - This script extracts a specific file from a Docker image without downloading the entire layer.
 - It uses HTTP Range requests to fetch compressed data in chunks, decompresses incrementally, and stops as soon as the target file is fully extracted.

## Usage

 - `python experiments/carve-file-from-layer.py "aciliadevops/disney-local-web:latest" /etc/passwd`
     - technique proven in https://github.com/thesavant42/docker-dorker

```bash
python .\carve-file-from-layer.py  "aciliadevops/disney-local-web:latest" /etc/passwd
Fetching manifest for aciliadevops/disney-local-web:latest...
Found 7 layer(s). Searching for /etc/passwd...

Scanning layer 1/7: sha256:20043066d3d5c...
  Layer size: 29,724,688 bytes
  Downloaded: 65,536B -> Decompressed: 300,732B -> Entries: 111
  FOUND: /etc/passwd (888 bytes) at entry #111

Done! File saved to: etc\passwd
Stats: Downloaded 65,536 bytes of 29,724,688 byte layer (0.2%) in 1.14s
```

```bash
cat .\etc\passwd
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/run/ircd:/usr/sbin/nologin
_apt:x:42:65534::/nonexistent:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
ubuntu:x:1000:1000:Ubuntu:/home/ubuntu:/bin/bash
```