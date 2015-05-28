---
layout: post
title: "Audio as a low-bandwidth authentic channel"
subtitle: ""
category: 
tags: [security, mobile, authentication, iot]
---

Consider any of the following problems:

1. We have a widget that we'd like to set up, perhaps using a smartphone.  The widget doesn't
   have any user interface, and adding one is inappropriate (say, it's a lightbulb).
   
2. I have an iPad and an Android phone.  I want to send information between the two.

3. I have two devices of any kind in close proximity.  I'd like them to agree on a secret without
   relying on anything other than their proximity.

I think audio is an excellent, underused choice for solving problems like this.

Here's why:

# Cross-platform support

Every phone, tablet and laptop has a good quality microphone and speaker.  Software interfaces to these peripherals are widely available, across operating systems and application platforms.  Even web browsers can synthesise and record audio these days.

# Peripheral cost and simplicity

For embedded devices, audio peripherals are cheaper than RF.  Using a digital MEMS microphone means
minimal additional circuitry.  Failing that, your microcontroller likely has a ADC that can be pressed
into service.  Choosing your audio codec carefully and you might be able to bit-bang a transducer to
avoid needing a DAC.

In comparison, Bluetooth LE is fiercely complicated, closed and relatively expensive.  Wifi and full-fat Bluetooth
are even more complex and expensive, and power hungry.  Add to that: Wifi and Bluetooth don't actually work
across platforms, and BLE drivers on Android devics are unusably buggy trash.

# Human intuition

Humans, in general, have an excellent intuition when it comes to evaluating the secrecy and authenticity
of audio: everyday conversation involves making judgements along these lines!  We also have a good ability
to determine the source of most sounds in the audible range.

Most attacks on network security protocols (eavesdropping, man-in-the-middle, replay, etc.) can be explained
to the layperson by performing them using human conversation.

You only need to watch someone trying to get a better Wifi signal to know that this kind of
understanding is missing with RF media.  To the average user RF is supernatural, and the Wifi gods
are quick to anger.

We can make use of this intuition to somewhat relieve worries about attacks on protocols using audio.

