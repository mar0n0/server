from quart import Quart, request, jsonify
import asyncio
import subprocess
import os
import json

app = Quart(__name__)
SCANNER_DIR = "../privacy_quantification"
APKS_DIR = "../apks"


async def download_apk(package_name, package_version):
    print("Downloading APK:{}  Version:{} ...".format(package_name, package_version))
    cmd = "docker exec googleplay-api python3 /scripts/get_apk.py -p {} -v {}".format(package_name, package_version)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    result = out.decode().split('\n')[0]
    return result


async def scan_apk(package_name, package_version):
    print("Scanning APK:{}  Version:{} ...".format(package_name, package_version))
    cmd = "python3 {} -s {} -a {} -p {} -v {}".format(os.path.join(SCANNER_DIR, "scan.py"), SCANNER_DIR, APKS_DIR, package_name, package_version)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    #result = out.decode().split('\n')[0]
    result = out.decode().split('\n')
    methods_piis = result[0]
    permissions_piis = result[1]
    score = result[2]
    return methods_piis, permissions_piis, score


# Format PIIS information for response
def formatPIIS(methods_piis, permissions_piis):
    
    piis = ""
    methods_piis_json = methods_piis.replace("'", '"')
    methods = json.loads(methods_piis_json)
    
    for method in methods:
        piis = piis + method[0] + ":" + method[1] + ";"
        
    
    permissions_piis_json = permissions_piis.replace("'", '"')
    permissions = json.loads(permissions_piis_json)
    
    for permission in permissions:
        piis = piis + permission[0] + ":" + permission[1] + ";"
    
    return piis



@app.route('/analysis', methods=['POST'])
async def handle_request():
    data = await request.get_json()
    packagename = data['packagename']
    packageversion = data['packageversion']
    print("Received a request for the APK: {} with the Version: {}".format(packagename, packageversion))
    
    # Download APK
    result = await download_apk(packagename, packageversion) 
    
    if result == "Success":
        if os.path.exists(os.path.join(APKS_DIR, packagename, str(packageversion), packagename + ".apk")):
            # Analyse APK
            methods_piis, permissions_piis, score = await scan_apk(packagename, packageversion) 
            piis = formatPIIS(methods_piis, permissions_piis)
            print(piis)
            return jsonify({"score": score, "piis": piis}) 
        else:
            return jsonify({"error": "Analysis tool did not find apk"})
    else:
        return jsonify({"error": "Error during apk download!"})
    

if __name__ == '__main__':
    app.run(debug=True)
