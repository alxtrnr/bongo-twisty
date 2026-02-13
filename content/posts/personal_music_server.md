+++
title = "Setting Up a Personal Music Server"
description = ""
date = 2026-02-13
tags = []
+++

A few months ago I [set my music free](https://www.bongotwisty.blog/set_the_music_free/) with an instance of the Navidrome Music Streaming Server on [Pikapod](https://www.pikapods.com). It was very easy. I was up and running in no time. 

There was an old laptop that I could have used as a server but was put off by the thought of wrangling network settings. I had my fill of that with a Nextcloud instance on a Raspberry Pie some years ago.

Pikapod provides a great service at a good price and profit shares with the developers of the open source apps it hosts. All good. I was happy with the service. 

Some time after I learned about [Tailscale](https://tailscale.com). It basically removes the pain of configuring a secure network to facilitate remote access to a local server. For my use case it's free. What's not to like?   

What with an old unused laptop lying around, knowing I could do this and with a bit of time on my hands I decided to go for it. Guided by an LLM it was all quite straight forward. As I am writing this post the process of syncing several hundred GBs of music files to the local server is completing in the background. All working as expected. Streaming on local and remote networks. 

Happy days. I'm now one of the increasing number of people whose hosting their own music streaming service.  
 
Here's a few details - 
***
## Server
 
- **Model**: Lenovo IdeaPad Flex 15D\
- **CPU**: Intel Atom x7-Z8750 (4 cores, 1.6-2.56 GHz)
- **RAM**: 4GB
- **OS**: Ubuntu Server 24.04 LTS

***
## CPU Constraints

- **No real-time transcoding** - CPU will struggle with FLAC→MP3 conversion
- **Solution**: Sync only MP3 files, pre-convert lossless formats
- **Limited concurrent streams** - Max 2-3 simultaneous users
- **Power efficient**: 2W TDP, suitable for 24/7 operation

***

## rclone Filter File

```
# MP3-only filter (optimized for Atom processor - no transcoding needed)

# Include MP3 files ONLY
+ *.mp3
+ *.MP3

# Include album artwork
+ *.jpg
+ *.jpeg
+ *.png
+ *.JPG
+ *.JPEG
+ *.PNG
+ cover.*
+ folder.*
+ Cover.*
+ Folder.*

# Include playlist files
+ *.m3u
+ *.m3u8
+ *.M3U

# Exclude ALL other audio formats (prevent transcoding load)
- *.flac
- *.FLAC
- *.m4a
- *.M4A
- *.aac
- *.AAC
- *.ogg
- *.OGG
- *.opus
- *.OPUS
- *.wav
- *.WAV
- *.wma
- *.WMA
- *.ape
- *.alac
- *.aiff

# Exclude system files
- .DS_Store
- Thumbs.db
- desktop.ini
- .directory

# Exclude temporary/hidden files
- *.tmp
- *.temp
- *~
- .~*
- .*

# Exclude text/documentation
- *.txt
- *.pdf
- *.doc
- *.docx
- *.nfo
- *.log
- *.cue

# Include directories
+ */
```


## Sync Script


```bash
#!/bin/bash

################################################################################
# Navidrome Local Server Music Sync Script
# Syncs music from local storage to Tailscale-connected Navidrome server
# Optimized for low-power Atom processor
################################################################################

# === CONFIGURATION ===
MUSIC_SOURCE="/your/music/directory"
RCLONE_REMOTE="what_you_named_your_navidrome_server:/your/music/directory"
FILTER_FILE="$HOME/.config/rclone/what_you_named_your_filter.txt"

# Navidrome API settings
NAVIDROME_URL="http://XXX.XX.XX.XX:4533"
NAVIDROME_USER="YOUR USER NAME"
NAVIDROME_PASS="YOUR PASSWORD"

# === SCRIPT START ===
echo "========================================"
echo "Navidrome Local Server Music Sync"
echo "Started: $(date)"
echo "========================================"

# Check if source directory exists
if [ ! -d "$MUSIC_SOURCE" ]; then
    echo "ERROR: Music source directory not found: $MUSIC_SOURCE"
    exit 1
fi

# Check if filter file exists
if [ ! -f "$FILTER_FILE" ]; then
    echo "WARNING: Filter file not found: $FILTER_FILE"
    echo "Proceeding without filters..."
    FILTER_ARG=""
else
    FILTER_ARG="--filter-from $FILTER_FILE"
fi

# Perform rclone sync with optimized settings for local network
echo ""
echo "Starting music sync..."
echo "Source: $MUSIC_SOURCE"
echo "Destination: $RCLONE_REMOTE"
echo ""

rclone sync "$MUSIC_SOURCE" "$RCLONE_REMOTE" \
    $FILTER_ARG \
    --progress \
    --stats 10s \
    --transfers 8 \
    --checkers 16 \
    --stats-one-line \
    --bwlimit-file 50M

# Check sync result
SYNC_EXIT_CODE=$?

if [ $SYNC_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✓ Sync completed successfully!"
    echo ""
    
    # Trigger Navidrome library scan
    echo "Triggering Navidrome library scan..."
    
    # Generate salt and MD5 token for authentication
    SALT=$(date +%s | md5sum | cut -d' ' -f1 | cut -c1-12)
    TOKEN=$(echo -n "${NAVIDROME_PASS}${SALT}" | md5sum | cut -d' ' -f1)
    
    # Call the startScan API
    SCAN_RESPONSE=$(curl -s "${NAVIDROME_URL}/rest/startScan?u=${NAVIDROME_USER}&t=${TOKEN}&s=${SALT}&v=1.16.1&c=rclone_sync&f=json")
    
    # Check response
    if echo "$SCAN_RESPONSE" | grep -q '"status":"ok"'; then
        if echo "$SCAN_RESPONSE" | grep -q '"scanning":true'; then
            echo "✓ Library scan triggered successfully!"
            echo "  Navidrome is now scanning your music library..."
        else
            echo "✓ Scan request accepted"
        fi
    elif echo "$SCAN_RESPONSE" | grep -q '"status":"failed"'; then
        ERROR_MSG=$(echo "$SCAN_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
        echo "⚠ Scan failed: $ERROR_MSG"
    else
        echo "⚠ Unexpected response"
        echo "$SCAN_RESPONSE"
    fi
    
else
    echo ""
    echo "✗ Sync failed with exit code: $SYNC_EXIT_CODE"
    echo "Skipping Navidrome scan."
    exit 1
fi

echo ""
echo "========================================"
echo "Completed: $(date)"
echo "========================================"
```

***

## Resources

- **Navidrome Docs**: https://www.navidrome.org/docs/
- **Navidrome Config Options**: https://www.navidrome.org/docs/usage/configuration-options/
- **Tailscale Docs**: https://tailscale.com/kb/
- **rclone Docs**: https://rclone.org/docs/

