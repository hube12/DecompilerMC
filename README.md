# DecompilerMC

---
**What is this for?**

This tool will help you convert mappings from mojang from their proguard format to the tsrg format that then can be used directly with specialsource which will then remap the client jar. Once that done it can be decompiled either with cfr (code only) or fernflower (assets and code).

Of course we provide all that toolchain directly so your output will be readable (and soon executable) code as you could get with MCP (ModCoderPack)

---
**Important Note**

You need to run first your Minecraft Launcher to download the desired version (we support only from 19w36a and 1.14.4 since this is where mojang shipped mappings) then you are good to go

We support both linux and windows.

You need a java runtime inside your path (Java 8 should be good)

CFR decompilation is approximately 60s and fernflower takes roughly 200s, please give it time

For windows you can run the release file directly (in https://github.com/hube12/DecompilerMC/releases/tag/0.1 ), you can also run it directly with python 3.5+ with `python main.py`

For linux you can run the release file directly (in https://github.com/hube12/DecompilerMC/releases/tag/0.2 ), you can also run it directly with python 3.5+ with `python main.py`

For MAC OS you can run the release file directly (in https://github.com/hube12/DecompilerMC/releases/tag/0.3 ), you can also run it directly with python 3.5+ with `python main.py`

----
