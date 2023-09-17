from quart import Quart, request, jsonify
import asyncio
import subprocess
import os
import json
import psycopg2

# Function that initializes the tables in the database
def init_db():
    conn = psycopg2.connect(database="apps",user="apps",password="apps",host="172.17.0.1",port="5432")
    cursor_obj = conn.cursor()
    cursor_obj.execute("CREATE TABLE IF NOT EXISTS apps_information (packagename TEXT, version INT, piis TEXT, score INT);")
    conn.commit()
    conn.close()

# Function that inserts information in the database
def add_db(packagename, version, piis, score):
    conn = psycopg2.connect(database="apps",user="apps",password="apps",host="172.17.0.1",port="5432")
    cursor_obj = conn.cursor()
    cursor_obj.execute("INSERT INTO apps_information(packagename, version, piis, score) VALUES(%s,%s,%s,%s)", (packagename, version, piis, score))
    conn.commit()
    conn.close()

# Function that searches for the app in the postgresql database
def search_db(packagename, version):
    con = psycopg2.connect(database="apps",user="apps",password="apps",host="172.17.0.1",port="5432")
    cursor_obj = con.cursor()
    cursor_obj.execute("SELECT * from apps_information WHERE packagename= %s AND version=%s", (packagename, version))
    result = cursor_obj.fetchone()
    return result
    
    
# Function that downlods an app
async def download_apk(package_name, package_version):
    print("Downloading APK:{}  Version:{} ...".format(package_name, package_version))
    cmd = "docker exec googleplay-api python3 /scripts/get_apk.py -p {} -v {}".format(package_name, package_version)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
    result = out.decode().split('\n')[0]
    return result

# Function that scans the app
async def scan_apk(package_name, package_version):
    print("Scanning APK:{}  Version:{} ...".format(package_name, package_version))
    cmd = "python3 {} -s {} -a {} -p {} -v {}".format(os.path.join(SCANNER_DIR, "scan.py"), SCANNER_DIR, APKS_DIR, package_name, package_version)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    out, err = p.communicate()
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


init_db()
SCANNER_DIR = "../privacy_quantification"
APKS_DIR = "../apks"
app = Quart(__name__)


# Endpoint to receive app requests
@app.route('/analysis', methods=['POST'])
async def handle_request():

    data = await request.get_json()
    packagename = data['packagename']
    packageversion = data['packageversion']
    print("Received a request for the APK: {} with the Version: {}".format(packagename, packageversion))

    search_result = search_db(packagename, packageversion) # Search DB
    if search_result: 
        print("Databse already has an apk: {} with the version: {}".format(packagename, packageversion))
        return jsonify({"score": search_result[3], "piis": search_result[2]}) 
    
    result = await download_apk(packagename, packageversion) # Download APK    
    if result == "Success":
        
        if os.path.exists(os.path.join(APKS_DIR, packagename, str(packageversion), packagename + ".apk")):
            
            methods_piis, permissions_piis, score = await scan_apk(packagename, packageversion) # scan apk
            piis = formatPIIS(methods_piis, permissions_piis) # Format piis
            add_db(packagename, packageversion, piis, score) # Add to db
            
            return jsonify({"score": score, "piis": piis}) 
        else:
            
            return jsonify({"error": "Analysis tool did not find apk"})
    else:
        
        return jsonify({"error": "Error during apk download!"})
