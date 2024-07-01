# eq-link-generator
![Before and After](https://i.imgur.com/2GuGbPC.gif) ![Before and After](https://i.imgur.com/kK9SvAQ.gif)
## About / Usage
EQ Link Generator is a tool that allows you to inject clickable item links into your in-game macros whether you possess the item or not. You can set a prefix (WTB/WTS or other) and up to 2 items per line of a macro along with pricing, then hit submit and it will generate the necessary hex string that needs to be in your Charname_server_CLASS.ini file in your EQ directory. This file holds all your in-game macro information. You may either hit the "Copy to Clipboard" and paste it in yourself, or hit "Write to ini" and select your chosen ini file as well as which page and button number you want to use and it will paste it in for you.

Additionally, you can price check each of the two item fields after typing in the item name to get an idea of where to set your price. You may also set a minimum price threshold and select an inventory dump file (created by typing "/outputfile inventory" in game) then hit 'Get Prices' and it will price check all items in your top level inventory and all bags to check for items worth above your minimum threshold.

Another feature is the ability to do a full inventory price checking. You can do this by taking an inventory dump by typing '/outputfile inventory' in game, then selecting that file in EQ Link Generator, then optionally setting a minimum plat price and a bag number (or leave it on 'All' default for all bags) and hit 'Get Prices' to price check your entire inventory for items of value.

NOTE: You must close the EQ client when using "write ini" or modfying your ini file manually then restart the game for changes to take effect. Always back up your original Charname_server_CLASS.ini file before using this app just in case.
## Installation (.py)
Install Python if not already installed. Clone this repo (or download zip and extract) then open a command prompt and cd into the eq-link-generator folder then type:
```
pip install -r requirements.txt
```
Wait for that to finish then to run the app type:
```
python eqlink.py
```

## Installation (.exe)
Navigate to "Releases" on the right sidebar (https://github.com/jcr4990/eq-link-generator/releases) and download the latest eqlink.zip then extract to location of your choosing and click eqlink.exe
> [!WARNING]
> Windows Defender and other antivirus software will likely label this as a virus so you will have to allow it. It's a false positive due to the use of pyinstaller to convert this python script to an exe. If this makes you uncomfortable you can use the .py installation instructions above and run it as a regular python script with no virus warnings.

## External Resources
Pricing data provided by https://araduneauctions.net/ 

Item data provided by https://items.sodeq.org/

Thanks to these developers for making this project possible!