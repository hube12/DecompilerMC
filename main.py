#!/usr/bin/env python3
import argparse
import datetime
import glob
import hashlib
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
import zipfile
from os.path import join, split
from pathlib import Path
from shutil import which
from subprocess import CalledProcessError
from typing import Literal, TypeAlias, Union
from urllib.error import HTTPError, URLError

if sys.version_info < (3, 7): raise OSError("Python version must be 3.7 or above.")

SPECIAL_SOURCE_VERSION = "1.11.6"
MANIFEST_LOCATION = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
CLIENT = "client"
SERVER = "server"
DECOMPILERS = {
    "fernflower": {},
    "cfr": {"version": "0.152"}
}
SideType: TypeAlias = Literal['client', 'server']

cwd = Path(__file__).parent

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

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

def is_file_outdated(path: Path) -> bool:
    creation_time = datetime.datetime.fromtimestamp(os.path.getctime(path))
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    return creation_time < yesterday

def delete_file(path: Path) -> None:
    logging.debug(f"Removing {path}...")
    os.remove(path)

def check_java() -> bool:
    """Check for a Java installation"""
    if sys.platform.startswith('win'):
        # Check Windows registry
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
                return True
            except (CalledProcessError, OSError):
                pass

        # Check for global installation
        try:
            subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
            return True
        except (CalledProcessError, OSError):
            pass

        # Check in known installation paths
        if which('java.exe', path=os.environ['ProgramW6432']) or \
            which('java.exe', path=os.environ['ProgramFiles']) or \
            which('java.exe', path=os.environ['ProgramFiles(x86)']):
            return True

    elif sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        # Check for global installation
        try:
            subprocess.run(['java', '-version'], stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, check=True)
            return True
        except (CalledProcessError, OSError):
            pass

        # Check in known installation paths
        if which('java', path='/usr/bin') or which('java', path='/usr/local/bin') or which('java', path='/opt'):
            return True

    else:
        raise OSError(f"Unknown platform: {sys.platform}")
    
    raise RuntimeError('Java JDK is not installed! Please install a Java JDK from https://java.oracle.com, or install OpenJDK.')


def get_global_manifest() -> None:
    version_manifest = cwd / "versions" / "version_manifest.json"
    if version_manifest.exists() and version_manifest.is_file() and not is_file_outdated(version_manifest):
        logging.info("Manifest already exists, not downloading again")
        return
    download_file(MANIFEST_LOCATION, version_manifest)


def download_file(url: str, filename: Path) -> None:
    try:
        logging.debug(f'Downloading {url} to {filename}...')
        f = urllib.request.urlopen(url)
        if filename.exists():
            filename.unlink()
        filename.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'wb+') as local_file:
            local_file.write(f.read())
            logging.debug(f'Downloaded {filename} successfully!')
    except (HTTPError, URLError) as e:
        if Path(filename).exists():
            logging.warning(f'Failed to download {filename}, using cached version')
            return
        raise e


def get_latest_version() -> tuple[str | None, str | None]:
    path_to_json = cwd / "tmp" / "manifest.json"
    download_file(MANIFEST_LOCATION, path_to_json)
    snapshot: str | None = None
    release: str | None = None
    if path_to_json.is_file():
        path_to_json = path_to_json.resolve()
        with open(path_to_json) as f:
            versions = json.load(f)["latest"]
            if versions:
                release = versions.get("release")
                snapshot = versions.get("snapshot")

    if snapshot is None or release is None:
        raise RuntimeError("Error getting latest versions, please refresh cache")

    return snapshot, release


def get_version_manifest(target_version: str) -> None:
    version_json = cwd / "versions" / target_version / "version.json"
    if version_json.exists() and version_json.is_file():
        logging.info("Version manifest already exists, not downloading again")
        return
    version_manifest = cwd / "versions" / "version_manifest.json"
    if not (version_manifest.exists() and version_manifest.is_file()):
        raise RuntimeError(f'Missing manifest file: {version_manifest}')
    
    version_manifest = version_manifest.resolve()
    with open(version_manifest) as f:
        versions = json.load(f)["versions"]
        for version in versions:
            if version.get("id") and version.get("id") == target_version and version.get("url"):
                download_file(version.get("url"), version_json)
                break


def sha256(fname: Union[Union[str, bytes], int]) -> str:
    import hashlib
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def get_version_jar(target_version: str, side: SideType) -> None:
    version_json = cwd / "versions" / target_version / "version.json"
    jar_path = cwd / "versions" / target_version / f"{side}.jar"
    if jar_path.exists() and jar_path.is_file():
        logging.info(f"{jar_path} already exists, not downloading again")
        return
    if not (version_json.exists() and version_json.is_file()):
        raise Exception('Missing manifest file: version.json')

    with open(version_json) as f:
        jsn = json.load(f)
        if not (jsn.get("downloads") and jsn.get("downloads").get(side) and jsn.get("downloads").get(side).get("url")):
            raise Exception("Could not download jar, missing fields")

        download_file(jsn.get("downloads").get(side).get("url"), jar_path)
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
                        raise RuntimeError(f"Jar should be extracted but version list is not in the correct format, expected 3 fields, got {len(element)} for {content}")
                    version_hash = element[0].decode()
                    version = element[1].decode()
                    path = element[2].decode()
                    if version != target_version:
                        logging.warning(f"Version is not identical to the one targeted got {version} exepected {target_version}")
                    new_jar_path = f"versions/{target_version}"
                    new_jar_path = z.extract(f"META-INF/versions/{path}", new_jar_path)
                    if not Path(new_jar_path).exists():
                        raise Exception(f"New {side} jar could not be extracted from archive at {new_jar_path}, failure")
                    file_hash = sha256(new_jar_path)
                    if file_hash != version_hash:
                        raise Exception(f"Extracted file hash and expected hash did not match up, got {file_hash} expected {version_hash}")
                    shutil.move(new_jar_path, jar_path)
                    shutil.rmtree(f"versions/{target_version}/META-INF")            
    logging.info("Done!")


def get_mappings(version: str, side: SideType) -> None:
    mappings_file = cwd / "mappings" / version / f"{side}.txt"
    converted_mappings_file = cwd / "mappings" / version / f"{side}.tsrg"
    if (mappings_file.exists() and mappings_file.is_file()) or (converted_mappings_file.exists() and converted_mappings_file.is_file()):
        logging.info("Mappings already exist, not downloading again")
        return
    version_json = cwd / "versions" / version / "version.json"
    if version_json.exists() and version_json.is_file():
        logging.debug(f'Found {version}.json')
        with open(version_json) as f:
            jfile = json.load(f)
            url = jfile['downloads'].get(f'{side}_mappings', {}).get('url')
            if not url:
                raise Exception(f'Error: {side} mappings for {version} not available from version.json')
            logging.info(f'Downloading the mappings for {version}...')
            download_file(url, mappings_file)
    else:
        raise RuntimeError(f'Missing manifest file: {version_json}')


def remap(version: str, side: SideType) -> None:
    logging.info('=== Remapping jar using SpecialSource ====')
    t = time.time()

    path = cwd / "versions" / version / f"{side}.jar"
    # that part will not be assured by arguments
    if not path.exists() or not path.is_file():
        path_temp = (mc_path / "versions" / version / f"{version}.jar").expanduser()
        if path_temp.exists() and path_temp.is_file():
            path = path_temp
        else:
            raise RuntimeError(f'Missing file: {path}')
    path = path.resolve()

    mapp = cwd / "mappings" / version / f"{side}.tsrg"
    if not mapp.exists() or not mapp.is_file():
        raise RuntimeError(f'Missing file: {mapp}')
    mapp = mapp.resolve()

    specialsource = cwd / "lib" / f"SpecialSource-{SPECIAL_SOURCE_VERSION}.jar"
    if not specialsource.exists() or not specialsource.is_file():
        raise RuntimeError(f'Missing file: {special_ource}')
    specialsource = specialsource.resolve()

    outpath = cwd / "src" / f"{version}-{side}-temp.jar"

    subprocess.run(['java',
                    '-jar', str(specialsource),
                    '--in-jar', str(path),
                    '--out-jar', str(outpath),
                    '--srg-in', str(mapp),
                    "--kill-lvt"  # kill snowmen
                    ], check=True, capture_output=logger.level >= logging.INFO)
    logging.info(f'Created {outpath}')
    logging.debug('Done in %.1fs' % (time.time() - t))


def decompile_fernflower(decompiled_version: str, version: str, side: SideType, force) -> None:
    logging.info('=== Decompiling using FernFlower (silent) ===')
    t = time.time()

    path = cwd / "src" / f"{version}-{side}-temp.jar"
    if not path.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {path}')
    path = path.resolve()

    fernflower = cwd / "lib" / "fernflower.jar"
    if not fernflower.exists() or not fernflower.is_file():
        raise RuntimeError(f'Missing file: {fernflower}')
    fernflower = fernflower.resolve()

    side_folder = cwd / "src" / decompiled_version / side
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
                    str(path), side_folder
                    ], check=True, capture_output=logger.level >= logging.INFO)
    delete_file(path)
    logging.info("Decompressing remapped jar to directory...")
    with zipfile.ZipFile(side_folder / f"{version}-{side}-temp.jar") as z:
        z.extractall(path=side_folder)
    logging.info(f'File decompressed in {decompiled_version}/{side}')
    logging.debug(f'Done in %.1fs ()' % (time.time() - t))
    if force:
        delete_file(side_folder / f'{version}-{side}-temp.jar')


def decompile_cfr(decompiled_version: str, version: str, side: SideType) -> None:
    logging.info('=== Decompiling using CFR (silent) ===')
    t = time.time()

    path = cwd / "src" / f"{version}-{side}-temp.jar"
    if not path.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {path}')
    path = path.resolve()

    cfr = cwd / "lib" / f"cfr-{DECOMPILERS["cfr"]["version"]}.jar"
    if not cfr.exists() or not path.is_file():
        raise RuntimeError(f'Missing file: {cfr}')
    cfr = cfr.resolve()

    side_folder = cwd / "src" / decompiled_version / side
    side_folder.resolve()

    subprocess.run(['java',
                    '-Xmx4G',
                    '-Xms1G',
                    '-jar', str(cfr),
                    str(path),
                    '--outputdir', str(side_folder),
                    '--caseinsensitivefs', 'true',
                    "--silent", "true"
                    ], check=True, capture_output=logger.level >= logging.INFO)
    delete_file(path)
    delete_file(side_folder / "summary.txt")
    logging.debug('Done in %.1fs' % (time.time() - t))

def decompile(decompiler: str, decompiled_version: str, version: str, side: SideType, force: bool) -> None:
    if decompiler == "cfr":
        decompile_cfr(decompiled_version, version, side)
    else:
        decompile_fernflower(decompiled_version, version, side, force)

def remove_brackets(line: str, counter: int) -> tuple[str, int]:
    while '[]' in line:  # get rid of the array brackets while counting them
        counter += 1
        line = line[:-2]
    return line, counter


def remap_file_path(path: str) -> str:
    remap_primitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J", "byte": "B", "short": "S",
                        "char": "C", "void": "V"}
    return "L" + "/".join(path.split(".")) + ";" if path not in remap_primitives else remap_primitives[path]


def convert_mappings(version: str, side: SideType) -> None:
    dir_path = cwd / "mappings" / version
    mappings_file = dir_path / f"{side}.txt"
    converted_mappings_file = dir_path / f"{side}.tsrg"

    if (converted_mappings_file.exists() and converted_mappings_file.is_file()):
        logging.info(f"'{side}' mappings file for {version} already converted, not converting again")
        return

    with open(mappings_file, 'r') as inputFile:
        file_name: dict[str, str] = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if not line.startswith('    '):
                obf_name = obf_name.split(":")[0]
                file_name[remap_file_path(deobf_name)] = obf_name  # save it to compare to put the Lb

    with open(mappings_file, 'r') as inputFile, open(converted_mappings_file, 'w+') as outputFile:
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
    logging.info("Mappings converted!")


def make_paths(version: str, side: SideType, clean: bool, force: bool) -> str:
    path = cwd / "mappings" / version
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if clean:
            shutil.rmtree(path)
            path.mkdir(parents=True)
    path = cwd / "versions" / version
    if not path.exists():
        path.mkdir(parents=True)
    else:
        path = cwd / "versions" / version / "version.json"
        if path.is_file() and clean:
            path.unlink()
    if Path("versions").exists():
        path = cwd / "versions" / "version_manifest.json"
        if path.is_file() and clean:
            path.unlink()

    path = cwd / "versions" / version / side
    if path.exists() and path.is_file() and clean:
        if force:
            path = cwd / Path(f'versions/{version}')
            shutil.rmtree(path)
            path.mkdir(parents=True)

    path = cwd / "src" / version / side
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if clean or force:
            shutil.rmtree(path)
        else:
            logging.warning(f"{path} exists, creating new directory")
            version = version + side + "_" + str(random.getrandbits(128))
        path = cwd / "src" / version / side
        path.mkdir(parents=True)

    path = cwd / "tmp" / version / side
    if not path.exists():
        path.mkdir(parents=True)
    else:
        if clean:
            shutil.rmtree(path)
            path.mkdir(parents=True)

    return version


def run(version: str, side: SideType, decompiler="cfr", clean=False, force=False) -> str:
    decompiled_version = make_paths(version, side, clean, force)
    get_global_manifest()
    get_version_manifest(version)

    get_version_jar(version, side)

    if version >= "26.1":
        # MC 26.1+ does not have any obfuscation
        inpath = cwd / "versions" / version / f"{side}.jar"
        outpath = cwd / "src" / f"{version}-{side}-temp.jar"
        shutil.copy(inpath, outpath)
    else:
        get_mappings(version, side)
        convert_mappings(version, side)
        remap(version, side)

    decompile(decompiler, decompiled_version, version, side, force)

    return decompiled_version


def main():
    check_java()
    snapshot, latest = get_latest_version()
    # for arguments
    parser = argparse.ArgumentParser(description='Decompile Minecraft source code')
    parser.add_argument('mcversion', type=str, nargs="?", default=latest,
                        help=f"The version you want to decompile (any version starting from 19w36a (snapshot) and 1.14.4 (releases))\n"
                             f"Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest})")
    parser.add_argument('--interactive', '-i', type=str2bool, default=False,
                        help="Enable an interactive CLI to specify options (all other command line arguments, besides --will be ignored)")
    parser.add_argument('--side', '-s', type=str, dest='side', default="client", choices=["client", "server"],
                        help='Whether to decompile the client side or server side')
    parser.add_argument('--clean', '-c', dest='clean', action='store_true', default=False,
                        help=f"Clean old runs")
    parser.add_argument('--force', '-f', dest='force', action='store_true', default=False,
                        help=f"Force resolving conflicts by replacing old files")
    parser.add_argument('--decompiler', '-d', type=str, dest='decompiler', default="cfr", choices=DECOMPILERS.keys(),
                        help=f"Select a copmiler to run")
    parser.add_argument('--quiet', '-q', dest='quiet', action='store_true', default=False,
                        help=f"Suppresses logging output")
    
    args = parser.parse_args()

    try:
        if args.interactive:
            # Enable interactive mode

            args.clean = input("Do you want to clean up old runs? (y/N): ") in ["y", "yes"]
            if not args.clean:
                args.force = input("Do you want to force replacing old files on conflict? (y/N): ") in ["y", "yes"]

            version = input(f"Please input a valid version starting from 19w36a (snapshot) and 1.14.4 (releases),\n" +
                            f"Use 'snap' for latest snapshot ({snapshot}) or 'latest' for latest version ({latest}): ") or latest
            if version in ["snap", "s", "snapshot"]:
                version = snapshot
            if version in ["latest", "l"]:
                version = latest
            args.mcversion = version

            args.side = SERVER if input("Please select either client or server side (C/s): ").lower() in ["server", "s"] else CLIENT
            args.decompiler = "fernflower" if input("Please input your decompiler of choice: cfr or fernflower (CFR/f): ").lower() in ["fernflower", "f"] else "cfr"

        if args.quiet:
            logging.basicConfig(level=logging.ERROR)

        decompiled_version = run(args.mcversion, args.side, args.decompiler, args.clean, args.force)

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt detected, exiting")
        sys.exit(-1)
    except (Exception, RuntimeError, OSError) as e:
        logging.critical("===Error detected!===")
        traceback.print_exc()
        sys.exit(-1)
    logging.info("===FINISHED===")
    logging.info(f"Output is in /src/{decompiled_version}")


if __name__ == "__main__":
    main()
