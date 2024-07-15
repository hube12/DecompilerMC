#!/usr/bin/env python3
import argparse
import glob
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from os.path import join, split
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError
from typing import Union
from urllib.error import HTTPError, URLError

assert sys.version_info >= (3, 7)

SPECIAL_SOURCE_VERSION = "1.11.4"
MANIFEST_LOCATION = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
CLIENT = "client"
SERVER = "server"
DECOMPILERS = {
    "fernflower": {},
    "cfr": {"version": "0.152"}
}

def get_minecraft_path():
    if sys.platform.startswith('linux'):
        return Path("~/.minecraft")
    elif sys.platform.startswith('win'):
        return Path("~/AppData/Roaming/.minecraft")
    elif sys.platform.startswith('darwin'):
        return Path("~/Library/Application Support/minecraft")
    else:
        raise Exception(f"Unknown platform: {sys.platform}")


mc_path = get_minecraft_path()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def check_java():
    """Check for java and setup the proper directory if needed"""
    results = []
    if sys.platform.startswith('win'):
        if not results:
            import winreg

            for flag in [winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                try:
                    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\JavaSoft\Java Development Kit', 0,
                                       winreg.KEY_READ | flag)
                    version, _ = winreg.QueryValueEx(k, 'CurrentVersion')
                    k.Close()
                    k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                       r'Software\JavaSoft\Java Development Kit\%s' % version, 0,
                                       winreg.KEY_READ | flag)
                    path, _ = winreg.QueryValueEx(k, 'JavaHome')
                    k.Close()
                    path = join(str(path), 'bin')
                    subprocess.run(['"%s"' % join(path, 'java'), ' -version'], stdout=open(os.devnull, 'w'),
                                   stderr=subprocess.STDOUT, check=True)
                    results.append(path)
                except (CalledProcessError, OSError):
                    pass
        if not results:
            try:
                subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                results.append('')
            except (CalledProcessError, OSError):
                pass
        if not results and 'ProgramW6432' in os.environ:
            results.append(which('java.exe', path=os.environ['ProgramW6432']))
        if not results and 'ProgramFiles' in os.environ:
            results.append(which('java.exe', path=os.environ['ProgramFiles']))
        if not results and 'ProgramFiles(x86)' in os.environ:
            results.append(which('java.exe', path=os.environ['ProgramFiles(x86)']))
    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        if not results:
            try:
                subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
                results.append('')
            except (CalledProcessError, OSError):
                pass
        if not results:
            results.append(which('java', path='/usr/bin'))
        if not results:
            results.append(which('java', path='/usr/local/bin'))
        if not results:
            results.append(which('java', path='/opt'))
    results = [path for path in results if path is not None]
    if not results:
        raise Exception('Java JDK is not installed! Please install java JDK from https://java.oracle.com or OpenJDK.')


def get_global_manifest(quiet):
    version_manifest = Path(f"versions/version_manifest.json")
    if version_manifest.exists() and version_manifest.is_file():
        if not quiet:
            print("Manifest already exists, not downloading again")
        return
    download_file(MANIFEST_LOCATION, version_manifest, quiet)


def download_file(url, filename, quiet=True):
    try:
        if not quiet:
            print(f'Downloading {url} to {filename}...')
        f = urllib.request.urlopen(url)
        if filename.exists():
            filename.unlink()
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'wb+') as local_file:
            local_file.write(f.read())
            if not quiet:
                print(f'Downloaded {filename} successfully!')
    except (HTTPError, URLError) as e:
        if Path(filename).exists():
            if not quiet:
                print(f'Failed to download {filename}, using cached version')
            return
        raise e


def get_latest_version():
    path_to_json = Path(__file__).parent / 'tmp/manifest.json'
    download_file(MANIFEST_LOCATION, path_to_json, True)
    snapshot = None
    version = None
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["latest"]
            if versions and versions.get("release") and versions.get("release"):
                version = versions.get("release")
                snapshot = versions.get("snapshot")
    return snapshot, version


def get_version_manifest(target_version, quiet):
    version_json = Path(f"versions/{target_version}/version.json")
    if version_json.exists() and version_json.is_file():
        if not quiet:
            print("Version manifest already exists, not downloading again")
        return
    version_manifest = Path('versions/version_manifest.json')
    if not (version_manifest.exists() and version_manifest.is_file()):
        raise Exception('Missing manifest file: version.json')
    
    version_manifest = version_manifest.resolve()
    with open(version_manifest) as f:
        versions = json.load(f)["versions"]
        for version in versions:
            if version.get("id") and version.get("id") == target_version and version.get("url"):
                download_file(version.get("url"), version_json, quiet)
                break


def sha256(fname: Union[Union[str, bytes], int]):
    import hashlib
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_version_jar(target_version, side, quiet):
    version_json = Path(f"versions/{target_version}/version.json")
    jar_path = Path(f"versions/{target_version}/{side}.jar")
    if jar_path.exists() and jar_path.is_file():
        if not quiet:
            print(f"{jar_path} already exists, not downloading again")
        return
    if not (version_json.exists() and version_json.is_file()):
        raise Exception('ERROR: Missing manifest file: version.json')

    with open(version_json) as f:
        jsn = json.load(f)
        if not (jsn.get("downloads") and jsn.get("downloads").get(side) and jsn.get("downloads").get(side).get("url")):
            raise Exception("Could not download jar, missing fields")

        download_file(jsn.get("downloads").get(side).get("url"), jar_path, quiet)
        # In case the server is newer than 21w39a you need to actually extract it first from the archive
        if side == SERVER:
            if not Path(jar_path).exists():
                raise Exception(f"Jar was maybe downloaded but not located, this is a failure, check path at {jar_path}")

            with zipfile.ZipFile(jar_path, mode="r") as z:
                content = None
                try:
                    content = z.read("META-INF/versions.list")
                except Exception as _:
                    # we don't have a versions.list in it
                    pass
                if content is not None:
                    element = content.split(b"\t")
                    if len(element) != 3:
                        raise Exception(f"Jar should be extracted but version list is not in the correct format, expected 3 fields, got {len(element)} for {content}")
                    version_hash = element[0].decode()
                    version = element[1].decode()
                    path = element[2].decode()
                    if version != target_version and not quiet:
                        print(f"Warning, version is not identical to the one targeted got {version} exepected {target_version}")
                    new_jar_path = f"versions/{target_version}"
                    new_jar_path = z.extract(f"META-INF/versions/{path}", new_jar_path)
                    if not Path(new_jar_path).exists():
                        raise Exception(f"New {side} jar could not be extracted from archive at {new_jar_path}, failure")
                    file_hash = sha256(new_jar_path)
                    if file_hash != version_hash:
                        raise Exception(f"Extracted file hash and expected hash did not match up, got {file_hash} expected {version_hash}")
                    shutil.move(new_jar_path, jar_path)
                    shutil.rmtree(f"versions/{target_version}/META-INF")            
    if not quiet:
        print("Done!")


def get_mappings(version, side, quiet):
    mappings_file = Path(f'mappings/{version}/{side}.txt')
    if mappings_file.exists() and mappings_file.is_file():
        if not quiet:
            print("Mappings already exist, not downloading again")
        return
    version_json = Path(f'versions/{version}/version.json')
    if version_json.exists() and version_json.is_file():
        if not quiet:
            print(f'Found {version}.json')
        with open(version_json) as f:
            jfile = json.load(f)
            url = jfile['downloads']
            if side == CLIENT:  # client:
                if url.get('client_mappings'):
                    url = url['client_mappings']['url']
                else:
                    if not quiet:
                        print(f'Error: Missing client mappings for {version}')
            elif side == SERVER:  # server
                if url.get('server_mappings'):
                    url = url['server_mappings']['url']
                else:
                    if not quiet:
                        print(f'Error: Missing server mappings for {version}')
            else:
                raise Exception('ERROR, type not recognized')
            if not quiet:
                print(f'Downloading the mappings for {version}...')
            download_file(url, mappings_file, quiet)
    else:
        raise Exception('ERROR: Missing manifest file: version.json')


def remap(version, side, quiet):
    if not quiet:
        print('=== Remapping jar using SpecialSource ====')
    t = time.time()
    path = Path(f'versions/{version}/{side}.jar')
    # that part will not be assured by arguments
    if not path.exists() or not path.is_file():
        path_temp = (mc_path / f'versions/{version}/{version}.jar').expanduser()
        if path_temp.exists() and path_temp.is_file():
            r = input("Error, defaulting to client.jar from your local Minecraft folder, continue? (y/n)") or "y"
            if r != "y":
                sys.exit(-1)
            path = path_temp
    mapp = Path(f'mappings/{version}/{side}.tsrg')
    specialsource = Path(f'./lib/SpecialSource-{SPECIAL_SOURCE_VERSION}.jar')
    if not (path.exists() and mapp.exists() and specialsource.exists() and path.is_file() and mapp.is_file() and specialsource.is_file()):
       raise Exception(f'ERROR: Missing files: ./lib/SpecialSource-{SPECIAL_SOURCE_VERSION}.jar or mappings/{version}/{side}.tsrg or versions/{version}/{side}.jar')
    path = path.resolve()
    mapp = mapp.resolve()
    specialsource = specialsource.resolve()
    subprocess.run(['java',
                    '-jar', str(specialsource),
                    '--in-jar', str(path),
                    '--out-jar', f'./src/{version}-{side}-temp.jar',
                    '--srg-in', str(mapp),
                    "--kill-lvt"  # kill snowmen
                    ], check=True, capture_output=quiet)
    if not quiet:
        print(f'- New -> {version}-{side}-temp.jar')
        t = time.time() - t
        print('Done in %.1fs' % t)


def decompile_fernflower(decompiled_version, version, side, quiet, force):
    if not quiet:
        print('=== Decompiling using FernFlower (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{side}-temp.jar')
    fernflower = Path('./lib/fernflower.jar')
    if not (path.exists() and fernflower.exists()):
        raise Exception(f'ERROR: Missing files: ./lib/fernflower.jar or ./src/{version}-{side}-temp.jar')

    path = path.resolve()
    fernflower = fernflower.resolve()
    subprocess.run(['java',
                    '-Xmx4G',
                    '-Xms1G',
                    '-jar', str(fernflower),
                    '-hes=0',  # hide empty super invocation deactivated (might clutter but allow following)
                    '-hdc=0',  # hide empty default constructor deactivated (allow to track)
                    '-dgs=1',  # decompile generic signatures activated (make sure we can follow types)
                    '-lit=1',  # output numeric literals
                    '-asc=1',  # encode non-ASCII characters in string and character
                    '-log=WARN',
                    str(path), f'./src/{decompiled_version}/{side}'
                    ], check=True, capture_output=quiet)
    if not quiet:
        print(f'- Removing -> {version}-{side}-temp.jar')
    os.remove(f'./src/{version}-{side}-temp.jar')
    if not quiet:
        print("Decompressing remapped jar to directory")
    with zipfile.ZipFile(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar') as z:
        z.extractall(path=f'./src/{decompiled_version}/{side}')
    t = time.time() - t
    if not quiet:
        print(f'Done in %.1fs (file was decompressed in {decompiled_version}/{side})' % t)
        print('Remove Extra Jar file? (y/n): ')
        response = input() or "y"
        if response == 'y':
            print(f'- Removing -> {decompiled_version}/{side}/{version}-{side}-temp.jar')
            os.remove(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar')
    if force:
        os.remove(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar')


def decompile_cfr(decompiled_version, version, side, quiet):
    if not quiet:
        print('=== Decompiling using CFR (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{side}-temp.jar')
    cfr = Path(f'./lib/cfr-{DECOMPILERS['cfr']['version']}.jar')
    if not (path.exists() and cfr.exists()):
        raise Exception(f'ERROR: Missing files: ./lib/cfr-{DECOMPILERS['cfr']['version']}.jar or ./src/{version}-{side}-temp.jar')

    path = path.resolve()
    cfr = cfr.resolve()
    subprocess.run(['java',
                    '-Xmx4G',
                    '-Xms1G',
                    '-jar', str(cfr),
                    str(path),
                    '--outputdir', f'./src/{decompiled_version}/{side}',
                    '--caseinsensitivefs', 'true',
                    "--silent", "true"
                    ], check=True, capture_output=quiet)
    if not quiet:
        print(f'- Removing -> {version}-{side}-temp.jar')
        print(f'- Removing -> summary.txt')
    os.remove(f'./src/{version}-{side}-temp.jar')
    os.remove(f'./src/{decompiled_version}/{side}/summary.txt')
    if not quiet:
        t = time.time() - t
        print('Done in %.1fs' % t)


def decompile(decompiler, decompiled_version, version, side, quiet, force):
    if decompiler == "cfr":
        decompile_cfr(decompiled_version, version, side, quiet)
    else:
        decompile_fernflower(decompiled_version, version, side, quiet, force)


def remove_brackets(line, counter):
    while '[]' in line:  # get rid of the array brackets while counting them
        counter += 1
        line = line[:-2]
    return line, counter


def remap_file_path(path):
    remap_primitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J", "byte": "B", "short": "S",
                        "char": "C", "void": "V"}
    return "L" + "/".join(path.split(".")) + ";" if path not in remap_primitives else remap_primitives[path]


def convert_mappings(version, side, quiet):
    with open(f'mappings/{version}/{side}.txt', 'r') as inputFile:
        file_name = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if not line.startswith('    '):
                obf_name = obf_name.split(":")[0]
                file_name[remap_file_path(deobf_name)] = obf_name  # save it to compare to put the Lb

    with open(f'mappings/{version}/{side}.txt', 'r') as inputFile, open(f'mappings/{version}/{side}.tsrg',
                                                                        'w+') as outputFile:
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if line.startswith('    '):
                obf_name = obf_name.rstrip()  # remove leftover right spaces
                deobf_name = deobf_name.lstrip()  # remove leftover left spaces
                method_type, method_name = deobf_name.split(" ")  # split the `<methodType> <methodName>`
                method_type = method_type.split(":")[
                    -1]  # get rid of the line numbers at the beginning for functions eg: `14:32:void`-> `void`
                if "(" in method_name and ")" in method_name:  # detect a function function
                    variables = method_name.split('(')[-1].split(')')[0]  # get rid of the function name and parenthesis
                    function_name = method_name.split('(')[0]  # get the function name only
                    array_length_type = 0

                    method_type, array_length_type = remove_brackets(method_type, array_length_type)
                    method_type = remap_file_path(
                        method_type)  # remap the dots to / and add the L ; or remap to a primitives character
                    method_type = "L" + file_name[
                        method_type] + ";" if method_type in file_name else method_type  # get the obfuscated name of the class
                    if "." in method_type:  # if the class is already packaged then change the name that the obfuscated gave
                        method_type = "/".join(method_type.split("."))
                    for i in range(array_length_type):  # restore the array brackets upfront
                        if method_type[-1] == ";":
                            method_type = "[" + method_type[:-1] + ";"
                        else:
                            method_type = "[" + method_type

                    if variables != "":  # if there is variables
                        array_length_variables = [0] * len(variables)
                        variables = list(variables.split(","))  # split the variables
                        for i in range(len(variables)):  # remove the array brackets for each variable
                            variables[i], array_length_variables[i] = remove_brackets(variables[i],
                                                                                      array_length_variables[i])
                        variables = [remap_file_path(variable) for variable in
                                     variables]  # remap the dots to / and add the L ; or remap to a primitives character
                        variables = ["L" + file_name[variable] + ";" if variable in file_name else variable for variable
                                     in variables]  # get the obfuscated name of the class
                        variables = ["/".join(variable.split(".")) if "." in variable else variable for variable in
                                     variables]  # if the class is already packaged then change the obfuscated name
                        for i in range(len(variables)):  # restore the array brackets upfront for each variable
                            for j in range(array_length_variables[i]):
                                if variables[i][-1] == ";":
                                    variables[i] = "[" + variables[i][:-1] + ";"
                                else:
                                    variables[i] = "[" + variables[i]
                        variables = "".join(variables)

                    outputFile.write(f'\t{obf_name} ({variables}){method_type} {function_name}\n')
                else:
                    outputFile.write(f'\t{obf_name} {method_name}\n')

            else:
                obf_name = obf_name.split(":")[0]
                outputFile.write(remap_file_path(obf_name)[1:-1] + " " + remap_file_path(deobf_name)[1:-1] + "\n")
    if not quiet:
        print("Mappings converted!")


def make_paths(version, side, removal_bool, force, forceno):
    path = Path(f'mappings/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)
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

    path = Path(f'versions/{version}/{side}.jar')
    if path.exists() and path.is_file() and removal_bool:
        if force:
            path = Path(f'versions/{version}')
            shutil.rmtree(path)
            path.mkdir(parents=True)
        else:
            aw = input(f"versions/{version}/{side}.jar already exists, wipe it (w) or ignore (i) ? ") or "i"
            path = Path(f'versions/{version}')
            if aw == "w":
                shutil.rmtree(path)
                path.mkdir(parents=True)

    path = Path(f'src/{version}/{side}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if force:
            shutil.rmtree(Path(f"./src/{version}/{side}"))
        elif forceno:
            version = version + side + "_" + str(random.getrandbits(128))
        else:
            aw = input(
                f"/src/{version}/{side} already exists, wipe it (w), create a new folder (n) or kill the process (k) ? ")
            if aw == "w":
                shutil.rmtree(Path(f"./src/{version}/{side}"))
            elif aw == "n":
                version = version + side + "_" + str(random.getrandbits(128))
            else:
                raise KeyboardInterrupt
        path = Path(f'src/{version}/{side}')
        path.mkdir(parents=True)

    path = Path(f'tmp/{version}/{side}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)
    return version


def run(version, side, decompiler="cfr", quiet=True, clean=False, force=False, forceno=True):
    if not quiet:
        print("Decompiling using official Mojang mappings...")

    decompiled_version = make_paths(version, side, clean, force, forceno)
    get_global_manifest(quiet)
    get_version_manifest(version, quiet)

    get_mappings(version, side, quiet)
    convert_mappings(version, side, quiet)
    get_version_jar(version, side, quiet)
    remap(version, side, quiet)
    
    decompile(decompiler, decompiled_version, version, side, quiet, force)

    return decompiled_version


def main():
    check_java()
    snapshot, latest = get_latest_version()
    if snapshot is None or latest is None:
        raise Exception("Error getting latest versions, please refresh cache")
    # for arguments
    parser = argparse.ArgumentParser(description='Decompile Minecraft source code')
    parser.add_argument('--mcversion', '-mcv', type=str, dest='mcversion', default=latest,
                        help=f"The version you want to decompile (alid version starting from 19w36a (snapshot) and 1.14.4 (releases))\n"
                             f"Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest})")
    parser.add_argument('--interactive', '-i', type=str2bool, default=False,
                        help="Enable an interactive CLI to specify options (all other command line arguments, besides --quiet, will be ignored)")
    parser.add_argument('--side', '-s', type=str, dest='side', default="client",
                        help='The side you want to decompile (either client or server)')
    parser.add_argument('--clean', '-c', dest='clean', action='store_true', default=False,
                        help=f"Clean old runs")
    parser.add_argument('--force', '-f', dest='force', action='store_true', default=False,
                        help=f"Force resolving conflict by replacing old files.")
    parser.add_argument('--forceno', '-fn', dest='forceno', action='store_false', default=True,
                        help=f"Force resolving conflict by creating new directories.")
    parser.add_argument('--decompiler', '-d', type=str, dest='decompiler', default="cfr",
                        help=f"Choose between fernflower and cfr.")
    parser.add_argument('--quiet', '-q', dest='quiet', action='store_true', default=False,
                        help=f"Doesnt display the messages")
    
    use_flags = False
    args = parser.parse_args()

    try:
        if args.interactive:
            # Enable interactive mode

            args.clean = input("Do you want to clean up old runs? (y/N): ") in ["y", "yes"]

            version = input(f"Please input a valid version starting from 19w36a (snapshot) and 1.14.4 (releases),\n" +
                            f"Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest}): ") or latest
            if version in ["snap", "s", "snapshot"]:
                version = snapshot
            if version in ["latest", "l"]:
                version = latest
            args.mcversion = version

            args.side = SERVER if input("Please select either client or server side (C/s): ").lower() in ["server", "s"] else CLIENT
            args.decompiler = "fernflower" if input("Please input your decompiler of choice: cfr or fernflower (CFR/f): ").lower() in ["fernflower", "f"] else "cfr"

        decompiled_version = run(args.mcversion, args.side, args.decompiler, args.quiet, args.clean, args.force, args.forceno, steps)

    except KeyboardInterrupt:
        if not args.quiet:
            print("Keyboard interrupt detected, exiting")
        sys.exit(-1)
    except Exception as e:
        if not args.quiet:
            print("===Error detected!===")
            print(e)
            input("Press Enter key to exit")
            sys.exit(-1)
        else:
            raise e
    if not args.quiet:
        print("===FINISHED===")
        print(f"output is in /src/{decompiled_version}")
        input("Press Enter key to exit")


if __name__ == "__main__":
    main()
