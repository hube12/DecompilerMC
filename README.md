# DecompilerMC

This tool automatically decompiles and remaps specific Minecraft versions. (Specifically, it converts Mojang's mappings from their proguard format to the tsrg format. SpecialSource then uses that and remaps the client jar, which is then decompiled either with CFR (code only) or Fernflower (assets and code).)

Your output will be readable/executable code similar to ModCoderPack or other decompilers.

## Prerequisites

You will need
- an Internet connection to download the mappings. You can obviously put them in the respective folder if you have them physically.
- Windows, MacOS, or Linux.
- A Java runtime inside your path (Java 8 should be good).

You can run this directly with Python 3.7+ with `python3 main.py`. CFR decompilation takes approximately 60s and fernflower takes roughly 200s. The code will then be inside the folder called `./src/<name_version(option_hash)>/<side>`; you can find the jar and the version manifest in the `./versions/` directory.

The `./tmp/` directory can be removed without impact.

There is a common release here: https://github.com/hube12/DecompilerMC/releases/latest for all versions.

----

## Command-line Arguments (Optional)
You can use arguments instead of terminal-based choices. This is not required, but will automatically start if a mcversion is passed.

```bash
usage: main.py [-h] [--mcversion MCVERSION] [--side SIDE] [--clean] [--force]
               [--forceno] [--decompiler DECOMPILER] [--nauto]
               [--download_mapping DOWNLOAD_MAPPING]
               [--remap_mapping [REMAP_MAPPING]]
               [--download_jar [DOWNLOAD_JAR]] [--remap_jar [REMAP_JAR]]
               [--delete_dep [DELETE_DEP]] [--decompile [DECOMPILE]] [--quiet]

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
  --force, -f           Force resolve conflicts by replacing old files. (Use if a specific path is necessary)
  --forceno, -fn        Force resolve conflicts by creating new directories.
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
  --quiet, -q           Doesn't display messages (recommended)
```

Examples:
- Decompile latest release without any output: `python3 main.py --mcv latest -q` 
- Decompile latest snapshot server side with output: `python3 main.py --mcversion snap --side server` 
- Decompile 1.14.4 client side with output and not automatic with forcing delete of old runs:  `python3 main.py -mcv 1.14.4 -s client -na -f -rmap -rjar -dm -dj -dd -dec -q -c` 

----

To build as an executable, the commands are
```python
pip install pyinstaller
pyinstaller main.py --distpath build --onefile
```
