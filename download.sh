#!/bin/bash

# get urls for the chosen server
# base_url = hu of network config
server="${1:-"cn"}"
test="${2:-"prod"}"

case $server in
    "en") network_config_url="https://ak-conf.arknights.global/config/prod/official/network_config";;
    "jp") network_config_url="https://ak-conf.arknights.jp/config/prod/official/network_config";;
    "kr") network_config_url="https://ak-conf.arknights.kr/config/prod/official/network_config";;
    "tw") network_config_url="https://ak-conf.txwy.tw/config/prod/official/network_config";;
    "bili") network_config_url="https://ak-conf.hypergryph.com/config/prod/b/network_config";;
    *) network_config_url="https://ak-conf.hypergryph.com/config/prod/official/network_config";;
    # cn is default
esac

network_config=$(curl -s "$network_config_url" | jq -r ".content")
network_urls=$(echo $network_config | jq -r ".configs[$(echo $network_config | jq ".funcVer")].network")
version_url=$(echo $network_urls | jq -r ".hv" | sed "s/{0}/Android/g")
res_version=$(curl -s "$version_url" | jq -r ".resVersion")
assets_url="$(echo $network_urls | jq -r ".hu")/Android/assets/${res_version}"

download_file() {
    local path="$1"
    local formatted_path=$(echo "$path" | sed -e "s|/|_|g" -e "s|#|__|" -e "s|\..*|.dat|g")

    wget -q -c -P "/tmp/akassets" "${assets_url}/${formatted_path}"
    if [[ $path == *.ab ]]; then
        unzip -q -o "/tmp/akassets/${formatted_path}" -d "./bundles"
        rm "/tmp/akassets/${formatted_path}"
    else
        mkdir -p "$(dirname "./bundles/${path}")"
        mv "/tmp/akassets/${formatted_path}" "./bundles/${path}"
    fi
    echo "${path}"
}

# compare diff
if [[ $(cat "./hot_update_list-$server.json" | jq -r ".versionId") == $res_version ]]; then
    >&2 echo "Up to date!"
    exit 0
fi;

mkdir -p "./bundles"


declare -A old_hash
while IFS="," read -r path hash; do
    old_hash[$path]=$hash
done < <(cat "./hot_update_list-$server.json" | jq -r -c '.abInfos[] | "\(.name),\(.hash)"')

# download
curl -s "${assets_url}/hot_update_list.json" | jq . > "./hot_update_list-$server.json"
while IFS="," read -r path hash; do
    if [[ "${hash}" != "${old_hash[$path]}" && $test != "test" ]]; then
        download_file "$path"
    fi
done < <(cat "./hot_update_list-$server.json" | jq -r -c '.abInfos[] | "\(.name),\(.hash)"')

cp "./hot_update_list-$server.json" "./bundles/hot_update_list.json"

# extract
chmod +x "ArknightsStudioCLI/ArknightsStudioCLI"
for path in $(find "./bundles" -type f -name "*.ab"); do
    ArknightsStudioCLI/ArknightsStudioCLI "${path}" -g containerFull -t tex2d,sprite,akPortrait,textAsset,audio -o "./assets" 1>/dev/null
done
