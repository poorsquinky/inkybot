# Inkybot

This project creates a wall display using a Raspberry Pi equipped with a Pimoroni Inky Impression 4": https://shop.pimoroni.com/products/inky-impression-4


## Disclaimer

Given that the e-ink display takes several seconds to update, this project will not be useful as the primary or sole interface for much.  But as a secondary interface it's great to be able to reach up and hit a button on a picture frame and pause the music or toggle a wi-fi configuration setting, for example.


## Features / Roadmap

It's not organized into a useful project yet.  At present it has:

- Random image slideshow from a directory on the host, with scaling and color adaptive letterboxing
- Support for the four side buttons, with icon overlay
- An extensible, configurable state machine to support new types of display functions

Some things that are planned in the near future:

- Proper modularity -- this thing is a mess right now :)
- More built-in states and examples
  - Status graphs from Home Assistant or other sources
  - Mopidy or other media players


