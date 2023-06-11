from quart import Quart, request, jsonify
import asyncio
import subprocess
import os

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
    result = out.decode().split('\n')[0]
    return result


@app.route('/analysis', methods=['POST'])
async def handle_request():
    data = await request.get_json()
    packagename = data['packagename']
    packageversion = data['packageversion']
    
    print("Received a request for the APK: {} with the Version: {}".format(packagename, packageversion))
    
    result = await download_apk(packagename, packageversion) # Download APK
    if result == "Success":
        result = await scan_apk(packagename, packageversion) # Analyse APK
    return jsonify({"score": result}) 
    

if __name__ == '__main__':
    app.run(debug=True)
