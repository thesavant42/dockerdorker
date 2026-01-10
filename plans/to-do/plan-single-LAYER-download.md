# Request: cmd-pal addition

## Individual-Layer Downloads 

### NOT YET READY FOR IMPLEMENTATION

I want to rework the textual command palette flow to add a new /ddork command:

`/ddork layer save OWNER-REPO-TAG-INT.tgz`

### Extendingthe previous examoples:
- Where: 
    - OWNER:    drichnerdisney
    - REPO:     ollama
    - TAG:      v1
    - INT:      Relative layer number. In our example, if it has 38 layers, and I want the last layer, the file would be saved as:
        - `drichnerdisney-ollama-v1-amd64-38.tgz`

Flow: 
 - Get image config information from the registry, using the API
    - `/ddork layers drichnerdisney/ollama:v1` in the Cmd Palette 
        - Research how this is command is configured first, since most of the workflow is likely to be reusable.


### Implemenrtation Completed:
- **Do not modify these; they are completed.**

```
/ddork search disney     						# the new way to search from the command palette 
												# running this is the same as search was before

/ddork repos drichnerdisney						# cmd palette to list repos for namespace "drichnerdisney"
												# This would be the same as clicking enter on a highlighted repository in the current flow
/ddork tags drichnerdisney/ollama				# cmd palette to list tags for repo "drichnerdisney/ollama"
												# This happens automatically for the user in the current flow, now it will also be manual
/ddork containers drichnerdisney/ollama:v1		# cmd palette to list tags for repo "drichnerdisney/ollama:v1"
												# list all container digest for a tag
/ddork layers drichnerdisney/ollama:v1			# gets layer digest info from docker.io registry (not docker hub)

/ddork files drichnerdisney/ollama:v1			# same as running the standalone file listing script

/ddork carve drichnerdisney/ollama:v1 /etc/passwd # single-file carving 
```
---

# Commit 0eb135ce3834e85deb9e67bfba8fdf32f1690d1f
- Implemented /ddork 
    - Review the files from this commit
Files of note when designing this feature:

- app/ui/commands/ddork_provider.py

- app/ui/messages.py
- main.py