+++
title = "Eddington Number. A Cycling Statistics App"
description = "An application that calculates your cycling Eddington number and provides detailed riding statistics using the Ride with GPS API."
date = 2025-02-21T14:52:00
draft = false
tags = ["Cycling"]
toc = false
+++

The Eddington number (E) for cycling is the maximum number where a cyclist has ridden E miles on E distinct days. For example, an E-number of 100 means you have cycled at least 100 miles on 100 different days. 
***
<img style="display:block;margin:auto" src="https://i.ibb.co/8LySH7QG/Screenshot-from-2025-03-01-07-43-28.png">

***

It need not be cycling. You could use it for any activity of interest. Mr. Arthur Stanley Eddington came up with the calculation. His primary interest was in astronomy, physics, and math. He also rode a bike. His life time Eddington number was 84. 

I have a lot of rides logged on [RWGPS](https://ridewithgps.com/users/151788/). Inspired by [Matthew Conroy](https://mathstodon.xyz/@matthewconroy/113683688526479791) I had a go at working with Python to draw on the data from these rides and work out what my Eddington number is. After a few hours wrangling code (with help from an LLM) the result is an application that calculates your cycling Eddington number and provides detailed riding statistics using the Ride with GPS API. 

**Key Features**

The app provides comprehensive cycling statistics through an intuitive command-line interface:

- **Eddington Number Tracking**: Calculate your overall Eddington number and track your progress toward the next milestone
- **Yearly Statistics**: View Eddington numbers broken down by year, including your highest yearly achievement
- **Year-to-Date Analysis**: See your current year's progress and how many rides you need to reach your next yearly Eddington goal
- **Ride Distribution**: Analyse the distribution of your rides by distance thresholds
- **Milestone Achievements**: Track century rides (100+ miles/km), double centuries, triple centuries, and quad centuries
- **Top Rides**: View your top 5 longest rides with titles and distances
- **Monthly Statistics**: See your riding patterns month by month

**Technical Details**

The application uses:
- Token-based authentication with the RWGPS API
- Intelligent caching to minimize API calls
- Support for both miles and kilometers
- Decimal precision management for accurate calculations
- Command-line interface with various subcommands for specific views

You can easily switch between miles and kilometers, force refresh data when needed, and get a clear overview of your cycling achievements.

***
**CLI (Command Line Interface)**

<pre>Cycling Statistics Analysis

positional arguments:
  {summary,eddington,ytd,yearly,metrics,distribution,distance,longest,monthly,unit,status}
                        Command to execute
    summary             Display full statistics summary
    eddington           Show Eddington number progress
    ytd                 Show year-to-date statistics
    yearly              Show yearly Eddington numbers
    metrics             Show ride metrics
    distribution        Show ride distribution
    distance            Show distance achievements
    longest             Show top 5 longest rides
    monthly             Show monthly statistics
    unit                Set or toggle distance unit
    status              Show current unit setting and stats

options:
  -h, --help            show this help message and exit
  --unit {miles,km}     Distance unit (miles or km)
  --refresh             Force refresh data instead of using cache
</pre>

***

**Metric Display**

<pre>=== CYCLING STATISTICS (distances in km) ===
Current unit: km (use --unit option to change)
Total rides analyzed: 4111

=== OVERALL EDDINGTON PROGRESS ===
Current overall Eddington: 129
In progress: E=130 (129 rides of 130+ km)
Need 1 more rides of 130+ km for E=130
Next goal after that: E=131 (127 rides of 131+ km)
Will need 4 more rides of 131+ km for E=131

=== EDDINGTON YEAR TO DATE (2025) ===
Rides this year: 42
Distance this year: 2,462.8 km
Current year Eddington: 33
In progress: E=34 (33 rides of 34+ km)
Need 1 more rides of 34+ km for E=34

=== YEARLY EDDINGTON NUMBERS ===
2025: 33
2024: 58
2023: 48
2022: 48
2021: 49
2020: 48
2019: 56
2018: 48
2017: 49
2016: 61 *Highest*
2015: 58
2014: 56
2013: 51
2012: 28

=== RIDE METRICS ===
Longest ride: 1463.6 km
Average ride: 37.2 km
Total distance: 153020.8 km

=== RIDE DISTRIBUTION ===
Range           | Count  | Percentage
----------------|--------|----------
0-50            | 3375   | 82.10%
50-100          | 543    | 13.21%
100-150         | 88     | 2.14%
150-200         | 31     | 0.75%
200-250         | 39     | 0.95%
250-300         | 5      | 0.12%
300-350         | 16     | 0.39%
400-450         | 5      | 0.12%
600-650         | 6      | 0.15%
1200-1250       | 1      | 0.02%
1400-1450       | 1      | 0.02%
1450-1500       | 1      | 0.02%

=== DISTANCE ACHIEVEMENTS ===
Randonneur 50 km: 543
Randonneur 100 km: 88
Randonneur 150 km: 31
Randonneur 200 km: 44
Randonneur 300 km: 16
Randonneur 400 km: 5
Randonneur 600 km: 6
Randonneur 1000 km: 3

=== TOP 5 LONGEST RIDES ===
1. 1463.6 km - audax: LEL
2. 1411.2 km - audax: LEJOG
3. 1225.6 km - audax: PBP
4. 624.0 km - audax: Willesden&apos;s Last Gasp
5. 622.8 km - audax: Orbit London 600k DIY

=== MONTHLY STATISTICS ===
2025-02: 19 rides, 1133.6 km
2025-01: 23 rides, 1329.1 km
2024-12: 31 rides, 1642.3 km
2024-11: 20 rides, 1537.2 km
2024-10: 22 rides, 1300.8 km
2024-09: 12 rides, 720.6 km
2024-08: 21 rides, 1546.2 km
2024-07: 19 rides, 1296.2 km
2024-06: 19 rides, 1166.4 km
2024-05: 49 rides, 2422.1 km
2024-04: 31 rides, 1040.2 km
2024-03: 34 rides, 1208.9 km
</pre>
***
**Imperial Units**

<pre>=== CYCLING STATISTICS (distances in miles) ===
Current unit: miles (use --unit option to change)
Total rides analyzed: 4111

=== OVERALL EDDINGTON PROGRESS ===
Current overall Eddington: 98
In progress: E=99 (98 rides of 99+ miles)
Need 1 more rides of 99+ miles for E=99
Next goal after that: E=100 (98 rides of 100+ miles)
Will need 2 more rides of 100+ miles for E=100

=== EDDINGTON YEAR TO DATE (2025) ===
Rides this year: 42
Distance this year: 1,530.3 miles
Current year Eddington: 28
In progress: E=29 (27 rides of 29+ miles)
Need 2 more rides of 29+ miles for E=29

=== YEARLY EDDINGTON NUMBERS ===
2025: 28
2024: 42
2023: 31
2022: 33
2021: 33
2020: 31
2019: 39
2018: 34
2017: 35
2016: 43
2015: 44 *Highest*
2014: 39
2013: 38
2012: 20

=== RIDE METRICS ===
Longest ride: 909.5 miles
Average ride: 23.1 miles
Total distance: 95082.7 miles

=== RIDE DISTRIBUTION ===
Range           | Count  | Percentage
----------------|--------|----------
0-50            | 3857   | 93.82%
50-100          | 156    | 3.79%
100-150         | 63     | 1.53%
150-200         | 20     | 0.49%
200-250         | 1      | 0.02%
250-300         | 5      | 0.12%
350-400         | 6      | 0.15%
750-800         | 1      | 0.02%
850-900         | 1      | 0.02%
900-950         | 1      | 0.02%

=== DISTANCE ACHIEVEMENTS ===
Century rides (100+ miles): 98
Double centuries (200+ miles): 15
Triple centuries (300+ miles): 9
Quad centuries (400+ miles): 3

=== TOP 5 LONGEST RIDES ===
1. 909.5 miles - audax: LEL
2. 876.9 miles - audax: LEJOG
3. 761.6 miles - audax: PBP
4. 387.7 miles - audax: Willesden&apos;s Last Gasp
5. 387.0 miles - audax: Orbit London 600k DIY

=== MONTHLY STATISTICS ===
2025-02: 19 rides, 704.4 miles
2025-01: 23 rides, 825.9 miles
2024-12: 31 rides, 1020.5 miles
2024-11: 20 rides, 955.2 miles
2024-10: 22 rides, 808.3 miles
2024-09: 12 rides, 447.8 miles
2024-08: 21 rides, 960.8 miles
2024-07: 19 rides, 805.4 miles
2024-06: 19 rides, 724.8 miles
2024-05: 49 rides, 1505.0 miles
2024-04: 31 rides, 646.4 miles
2024-03: 34 rides, 751.2 miles
</pre>

***

The code is on [GitHub](https://github.com/alxtrnr/eddington_number) if you have an interest. Lot's could be done with it to make the app more visual and accessible online.  Very interested in anything anyone else is minded to do with it. 




