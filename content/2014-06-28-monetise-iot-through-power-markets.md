+++
date = 2014-06-28
path = "2014/06/28/monetise-iot-through-power-markets"
template = "page.html"
title = "How to monetise the IoT through energy markets"
subtitle = ""
tags = ["iot", "abuse", "economics"]
+++
Let's assume for a moment you are an IoT company like [Nest][nest], controlling[^1] a chunk of devices which use energy.  The more energy demand at your behest, the better: HVAC, refrigerators and heating are excellent choices.

Your business model is probably a mix of hardware sales and cloud services.  But you're missing a trick: you should also *capitalise on your extant control of energy demand*.  Here's how:

1. Buy electricity options.
2. Spike price by increasing power demand for a few minutes.
3. *Sell sell sell!*

This is obviously risky, unethical, and perhaps illegal.  But the IoT is largely *about* disregarding risks. The financial services industry are typically comfortable with the other downsides, so you may wish to partner with a trading firm.

There are already emergent phenomena in the power grid: a [certain soap opera in the UK is associated with a 0.5-1.3GW demand spike][eastenders] ([normal demand][ukdemand] is around 30GW).  But predictable events like this don't give you any valuable advantage against the rest of the market.

There are a variety of refinements to this basic idea:

* If you have a [good idea of where your users are in relation to the power consuming equipment][nest-away], you can minimise the chances of your users will notice their equipment turning on and off strangely.
* You can do a 'lite' version of this idea and merely quantise turn-on/-off times of everything to coarse boundaries.  Instead of turning heating on for a population [arriving home][nest-back] between 17:45 and 19:00, turn it on for everybody at 17:40.  This has the downside of probably being lost in the noise of normal daily fluctuations.
* If you develop a relationship with your trading firm, your ability to *predict* (rather than influence) energy fluctuations is also likely to be valuable.  Especially if you can do this far ahead of time.

[^1]: Direct or indirect. It doesn't much matter if they can control things remotely, or can sign a firmware update to add that capability.

[nest]: https://nest.com/
[nest-away]: http://support.nest.com/article/What-is-Auto-Away
[nest-back]: https://nest.com/works-with-nest/
[eastenders]: http://www.digitalspy.co.uk/soaps/s2/eastenders/news/a151673/enders-causes-national-power-surge.html
[ukdemand]: http://www.gridwatch.templar.co.uk/
