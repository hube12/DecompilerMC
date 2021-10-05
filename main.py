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
        sys.exit(-1)


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
        print('Java JDK is not installed ! Please install java JDK from https://java.oracle.com or OpenJDK')
        input("Aborting, press anything to exit")
        sys.exit(1)


def get_global_manifest(quiet):
    if Path(f"versions/version_manifest.json").exists() and Path(f"versions/version_manifest.json").is_file():
        if not quiet:
            print(
                "Manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    download_file(MANIFEST_LOCATION, f"versions/version_manifest.json", quiet)


def download_file(url, filename, quiet):
    try:
        if not quiet:
            print(f'Downloading {filename}...')
        f = urllib.request.urlopen(url)
        with open(filename, 'wb+') as local_file:
            local_file.write(f.read())
    except HTTPError as e:
        if not quiet:
            print('HTTP Error')
            print(e)
        sys.exit(-1)
    except URLError as e:
        if not quiet:
            print('URL Error')
            print(e)
        sys.exit(-1)


def get_latest_version():
    download_file(MANIFEST_LOCATION, f"manifest.json", True)
    path_to_json = Path(f'manifest.json')
    snapshot = None
    version = None
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["latest"]
            if versions and versions.get("release") and versions.get("release"):
                version = versions.get("release")
                snapshot = versions.get("snapshot")
    path_to_json.unlink()
    return snapshot, version


def get_version_manifest(target_version, quiet):
    if Path(f"versions/{target_version}/version.json").exists() and Path(f"versions/{target_version}/version.json").is_file():
        if not quiet:
            print(
                "Version manifest already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path(f'versions/version_manifest.json')
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["versions"]
            for version in versions:
                if version.get("id") and version.get("id") == target_version and version.get("url"):
                    download_file(version.get("url"), f"versions/{target_version}/version.json", quiet)
                    break
    else:
        if not quiet:
            print('ERROR: Missing manifest file: version.json')
            input("Aborting, press anything to exit")
        sys.exit(-1)


def sha256(fname: Union[Union[str, bytes], int]):
    import hashlib
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_version_jar(target_version, side, quiet):
    path_to_json = Path(f"versions/{target_version}/version.json")
    if Path(f"versions/{target_version}/{side}.jar").exists() and Path(f"versions/{target_version}/{side}.jar").is_file():
        if not quiet:
            print(f"versions/{target_version}/{side}.jar already existing, not downloading again")
        return
    if path_to_json.exists() and path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jsn = json.load(f)
            if jsn.get("downloads") and jsn.get("downloads").get(side) and jsn.get("downloads").get(side).get("url"):
                jar_path = f"versions/{target_version}/{side}.jar"
                download_file(jsn.get("downloads").get(side).get("url"), jar_path, quiet)
                # In case the server is newer than 21w39a you need to actually extract it first from the archive
                if side == SERVER:
                    if Path(jar_path).exists():
                        with zipfile.ZipFile(jar_path, mode="r") as z:
                            content = None
                            try:
                                content = z.read("META-INF/versions.list")
                            except Exception as e:
                                # we don't have a versions.list in it
                                pass
                            if content != None:
                                element = content.split(b"\t")
                                if len(element) != 3:
                                    print(f"Jar should be extracted but version list is not in the correct format, expected 3 fields, got {len(element)} for {content}")
                                    sys.exit(-1)
                                version_hash = element[0].decode()
                                version = element[1].decode()
                                path = element[2].decode()
                                if version != target_version and not quiet:
                                    print(f"Warning, version is not identical to the one targeted got {version} exepected {target_version}")
                                new_jar_path = f"versions/{target_version}"
                                try:
                                    new_jar_path = z.extract(f"META-INF/versions/{path}", new_jar_path)
                                except Exception as e:
                                    print(f"Could not extract to {new_jar_path} with error {e}")
                                    sys.exit(-1)
                                if Path(new_jar_path).exists():
                                    file_hash = sha256(new_jar_path)
                                    if file_hash != version_hash:
                                        print(f"Extracted file hash and expected hash did not match up, got {file_hash} expected {version_hash}")
                                        sys.exit(-1)
                                    try:
                                        shutil.move(new_jar_path, jar_path)
                                        shutil.rmtree(f"versions/{target_version}/META-INF")
                                    except Exception as e:
                                        print("Exception while removing the temp file", e)
                                        sys.exit(-1)
                                else:
                                    print(f"New {side} jar could not be extracted from archive at {new_jar_path}, failure")
                                    sys.exit(-1)
                    else:
                        print(f"Jar was maybe downloaded but not located, this is a failure, check path at {jar_path}")
                        sys.exit(-1)
            else:
                if not quiet:
                    print("Could not download jar, missing fields")
                    input("Aborting, press anything to exit")
                sys.exit(-1)
    else:
        if not quiet:
            print('ERROR: Missing manifest file: version.json')
            input("Aborting, press anything to exit")
        sys.exit(-1)
    if not quiet:
        print("Done !")


def get_mappings(version, side, quiet):
    if Path(f'mappings/{version}/{side}.txt').exists() and Path(f'mappings/{version}/{side}.txt').is_file():
        if not quiet:
            print(
                "Mappings already existing, not downloading again, if you want to please accept safe removal at beginning")
        return
    path_to_json = Path(f'versions/{version}/version.json')
    if path_to_json.exists() and path_to_json.is_file():
        if not quiet:
            print(f'Found {version}.json')
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            jfile = json.load(f)
            url = jfile['downloads']
            if side == CLIENT:  # client:
                if url['client_mappings']:
                    url = url['client_mappings']['url']
                else:
                    if not quiet:
                        print(f'Error: Missing client mappings for {version}')
            elif side == SERVER:  # server
                if url['server_mappings']:
                    url = url['server_mappings']['url']
                else:
                    if not quiet:
                        print(f'Error: Missing server mappings for {version}')
            else:
                if not quiet:
                    print('ERROR, type not recognized')
                sys.exit(-1)
            if not quiet:
                print(f'Downloading the mappings for {version}...')
            download_file(url, f'mappings/{version}/{"client" if side == CLIENT else "server"}.txt', quiet)
    else:
        if not quiet:
            print('ERROR: Missing manifest file: version.json')
            input("Aborting, press anything to exit")
        sys.exit(-1)


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
    specialsource = Path('./lib/SpecialSource-1.9.1.jar')
    if path.exists() and mapp.exists() and specialsource.exists() and path.is_file() and mapp.is_file() and specialsource.is_file():
        path = path.resolve()
        mapp = mapp.resolve()
        specialsource = specialsource.resolve()
        subprocess.run(['java',
                        '-jar', specialsource.__str__(),
                        '--in-jar', path.__str__(),
                        '--out-jar', f'./src/{version}-{side}-temp.jar',
                        '--srg-in', mapp.__str__(),
                        "--kill-lvt"  # kill snowmen
                        ], check=True, capture_output=quiet)
        if not quiet:
            print(f'- New -> {version}-{side}-temp.jar')
            t = time.time() - t
            print('Done in %.1fs' % t)
    else:
        if not quiet:
            print(
                f'ERROR: Missing files: ./lib/SpecialSource-1.8.6.jar or mappings/{version}/{side}.tsrg or versions/{version}/{side}.jar')
            input("Aborting, press anything to exit")
        sys.exit(-1)


def decompile_fern_flower(decompiled_version, version, side, quiet, force):
    if not quiet:
        print('=== Decompiling using FernFlower (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{side}-temp.jar')
    fernflower = Path('./lib/fernflower.jar')
    if path.exists() and fernflower.exists():
        path = path.resolve()
        fernflower = fernflower.resolve()
        subprocess.run(['java',
                        '-Xmx4G',
                        '-Xms1G',
                        '-jar', fernflower.__str__(),
                        '-hes=0',  # hide empty super invocation deactivated (might clutter but allow following)
                        '-hdc=0',  # hide empty default constructor deactivated (allow to track)
                        '-dgs=1',  # decompile generic signatures activated (make sure we can follow types)
                        '-ren=1',  # rename ambiguous activated
                        '-lit=1',  # output numeric literals
                        '-asc=1',  # encode non-ASCII characters in string and character
                        '-log=WARN',
                        path.__str__(), f'./src/{decompiled_version}/{side}'
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
            print('Done in %.1fs (file was decompressed in {decompiled_version}/{side})' % t)
            print(f'Remove Extra Jar file? (y/n): ')
            response = input() or "y"
            if response == 'y':
                print(f'- Removing -> {decompiled_version}/{side}/{version}-{side}-temp.jar')
                os.remove(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar')
        if force:
            os.remove(f'./src/{decompiled_version}/{side}/{version}-{side}-temp.jar')

    else:
        if not quiet:
            print(f'ERROR: Missing files: ./lib/fernflower.jar or ./src/{version}-{side}-temp.jar')
            input("Aborting, press anything to exit")
        sys.exit(-1)


def decompile_cfr(decompiled_version, version, side, quiet):
    if not quiet:
        print('=== Decompiling using CFR (silent) ===')
    t = time.time()
    path = Path(f'./src/{version}-{side}-temp.jar')
    cfr = Path('./lib/cfr-0.146.jar')
    if path.exists() and cfr.exists():
        path = path.resolve()
        cfr = cfr.resolve()
        subprocess.run(['java',
                        '-Xmx4G',
                        '-Xms1G',
                        '-jar', cfr.__str__(),
                        path.__str__(),
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
    else:
        if not quiet:
            print(f'ERROR: Missing files: ./lib/cfr-0.146.jar or ./src/{version}-{side}-temp.jar')
            input("Aborting, press anything to exit")
        sys.exit(-1)


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
        print("Done !")


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
                sys.exit(-1)
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


def delete_dependencies(version, side):
    path = f'./tmp/{version}/{side}'

    with zipfile.ZipFile(f'./src/{version}-{side}-temp.jar') as z:
        z.extractall(path=path)

    for _dir in [join(path, "com"), path]:
        for f in os.listdir(_dir):
            if os.path.isdir(join(_dir, f)) and split(f)[-1] not in ['net', 'assets', 'data', 'mojang', 'com',
                                                                     'META-INF']:
                shutil.rmtree(join(_dir, f))

    with zipfile.ZipFile(f'./src/{version}-{side}-temp.jar', 'w') as z:
        for f in glob.iglob(f'{path}/**', recursive=True):
            z.write(f, arcname=f[len(path) + 1:])


def main():
    check_java()
    snapshot, latest = get_latest_version()
    if snapshot is None or latest is None:
        print("Error getting latest versions, please refresh cache")
        sys.exit(1)
    # for arguments
    parser = argparse.ArgumentParser(description='Decompile Minecraft source code')
    parser.add_argument('--mcversion', '-mcv', type=str, dest='mcversion',
                        help=f"The version you want to decompile (alid version starting from 19w36a (snapshot) and 1.14.4 (releases))\n"
                             f"Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest})")
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
    parser.add_argument('--nauto', '-na', dest='nauto', action='store_true', default=False,
                        help=f"Choose between auto and manual mode.")
    parser.add_argument('--download_mapping', '-dm', nargs='?', const=True, type=str2bool, dest='download_mapping',
                        default=True,
                        required="--nauto" in sys.argv or "-na" in sys.argv,
                        help=f"Download the mappings (only if auto off)")
    parser.add_argument('--remap_mapping', '-rmap', nargs='?', const=True, type=str2bool, dest='remap_mapping',
                        default=True,
                        required="--nauto" in sys.argv or "-na" in sys.argv,
                        help=f"Remap the mappings to tsrg (only if auto off)")
    parser.add_argument('--download_jar', '-dj', nargs='?', const=True, type=str2bool, dest='download_jar',
                        default=True,
                        required="--nauto" in sys.argv or "-na" in sys.argv,
                        help=f"Download the jar (only if auto off)")
    parser.add_argument('--remap_jar', '-rjar', nargs='?', const=True, type=str2bool, dest='remap_jar', default=True,
                        required="--nauto" in sys.argv or "-na" in sys.argv, help=f"Remap the jar (only if auto off)")
    parser.add_argument('--delete_dep', '-dd', nargs='?', const=True, type=str2bool, dest='delete_dep', default=True,
                        required="--nauto" in sys.argv or "-na" in sys.argv,
                        help=f"Delete the dependencies (only if auto off)")
    parser.add_argument('--decompile', '-dec', nargs='?', const=True, type=str2bool, dest='decompile', default=True,
                        required="--nauto" in sys.argv or "-na" in sys.argv, help=f"Decompile (only if auto off)")
    parser.add_argument('--quiet', '-q', dest='quiet', action='store_true', default=False,
                        help=f"Doesnt display the messages")
    use_flags = False
    args = parser.parse_args()
    if args.mcversion:
        use_flags = True
    if not args.quiet:
        print("Decompiling using official mojang mappings (Default option are in uppercase, you can just enter)")
    if use_flags:
        removal_bool = args.clean
    else:
        removal_bool = 1 if input("Do you want to clean up old runs? (y/N): ") in ["y", "yes"] else 0
    if use_flags:
        decompiler = args.decompiler
    else:
        decompiler = input("Please input you decompiler choice: fernflower or cfr (CFR/f): ")
    decompiler = decompiler.lower() if decompiler.lower() in ["fernflower", "cfr", "f"] else "cfr"
    if use_flags:
        version = args.mcversion
        if version is None:
            print(
                "Error you should provide a version with --mcversion <version>, use latest or snap if you dont know which one")
            sys.exit(-1)
    else:
        version = input(f"Please input a valid version starting from 19w36a (snapshot) and 1.14.4 (releases),\n" +
                        f"Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest}) :") or latest
    if version in ["snap", "s", "snapshot"]:
        version = snapshot
    if version in ["latest", "l"]:
        version = latest
    if use_flags:
        side = args.side
    else:
        side = input("Please select either client or server side (C/s) : ")
    side = side.lower() if side.lower() in ["client", "server", "c", "s"] else CLIENT
    side = CLIENT if side in ["client", "c"] else SERVER
    decompiled_version = make_paths(version, side, removal_bool, args.force, args.forceno)
    get_global_manifest(args.quiet)
    get_version_manifest(version, args.quiet)
    if use_flags:
        r = not args.nauto
    else:
        r = input("Auto Mode? (Y/n): ") or "y"
        r = r.lower() == "y"
    if r:
        get_mappings(version, side, args.quiet)
        convert_mappings(version, side, args.quiet)
        get_version_jar(version, side, args.quiet)
        remap(version, side, args.quiet)
        if decompiler.lower() == "cfr":
            decompile_cfr(decompiled_version, version, side, args.quiet)
        else:
            decompile_fern_flower(decompiled_version, version, side, args.quiet, args.force)
        if not args.quiet:
            print("===FINISHED===")
            print(f"output is in /src/{version}")
            input("Press Enter key to exit")
        sys.exit(0)

    if use_flags:
        r = args.download_mapping
    else:
        r = input('Download mappings? (y/n): ') or "y"
        r = r.lower() == "y"
    if r:
        get_mappings(version, side, args.quiet)

    if use_flags:
        r = args.remap_mapping
    else:
        r = input('Remap mappings to tsrg? (y/n): ') or "y"
        r = r.lower() == "y"
    if r:
        convert_mappings(version, side, args.quiet)

    if use_flags:
        r = args.download_jar
    else:
        r = input(f'Get {version}-{side}.jar ? (y/n): ') or "y"
        r = r.lower() == "y"
    if r:
        get_version_jar(version, side, args.quiet)

    if use_flags:
        r = args.remap_jar
    else:
        r = input('Remap? (y/n): ') or "y"
        r = r.lower() == "y"
    if r:
        remap(version, side, args.quiet)

    if use_flags:
        r = args.delete_dep
    else:
        r = input('Delete Dependencies? (y/n): ') or "y"
        r = r.lower() == "y"
    if r:
        delete_dependencies(version, side)

    if use_flags:
        r = args.decompile
    else:
        r = input('Decompile? (y/n): ') or "y"
        r = r.lower() == "y"
    if r:
        if decompiler.lower() == "cfr":
            decompile_cfr(decompiled_version, version, side, args.quiet)
        else:
            decompile_fern_flower(decompiled_version, version, side, args.quiet, args.force)
    if not args.quiet:
        print("===FINISHED===")
        print(f"output is in /src/{decompiled_version}")
        input("Press Enter key to exit")
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
