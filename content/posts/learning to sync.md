+++
title = "Learning to Sync"
description = "... and how to stop deleting MP3s"
date = 2026-02-20
tags = []
+++

I could not leave good enough alone. I've continued to tweak the script that syncs music files between my desktop and [Navidrome](https://www.navidrome.org/about/) server. 

The original script ignored music files that were not mp3s. This was due to the limitations of the CPU in the laptop used as a server. It's around 14 years old and even when new was not up to much beyond web browsing and playing media files. Having flacs on the server requires the CPU to transcode them on the fly. It's not up to that hence I filtered out flacs from the sync. 

The thing is I have been growing my collection of flac files and want to listen to those tunes as well. 

I had the idea to modify the script such that flacs would be converted to mp3s on my desktop, the newly created mp3s saved in a staging directory, sync that directory to the server and leave the flacs where they were, unchanged. Sounded pretty simple. 

I've never been quick to get a mental model of sync workflows. Not one to give up trying I stuck with it for a bit more time than might seem reasonable. 

I got the core functionality sorted out pretty quickly. It took a lot longer to work out how to correctly manage and check cache files against content on the server, the desktop and the staging directory. It took a least a dozen attempts to get it right. Each failed attempt involved flacs being converted, mp3s being synced, cache files being checked against content, then the transferred mp3s being deleted from the server. Thankfully it was only the mp3s created from the conversion process that were being deleted but still... it became rather tiresome. I almost gave up. 

Happy to say I got it working in the end. The script now generates the desired results. It's lovely to see it doing what I was after. Very satisfying. Aside from getting to grips with [Rclone](https://rclone.org) and syncing I have also gained a respectful appreciation of dry runs. It's been an exercise of learning from my mistakes. 

There are further tweaks I really should make. Main gaps are around resilience during interruption and better logging. Flac conversion could also be made faster with parallelisation. That's not strictly necessary but it would be nice to have. Like I said. I cannot leave good enough alone.  