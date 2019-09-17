#!/usr/bin/env python3
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

MANIFEST_LOCATION = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
CLIENT = "client"
SERVER = "server"


def get_minecraft_path():
    if sys.platform.startswith('linux'):
        return Path("~/.minecraft")
    elif sys.platform.startswith('win'):
        return Path("~/AppData/Roaming/.minecraft")
    elif sys.platform.startswith('darwin'):
        return Path("~/Library/Application Support/minecraft")
    else:
        print("Cannot detect of version : %s. Please report to your closest sysadmin" % sys.platform)
        sys.exit()


mc_path = get_minecraft_path()


def get_manifest():
    if Path(f"versions/version_manifest.json").exists() and Path(f"versions/version_manifest.json").is_file():
        print("Manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    download_file(MANIFEST_LOCATION, f"versions/version_manifest.json")


def download_file(url, filename):
    try:
        print(f'Downloading {filename}...')
        f = urllib.request.urlopen(url)
        with open(filename, 'wb') as local_file:
            local_file.write(f.read())
    except urllib.request.HTTPError as e:
        print('HTTP Error')
        print(e)
    except urllib.request.URLError as e:
        print('URL Error')
        print(e)


def get_version_manifest(target_version):
    if Path(f"versions/{target_version}/version.json").exists() and Path(f"versions/{target_version}/version.json").is_file():
        print("Version manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    pathToJson = Path(f'versions/version_manifest.json')
    if pathToJson.exists() and pathToJson.is_file():
        pathToJson = pathToJson.resolve()
        with open(pathToJson) as f:
            versions = json.load(f)["versions"]
            for version in versions:
                if version.get("id") and version.get("id") == target_version and version.get("url"):
                    download_file(version.get("url"), f"versions/{target_version}/version.json")
                    break
    else:
        print('ERROR: Missing manifest file: version.json')
        print("Aborting")
        input()
        sys.exit()


def get_version_jar(target_version, type):
    path_to_json = Path(f"versions/{target_version}/version.json")
    if Path(f"versions/{target_version}/{type}.jar").exists() and Path(f"versions/{target_version}/{type}.jar").is_file():
        print(f"versions/{target_version}/{type}.jar already existing, not downloading again")
        return
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jsn = json.load(f)
            if jsn.get("downloads") and jsn.get("downloads").get(type) and jsn.get("downloads").get(type).get("url"):
                download_file(jsn.get("downloads").get(type).get("url"), f"versions/{target_version}/{type}.jar")
            else:
                print("Could not download jar, missing fields")
                print("Aborting")
                input()
                sys.exit()
    else:
        print('ERROR: Missing manifest file: version.json')
        print("Aborting")
        input()
        sys.exit()
    print("Done !")


def get_mappings(version, type):
    if Path(f'mappings/{version}/{type}.txt').exists() and Path(f'mappings/{version}/{type}.txt').is_file():
        print("Mappings already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path(f'versions/{version}/version.json')
    if path_to_json.exists() and path_to_json.is_file():
        print(f'Found {version}.json')
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jfile = json.load(f)
            url = jfile['downloads']
            if type == CLIENT:  # client:
                if url['client_mappings']:
                    url = url['client_mappings']['url']
                else:
                    print(f'Error: Missing client mappings for {version}')
            elif type == SERVER:  # server
                if url['server_mappings']:
                    url = url['server_mappings']['url']
                else:
                    print(f'Error: Missing server mappings for {version}')
            else:
                print('ERROR, type not recognized')
                sys.exit()

            print(f'Downloading the mappings for {version}...')
            download_file(url, f'mappings/{version}/{"client" if type==CLIENT else "server"}.txt')
    else:
        print('ERROR: Missing manifest file: version.json')
        print("Aborting")
        input()
        sys.exit()


def remap(version, type):
    print('=== Remapping jar using SpecialSource ====')
    t = time.time()
    path = Path(f'versions/{version}/{type}.jar')
    if not path.exists() or not path.is_file():
        path_temp = (mc_path / f'versions/{version}/{version}.jar').expanduser()
        if path_temp.exists() and path_temp.is_file():
            r = input("Error, defaulting to client.jar from your local minecraft folder, continue? (y/n)") or "y"
            if r != "y":
                sys.exit()
            path=path_temp
    mapp = Path(f'mappings/{version}/{type}.tsrg')
    specialsource = Path('./lib/SpecialSource-1.8.6.jar')
    if path.exists() and mapp.exists() and specialsource.exists() and path.is_file() and mapp.is_file() and specialsource.is_file():
        path = path.resolve()
        mapp = mapp.resolve()
        specialsource = specialsource.resolve()
        subprocess.run(['java', '-jar', specialsource.__str__(), '--in-jar', path.__str__(), '--out-jar', f'./src/{version}-{type}-temp.jar', '--srg-in', mapp.__str__(), "--kill-lvt"], check=True)
        print(f'- New -> {version}-{type}-temp.jar')
        t = time.time() - t
        print('Done in %.1fs' % t)
    else:
        print(f'ERROR: Missing files: ./lib/SpecialSource-1.8.6.jar or mappings/{version}/{type}.tsrg or versions/{version}/{type}.jar')
        print("Aborting")
        input()
        sys.exit()


def decompile_fernflower(decompVersion, version,type):
    print('=== Decompiling using FernFlower (not silent dunno why) ===')
    t = time.time()
    path = Path(f'./src/{version}-{type}-temp.jar')
    fernflower = Path('./lib/fernflower.jar')
    if path.exists() and fernflower.exists():
        path = path.resolve()
        fernflower = fernflower.resolve()
        subprocess.run(['java', '-jar', fernflower.__str__(), "-hes=0 -hdc=0 -dgs=1 -ren=1 -log=WARN", path.__str__(), f'./src/{decompVersion}/{type}'], check=True)
        print(f'- Removing -> {version}-{type}-temp.jar')
        os.remove(f'./src/{version}-{type}-temp.jar')
        print("Decompressing remapped jar to directory")
        with zipfile.ZipFile(f'./src/{decompVersion}/{type}/{version}-{type}-temp.jar') as z:
            z.extractall(path=f'./src/{decompVersion}/{type}')
        t = time.time() - t
        print('Done in %.1fs' % t)
        print(f'Remove Extra Jar file (file was decompressed in {decompVersion}/{type})? (y/n): ')
        response = input() or "y"
        if response == 'y':
            print(f'- Removing -> {decompVersion}/{type}/{version}-{type}-temp.jar')
            os.remove(f'./src/{decompVersion}/{type}/{version}-{type}-temp.jar')
    else:
        print(f'ERROR: Missing files: ./lib/fernflower.jar or ./src/{version}-{type}-temp.jar')
        print("Aborting")
        input()
        sys.exit()


def decompile_cfr(decompVersion, version,type):
    print('=== Decompiling using CFR (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{type}-temp.jar')
    cfr = Path('./lib/cfr-0.146.jar')
    if path.exists() and cfr.exists():
        path = path.resolve()
        cfr = cfr.resolve()
        subprocess.run(['java', '-jar', cfr.__str__(), path.__str__(), '--outputdir', f'./src/{decompVersion}/{type}', '--caseinsensitivefs', 'true', "--silent", "true"], check=True)
        print(f'- Removing -> {version}-{type}-temp.jar')
        print(f'- Removing -> summary.txt')
        os.remove(f'./src/{version}-{type}-temp.jar')
        os.remove(f'./src/{decompVersion}/{type}/summary.txt')

        t = time.time() - t
        print('Done in %.1fs' % t)
    else:
        print(f'ERROR: Missing files: ./lib/cfr-0.146.jar or ./src/{version}-{type}-temp.jar')
        print("Aborting")
        input()
        sys.exit()


def get_rid_brackets(input, counter):
    while '[]' in input:  # get rid of the array brackets while counting them
        counter += 1
        input = input[:-2]
    return input, counter


def remap_mappings(version, type):
    remapPrimitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J", "byte": "B", "short": "S", "char": "C", "void": "V"}
    remapFilePath = lambda path: "L" + "/".join(path.split(".")) + ";" if path not in remapPrimitives else remapPrimitives[path]
    with open(f'mappings/{version}/{type}.txt', 'r') as inputFile:
        fileName = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if not line.startswith('    '):
                obf_name = obf_name.split(":")[0]
                fileName[remapFilePath(deobf_name)] = obf_name  # save it to compare to put the Lb

    with open(f'mappings/{version}/{type}.txt', 'r') as inputFile, open(f'mappings/{version}/{type}.tsrg', 'w+') as outputFile:
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if line.startswith('    '):
                obf_name = obf_name.rstrip()  # remove leftover right spaces
                deobf_name = deobf_name.lstrip()  # remove leftover left spaces
                methodType, methodName = deobf_name.split(" ")  # split the `<methodType> <methodName>`
                methodType = methodType.split(":")[-1]  # get rid of the line numbers at the beginning for functions eg: `14:32:void`-> `void`
                if "(" in methodName and ")" in methodName:  # detect a function function
                    variables = methodName.split('(')[-1].split(')')[0]  # get rid of the function name and parenthesis
                    functionName = methodName.split('(')[0]  # get the function name only
                    array_length_type = 0

                    methodType, array_length_type = get_rid_brackets(methodType, array_length_type)
                    methodType = remapFilePath(methodType)  # remap the dots to / and add the L ; or remap to a primitives character
                    methodType = "L" + fileName[methodType] + ";" if methodType in fileName else methodType  # get the obfuscated name of the class
                    if "." in methodType:  # if the class is already packaged then change the name that the obfuscated gave
                        methodType = "/".join(methodType.split("."))
                    for i in range(array_length_type):  # restore the array brackets upfront
                        if methodType[-1] == ";":
                            methodType = "[" + methodType[:-1] + ";"
                        else:
                            methodType = "[" + methodType

                    if variables != "":  # if there is variables
                        array_length_variables = [0] * len(variables)
                        variables = list(variables.split(","))  # split the variables
                        for i in range(len(variables)):  # remove the array brackets for each variable
                            variables[i], array_length_variables[i] = get_rid_brackets(variables[i], array_length_variables[i])
                        variables = [remapFilePath(variable) for variable in variables]  # remap the dots to / and add the L ; or remap to a primitives character
                        variables = ["L" + fileName[variable] + ";" if variable in fileName else variable for variable in variables]  # get the obfuscated name of the class
                        variables = ["/".join(variable.split(".")) if "." in variable else variable for variable in variables]  # if the class is already packaged then change the obfuscated name
                        for i in range(len(variables)):  # restore the array brackets upfront for each variable
                            for j in range(array_length_variables[i]):
                                if variables[i][-1] == ";":
                                    variables[i] = "[" + variables[i][:-1] + ";"
                                else:
                                    variables[i] = "[" + variables[i]
                        variables = "".join(variables)

                    outputFile.write(f'\t{obf_name} ({variables}){methodType} {functionName}\n')
                else:
                    outputFile.write(f'\t{obf_name} {methodName}\n')

            else:
                obf_name = obf_name.split(":")[0]
                outputFile.write(remapFilePath(obf_name)[1:-1] + " " + remapFilePath(deobf_name)[1:-1] + "\n")

    print("Done !")


def make_paths(version, type, removal_bool):
    path = Path(f'mappings/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)

    path = Path(f'versions/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        path = Path(f'versions/{version}/version.json')
        if path.is_file() and removal_bool:
            path.unlink()
    if Path("versions").exists():
        path = Path(f'versions/version_manifest.json')
        if path.is_file() and removal_bool:
            path.unlink()

    path = Path(f'versions/{version}/{type}.jar')
    if path.exists() and path.is_file() and removal_bool:
        aw = input(f"versions/{version}/{type}.jar already exists, wipe it (w) or ignore (i) ? ") or "i"
        if aw == "w":
            shutil.rmtree(path)

    path = Path(f'src/{version}/{type}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        aw = input(f"/src/{version}/{type} already exists, wipe it (w), create a new folder (n) or kill the process (k) ? ")
        if aw == "w":
            shutil.rmtree(Path(f"./src/{version}/{type}"))
        elif aw == "n":
            version = version + type + "_" + str(random.getrandbits(128))
        else:
            sys.exit()
        path = Path(f'src/{version}/{type}')
        path.mkdir(parents=True)
    return version


def main():
    print("Decompiling using official mojang mappings...")
    removal_bool= 1 if input("Do you want to clean up some leftovers? (y/n): ") in ["y","yes"] else 0
    decompiler = input("Please input you decompiler choice: fernflower (f) or cfr (default: cfr) : ")
    decompiler = decompiler if decompiler.lower() in ["fernflower", "cfr", "f"] else "cfr"
    version = input("Please input a valid version starting from 19w36a and 1.14.4 : ") or "1.14.4"
    type = input("Please select either client or server side (c/s) : ")
    type = type if type in ["client", "server", "c", "s"] else CLIENT
    type = CLIENT if type in ["client", "c"] else SERVER
    decompiled_version = make_paths(version, type,removal_bool)
    get_manifest()
    get_version_manifest(version)
    r = input("Auto Mode? (y/n): ") or "n"
    if r == "y":
        get_mappings(version, type)
        remap_mappings(version, type)
        get_version_jar(version, type)
        remap(version, type)
        if decompiler.lower() == "cfr":
            decompile_cfr(decompiled_version, version,type)
        else:
            decompile_fernflower(decompiled_version, version,type)
        print("===FINISHED===")
        print(f"output is in /src/{version}")
        input("Press Enter key to exit")
        sys.exit()

    r = input('Download mappings? (y/n): ') or "y"
    if r == 'y':
        get_mappings(version, type)

    r = input('Remap mappings to tsrg? (y/n): ') or "y"
    if r == 'y':
        remap_mappings(version, type)

    r = input(f'Get {version}-{type}.jar ? (y/n): ') or "y"
    if r == "y":
        get_version_jar(version, type)

    r = input('Remap? (y/n): ') or "y"
    if r == 'y':
        remap(version, type)

    r = input('Decompile? (y/n): ') or "y"
    if r == 'y':
        if decompiler.lower() == "cfr":
            decompile_cfr(decompiled_version, version,type)
        else:
            decompile_fernflower(decompiled_version, version,type)

    print("===FINISHED===")
    print(f"output is in /src/{version}")
    input("Press Enter key to exit")


if __name__ == "__main__":
    main()
