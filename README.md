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

You can find the jar and the version manifest in the `./versions/` directory

The code will then be inside the folder called `./src/<name_version(option_hash)>/<side>`

The `./tmp/` directory can be removed without impact

There is a common release here:  https://github.com/hube12/DecompilerMC/releases/latest for all version

----

You can use arguments instead of terminal based choice, this is not required but once you pass a mcversion it will start the process

We recommend using -q everytime otherwise it might ask stdin questions.

By default we employ the nice guy strategy which is if the folder exist we create a new random one, please consider using -f, 
if you actually need a specific path.

Examples:
- Decompile latest release without any output: `python3 main.py latest -q` 
- Decompile latest snapshot server side with output: `python3 main.py snap --side server` 
- Decompile 1.14.4 client side with output cleaning any old runs:  `python3 main.py 1.14.4 -s client -f -q -c` 


```bash
usage: main.py [-h] [--interactive INTERACTIVE] [--side {client,server}] [--clean] [--force] [--decompiler {fernflower,cfr}] [--quiet] mcversion

Decompile Minecraft source code

positional arguments:
  mcversion             The version you want to decompile (alid version starting from 19w36a (snapshot) and 1.14.4 (releases)) Use 'snap' for
                        latest snapshot or 'latest' for latest version

options:
  -h, --help            show this help message and exit
  --interactive INTERACTIVE, -i INTERACTIVE
                        Enable an interactive CLI to specify options (all other command line arguments, besides --quiet, will be ignored)
  --side {client,server}, -s {client,server}
                        Whether to decompile the client side or server side
  --clean, -c           Clean old runs
  --force, -f           Force resolving conflicts by replacing old files
  --decompiler {fernflower,cfr}, -d {fernflower,cfr}
                        Select a copmiler to run
  --quiet, -q           Suppresses logging output
```

----

Build command (for executable):

```python
pip install pyinstaller
pyinstaller main.py --distpath build --onefile
```
