# DecompilerMC

---
**What is this for?**

This tool will help you convert mappings from mojang from their proguard format to the tsrg format that then can be used directly with specialsource which will then remap the client jar. Once that done it can be decompiled either with cfr (code only) or fernflower (assets and code).

Of course we provide all that toolchain directly so your output will be readable (and soon executable) code as you could get with MCP (ModCoderPack)

---
**Important Note**

You need an internet connection to download the mappings, you can ofc put them in the respective folder if you have them physically

We support Windows, MacOS and linux

You need a java runtime inside your path (Java 8 should be good)

CFR decompilation is approximately 60s and fernflower takes roughly 200s, please give it time

You can run it directly with python 3.7+ with `python3 main.py`

There is a common release here:  https://github.com/hube12/DecompilerMC/releases/latest for all version

----

You can use arguments instead of terminal based choice, this is not required but once you pass a mcversion it will start the process

We recommend using -q everytime otherwise it might ask stdin questions.

By default we employ the nice guy strategy which is if the folder exist we create a new random one, please consider using -f, 
if you actually need a specific path.

Examples:
- Decompile latest release without any output: `python3 main.py --mcv latest -q` 
- Decompile latest snapshot server side with output: `python3 main.py --mcversion snap --side server` 
- Decompile 1.14.4 client side with output and not automatic with forcing delete of old runs:  `python3 main.py -mcv 1.14.4 -s client -na -f -rmap -rjar -dm -dj -dd -dec -q -c` 


```bash

usage: main.py [-h] [--mcversion MCVERSION] [--side SIDE] [--clean] [--force]
               [--forceno] [--decompiler DECOMPILER] [--nauto]
               [--download_mapping DOWNLOAD_MAPPING]
               [--remap_mapping [REMAP_MAPPING]]
               [--download_jar [DOWNLOAD_JAR]] [--remap_jar [REMAP_JAR]]
               [--delete_dep [DELETE_DEP]] [--decompile [DECOMPILE]] [--quiet]

Decompile Minecraft source code

optional arguments:
  -h, --help            show this help message and exit
  --mcversion MCVERSION, -mcv MCVERSION
                        The version you want to decompile (all versions
                        starting from 19w36a (snapshot) and 1.14.4 (releases))
                        Use 'snap' for latest snapshot (20w48a for example, it will get it automatically) or 'latest'
                        for latest version (1.16.4 for example, it will get it automatically)
  --side SIDE, -s SIDE  The side you want to decompile (either client or
                        server)
  --clean, -c           Clean old runs
  --force, -f           Force resolving conflict by replacing old files.
  --forceno, -fn        Force resolving conflict by creating new directories.
  --decompiler DECOMPILER, -d DECOMPILER
                        Choose between fernflower and cfr.
  --nauto, -na          Choose between auto and manual mode.
  --download_mapping DOWNLOAD_MAPPING, -dm DOWNLOAD_MAPPING
                        Download the mappings (only if auto off)
  --remap_mapping [REMAP_MAPPING], -rmap [REMAP_MAPPING]
                        Remap the mappings to tsrg (only if auto off)
  --download_jar [DOWNLOAD_JAR], -dj [DOWNLOAD_JAR]
                        Download the jar (only if auto off)
  --remap_jar [REMAP_JAR], -rjar [REMAP_JAR]
                        Remap the jar (only if auto off)
  --delete_dep [DELETE_DEP], -dd [DELETE_DEP]
                        Delete the dependencies (only if auto off)
  --decompile [DECOMPILE], -dec [DECOMPILE]
                        Decompile (only if auto off)
  --quiet, -q           Doesn't display the messages
```

----

Build command (for executable):

```python
pip install pyinstaller
pyinstaller main.py --distpath build --onefile
```
