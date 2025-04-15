import os
import sys
import json
import requests
import zipfile
import shutil

server = sys.argv[1] if len(sys.argv) > 1 else "cn"

network_config_url = {
    "en": "https://ak-conf.arknights.global/config/prod/official/network_config",
    "jp": "https://ak-conf.arknights.jp/config/prod/official/network_config",
    "kr": "https://ak-conf.arknights.kr/config/prod/official/network_config",
    "tw": "https://ak-conf-tw.gryphline.com/config/prod/official/network_config",
    "bili": "https://ak-conf.hypergryph.com/config/prod/b/network_config",
    "cn": "https://ak-conf.hypergryph.com/config/prod/official/network_config",
}[server]

response = requests.get(network_config_url)
network_config = json.loads(response.json()["content"])

func_ver = network_config["funcVer"]
network_urls = network_config["configs"][func_ver]["network"]
version_url = network_urls["hv"].replace("{0}", "Android")

response = requests.get(version_url)
version_data = response.json()
res_version = version_data["resVersion"]
assets_url = f"{network_urls['hu']}/Android/assets/{res_version}"

with open(f"./hot_update_list-{server}.json", 'r') as f:
    hot_update_list = json.load(f)

if hot_update_list["versionId"] == res_version:
    print("Up to date!", file=sys.stderr)
    sys.exit(0)

os.makedirs("./bundles", exist_ok=True)
old_hash: dict[str, str] = {}
with open(f"./hot_update_list-{server}.json", 'r') as f:
    hot_update_list = json.load(f)
    for ab_info in hot_update_list["abInfos"]:
        old_hash[ab_info["name"]] = ab_info["hash"]

response = requests.get(f"{assets_url}/hot_update_list.json")
with open(f"./hot_update_list-{server}.json", 'wb') as f:
    f.write(response.content)
hot_update_list = response.json()

for ab_info in hot_update_list["abInfos"]:
    path = ab_info["name"]
    hash_value = ab_info["hash"]

    if hash_value != old_hash.get(path):
        formatted_path = path.replace("/", "_").replace("#", "__").split('.')[0] + ".dat"
        asset_path = f"{assets_url}/{formatted_path}"
        
        os.makedirs("/tmp/akassets", exist_ok=True)
        try:
            with requests.get(asset_path, stream=True) as response, open(f"/tmp/akassets/{formatted_path}", 'wb') as out_file:
                for chunk in response.iter_content(None):
                    out_file.write(chunk)
        except Exception as e:
            print("ERROR", path, e)
        else:
            with zipfile.ZipFile(f"/tmp/akassets/{formatted_path}", 'r') as zip_ref:
                zip_ref.extractall("./bundles")
        finally:
            os.remove(f"/tmp/akassets/{formatted_path}")
            print(path)



shutil.copy(f"./hot_update_list-{server}.json", "./bundles/hot_update_list.json")

os.chmod("ArknightsStudioCLI/ArknightsStudioCLI", 0o755)
for root, dirs, files in os.walk("./bundles"):
    for file in files:
        if file.endswith(".ab"):
            file_path = os.path.join(root, file)
            os.system(f"ArknightsStudioCLI/ArknightsStudioCLI '{file_path}' -g containerFull -t tex2d,sprite,akPortrait,textAsset,audio -o './assets' 1>/dev/null")
