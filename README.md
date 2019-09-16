# DecompilerMC

---
**What is this for?**

This tool will help you convert mappings from mojang from their proguard format to the tsrg format that then can be used directly with specialsource which will then remap the client jar. Once that done it can be decompiled either with cfr (code only) or fernflower (assets and code).

Of course we provide all that toolchain directly so your output will be readable (and soon executable) code as you could get with MCP (ModCoderPack)

---
**Important Note**

You need an internet connection to download the mappings, you can ofc put them in the respective folder if you have them physically

We support linux, MacOS and linux

You need a java runtime inside your path (Java 8 should be good)

CFR decompilation is approximately 60s and fernflower takes roughly 200s, please give it time

You can run it directly with python 3.5+ with `python3 main.py`

There is a common release here:  https://github.com/hube12/DecompilerMC/releases/tag/0.4 for all version

----
