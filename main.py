#!/usr/bin/env python3
import argparse
import glob
import hashlib
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
from typing import Literal, TypeAlias, Union
from urllib.error import HTTPError, URLError

if sys.version_info < (3, 7): raise OSError("Python verson must be 3.7 or above.")

CFR_VERSION = "0.152"
SPECIAL_SOURCE_VERSION = "1.11.4"
MANIFEST_LOCATION = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
CLIENT = "client"
SERVER = "server"
SideType: TypeAlias = Literal['client', 'server']
PATH_TO_ROOT_DIR = Path(os.path.dirname(sys.argv[0]))


def get_minecraft_path() -> Path:
    if sys.platform.startswith('linux'):
        return Path("~", ".minecraft")
    elif sys.platform.startswith('win'):
        return Path("~", "AppData", "Roaming", ".minecraft")
    elif sys.platform.startswith('darwin'):
        return Path("~", "Library", "Application Support", "minecraft")
    raise RuntimeError(f"Platform {sys.platform} is not supported.")


mc_path = get_minecraft_path()


def str2bool(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError(f'Could not convert {v} to a Boolean value.')


def check_java() -> None:
    """Check for Java and setup the proper directory if needed."""
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
        raise RuntimeError(
            'Java JDK is not installed! Please install a Java JDK from https://java.oracle.com, or install OpenJDK.')


def get_global_manifest(quiet) -> None:
    versionManifsetPath = (PATH_TO_ROOT_DIR / "versions" / "version_manifest.json")
    if versionManifsetPath.is_file():
        if not quiet:
            print(
                f"Manifest already exists; not downloading again. If another manifest is wanted, please delete manually before running the program (location: {versionManifsetPath}).")
        return
    download_file(MANIFEST_LOCATION, versionManifsetPath, quiet)


def download_file(url, filename: Path, quiet) -> None:
    try:
        if not quiet:
            print(f'Downloading {filename}...')
        f = urllib.request.urlopen(url)
        with open(filename, 'wb+') as local_file:
            local_file.write(f.read())
    except HTTPError as e:
        raise RuntimeError(f'HTTP Error: {e}')
    except URLError as e:
        raise RuntimeError(f'URL Error: {e}')


def get_latest_version() -> tuple[str, str]:
    path_to_json = (PATH_TO_ROOT_DIR / 'manifest.json')
    download_file(MANIFEST_LOCATION, path_to_json, True)
    snapshot = None
    release = None
    if path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["latest"]
            if versions and versions.get("release"):
                release: str = versions.get("release")
            if versions and versions.get("snapshot"):
                snapshot: str = versions.get("snapshot")
    path_to_json.unlink()
    if release is None:
        raise RuntimeError("Could not get latest release. Please refresh cache.")
    if snapshot is None:
        raise RuntimeError("Could not get latest snapshot. Please refresh cache.")
    return snapshot, release


def get_version_manifest(target_version: str, quiet) -> None:
    version_path = (PATH_TO_ROOT_DIR / "versions" / target_version / "version.json")
    if version_path.is_file():
        if not quiet:
            print(
                f"Version manifest already exists; not downloading again. If another version manifest is wanted, please delete manually before running the program (location: {version_path}).")
        return
    path_to_json = (PATH_TO_ROOT_DIR / "versions" / "version_manifest.json")
    if not path_to_json.exists() or not path_to_json.is_file(): raise RuntimeError(
        f'Missing manifest file: {path_to_json}')
    path_to_json = path_to_json.resolve()
    with open(path_to_json) as f:
        versions = json.load(f)["versions"]
        for version in versions:
            if version.get("id") and version.get("id") == target_version and version.get("url"):
                download_file(version.get("url"), version_path, quiet)
                break


def sha256(fname: Union[Union[str, bytes], int]) -> str:
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_version_jar(target_version: str, side: SideType, quiet) -> None:
    path_to_json = (PATH_TO_ROOT_DIR / "versions" / target_version / "version.json")
    target_side_path = (PATH_TO_ROOT_DIR / "versions" / target_version / f"{side}.jar")
    if target_side_path.is_file():
        if not quiet:
            print(
                f"Version jar already exists; not downloading again. If another version jar is wanted, please delete manually before running the program (location: {target_side_path}).")
        return
    if not path_to_json.exists() or not path_to_json.is_file(): raise RuntimeError(
        f'Missing manifest file: {path_to_json}')
    path_to_json = path_to_json.resolve()
    with open(path_to_json) as f:
        jsn = json.load(f)
        if not jsn.get("downloads") or not jsn.get("downloads").get(side) or not jsn.get("downloads").get(side).get(
            "url"):
            raise RuntimeError("Could not download jar, missing fields")
        download_file(jsn.get("downloads").get(side).get("url"), target_side_path, quiet)
        # In case the server is newer than 21w39a you need to actually extract it first from the archive
        if side == SERVER:
            if not target_side_path.exists():
                raise RuntimeError(
                    f"Jar was maybe downloaded but not located, this is a failure, check path at {target_side_path}")
            with zipfile.ZipFile(target_side_path, mode="r") as z:
                content = None
                try:
                    content = z.read(Path(f"META-INF", "versions.list"))
                except Exception as _:
                    # we don't have a versions.list in it
                    pass
                if content is not None:
                    element = content.split(b"\t")
                    if len(element) != 3:
                        raise RuntimeError(
                            f"Jar should be extracted but version list is not in the correct format, expected 3 fields, got {len(element)} for {content}")
                    version_hash = element[0].decode()
                    version = element[1].decode()
                    path = element[2].decode()
                    if version != target_version and not quiet:
                        print(
                            f"Warning: received version ({version}) does not match the targeted version ({target_version}).")
                    new_jar_path = (PATH_TO_ROOT_DIR / "versions" / target_version)
                    try:
                        new_jar_path = z.extract(Path("META-INF", "versions", path), new_jar_path)
                    except Exception as e:
                        raise RuntimeError(f"Could not extract to {new_jar_path}: {e}")
                    if not (PATH_TO_ROOT_DIR / new_jar_path).exists():
                        raise RuntimeError(f"New {side} jar could not be extracted from archive at {new_jar_path}.")
                    file_hash = sha256(new_jar_path)
                    if file_hash != version_hash:
                        raise RuntimeError(
                            f"Extracted file's hash ({file_hash}) and expected hash ({version_hash}) did not match.")
                    try:
                        shutil.move((PATH_TO_ROOT_DIR / new_jar_path), target_side_path)
                        shutil.rmtree((PATH_TO_ROOT_DIR / "versions" / target_version / "META-INF"))
                    except Exception as e:
                        raise RuntimeError("Exception while removing the temp file", e)
    if not quiet:
        print("Done !")


def get_mappings(version: str, side: SideType, quiet) -> None:
    versionSidePath = (PATH_TO_ROOT_DIR / "mappings" / version / f"{side}.txt")
    if versionSidePath.is_file():
        if not quiet:
            print(
                f"Mappings already exist; not downloading again. If other mappings are wanted, please delete manually before running the program (location: {versionSidePath}).")
        return
    path_to_json = (PATH_TO_ROOT_DIR / "versions" / version / "version.json")
    if not path_to_json.exists() or not path_to_json.is_file():
        raise RuntimeError(f'Missing manifest file: {path_to_json}')
    if not quiet:
        print(f'Found {path_to_json}')
    path_to_json = path_to_json.resolve()
    with open(path_to_json) as f:
        jfile = json.load(f)
        url = jfile['downloads']
        if side == CLIENT:  # client:
            if 'client_mappings' not in url or 'url' not in url['client_mappings']:
                # TODO: Clean up failed run before raising
                raise RuntimeError(f'Could not find client mappings for {version}')
            url = url['client_mappings']['url']
        elif side == SERVER:  # server
            if 'server_mappings' not in url or 'url' not in url['server_mappings']:
                # TODO: Clean up failed run before raising
                raise RuntimeError(f'Could not find server mappings for {version}')
            url = url['server_mappings']['url']
        else:
            raise RuntimeError('Type not recognized.')
        if not quiet:
            print(f'Downloading the mappings for {version}...')
        download_file(url,
                      (PATH_TO_ROOT_DIR / "mappings" / version / f"{'client' if side == CLIENT else 'server'}.txt"),
                      quiet)


def remap(version: str, side: SideType, quiet) -> None:
    if not quiet:
        print('=== Remapping jar using SpecialSource ====')
    t = time.time()
    path = (PATH_TO_ROOT_DIR / "versions" / version / f"{side}.jar")
    # that part will not be assured by arguments
    if not path.exists() or not path.is_file():
        path_temp = (mc_path / "versions" / version / f"{version}.jar").expanduser()
        if path_temp.is_file():
            # TODO: Automate choice if auto mode is enabled
            r = input("Error: defaulting to client.jar from your local Minecraft folder. Continue? (y/n)") or "y"
            if r != "y":
                # TODO: Replace with something else
                sys.exit(-1)
            path = path_temp
    if not path.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {path}')
    path = path.resolve()

    mapp = (PATH_TO_ROOT_DIR / "mappings" / version / f"{side}.tsrg")
    if not mapp.exists() or not mapp.is_file():
        raise RuntimeError(f'Missing file: {mapp}')
    mapp = mapp.resolve()

    special_source_path = (PATH_TO_ROOT_DIR / "lib" / f"SpecialSource-{SPECIAL_SOURCE_VERSION}.jar")
    if not special_source_path.exists() or not special_source_path.is_file():
        raise RuntimeError(f'Missing file: {special_source_path}')
    special_source_path = special_source_path.resolve()
    out_jar_path = (PATH_TO_ROOT_DIR / "src" / f"{version}-{side}-temp.jar")

    subprocess.run(['java',
                    '-jar', special_source_path.__str__(),
                    '--in-jar', path.__str__(),
                    '--out-jar', out_jar_path,
                    '--srg-in', mapp.__str__(),
                    "--kill-lvt"  # kill snowmen
                    ], check=True, capture_output=quiet)
    if not quiet:
        print(f'Created {out_jar_path}.')
        t = time.time() - t
        print('Done in %.1fs' % t)


def decompile_fern_flower(decompiled_version: str, version: str, side: SideType, quiet, force) -> None:
    if not quiet:
        print('=== Decompiling using FernFlower (silent) ===')
    t = time.time()

    path = (PATH_TO_ROOT_DIR / "src" / f"{version}-{side}-temp.jar")
    if not path.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {path}')
    path = path.resolve()

    fernflower = (PATH_TO_ROOT_DIR / "lib" / "fernflower.jar")
    if not fernflower.exists() or not fernflower.is_file():
        raise RuntimeError(f'Missing file: {fernflower}')
    fernflower = fernflower.resolve()

    side_folder = (PATH_TO_ROOT_DIR / "src" / decompiled_version / side)
    subprocess.run(['java',
                    '-Xmx4G',
                    '-Xms1G',
                    '-jar', fernflower.__str__(),
                    '-hes=0',  # hide empty super invocation deactivated (might clutter but allow following)
                    '-hdc=0',  # hide empty default constructor deactivated (allow to track)
                    '-dgs=1',  # decompile generic signatures activated (make sure we can follow types)
                    '-lit=1',  # output numeric literals
                    '-asc=1',  # encode non-ASCII characters in string and character
                    '-log=WARN',
                    path.__str__(), side_folder
                    ], check=True, capture_output=quiet)
    if not quiet:
        print(f'Removing {path}...')
    os.remove(path)
    if not quiet:
        print("Decompressing remapped jar to directory...")
    with zipfile.ZipFile(side_folder / f"{version}-{side}-temp.jar") as z:
        z.extractall(path=side_folder)
    t = time.time() - t
    if not quiet:
        print(f'Done in %.1fs (file was decompressed in {decompiled_version}/{side})' % t)
        # TODO: Automate choice if auto mode is enabled
        print('Remove Extra Jar file? (y/n): ')
        response = input() or "y"
        if response == 'y':
            print(f'Removing {side_folder / f"{version}-{side}-temp.jar"}...')
            os.remove(side_folder / f"{version}-{side}-temp.jar")
    if force:
        os.remove(side_folder / f'{version}-{side}-temp.jar')


def decompile_cfr(decompiled_version: str, version: str, side: SideType, quiet) -> None:
    if not quiet:
        print('=== Decompiling using CFR (silent) ===')
    t = time.time()

    path = (PATH_TO_ROOT_DIR / "src" / f"{version}-{side}-temp.jar")
    if not path.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {path}')
    path = path.resolve()

    cfr = (PATH_TO_ROOT_DIR / "lib" / f"cfr-{CFR_VERSION}.jar")
    if not cfr.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {cfr}')
    cfr = cfr.resolve()

    side_folder = (PATH_TO_ROOT_DIR / "src" / decompiled_version / side)
    subprocess.run(['java',
                    '-Xmx4G',
                    '-Xms1G',
                    '-jar', cfr.__str__(),
                    path.__str__(),
                    '--outputdir', side_folder,
                    '--caseinsensitivefs', 'true',
                    "--silent", "true"
                    ], check=True, capture_output=quiet)
    if not quiet:
        print(f'Removing {path}...')
    os.remove(path)
    if not quiet:
        print(f'Removing {side_folder / "summary.txt"}...')
    os.remove(side_folder / "summary.txt")
    if not quiet:
        t = time.time() - t
        print('Done in %.1fs' % t)


def remove_brackets(line: str, counter: int) -> tuple[str, int]:
    while '[]' in line:  # get rid of the array brackets while counting them
        counter += 1
        line = line[:-2]
    return line, counter


def remap_file_path(path: str) -> str:
    remap_primitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J", "byte": "B", "short": "S",
                        "char": "C", "void": "V"}
    return "L" + "/".join(path.split(".")) + ";" if path not in remap_primitives else remap_primitives[path]


def convert_mappings(version: str, side: SideType, quiet) -> None:
    version_side_path = (PATH_TO_ROOT_DIR / "mappings" / version / f"{side}.txt")
    with open(version_side_path, 'r') as inputFile:
        file_name: dict[str, str] = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if not line.startswith('    '):
                obf_name = obf_name.split(":")[0]
                file_name[remap_file_path(deobf_name)] = obf_name  # save it to compare to put the Lb

    with open(version_side_path, 'r') as inputFile, open(PATH_TO_ROOT_DIR / "mappings" / version / f"{side}.tsrg",
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
                            for _ in range(array_length_variables[i]):
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


def make_paths(version: str, side: SideType, removal_bool, force, forceno) -> str:
    path = (PATH_TO_ROOT_DIR / "mappings" / version)
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)

    path = (PATH_TO_ROOT_DIR / "versions" / version)
    if not path.exists():
        path.mkdir(parents=True)
    else:
        path = (path / "version.json")
        if path.is_file() and removal_bool:
            path.unlink()

    if (PATH_TO_ROOT_DIR / "versions").exists():
        path = (PATH_TO_ROOT_DIR / "versions" / "version_manifest.json")
        if path.is_file() and removal_bool:
            path.unlink()

    path = (PATH_TO_ROOT_DIR / "versions" / version / f"{side}.jar")
    if path.is_file() and removal_bool:
        if force:
            path = (PATH_TO_ROOT_DIR / "versions" / version)
            shutil.rmtree(path)
            path.mkdir(parents=True)
        else:
            aw = input(f"versions/{version}/{side}.jar already exists, wipe it (w) or ignore (i) ? ") or "i"
            path = (PATH_TO_ROOT_DIR / "versions" / version)
            if aw == "w":
                shutil.rmtree(path)
                path.mkdir(parents=True)

    path = (PATH_TO_ROOT_DIR / "src" / version / side)
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if force:
            shutil.rmtree(path)
        elif forceno:
            version = version + side + "_" + str(random.getrandbits(128))
            path = (PATH_TO_ROOT_DIR / "src" / version / side)
        else:
            aw = input(
                f"/src/{version}/{side} already exists, wipe it (w), create a new folder (n) or kill the process (k) ? ") or "n"
            if aw == "w":
                shutil.rmtree(path)
            elif aw == "n":
                version = version + side + "_" + str(random.getrandbits(128))
                path = (PATH_TO_ROOT_DIR / "src" / version / side)
            else:
                sys.exit(-1)
        path.mkdir(parents=True)

    path = (PATH_TO_ROOT_DIR / "tmp" / version / side)
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if removal_bool:
            shutil.rmtree(path)
            path.mkdir(parents=True)
    return version


def delete_dependencies(version: str, side: SideType) -> None:
    path = (PATH_TO_ROOT_DIR / "tmp" / version / side)
    temp_jar_path = (PATH_TO_ROOT_DIR / "src" / f"{version}-{side}-temp.jar")
    with zipfile.ZipFile(temp_jar_path) as z:
        z.extractall(path=path)

    for _dir in [join(path, "com"), path]:
        for f in os.listdir(_dir):
            if os.path.isdir(join(_dir, f)) and split(f)[-1] not in ['net', 'assets', 'data', 'mojang', 'com',
                                                                     'META-INF']:
                shutil.rmtree(join(_dir, f))

    with zipfile.ZipFile(temp_jar_path, 'w') as z:
        for f in glob.iglob(f'{path}{os.sep}**', recursive=True):
            z.write(f, arcname=f[len(str(path)) + 1:])


def main():
    check_java()
    snapshot, latest = get_latest_version()
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
                        help=f"Force resolve conflicts by replacing old files.")
    parser.add_argument('--forceno', '-fn', dest='forceno', action='store_false', default=True,
                        help=f"Force resolve conflicts by creating new directories.")
    parser.add_argument('--decompiler', '-d', type=str, dest='decompiler', default="cfr",
                        help=f"Choose between Fernflower and CFR.")
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
        print(
            "Decompiling using official Mojang mappings (Default options are in uppercase, you can just press Enter):")
    if use_flags:
        removal_bool = args.clean
    else:
        removal_bool = input("Do you want to clean up old runs? (y/N): ") in ["y", "yes"]
    if use_flags:
        decompiler = args.decompiler
    else:
        decompiler = input("Please input your decompiler choice: Fernflower or CFR (CFR/f): ")
    decompiler = decompiler.lower() if decompiler.lower() in ["fernflower", "cfr", "f"] else "cfr"
    if use_flags:
        version: str | None = args.mcversion
        if version is None:
            raise ValueError('You must provide a version with --mcversion <version, "latest", or "snap">')
    else:
        version = input(f"Please input a valid version starting from 19w36a (snapshot) or 1.14.4 (releases).\n" +
                        f"Use 'snap' for the latest snapshot ({snapshot}) or 'latest' for the latest version ({latest}) :") or latest
    if version in ["snap", "s", "snapshot"]:
        version = snapshot
    if version in ["latest", "l"]:
        version = latest
    if use_flags:
        side: str = args.side
    else:
        side = input("Please select either client or server side (C/s) : ")
    side = side.lower() if side.lower() in ("client", "server", "c", "s") else CLIENT
    side = CLIENT if side in ("client", "c") else SERVER
    decompiled_version = make_paths(version, side, removal_bool, args.force, args.forceno)
    get_global_manifest(args.quiet)
    get_version_manifest(version, args.quiet)
    if use_flags:
        r = not args.nauto
    else:
        r = input("Auto mode? (Y/n): ") or "y"
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
            print(f"Output is in /src/{decompiled_version}")
        return

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
        print(f"Output is in /src/{decompiled_version}")


if __name__ == "__main__":
    main()
