> [!WARNING]
> [Since Minecraft 26.1](https://www.minecraft.net/en-us/article/removing-obfuscation-in-java-edition), this tool is no longer required and is not recommended for use in new modding projects.
>
> For convenience of developers still using this project in their workflow, this tool has been updated to skip the unneeded decompiling/deobfuscating steps and extract the contents of Minecraft 26.1+ .jar files directly.

# DecompilerMC

This tool allows you to download and extract the source code for a specified Minecraft version for modding purposes. On applicable versions (1.14.4 to 1.21.11), it obtains the deobfuscation mappings provided by Mojang and applies them. It then decompiles the JAR and outputs the contents, providing readable/executable code similar to ModCoderPack or other decompilers.

## Prerequisites

- An Internet connection (to download the mappings)
- Windows, macOS, or Linux
- Java 8 or higher
- Python 3.7 or higher

## Running

Simply run `python3 main.py` in your terminal. You can also specify the following arguments and options:

```bash
usage: main.py [-h] [--interactive INTERACTIVE] [--side {client,server}] [--clean] [--force] [--decompiler {fernflower,cfr}] [--quiet]
               [mcversion]

Decompile Minecraft source code

positional arguments:
  mcversion             The version you want to decompile (any version starting from 19w36a (snapshot) and 1.14.4 (releases)) Use 'snap' for
                        latest snapshot or 'latest' for latest version

options:
  -h, --help            show this help message and exit
  --interactive, -i INTERACTIVE
                        Enable an interactive CLI to specify options (all other command line arguments, besides --quiet, will be ignored)
  --side, -s {client,server}
                        Whether to decompile the client side or server side
  --clean, -c           Clean old runs
  --force, -f           Force resolving conflicts by replacing old files
  --decompiler, -d {fernflower,cfr}
                        Select a copmiler to run
  --quiet, -q           Suppresses logging output
```

Examples:
- Decompile latest release without any output: `python3 main.py --mcv latest -q` 
- Decompile latest snapshot server side with output: `python3 main.py snap --side server` 
- Decompile 1.14.4 client side with output, cleaning up old runs:  `python3 main.py 1.14.4 -s client -f -q -c` 

CFR decompilation takes approximately 60s and fernflower takes roughly 200s. The code will then be inside the folder called `./src/<name_version(option_hash)>/<side>`; you can find the jar and the version manifest in the `./versions/` directory.

The `./tmp/` directory can be removed without impact.

There is a common release here: https://github.com/hube12/DecompilerMC/releases/latest for all versions.

## Building Executable

To build DecompilerMC as an executable using `pyinstaller`, you can run the following:

```sh
pyinstaller main.py --distpath build --onefile
```

If you do not have `pyinstaller`, you can install it via `pip`: `pip install pyinstaller`
