# Enumeration modules

## List all files
- `app\modules\enumerate\list_dockerhub_container_files.py`
    - List all files in a Docker Hub container image using partial streaming.

- Enumerates all layers and iterates through them to build a complete filesystem listing, using HTTP Range requests to minimize bandwidth.

```bash
Usage:
    python experiments/list_dockerhub_container_files.py aciliadevops/disney-local-web:latest
```
 - This is *not* the API module; this is a standalone script that can be used to compare results with the dockerdocker API results.

Output is [here](plans\to-do\plan-pseudo-tty-filesystem-formatting)
 - it's 726 lines, don't try to read it all at once. Here's a sample:

 ```bash
 FILE LISTING (620 entries)
============================================================
Layer          Type   Mode              Size  Path
-------------- ------ ----------- ----------  ------------------------------
38513bd72563   DIR    drwxr-xr-x          -  ./
38513bd72563   LINK   lrwxrwxrwx          0  bin -> usr/bin
38513bd72563   DIR    drwxr-xr-x          -  boot/
38513bd72563   DIR    drwxr-xr-x          -  dev/
38513bd72563   DIR    drwxr-xr-x          -  etc/
38513bd72563   FILE   -rw-------          0  etc/.pwd.lock
38513bd72563   DIR    drwxr-xr-x          -  etc/alternatives/
38513bd72563   FILE   -rw-r--r--        100  etc/alternatives/README
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/awk -> /usr/bin/mawk
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/awk.1.gz -> /usr/share/man/man1/mawk.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/builtins.7.gz -> /usr/share/man/man7/bash-builtins.7.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/nawk -> /usr/bin/mawk
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/nawk.1.gz -> /usr/share/man/man1/mawk.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/pager -> /bin/more
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/pager.1.gz -> /usr/share/man/man1/more.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/rmt -> /usr/sbin/rmt-tar
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/rmt.8.gz -> /usr/share/man/man8/rmt-tar.8.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which -> /usr/bin/which.debianutils
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.1.gz -> /usr/share/man/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.de1.gz -> /usr/share/man/de/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.es1.gz -> /usr/share/man/es/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.fr1.gz -> /usr/share/man/fr/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.it1.gz -> /usr/share/man/it/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.ja1.gz -> /usr/share/man/ja/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.pl1.gz -> /usr/share/man/pl/man1/which.debianutils.1.gz
38513bd72563   LINK   lrwxrwxrwx          0  etc/alternatives/which.sl1.gz -> /usr/share/man/sl/man1/which.debianutils.1.gz
38513bd72563   DIR    drwxr-xr-x          -  etc/apt/
38513bd72563   DIR    drwxr-xr-x          -  etc/apt/apt.conf.d/
38513bd72563   FILE   -rw-r--r--        399  etc/apt/apt.conf.d/01autoremove
38513bd72563   FILE   -rw-r--r--        182  etc/apt/apt.conf.d/70debconf
```
