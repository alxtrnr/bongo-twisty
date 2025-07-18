+++
title = "Driven to distraction   AIW 9800se - lost and found"
description = ""
date = "2007-11-25"
draft = false
tags = []
toc = false
+++

For the geek log.

Added an extra 2 gig of RAM and the graphics adapter defaulted to the standard VGA settings. This means instead of the display being powered by the graphics card it's powered by some little thing built onto the PCs motherboard - something to do with BIOS settings defaulting when the RAM is changed. Why it should do that I have no idea. The result is no wide screen resolution. ATI drivers no longer showing. No ATI in devices. Not possible to reinstall drivers. Software / hardware settings not suitable error message.

After some hours poking around in devices and monitor settings I resolved the problem. That was good. I'd removed 512mb of RAM to see if that would make a difference so now wanted to see if I put it back it would still work - I thought that it should. I anticipated the graphics adapter would once again revert to the standard VGA settings but this time I would know how to fix it.

The adapter did revert . This time though it took something different to fix it. Much simpler than the first which I won't describe. I never once used a hammer. Here is what I did.

Remove existing RAM modules (x3) and replace with x3 1 gig modules.

1. Turn on PC
2. Resolution no good.
3. Turn of PC.
4. Boot up and press F8 lots of times.
5. Select "VGA mode"
6. Select enter.
7. PC boots up. Resolution OK but no drivers loaded.
8. Reinstall ATI drivers and reboot.

Problem solved. Between steps 2 and 8 download up to date drivers, remove all installed ATI drivers and clean up with Driver Cleaner.

Every time I tried installing the drivers without F8 / select VGA step I'd get an error message, something about no modules and the wrong hardware / software setup.

Tech Info: 3 gig RAM / ATI AIW 128mb 9800se / CCC 7.11 / winXP. screen res 1680 x 1050.

Whether this will ever work again for me or anyone else I don't know. Handy if it does.