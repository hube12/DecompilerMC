from pathlib import Path
import subprocess, os, time, urllib.request, shutil, sys, random, json


def downloadFile(url, filename):
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


def getMappings(version):
    if Path(f'mappings/{version}/client.txt').is_file():
        return
    pathToJson = Path(f'~/AppData/Roaming/.minecraft/versions/{version}/{version}.json').expanduser()

    if pathToJson.exists() and pathToJson.is_file():
        print(f'Found {version}.json')
        pathToJson = pathToJson.resolve()

        with open(pathToJson) as f:

            jfile = json.load(f)
            url = jfile['downloads']['client_mappings']['url']

            print(f'Downloading the mappings for {version}...')
            downloadFile(url, f'mappings/{version}/client.txt')
            print('Done!')
    else:
        print(f'ERROR: Missing files')


def remap(version):
    print('=== Remapping jar using SpecialSource ====')
    t = time.time()
    path = Path(f'~/AppData/Roaming/.minecraft/versions/{version}/{version}.jar').expanduser()
    mapp = Path(f'mappings/{version}/client.tsrg')
    specialsource = Path('./lib/SpecialSource-1.8.6.jar')

    if path.exists() and mapp.exists() and specialsource.exists():
        path = path.resolve()
        mapp = mapp.resolve()
        specialsource = specialsource.resolve()

        subprocess.run(['java', '-jar', specialsource.__str__(), '--in-jar', path.__str__(), '--out-jar',
                        f'./src/{version}-temp.jar', '--srg-in', mapp.__str__()], shell=True)

        print(f'- New -> {version}-temp.jar')

        t = time.time() - t
        print('Done in %.1fs' % t)
    else:
        print(f'ERROR: Missing files')


def decompile(version):
    print('=== Decompiling using CFR ====')
    t = time.time()

    path = Path(f'./src/{version}-temp.jar')
    cfr = Path('./lib/cfr-0.146.jar')
    if path.exists() and cfr.exists():
        path = path.resolve()
        cfr = cfr.resolve()

        subprocess.run(
            ['java', '-jar', cfr.__str__(), path.__str__(), '--outputdir', f'./src/{version}', '--caseinsensitivefs',
             'true'], shell=True)

        print(f'- Removing -> {version}-temp.jar')
        print(f'- Removing -> summary.txt')
        os.remove(f'./src/{version}-temp.jar')
        os.remove(f'./src/{version}/summary.txt')

        t = time.time() - t
        print('Done in %.1fs' % t)
    else:
        print(f'ERROR: Missing files')


def reMapMapping(version):
    remapPrimitives = {"int": "I", "double": "D", "boolean": "Z", "float": "F", "long": "J"}
    remapFilePath = lambda path: "L" + "/".join(path.split(".")) + ";" if path not in remapPrimitives else \
        remapPrimitives[path]
    with open(f'mappings/{version}/client.txt', 'r') as inputFile, open(f'mappings/{version}/client.tsrg',
                                                                        'w+')  as outputFile:
        fileName = {}
        for line in inputFile.readlines():
            if line.startswith('#'):  # comment at the top, could be stripped
                continue
            deobf_name, obf_name = line.split(' -> ')
            if line.startswith('    '):
                obf_name = obf_name.strip()
                deobf_name = deobf_name.lstrip()
                methodType, methodName = deobf_name.split(" ")
                methodType = methodType.split(":")[-1]  # get rid of the line numbers
                if "(" in methodName and ")" in methodName:  # function
                    variables = methodName.split('(')[-1].split(')')[0]
                    functionName = methodName.split('(')[0]
                    if methodType == "void":
                        methodType = "V"
                    else:
                        methodType = remapFilePath(methodType)
                    if variables != "":
                        variables = [remapFilePath(variable) for variable in variables.split(",")]

                        variables = "".join(
                            ["L" + fileName[variable] + ";" if variable in fileName else variable for variable in
                             variables])
                    outputFile.write(f' {obf_name} ({variables}){methodType} {functionName}\n')
                else:
                    outputFile.write(f' {obf_name} {methodName}\n')

            else:
                obf_name = obf_name.split(":")[0]
                fileName[remapFilePath(deobf_name)] = obf_name  # save it to compare to put the Lb
                outputFile.write(obf_name + " " + deobf_name + "\n")


def makePaths(version):
    path = Path(f'mappings/{version}')

    if not path.exists():
        path.mkdir(parents=True)
    path=Path(f'src/{version}')
    if not path.exists():
        path.mkdir(parents=True)
    else:
        aw = input(f"/src/{version} already exists, wipe it (w), create a new folder (n) or kill the process (k) ? ")
        if aw == "w":
            shutil.rmtree(Path(f"./src/{version}"))
        elif aw == "n":
            version = version + "_" + str(random.getrandbits(128))
        else:
            sys.exit()
        path = Path(f'src/{version}')
        path.mkdir(parents=True)
    return version

if __name__ == "__main__":

    version = "19w36a"
    decompVersion=makePaths(version)
    r = input('Download mappings? (y/n): ')
    if r == 'y':
        getMappings(version)

    r = input('Remap mappings to tsrg? (y/n): ')
    if r == 'y':
        reMapMapping(version)

    r = input('Remap? (y/n): ')
    if r == 'y':
        version = remap(version)

    r = input('Decompile? (y/n): ')
    if r == 'y':
        print(decompVersion)
        decompile(decompVersion)