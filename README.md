# Innioasis Updater is the official firmware installation tool for the Innioasis Y1, built by the users, _for_ the users.

# Came from an old Y1 Helper tutorial? We've got a new, guided tool called Innioasis Updater, To get started with it, or if you're looking for firmware downloads or updates for another Innioasis device, please head to [innioasis.com/pages/download](https://innioasis.com/pages/download)

[<img src="https://innioasis.app/mtkclient/gui/images/screenshot.jpg" alt="Innioasis Updater Screenshot"/>](https://innioasis.com/pages/download)

# Developer: Here's how to submit firmwares to Innioasis Updater
Simply edit slidia_manfiest.xml and submit a PR with an additional line stating your ROM's GitHub repo and latest release URL, for ROMs made for the Type B (1.8volt scroll wheel) variant of the Y1, plese ensure you prefix the rom.zip release's version tag with type-b (e.g type-b-1.2.3) ROM's without Type B designation in their version tag will be assumed to be the more common Type A(3volt scroll wheel) and listed in the Firmware Directory and Innioasis Updater upon an approved submission. A ROM.zip must contain all the images needed to flash in SP Flash Tool, as well as the Download Agent File and Scatter file, this affords the ROM full compatibility with Innioasis Updater and its underlying firmware flashing tools, namely SP Flash Tool and MTKClient

# Innioasis Updater
<img src="mtkclient/gui/images/icon.png" alt="Innioasis Updater Icon" width="128"/>
Innioasis Updater is an easy, one-click firmware installer for the Innioasis Y1 MP3 player running Android firmwares. It lists official software updates as well as community built firmwares.

# Looking to update or customise your Innioasis player? head to [innioasis.com/pages/download](https://innioasis.com/pages/download) to begin

## Devloped in Python using Cursor IDE by
- Ryan Specter of Team Slide

## Special Thanks to

### Team Slide branding lead
- u/_allstar
  
### the r/innioasis community and Mods

### Y1 Custom Android 4.2.2 ROM Developer
 - [@Multiwirth](https://www.github.com/multiwirth)

### Rockbox Y1 Port Developer and custom ROM packager
 - [@rockbox-y1](https://www.github.com/rockbox-y1)
 ### TikTok / YouTube creators
- Ryan /@catsteal3r on TikTok
- Corduroy cat - YouTuber
- Edit: I previously credited these as the same individual but it turns out they are actually seperate content creators. Sorry for any confusion caused. - Ryan Specter 
## MTKclient Credits

- bkerler for creating mtkclient
- kamakiri [xyzz]
- linecode exploit [chimera]
- Chaosmaster
- Geert-Jan Kreileman (MTKclient GUI, design & fixes)

## Installing on Linux (Not officially supported - you're on you're own)

- Install script (beta):

Try this install command in your terminal, and if it doesn't work for some reason, [file an issue](https://github.com/y1-community/Innioasis-Updater/issues) explaining your Linux distribution and the issue you encountered.

```
curl -fsSL https://innioasis.app/run_linux.sh | bash
```

- Setting up the MTKclient backend (if the install script doesn't do this properly and run it for you)

Please clone the repo on your linux system and follow the [MTKclient setup instructions](https://github.com/bkerler/mtkclient), once you've completed the setup process for MTKclient, simply open a terminal window, change into the directory you cloned Innioasis Updater into and run the command below.

```
python firmware_downloader.py
```
