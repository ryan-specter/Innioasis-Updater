/*!
 * Site i18n — English ↔ Night City (2077)
 * ---------------------------------------------------------------
 * i18n RULE: every new user-facing string added to this site must
 * also get a Night City translation here. Keep "Software", "Device
 * Model", "Release", and "Install / Restore" intact when they name
 * real Updater UI, so guides still point at the actual controls.
 * ---------------------------------------------------------------
 */
(function () {
    "use strict";

    var NIGHT_CITY = "2077";

    function isActive() {
        var root = document.documentElement;
        return !!root && root.getAttribute("data-lumen-theme") === NIGHT_CITY;
    }

    /* String rules: exact phrases, matched anywhere in a text node.
       Longer phrases are applied first so specific wins over generic. */
    var RULES = [
        /* Home */
        ["Up to date and all yours!", "Up to date and all yours."],
        ["Innioasis Updater helps you keep your player up-to-date with updates from Innioasis, and also lets you change your experience completely with custom software options like Rockbox, JJ Launcher, Solar, Koensayr and Inniclassic (to name a few)", "Innioasis Updater keeps your rig up-to-date with drops from Innioasis, and lets you flip your whole experience with custom soft like Rockbox, JJ Launcher, Solar, Koensayr and Inniclassic (to name a few)"],
        ["Get Innioasis Updater", "Grab Innioasis Updater"],
        ["Help me choose", "Pick your soft"],
        ["Community videos", "The Afterlife holos"],
        ["Get to Know Innioasis Updater", "Conoce Innioasis Updater"],
        ["Start here", "Start here"],
        ["Using Innioasis Updater", "Using Innioasis Updater"],
        ["Choose Y1 or Y2", "Choose Y1 or Y2"],
        ["Choose your software", "Choose your soft..."],
        ["Choose a project", "Choose your soft..."],
        ["Pick Original Software, Rockbox, Solar, JJ Launcher, Inniclassic, Y2Player, or Koensayr when it is listed for your model.", "Pick Original Software, Rockbox, Solar, JJ Launcher, Inniclassic, Y2Player, or Koensayr when it is on the board for your rig."],
        ["Use the model printed on the player. Y2 packages and install tools are different from Y1 packages.", "Use the model printed on the rig. Y2 drops and install tools are a different breed from Y1."],
        ["Updater prepares the files, then tells you when to power off and connect the USB cable.", "Updater preps the files, then tells you when to cut power and jack in the datalink."],
        ["Getting started with Rockbox on your Innioasis", "Getting started with Rockbox on your Innioasis"],
        ["Choose a route", "Pick a route"],
        ["Install Rockbox on Y1", "Rockbox on Y1"],
        ["Choose Y1, select Rockbox, pick a stable release, then connect only when Updater asks.", "Pick Y1, select Rockbox, grab a stable drop, then jack in only when Updater asks."],
        ["Read Y1 steps", "Read the Y1 run"],
        ["Install Rockbox on Y2", "Rockbox on Y2"],
        ["Choose Y2 first. The Y2 route uses a different package and must not be treated as a Y1 install.", "Pick Y2 first. The Y2 route runs a different drop and is never a Y1 install."],
        ["Read Y2 steps", "Read the Y2 run"],
        ["Restore Original Software on your Y1", "Back to stock on your Y1"],
        ["Restore Original Software on your Y2", "Back to stock on your Y2"],
        ["Restore Original Software on your Y1.", "Back to stock on your Y1."],
        ["Restore Original Software on your Y2.", "Back to stock on your Y2."],
        ["Restore Original Software", "Back to stock"],
        ["Coming back from Rockbox or another custom software uses the same Updater flow: select your model, choose Original Software, and run Install / Restore.", "Coming back from Rockbox or another custom soft is the same Updater flow: pick your model, choose Original Software, and run Install / Restore."],
        ["Y1 stock restore", "Y1 stock run"],
        ["Y2 stock restore", "Y2 stock run"],
        ["Works on Windows, macOS, or Linux after that computer’s Updater setup is ready.", "Works on Windows, macOS, or Linux after that rig’s Updater setup is done."],
        ["Support Updater and the Themes Gallery.", "We need Eddies."],
        ["Support Updater and the Themes Gallery", "We need Eddies"],
        ["Donate", "Give Eddies"],
        ["Privacy", "Privacy"],
        ["No cookies. No fingerprinting.", "No cookies. No fingerprinting."],
        ["Innioasis.app — the site for Updater Community Edition — does not use cookies or browser fingerprinting. We remember your site theme and text size, and only the preferences you allow.", "Innioasis.app — the deck for Updater Community Edition — runs no cookies and no fingerprinting. We keep your deck theme and text size, and only the prefs you allow."],
        ["Accept all", "Accept all"],
        ["Essential only", "Essentials only"],
        ["Manage", "Manage"],
        ["Remember my \"was this useful?\" answers", "Remember my \"preem or gonk?\" answers"],
        ["Asked on the guide pages.", "Asked on the run pages."],
        ["Remember my nightly-builds choice", "Remember my nightly-builds pick"],
        ["Used on the software directory.", "Used on the soft directory."],
        ["Your site theme and text size are always remembered — they are the look and readability you chose. Links to YouTube, Discord, Ko-fi, PayPal, Revolut, and Patreon open those sites' own pages, which have their own policies.", "Your deck theme and text size are always kept — they're the look and readability you picked. Links to YouTube, Discord, Ko-fi, PayPal, Revolut, and Patreon open those sites' own pages, which run their own policies."],
        ["Save choices", "Lock in the choices"],
        ["Links to YouTube, Discord, Ko-fi, PayPal, Revolut, and Patreon open those sites' own pages, which have their own policies.", "Links to YouTube, Discord, Ko-fi, PayPal, Revolut, and Patreon open those sites' own pages, which run their own policies."],
        ["Innioasis Updater and the Themes Gallery are community hobbyist projects. They rely on people giving their time, plus real costs for hosting, domain renewals, moderation, and release work. If these tools helped you install or restore your player, support the work that keeps them available.", "Innioasis Updater and the Themes Gallery are community hobbyist projects. They run on people’s time plus real costs: hosting, domain renewals, moderation, drop work, and Cloudflare Workers. If these tools helped you flash or restore your rig, fund the work that keeps them alive."],
        /* Carousel */
        ["Credit: ", "Cred: "],
        ["Video by ", "Holo by "],
        ["Video ", "Holo "],
        ["Prefer reading? The", "More of a reader? The"],
        ["written installation guide", "written install run"],
        /* Guide */
        ["Use Updater without guessing.", "Use Updater without guessing."],
        ["This guide applies to", "This run applies to"],
        ["Before you start", "Before you jack in"],
        ["Have the player you want to update, a USB data cable, and a Windows, macOS, or Linux computer. Charge the player first. A cable that only charges cannot carry the install.", "Have the rig you want to update, a datalink, and a Windows, macOS, or Linux deck. Charge the rig first. A cable that only charges cannot carry the install."],
        ["software installation changes system software. Keep the cable connected until Updater says it is safe to disconnect.", "soft install changes the system software. Keep the datalink connected until Updater says it is safe to unplug."],
        ["If a custom install does not start, the normal recovery path is Original Software for the same model.", "If a custom install does not start, the normal recovery path is Original Software for the same rig."],
        ["Here's where to start if you haven't already got Updater.", "Here's where to start if you haven't already got Updater."],
        ["Another platform?", "Another platform?"],
        ["Copy command", "Copy the command"],
        ["Copied!", "Copied!"],
        ["Download the installer, open it, and follow the setup prompts.", "Grab the installer, open it, and follow the setup prompts."],
        ["Download & Install Driver", "Grab & install the driver"],
        ["Download AppImage for Intel/AMD", "Grab AppImage for Intel/AMD"],
        ["Download the AppImage for Intel and AMD systems, make it executable, and run it.", "Grab the AppImage for Intel and AMD systems, make it executable, and run it."],
        ["Download the app, move it to Applications, then open it. If macOS says the app can't be opened because it is from an unidentified developer, open System Settings, click Privacy & Security, scroll down and click Open Anyway, then click Open when the warning reappears.", "Grab the app, drop it in Applications, then open it. If macOS says the app can't be opened because it's from an unidentified dev, open System Settings, hit Privacy & Security, scroll down and hit Open Anyway, then hit Open when the warning pops back up."],
        ["How Open Anyway works", "How Open Anyway works"],
        ["Download started", "Drop started"],
        ["You'll need to reboot your PC after installing to make it work.", "You'll need to reboot your deck after installing to make it work."],
        ["Choose your model and software", "Choose your model and soft"],
        ["Open Updater and follow the labels in the window. Select your model first, then select the software you want to run on that model.", "Open Updater and follow the labels in the window. Pick your model first, then pick the soft you want to run on that rig."],
        ["Device Model:", "Device Model:"],
        ["Software:", "Software:"],
        ["Release:", "Release:"],
        ["select Original Software, Rockbox, Solar, JJ Launcher, Inniclassic, Y2Player, or Koensayr when it is listed for your model.", "select Original Software, Rockbox, Solar, JJ Launcher, Inniclassic, Y2Player, or Koensayr when it is on the board for your rig."],
        ["select a release for the software and model you chose. Prefer a stable release unless you have a reason to test a preview or nightly build.", "grab a drop for the soft and rig you chose. Prefer a stable drop unless you are deliberately testing a preview or nightly build."],
        ["Install or restore", "Flash or restore"],
        ["Click Install / Restore. Updater downloads the selected package and extracts the files it needs.", "Click Install / Restore. Updater pulls the selected drop and extracts what it needs."],
        ["Wait for the connection instructions. Do not connect the player early unless the app specifically tells you to.", "Wait for the jack-in prompt. Do not jack the rig in early unless the app specifically tells you to."],
        ["Power the player fully off. If it will not shut down normally, follow the exact recovery prompt shown by Updater.", "Cut power on the rig fully. If it will not shut down normally, follow the exact recovery prompt Updater shows."],
        ["Connect the USB data cable when Updater says it is ready. Put the player down and do not move the cable.", "Jack the datalink in when Updater says it is ready. Put the rig down and do not move the cable."],
        ["When the app confirms success, disconnect the cable and start the player.", "When the app confirms success, unplug and boot the rig."],
        ["Going back to Original Software", "What if my player flatlines?"],
        ["You can return from Rockbox or another listed custom software with Updater. After the relevant Windows, macOS, or Linux setup is ready, this is not a different emergency tool: repeat the same Install / Restore journey and choose Original Software for the same model.", "You can return from Rockbox or another listed custom soft with Updater. Once the Windows, macOS, or Linux setup is ready, this is not a different emergency tool: repeat the same Install / Restore run and choose Original Software for the same rig."],
        ["Choose the model printed on the player. Never use a Y1 stock package on a Y2 or a Y2 package on a Y1.", "Choose the model printed on the rig. Never run a Y1 stock drop on a Y2 or a Y2 drop on a Y1."],
        ["Select Original Software, then choose a stable release shown for that model.", "Select Original Software, then grab a stable drop shown for that rig."],
        ["Click Install / Restore and wait for the app’s connection instructions.", "Click Install / Restore and wait for the app’s jack-in prompt."],
        ["Power off and connect the USB data cable only when Updater asks. Leave the player and cable alone until the success message.", "Cut power and jack in the datalink only when Updater asks. Leave the rig and cable alone until the success message."],
        ["If you came from Solar or Rockbox:", "If you came from Solar or Rockbox:"],
        ["do not try to remove folders or change hidden files first. The stock restore is a software install, so let Updater replace the system software for you.", "do not try to remove folders or touch hidden files first. The stock restore is a soft install, so let Updater replace the system for you."],
        ["Manual SP Flash Tool and MTKClient routes are for advanced recovery, not the normal return-to-stock path.", "Manual SP Flash Tool and MTKClient routes are for advanced recovery, not the normal return-to-stock path."],
        ["Software guides by model", "Soft guides by rig"],
        ["Pick the model printed on your player, then open the guide for the software you want. The model comes first so the guide stays model-matched.", "Pick the model printed on your rig, then open the run for the soft you want. The model comes first so the run stays model-matched."],
        ["Guides for Y1 projects:", "Runs for Y1 rigs:"],
        ["Guides for Y2 projects:", "Runs for Y2 rigs:"],
        /* Generic software guide (software-guide.html) */
        ["Software installation guide", "Soft install run"],
        ["Install a listed software on your Innioasis Y1 or Y2", "Install a listed soft on your Innioasis Y1 or Y2"],
        ["Pick the model printed on your player, then follow the steps in Updater for the software you chose. The model comes first so the steps stay model-matched.", "Pick the model printed on your rig, then follow the Updater steps for the soft you chose. The model comes first so the run stays model-matched."],
        ["Pick the model printed on your player and the software you want, then open this guide.", "Pick the model printed on your rig and the soft you want, then open this run."],
        ["Browse software by model", "Browse soft by rig"],
        [" or another listed custom software with Updater: choose the model printed on your player, select ", " or another listed custom soft with Updater: pick the model printed on your rig, select "],
        [". The stock restore is a software install, so Updater replaces the system software for you.", ". The stock restore is a soft install, so Updater replaces the system software for you."],
        /* Software FAQ: what each route gives you */
        ["What each route gives you", "What each route’s got for you"],
        ["Pick the software that matches how you listen.", "Elevate your braindance experience."],
        ["The software your player shipped with. Local music, Bluetooth, and the familiar interface with nothing extra to configure. It is the safe baseline and the quickest way back if a custom install does not behave.", "The soft your rig shipped with. Local music, Bluetooth, and the familiar interface with nothing extra to configure. It is the safe baseline and the fastest way back if a custom flash misbehaves."],
        ["The music-lover's route. A proper database that sorts albums and artists by tags instead of file names, gapless playback, crossfade, an equalizer, and a deep theme library including iPod-style interfaces. It is built around local files, so it stays offline.", "The music-head’s route. A proper database that sorts albums and artists by tags instead of file names, gapless playback, crossfade, an EQ, and a deep theme library including iPod-style interfaces. Built around local files, so it stays offline."],
        ["The network-first route. It enables Wi-Fi on the Y1 and Y2 and adds streaming and downloads: Deezer and Soulseek through its Reach music search, podcast downloads, and YouTube playback. A stem player can split a song into vocals, drums, bass, and melody for on-device remixing, and Rockbox rides on the same install so you can switch without reflashing.", "The network-first route. It fires up Wi-Fi on the Y1 and Y2 and adds streaming and downloads: Deezer and Soulseek through its Reach music search, podcast drops, and YouTube playback. A stem player can split a song into vocals, drums, bass, and melody for on-deck remixing, and Rockbox rides on the same install so you can switch without reflashing."],
        ["A fast, wheel-friendly launcher. Rapid library scanning, equalizer presets, track skipping with the hardware buttons from any screen, wireless file uploads over Wi-Fi, in-app Bluetooth pairing, and themes you can drop in or design with the web theme editor.", "A fast, wheel-friendly launcher. Rapid library scanning, EQ presets, track skipping with the hardware buttons from any screen, wireless file uploads over Wi-Fi, in-app Bluetooth pairing, and themes you can drop in or build with the web theme editor."],
        ["An iPod Classic tribute built on JJ Launcher. The classic menu look, a click-wheel style Music Quiz, synced lyrics, Last.fm scrobbling, plus podcasts, FM radio, and video. Y1 only, and still a community project.", "An iPod Classic tribute built on JJ Launcher. The classic menu look, a click-wheel style Music Quiz, synced lyrics, Last.fm scrobbling, plus podcasts, FM radio, and video. Y1 only, and still a community gig."],
        ["A music-first home screen for the Y2. Offline playback with a persistent queue, gapless and crossfade transitions, audiobooks that resume where you stopped, and every common format from FLAC to Opus. Bluetooth audio works, and no internet connection is required.", "A music-first home screen for the Y2. Offline playback with a persistent queue, gapless and crossfade transitions, audiobooks that resume where you stopped, and every common format from FLAC to Opus. Bluetooth audio works, and no net connection is required."],
        ["Not a new interface. It is a patcher that improves the stock Y1 software: Artist to Album navigation in the built-in music app, proper track metadata and controls over Bluetooth for car stereos, root access, and a debloated system. A good fit if you want to keep the original software and fix how it behaves.", "Not a new interface. It is a patcher that improves the stock Y1 soft: Artist to Album navigation in the built-in music app, proper track metadata and controls over Bluetooth for car stereos, root access, and a debloated system. A good fit if you want to keep the original soft and fix how it behaves."],
        ["These projects move fast. Read each project's release notes and issues tracker before installing. Solar, JJ Launcher, Inniclassic, Y2Player, and Koensayr are community software and can be rough around the edges. If anything goes wrong, restoring Original Software for your model is the way back.", "These gigs move fast. Read each project’s release notes and issues tracker before flashing. Solar, JJ Launcher, Inniclassic, Y2Player, and Koensayr are community soft and can be rough around the edges. If the gig goes sideways, restoring Original Software for your rig is the way back."],
        ["Restore on Y1", "Stock on Y1"],
        ["Restore on Y2", "Stock on Y2"],
        ["Solar on Y1", "Solar on Y1"],
        ["Solar on Y2", "Solar on Y2"],
        ["JJ Launcher on Y1", "JJ Launcher on Y1"],
        ["JJ Launcher on Y2", "JJ Launcher on Y2"],
        ["Inniclassic on Y1", "Inniclassic on Y1"],
        ["Y2Player on Y2", "Y2Player on Y2"],
        ["Koensayr on Y1", "Koensayr on Y1"],
        ["Was this useful?", "Preem soft, or gonk work, choom?"],
        ["Your answer helps improve this guide.", "Your answer helps sharpen this run."],
        ["Yes, I found it useful", "Preem"],
        ["Yes", "Preem"],
        ["Not yet", "Not yet"],
        ["Let us know how we can improve", "Ping the fixer with feedback"],
        ["Maybe later", "Later"],
        /* Homepage software table */
        ["Software for Y1 and Y2", "Soft for Y1 and Y2"],
        ["See what you can install.", "The Ripperdoc's got some great new soft for you"],
        ["Open the full release list", "Open the full drop list"],
        ["Software available for the Innioasis Y1 and Y2, with release listings for each model", "Soft on the board for the Innioasis Y1 and Y2, with drop listings for each rig"],
        ["All software listed is from the ", "All soft listed is from the "],
        [" shows the releases for each model, with install guides, manual ZIP downloads, and the ", " shows the drops for each rig, with install runs, manual ZIP downloads, and the "],
        ["Releases", "Drops"],
        ["Nightly", "Nightly"],
        ["Loading the latest Software versions…", "Pulling the latest soft drops…"],
        ["No releases", "No drops"],
        ["The latest versions refresh from the project release feeds.", "The latest drops refresh from the project release feeds."],
        ["The list loaded where available; some release feeds are unreachable right now.", "The list loaded where it could; some drop feeds are down right now."],
        /* Software directory */
        ["Browse Original Software and community Software releases for Innioasis Y1 and Y2.", "Browse Original Software and community soft drops for Innioasis Y1 and Y2."],
        ["Choose the model printed on your player, then browse every public Software release listed for it. When you are ready to install, use the guided Updater route instead of downloading a ZIP first.", "Choose the model printed on your rig, then browse every public soft drop listed for it. When you are ready to flash, take the guided Updater route instead of pulling a ZIP first."],
        ["Get it on Updater", "Grab it on Updater"],
        ["with guided install", "with guided install"],
        ["Install your choice with Updater", "Flash your choice with Updater"],
        ["Open the guide and install Innioasis Updater for your computer if you do not have it yet.", "Open the run and grab Innioasis Updater for your deck if you do not have it yet."],
        ["In Updater, select the model printed on your player from Device Model.", "In Updater, select the model printed on your rig from Device Model."],
        ["From Software, select the software you want to run on that model.", "From Software, select the soft you want to run on that rig."],
        ["Select a release, click Install / Restore, then power off and connect the player only when Updater asks.", "Select a drop, click Install / Restore, then cut power and jack the rig in only when Updater asks."],
        ["Need the installer? Open the guide and expand the Updater download section.", "Need the installer? Open the run and expand the Updater drop section."],
        ["Choose the software you want to run.", "Choose the soft you want to run."],
        ["Show nightly builds", "Show nightly builds"],
        ["Show preview and nightly builds alongside stable releases.", "Show preview and nightly builds alongside stable drops."],
        ["No stable release yet", "No stable drop yet"],
        ["Tick the nightly-builds option to see previews", "Tick the nightly-builds option to see previews"],
        ["If something goes wrong", "If the gig goes sideways"],
        ["The safe way back", "The safe way back"],
        ["Use the guide", "Take the run"],
        ["Release details and zip", "Drop details and zip"],
        ["No ZIP asset was found in this release.", "No ZIP asset in this drop."],
        ["Y1 · Type A", "Y1 · Type A"],
        ["Y1 · Type B", "Y1 · Type B"],
        ["Checking public releases", "Scanning the drop feed"],
        ["No public releases", "No drops on the board"],
        ["Release feed unavailable", "Drop feed is down"],
        ["No release with", "No drop with"],
        ["Try project releases", "Check the project's drops"],
        ["Loading public release information", "Pulling drop intel"],
        ["All public releases are shown.", "All public drops are on the board."],
        ["Release information is not available right now. The project links remain available.", "Drop intel is down right now. The project links still work."],
        ["No software project is currently listed for this model and filter. Try another project or check the project release pages.", "Nothing is on the board for that rig and filter. Try another soft or check the project's drop pages."],
        /* Rockbox */
        ["Getting Rockbox on your Y1 or Y2", "Getting Rockbox on your Y1 or Y2"],
        ["What the install changes", "What the flash changes"],
        ["Rockbox is custom software. It does not remove your ability to return to the stock interface when the matching Original Software package is available.", "Rockbox is custom soft. It does not remove your ability to return to the stock interface when the matching Original Software drop is available."],
        ["Do not mix models.", "Do not mix rigs."],
        ["Select Y1 for a Y1 player and Y2 for a Y2 player. A similar-looking release name is not enough evidence that a package is compatible.", "Select Y1 for a Y1 rig and Y2 for a Y2 rig. A similar-looking drop name is not proof the package is compatible."],
        ["Watch the video", "Watch the holo"],
        ["The shared Updater route", "The shared Updater run"],
        ["Install Updater and connect nothing until it asks.", "Install Updater and hold off jacking in until it asks."],
        ["Choose the model printed on the player in Device Model.", "Choose the model printed on the rig in Device Model."],
        ["Choose Rockbox in Software.", "Choose Rockbox in Software."],
        ["Choose a stable release unless you are deliberately testing a nightly build.", "Choose a stable drop unless you are deliberately testing a nightly build."],
        ["Click Install / Restore, then follow the power-off and USB connection prompt.", "Click Install / Restore, then follow the power-off and datalink prompt."],
        ["Disconnect only after the success message.", "Unplug only after the success message."],
        ["240p, 360p, and themes", "240p, 360p, and themes"],
        ["Returning to Original Software", "Returning to stock"],
        ["Choose the same model again, select Original Software, choose a stable release, and use Install / Restore.", "Choose the same rig again, select Original Software, grab a stable drop, and use Install / Restore."],
        /* Rockbox questions + dotfiles tip. The OS steps inside the tip
           keep real app names and keyboard shortcuts as-is; only the
           surrounding prose is rephrased for Night City. */
        ["Rockbox questions", "Rockbox questions"],
        ["I reinstalled Rockbox and it didn't fix anything.", "I reflashed Rockbox and nothing changed."],
        ["Reinstalling Rockbox writes the same build over the same files, so it cannot reset the things Rockbox keeps on the MicroSD. If the problem is a broken setting, theme, playlist, or database that lives on the card, reinstalling will not clear it. The reliable reset is deleting the ", "Reflashing Rockbox writes the same build over the same files, so it cannot reset what Rockbox keeps on the MicroSD. If the problem is a broken setting, theme, playlist, or database living on the card, a reflash will not clear it. The reliable reset is deleting the "],
        [" folder from the MicroSD — Rockbox builds a fresh one on the next boot.", " folder from the MicroSD — Rockbox builds a fresh one on the next boot."],
        ["Power the player fully off and remove the MicroSD card, or connect the player as a USB drive.", "Power the rig fully off and pop the MicroSD, or jack the rig in as a USB drive."],
        ["Show hidden files on your computer so the folder is visible.", "Show hidden files on your deck so the folder is visible."],
        ["Reinsert the card and start the player. Rockbox recreates the folder with defaults.", "Reinsert the card and boot the rig. Rockbox recreates the folder with defaults."],
        ["Re-apply your theme and settings. If the problem only comes back after a specific theme, that theme is the cause.", "Re-apply your theme and settings. If the problem only returns after a specific theme, that theme is the cause."],
        [" does not uninstall Rockbox and does not touch your music — the folder holds settings, themes, and caches, and is rebuilt automatically. If you want to keep your themes, copy the folder out of ", " does not uninstall Rockbox and does not touch your music — the folder holds settings, themes, and caches, and is rebuilt automatically. Want to keep your themes? Copy the folder out of "],
        ["Why can't I see the .rockbox folder on my MicroSD?", "Why can't I see the .rockbox folder on my MicroSD?"],
        ["Folders whose name starts with a dot are hidden by default on most computers. You do not need to see it to install Rockbox — Updater handles the files. If you are troubleshooting and want to delete it, turn on hidden files first.", "Folders whose name starts with a dot are hidden by default on most decks. You do not need to see it to install Rockbox — Updater handles the files. If you are fixing something and want to delete it, turn on hidden files first."],
        ["Will deleting .rockbox reset my theme and settings?", "Will deleting .rockbox reset my theme and settings?"],
        [" holds Rockbox's settings, theme, playlists, and cached database. Deleting it returns Rockbox to a clean default state. Back up the whole folder (or rename it to ", " holds Rockbox's settings, theme, playlists, and cached database. Deleting it returns Rockbox to a clean default state. Back up the whole folder (or rename it to "],
        [") if you might want any of it back, then start the player and Rockbox creates a new folder.", ") if you might want any of it back, then start the rig and Rockbox creates a new folder."],
        ["Show dotfiles on your computer", "Show dotfiles on your deck"],
        ["Windows:", "Windows:"],
        ["macOS:", "macOS:"],
        ["Linux · GNOME Files:", "Linux · GNOME Files:"],
        ["Linux · KDE Dolphin:", "Linux · KDE Dolphin:"],
        [" in File Explorer open the ", " in File Explorer open the "],
        [" tab and tick ", " tab and tick "],
        [" in Finder press ", " in Finder press "],
        [" to toggle hidden files.", " to toggle hidden files."],
        [" press ", " press "],
        [", or open the menu and choose ", ", or open the menu and choose "],
        [", or use ", ", or use "],
        ["Hidden items", "Hidden items"],
        ["Show Hidden Files", "Show Hidden Files"],
        ["View → Show Hidden Files", "View → Show Hidden Files"],
        ["Was this reference useful?", "Preem soft, or gonk work, choom?"],
        /* Drivers */
        ["Make the computer ready before the player.", "Make the deck ready before the rig."],
        ["Most connection problems come from the driver, permissions, cable, or timing. Windows needs the MediaTek driver installed. Linux needs the right USB permissions. Find your platform below.", "Most connection problems come from the driver, permissions, datalink, or timing. Windows needs the MediaTek driver installed. Linux needs the right USB permissions. Find your platform below."],
        ["Download the MediaTek driver installer below.", "Grab the MediaTek driver installer below."],
        ["Run the installer and allow Windows to install the driver.", "Run the installer and let Windows install the driver."],
        ["Restart the computer.", "Reboot the deck."],
        ["Open Updater and wait for the connect prompt before you plug in the powered-off player.", "Open Updater and wait for the jack-in prompt before you jack in the powered-off rig."],
        ["Some Windows systems block the driver through Core isolation (Memory integrity). If Updater still cannot see the player after a restart, turn Memory integrity off in Windows Security, restart, and reinstall the driver. Turn the setting back on when you are finished if your system allows it.", "Some Windows systems block the driver through Core isolation (Memory integrity). If Updater still cannot see the rig after a reboot, turn Memory integrity off in Windows Security, reboot, and reinstall the driver. Turn the setting back on when you are done if your system allows it."],
        ["Download Windows driver", "Download Windows driver"],
        ["Linux USB permissions", "Linux USB permissions"],
        ["Linux needs your user account to be allowed to talk to the MediaTek USB chip inside the player. Updater usually sorts this out during install, and the same permission covers SP Flash Tool, so treat this as a fix-it step rather than a normal stage.", "Linux needs your user account to be allowed to talk to the MediaTek USB chip inside the rig. Updater usually sorts this out during install, and the same permission covers SP Flash Tool, so treat this as a fix-it step rather than a normal stage."],
        ["Run Updater as your normal user, not as root. The installer asks for administrator access only when it needs it.", "Run Updater as your normal user, not as root. The installer asks for administrator access only when it needs it."],
        ["Check the player is seen at all. Power the player off, connect the cable, and run the lsusb command in a terminal. A connected player shows up as a MediaTek device with the vendor ID 0e8d.", "Check the rig is seen at all. Power the rig off, jack in the datalink, and run the lsusb command in a terminal. A connected rig shows up as a MediaTek device with the vendor ID 0e8d."],
        ["If it appears in lsusb but Innioasis Updater or SP Flash Tool says permission denied or cannot open the port, your user is missing access to the USB device. The same udev rule covers both tools, so add one that lets the users group read it.", "If it shows in lsusb but Innioasis Updater or SP Flash Tool says permission denied or cannot open the port, your user is missing access to the USB device. The same udev rule covers both tools, so add one that lets the users group read it."],
        ["Save that line to a new file named /etc/udev/rules.d/51-innioasis.rules, then run:", "Save that line to a new file named /etc/udev/rules.d/51-innioasis.rules, then run:"],
        ["Unplug the player fully, plug it back in, and try the install again.", "Unplug the rig fully, jack it back in, and try the install again."],
        ["If SP Flash Tool reports a serial permission or port race, unplug fully and reconnect only when prompted.", "If SP Flash Tool reports a serial permission or port race, unplug fully and jack back in only when prompted."],
        ["Do not improvise flash offsets.", "Do not improvise flash offsets."],
        ["If you move to a manual recovery tool, use the files and model-specific configuration shipped with the project.", "If you move to a manual recovery tool, use the files and model-specific config shipped with the project."],
        ["Download Updater CE", "Grab Updater CE"],
        ["Cable and timing", "Datalink and timing"],
        ["Use a known USB data cable.", "Use a known datalink."],
        ["Avoid hubs while troubleshooting.", "Skip the hubs."],
        ["Power the correct model fully off.", "Power the right rig fully off."],
        ["Connect only at the prompt.", "Jack in only at the prompt."],
        ["Back to the main guide", "Back to the main run"],
        /* Troubleshooting */
        ["Find the point where the install stopped.", "Find where the install flatlined."],
        ["The fastest fix depends on whether Updater stopped while preparing files, while waiting for USB, or after it detected the player.", "The fastest fix depends on whether Updater stopped while prepping files, while waiting for USB, or after it found the rig."],
        ["It stopped before the USB prompt", "It flatlined before the USB prompt"],
        ["This is a computer-side problem, not a cable timing problem.", "This is a deck-side problem, not a datalink timing problem."],
        ["Re-check that the model is correct, re-extract the selected package, and try Install / Restore again.", "Re-check that the model is correct, re-extract the selected drop, and try Install / Restore again."],
        ["It cannot connect to the player", "It cannot reach the rig"],
        ["Fully power off the correct Y1 or Y2.", "Fully power off the right Y1 or Y2."],
        ["Unplug the cable, close other flash or Android tools, and start the install again.", "Unplug the datalink, close other flash or Android tools, and start the install again."],
        ["Connect only when Updater says it is ready.", "Jack in only when Updater says it is ready."],
        ["Use a short USB data cable directly in the computer, not a hub if possible.", "Use a short datalink straight into the deck, not a hub if you can help it."],
        ["On Windows, reinstall the MediaTek driver and restart. On Linux, check USB/serial permissions.", "On Windows, reinstall the MediaTek driver and restart. On Linux, check USB/serial permissions."],
        ["It detected the player but the flash failed", "It found the rig but the flash failed"],
        ["Do not keep retrying with a different model or package.", "Do not keep retrying with a different model or drop."],
        ["Windows driver notes", "Windows driver notes"],
        ["Open driver guide", "Open driver run"],
        ["Clean install guide", "Clean install run"],
        ["Still stuck?", "Still stuck?"],
        ["Ask the community", "Ask at the Afterlife"],
        ["Support maintenance", "Fund the cause"],
        /* FAQ */
        ["Software questions answered", "Soft questions answered"],
        ["Which software is right for you?", "Which soft is right for you?"],
        ["Tutorials by model", "Gigs by rig"],
        ["Pick the model printed on your player, then choose the project from that list. Each link opens the tutorial for that model and project.", "Pick the model printed on your rig, then choose the soft from that list. Each link opens the run for that model and soft."],
        ["Projects available for Y1:", "Soft on the board for Y1:"],
        ["Projects available for Y2:", "Soft on the board for Y2:"],
        ["Browse Y1 releases", "Browse Y1 drops"],
        ["Browse Y2 releases", "Browse Y2 drops"],
        ["Model compatibility at a glance", "Rig compatibility at a glance"],
        /* Developer guide: base ROMs */
        ["Start from a base ROM", "Start from a base shard"],
        ["Base ROM downloads for custom firmware development, with the Android version and wireless features each one enables", "Base shard downloads for custom soft development, with the Android version and wireless features each one enables"],
        ["Base ROMs give custom firmware developers a clean Android foundation with the wireless radio chips enabled. On the Y1 they enable Wi-Fi and GPS alongside the factory Bluetooth and FM; on the Y2 they enable Wi-Fi, GPS, and FM alongside the factory Bluetooth.", "Base shards give custom soft devs a clean Android foundation with the wireless radio chips firing. On the Y1 they enable Wi-Fi and GPS alongside the factory Bluetooth and FM; on the Y2 they enable Wi-Fi, GPS, and FM alongside the factory Bluetooth."],
        ["Adds Wi-Fi and GPS to the factory Bluetooth and FM (FM already works on the Y1 from the factory). For Y1 players that shipped with OS 2.0.0 or later.", "Adds Wi-Fi and GPS to the factory Bluetooth and FM (FM already runs on the Y1 from the factory). For Y1 rigs that shipped with OS 2.0.0 or later."],
        ["Adds Wi-Fi and GPS to the factory Bluetooth and FM (FM already works on the Y1 from the factory). For Y1 players that shipped with an OS earlier than 2.0.0.", "Adds Wi-Fi and GPS to the factory Bluetooth and FM (FM already runs on the Y1 from the factory). For Y1 rigs that shipped with an OS earlier than 2.0.0."],
        ["Adds Wi-Fi, GPS, and FM to the factory Bluetooth. The Y2 radio chip is fully enabled, so FM is available here too.", "Adds Wi-Fi, GPS, and FM to the factory Bluetooth. The Y2 radio chip is fully live, so FM is on the board here too."],
        ["These images are the stock Android base (AOSP) with the device wireless radios enabled, so a custom firmware can add network features instead of replacing the radio stack. They are the practical starting point for the publishing steps below.", "These images are the stock Android base (AOSP) with the device wireless radios firing, so a custom soft can add network features instead of replacing the radio stack. They are the practical starting point for the publishing steps below."],
        /* Support devs */
        ["We get by with a lil' help from our friends", "We get by with a lil' help from our choombas"],
        ["Innioasis Updater, the software directory, themes, and recovery notes are maintained by community contributors. This page explains the practical ways to help.", "Innioasis Updater, the soft directory, themes, and recovery notes are kept alive by community contributors. This page explains the practical ways to help."],
        ["Ways to contribute", "Ways to pull weight"],
        ["Report clearly", "File a clean report"],
        ["Include the model, operating system, project, release, exact message, and the point where the install stopped.", "Include the model, OS, project, drop, exact message, and the point where the install flatlined."],
        ["Improve a guide", "Sharpen a guide"],
        ["Build and test", "Build and stress-test"],
        ["Software projects, themes, tools, and device testing all help the ecosystem move forward.", "Soft projects, themes, tools, and device testing all push the ecosystem forward."],
        ["Innioasis Updater and the Themes Gallery are community hobbyist projects. They are kept going by contributors, but hosting, domain renewals, moderation, release work, and Cloudflare Workers create real costs.", "Innioasis Updater and the Themes Gallery are community hobbyist projects. Contributors keep them going, but hosting, domain renewals, moderation, drop work, and Cloudflare Workers create real costs."],
        ["Support on Ko-fi", "Fund on Ko-fi"],
        ["Developer documentation", "Dev docs"],
        ["Publishing a custom software? Read the developer guide for adding Y1 and Y2 releases to Updater.", "Shipping a custom soft? Read the dev guide for adding Y1 and Y2 drops to Updater."],
        ["Project links", "Project links"],
        /* SP Flash Tool */
        ["Keep the models separate.", "Keep the rigs separate."],
        ["Load the scatter and flash", "Load the scatter and flash"],
        ["Open SP Flash Tool from the Updater install folder.", "Open SP Flash Tool from the Updater install folder."],
        ["Click Download. The tool will wait for the player.", "Click Download. The tool will wait for the rig."],
        ["Power the player fully off, then connect the USB data cable. Put the player down and do not move it.", "Power the rig fully off, then jack in the datalink. Put the rig down and do not move it."],
        ["Wait for the green check mark. Only then disconnect the cable and start the player.", "Wait for the green check. Only then unplug and boot the rig."],
        ["If it does not flash", "If it won't flash"],
        ["Check that the scatter and ZIP match the model printed on the player.", "Check that the scatter and ZIP match the model printed on the rig."],
        ["Confirm the player is fully powered off before connecting.", "Confirm the rig is fully powered off before jacking in."],
        ["Reconnect the cable only when the tool is waiting. A port race can need a full unplug and a fresh Download click.", "Jack the datalink back in only when the tool is waiting. A port race can need a full unplug and a fresh Download click."],
        /* Footer */
        /* Community Edition keeps its name in every theme, including 2077. */
        ["Updater Community Edition", "Updater CE"],
        ["Community Edition", "CE"],
        ["Innioasis Updater", "Innioasis Updater"],
        ["Installation guide", "Install run"],
        ["Software Downloads", "Soft drops"],
        ["Troubleshooting", "Damage control"],
        ["Developer guide", "Dev guide"],
        ["Community", "The Afterlife"],
        ["Updater source code", "Updater source code"],
        ["Developers", "Ripperdocs"],
        ["Add software to Updater", "Ripperdocs Guidance"],
        ["Copyleft · Innioasis users and contributors, for the community.", "Copyleft · Night City residents and contributors, for the community."],
        ["Blog", "Blog"],
].sort(function (a, b) { return b[0].length - a[0].length; });

    /* Regex rules for JS-generated text (personalised steps, headings). */
    var REGEX_RULES = [
        /* The greedy "Community" string rule would turn the product name
           into "Updater The Afterlife Edition"; restore it after the
           string rules run. */
        [/Updater The Afterlife Edition/, "Updater CE"],
        [/The Afterlife Edition/, "Community Edition"],
        [/Afterlife Edition/, "Community Edition"],
        [/^Install (.+) on your (Y1|Y2)$/, "Flash $1 on your $2"],
        [/^Install (.+) on your (Y1|Y2)\.$/, "Flash $1 on your $2."],
        [/^Install (.+) on your (Y1|Y2) [-|] Innioasis Updater$/, "Flash $1 on your $2 | Innioasis Updater"],
        [/^Restore Original Software on your (Y1|Y2)$/, "Back to stock on your $1"],
        [/^Restore Original Software on your (Y1|Y2)\.$/, "Back to stock on your $1."],
        [/^Restore Original Software on your (Y1|Y2) \| Innioasis Updater$/, "Back to stock on your $1 | Innioasis Updater"],
        [/^Install (.+) on (Y1|Y2)\.$/, "Flash $1 on $2."],
        [/^Open Updater on your computer, or install it first with the button below\.$/, "Jack into Updater on your deck (or grab it with the button below)."],
        [/^In Device Model, select (Y1|Y2)\.$/, "In Device Model, pick $1."],
        [/^In Software, select ([^.]+)\.$/, "In Software, pick $1."],
        [/^Select a stable release shown for the (Y1|Y2)\.$/, "Grab a stable drop for the $1."],
        [/^Click Install \/ Restore, then power off the player\.$/, "Click Install / Restore, then power off the rig."],
        [/^Connect the player only when Updater says it is ready\.$/, "Jack the rig in only when Updater says go."],
        [/^Wait for the success message, then disconnect and start the player\.$/, "Wait for the green light, then unplug and boot the rig."],
        [/^That is the whole (.+) install on the (Y1|Y2)\. The download and computer setup sections below still apply if you need them\.$/, "That is the whole $1 flash on the $2. The drop and deck setup sections below still apply if you need them."],
        [/^That puts the (Y1|Y2) back on its original software\. The download and computer setup sections below still apply if you need them\.$/, "That puts the $1 back on stock. The drop and deck setup sections below still apply if you need them."],
        [/^Open the full (.+) (.+) tutorial$/, "Open the full $1 $2 run"],
        [/^Open the full (.+) tutorial$/, "Open the full $1 run"],
        [/^Loading (.+) releases…$/, "Pulling $1 drops…"],
        [/^All public (.+) releases are shown\.$/, "All public $1 drops are on the board."],
        [/^Release information for (.+) loaded where available; some project histories may be incomplete\.$/, "Drop intel for $1 loaded where available; some project histories may be incomplete."]
    ];

    function translate(text) {
        var out = String(text == null ? "" : text);
        RULES.forEach(function (pair) {
            out = out.split(pair[0]).join(pair[1]);
        });
        REGEX_RULES.forEach(function (rule) {
            out = out.replace(rule[0], rule[1]);
        });
        return out;
    }

    var originals = new WeakMap();
    var registry = [];

    function isSkippable(node) {
        var parent = node.parentElement;
        if (!parent) return true;
        var tag = parent.tagName;
        if (/^(SCRIPT|STYLE|TEXTAREA|SELECT|OPTION|CODE|PRE|NOSCRIPT|IFRAME|TITLE)$/.test(tag)) return true;
        if (parent.closest && parent.closest("pre, code, .lumen-code, [data-i18n-skip]")) return true;
        return false;
    }

    function applyToNode(node) {
        if (!node || node.nodeType !== 3) return;
        if (isSkippable(node)) return;
        var original = originals.get(node);
        if (original == null) {
            original = node.data;
            originals.set(node, original);
        }
        var flavored = translate(original);
        if (flavored !== node.data) {
            node.data = flavored;
            if (registry.indexOf(node) === -1) registry.push(node);
        }
    }

    function applyAll(root) {
        root = root || document.body;
        if (!root) return;
        var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
        var nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(applyToNode);
        if (root === document.body) {
            if (!originals.has(document)) originals.set(document, document.title);
            document.title = translate(originals.get(document));
        }
    }

    function restoreAll() {
        registry.forEach(function (node) {
            var original = originals.get(node);
            if (original != null && node.parentNode) node.data = original;
        });
        registry = [];
        if (originals.has(document)) document.title = originals.get(document);
    }

    var syncTimer = null;
    function scheduleSync() {
        clearTimeout(syncTimer);
        syncTimer = setTimeout(function () {
            if (isActive()) applyAll(document.body);
            else restoreAll();
        }, 0);
    }

    var themeObserver = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (mutation.type === "attributes" && mutation.attributeName === "data-lumen-theme") {
                scheduleSync();
            }
        });
    });

    var contentObserver = new MutationObserver(function (mutations) {
        if (!isActive()) return;
        var pending = [];
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType === 1) pending.push(node);
                else if (node.nodeType === 3) pending.push(node);
            });
        });
        if (!pending.length) return;
        clearTimeout(syncTimer);
        syncTimer = setTimeout(function () {
            pending.forEach(function (node) {
                if (node.nodeType === 1) applyAll(node);
                else applyToNode(node);
            });
        }, 0);
    });

    function init() {
        if (document.documentElement) {
            themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-lumen-theme"] });
        }
        if (document.body) {
            contentObserver.observe(document.body, { childList: true, subtree: true });
            scheduleSync();
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

    window.INNIOASIS_I18N = {
        translate: translate,
        isActive: isActive,
        NIGHT_CITY: NIGHT_CITY
    };
})();
