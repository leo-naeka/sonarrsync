#!/bin/ash

# Create /Config.txt based on the environment variables we were passed

cat << EOF > /Config.txt
[Sonarr]
url = $SOURCE_SONARR_URL
key = $SOURCE_SONARR_KEY
path = $SOURCE_SONARR_PATH

[Sonarr-target]
url = $TARGET_SONARR_URL
key = $TARGET_SONARR_KEY
path_from = $SOURCE_SONARR_PATH
path_to = $TARGET_SONARR_PATH
# Sync series coming _from_ the source in this quality profile
profile = $SOURCE_SONARR_PROFILE_NUM
# When adding series to the destination Sonarr, use _this_ quality profile (may differ from source)
target_profile = $TARGET_SONARR_PROFILE_NUM
EOF

# Now execute the sync script in a loop, waiting DELAY before running again
while true
do
	python /SonarrSync.py 
	sleep $DELAY
done
