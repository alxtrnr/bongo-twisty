+++
title = "I added 'TownSquare' to my blog"
description = "Hello Neighbours"
date = 2026-06-24
draft = false
tags = []
+++

> Your website but inhabited. The web is full of content but empty of people. TownSquare brings a little presence back. Visitors can see each other, say a few words, and share the same space. No accounts. No algorithms. Just the present.

That's the pitch on [TownSquare](https://townsquare.cauenapier.com), which is where I got the base code for the widget towards the bottom of this page.

The widget was created by [Cauê Napier](https://cauenapier.com) who released it free of charge for all to use. Thank you Cauê.

I liked it straight away. Closest I will ever come to being an [XKCD](https://xkcd.com) character. 

Since Cauê offered a hosted version that's the one I chose. It looked so easy. It was not quite as simple to add to my blog as the "three small steps" described [here](https://townsquare.cauenapier.com/docs/#start). Fair to say it took way longer than a "minute". That's not Cauê's fault. More so down to my cobbled together modified version of the [Hugo Simple](https://themes.gohugo.io/themes/hugo-simple/) theme. 

Every time the widget loaded my entire site took on the widgets default colour scheme. It's a nice enough scheme but is not what I wanted to happen. It took me a while to work out why. 

Turns out that the widget's stylesheet set CSS variables on the page's root element as well as its own container, which was overwriting my site's colour theme entirely. The fix was to load the widget and immediately override its colour variables inline so they resolved in the right order while also re-asserting my own site palette at the bottom of my custom CSS to protect it permanently. I added the widget to both the home page and the bottom of every post using Hugo's partial system in a single template file. The final bit was syncing dark mode. My blog toggle works by adding a class to the page body but the widget expects its own data attribute. A little bit of JavaScript was needed to watch for the toggle and keep both aligned. 

It was a bit of a challenge but I'm sure it will be easier that that for most people. All the same I'm delighted to be on the [TownSquare Map](https://townsquare.cauenapier.com/map) and happy to add a signpost to anyone else's site who may like a "neighbour". Just let me know via a webmention or [Letterbird](https://www.bongotwisty.blog/contact/).
