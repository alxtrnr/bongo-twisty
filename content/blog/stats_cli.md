+++
title = "Cycling Stats CLI"
description = ""
date = 2025-09-11T20:50:13+01:00
draft = false
author = "Alexander"
images = []
+++

News years day 2015.  Full of hopes and good intentions. I joined a Ride Every Day Challenge on Google +

Only one way to go about that sort of thing. One day at a time. There was plenty of times when I just rode round the block. Some rides were less than a km. I made it to the end though [without missing a day](https://www.bongotwisty.blog/gallery/cycling/rwgps_recap/2015/).

{{< rwgpsimg year="2015" name="y_2015_RWGPS.webp" alt="2015 recap" class="float-right" >}}

This was and remains the most distance I've ridden in one year. Nearly matched it in 2024. I set out to ride 10,000km. Reached that in August and then decided to go for it. 

{{< rwgpsimg year="2024" name="y_2024_RWGPS.webp" alt="2024 recap" class="float-right" >}}

That got me thinking it might be possible to best 2015's total. What with me being ten years older, if none the wiser, it seemed like a good thing to aim for in 2025. 

It's not been a year of riding every day. Had a feeling I was on track though. Writing [week notes](https://www.bongotwisty.blog/week362025/) this Monday prompted me to check on progress.\
At just under 69% through the year, 69% of the distance required had been completed. No idea progress and time was so closely aligned. Very encouraging. 

Thinking more about this during my morning ride today. Had an idea to build on, "[Eddington Number. A Cycling Statistics App](https://www.bongotwisty.blog/eddington-number-a-cycling-statistics-app./)", I created during February of this year. Wondered how I could add to the code and have it track an annual goal and display the distance I needed to do on a daily, weekly or monthly basis to reach it. The distance would be updated whenever I synced the app with new ride data added to my account on RWGPS. 

Spent a bit of time on it today. Managed to come up with something that does what I was thinking of and a bit more.

From the [README](https://github.com/alxtrnr/cycling-stats-cli/blob/main/README.md) - 

#### Goal Subcommands

- `add` : Add a new goal.
- `list` : List all configured goals.
- `delete` : Delete a goal by ID.
- `edit` : Edit an existing goal.
- `progress` : Show progress on goals.
- `set` : Set legacy annual distance goal.

#### Adding a Goal

Example:

```bash
python cli.py goal add --type distance --target 5000 --unit miles --start 2025-01-01 --end 2025-12-31 --title "Annual Distance Goal"
```

- `--type` : Type of goal (`distance`, `ride_count`, `elevation`, `time`, `frequency`).
- `--target` : Numeric target to achieve.
- `--unit` : Unit for the goal (e.g. `miles`, `km`, `m`, `ft`, `h`).
- `--start` : Start date for goal (YYYY-MM-DD).
- `--end` : End date for goal (YYYY-MM-DD).
- `--title` : Optional goal title.

And an example of how how goals and progress are displayed - 

```bash
python cli.py goal progress --all

Goal: Annual Distance Goal (20ef1aac-bd8a-49af-b09f-26e59ac1a682)

=== ANNUAL GOAL PROGRESS (2025) ===
Goal: 18,000 km
Current: 12,448.0 km (69.2% complete)
Year Progress: 69.6% elapsed
Days passed: 254 | Days remaining: 111
Status: ✅ On track

=== PACING TARGETS ===
To reach your goal, you need:
• Daily: 50.0 km/day
• Weekly: 350.1 km/week
• Monthly: 1522.5 km/month
```

Having this to play around with will encourage me to keep going. The [repo](https://github.com/alxtrnr/cycling-stats-cli) is on GitHub for anyone interested. 