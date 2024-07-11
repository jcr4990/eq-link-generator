import requests
import tkinter as tk
from tkinter import ttk
import pyperclip
from tkinter import scrolledtext, filedialog
import urllib.parse
from datetime import datetime, timedelta
import configparser
import time
import os
import gzip
import shutil
import pandas as pd
import threading
# from gtts import gTTS
import pyttsx3
from playsound import playsound


config_parser = configparser.ConfigParser(interpolation=None, delimiters=("=", ":"))
config_parser.optionxform = str


def start_thread():
    thread = threading.Thread(target=load_items)
    thread.daemon = True
    thread.start()


def extract_gz():
    files = os.listdir()
    if "items.txt" not in files:
        with gzip.open("items.txt.gz", 'rb') as f_in:
            with open('items.txt', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)


def load_items():
    global db
    log("Info", "Loading item data...")
    extract_gz()
    db = pd.read_csv('items.txt', delimiter='|', on_bad_lines='skip', low_memory=False)
    log("Info", "Item data loaded!")


def start_track_items():
    track_thread = threading.Thread(target=track_items)
    track_thread.daemon = True
    track_thread.start()
    items_to_track_btn.config(state=tk.DISABLED)
    items_to_track_btn.config(text="Tracking...")


def track_items():
    items = items_to_track.get("1.0", tk.END)
    itemlist = items.split("\n")
    track_timestamp = datetime.now()
    processed = []
    while True:
        print("Tracking...")
        for item in itemlist:
            if item == '':
                continue
            search_text = urllib.parse.quote(item)
            url = f'https://api.tlp-auctions.com/SalesLog?serverName=Teek&exact=true&searchTerm={search_text}'
            r = requests.get(url)
            results = r.json()['items']
            for result in results:
                result_id = result['id']
                auction_time = result['datetime']
                auction_datetime = datetime.strptime(auction_time, "%Y-%m-%dT%H:%M:%S")
                if auction_datetime > track_timestamp and result_id not in processed:
                    processed.append(result_id)
                    item_name = result['item']
                    auctioneer = result['auctioneer']
                    tts(f"{item_name} being sold by {auctioneer}")
            time.sleep(1)
        time.sleep(10)


def tts(msg):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)
    engine.setProperty('rate', 170) 
    engine.setProperty('volume', 1)
    engine.say(msg)
    engine.runAndWait()
    # tts = gTTS(text=msg, lang='en', slow=False)
    # tts.save("tts.mp3")
    # playsound("tts.mp3")


def get_inv_prices():
    if "inv_dump_file" not in globals():
        select_inv_dump()
    log("Info", "Fetching inventory price data (May take a while)")
    progress_bar = ttk.Progressbar(root, orient='horizontal', length=300, mode='determinate')
    progress_bar.grid(row=21, column=0, padx=5, pady=5, columnspan=5)
    r = requests.get("https://api.tlp-auctions.com/KronoPrice?serverName=Teek")
    krono_price = int(r.text.split(".")[0])

    with open(inv_dump_file, "r") as f:
        lines = f.readlines()

    items_to_pc = []
    for i, line in enumerate(lines):
        cols = line.split("\t")
        item_loc = cols[0]
        item_name = cols[1]
        bag_num = bag_num_input.get()
        if bag_num.lower() == "all":
            bag_num = ""
        if "General " + bag_num in item_loc and "Empty" not in item_name:
            if item_name not in items_to_pc:
                items_to_pc.append(item_name)

    for i, item in enumerate(items_to_pc):
        progress_bar['maximum'] = len(items_to_pc)
        progress_bar['value'] = i
        progress_bar.update()
        search_text = urllib.parse.quote(item)
        r = requests.get("https://api.tlp-auctions.com/PriceCheck?serverName=Teek&searchText=" + search_text)
        results = r.json()
        try:
            avg_price = results['averagePrice']
            if avg_price:
                avg_price = avg_price.split(".")[0]
                min_price = min_price_input.get()
                if min_price == '':
                    min_price = 0
                if int(avg_price) > int(min_price):
                    avg_price = format_price(krono_price, avg_price)
                    log("Info", f"{item} - {avg_price}")
        except KeyError:
            pass
        time.sleep(.5)
    progress_bar['value'] = progress_bar['maximum']
    log("Info", "Inventory Price Check Complete")


def select_inv_dump():
    global inv_dump_file
    inv_dump_file = filedialog.askopenfilename(
        filetypes=[(".txt Files", "*.txt")],
        title="Select a file"
    )
    if inv_dump_file:
        file_name = inv_dump_file.split("/")[-1]
        log("Info", f"Selected inventory dump file {file_name}")
        select_inv_dump_btn.config(text=file_name)
        # tk.Label(root, text=f"{file_name}").grid(row=12, column=2, pady=5, columnspan=3, sticky="w")


def select_logfile():
    global log_file
    log_file = filedialog.askopenfilename(
        filetypes=[(".txt Files", "*.txt")],
        title="Select a file"
    )
    if log_file:
        log("Info", f"Selected log file {log_file}")
        monitor_log_thread = threading.Thread(target=monitor_log)
        monitor_log_thread.daemon = True
        monitor_log_thread.start()


def monitor_log():
    with open(log_file, "r") as f:
        f.seek(0, 2)
        while True:
            data = f.readline()
            if data == '':
                continue
            else:
                data = data[27:]

            if data.startswith("You") and "'pc" in data:
                pc_item = data.split("'pc")[-1].strip().rstrip("'")
                print("PC Item: " + pc_item)
                get_prices(pc_item, tts_flag=True)


def select_ini():
    global ini_file
    ini_file = filedialog.askopenfilename(
        filetypes=[(".ini Files", "*.ini")],
        title="Select a file"
    )
    if ini_file:
        log("Info", f"Selected ini {ini_file}")


def write_ini(msg):
    if "ini_file" not in globals():
        select_ini()
    config_parser.read(ini_file)
    if "Socials" not in config_parser.sections():
        config_parser.add_section("Socials")
    pagenum = page.get()
    btnnum = btn.get()
    linenum = line.get()
    config_parser['Socials'][f'Page{pagenum}Button{btnnum}Name'] = msg.split("\x12")[0].strip()
    config_parser['Socials'][f'Page{pagenum}Button{btnnum}Color'] = "0"
    config_parser['Socials'][f'Page{pagenum}Button{btnnum}Line{linenum}'] = msg
    with open(ini_file, 'w') as configfile:
        config_parser.write(configfile)
    with open(ini_file, "r") as f:
        file = f.read()
        file = file.replace("\n\n", "\n")
        file = file.replace(" = ", "=")
    with open(ini_file, "w") as f:
        f.write(file)
    log("Info", f"Macro saved to page {pagenum} button {btnnum} line {linenum}")


def copy(msg):
    pyperclip.copy(msg)
    log("Info", "Copied to Clipboard!")


def log(logtype, msg):
    console.config(state=tk.NORMAL)
    console.insert(tk.END, f"[{logtype}] {msg}\n")
    console.update_idletasks()
    console.see(tk.END)
    console.config(state=tk.DISABLED)


def format_price(krono_price, raw_price):
    raw_price = int(raw_price.split(".")[0])
    krono_price = int(krono_price)
    kr = raw_price // krono_price
    pp = raw_price % krono_price

    if kr >= 1:
        if pp > 100:
            price = f"{kr}kr {pp}pp"
        elif pp <= 100:
            price = f"{kr}kr"
    else:
        price = f"{pp}pp"

    return price


def get_prices(name, tts_flag=False):
    r = requests.get("https://api.tlp-auctions.com/KronoPrice?serverName=Teek")
    krono_price = int(r.text.split(".")[0])
    search_text = urllib.parse.quote(name)
    r = requests.get("https://api.tlp-auctions.com/PriceCheck?serverName=Teek&searchText=" + search_text)
    results = r.json()

    try:
        log("Info", f"Price Checking: {name}")
        log("Info", f"Current Krono Price: {krono_price}")
        if results['auctions']:
            for result in results['auctions']:
                timestamp = datetime.fromisoformat(result['auctionDate']).strftime('%m/%d %I:%M%p')
                auctioneer = result['auctioneer']
                avg_price = format_price(krono_price, results['averagePrice'])
                price = format_price(krono_price, result['price'])
                log(f"{timestamp}", f"{auctioneer}: {price}")
            log("Info", f"Average Price {avg_price}")
            if tts_flag is True:
                tts(f"{name}, average price, {avg_price}")
        else:
            log("Info", "No pricing found")
    except KeyError:
        log("Error", "Price check failed")


def submit_action():
    msg = prefix.get()
    items = [
        {"name": item_one_name, "price": item_one_price},
        {"name": item_two_name, "price": item_two_price}
        ]

    for i, item in enumerate(items):
        name = item['name'].get()
        price = item['price'].get()
        if name != "":
            for i, entry in enumerate(db['name']):
                if entry == name:
                    hash = "\x12" + db['itemlink'][i] + "\x12"
                    break

            if hash is not None:
                msg = msg + f" {hash}"
                if price != "":
                    msg = msg + f" {price}"
                msg = msg + ","

    msg = msg.rstrip(",")
    print(msg)

    if len(msg) > 255:
        log("Error", "Output longer than 255 character limit")
        return None

    output.config(state=tk.NORMAL)
    output.insert(0, msg)
    output.config(state=tk.DISABLED)
    tk.Button(tab1, text="Copy to Clipboard", command=lambda: copy(msg)).grid(row=6, column=2, columnspan=2, pady=5)
    tk.Button(tab1, text="Write ini", command=lambda: write_ini(msg)).grid(row=7, column=1, rowspan=2, pady=5)
    log("Info", "Link generated!")


# Create the main window
root = tk.Tk()
root.title("EQ Link Generator")
style = ttk.Style()

notebook = ttk.Notebook(root)
tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)
tab3 = ttk.Frame(notebook)
tab4 = ttk.Frame(notebook)
notebook.add(tab1, text='Link Creator')
notebook.add(tab2, text='Inventory Price Checker')
notebook.add(tab3, text='Item Tracker')
notebook.add(tab4, text='In-Game Price Check')
notebook.grid(row=0, column=0)
style.configure('TNotebook.Tab',
                padding=[5, 5],
                borderwidth=3,
                background='lightgray',
                foreground='black',
                font=('Arial', 10, 'bold'),
                relief='raised',
                # width=20,
                height=10)


# Menu
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Select .ini File", command=select_ini)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)
root.config(menu=menubar)

# Prefix
tk.Label(tab1, text="Prefix:").grid(row=1, column=0, padx=5, pady=5)
prefix = tk.Entry(tab1, width=30)
prefix.grid(row=1, column=1, padx=5, pady=5, sticky="w")
prefix.insert(0, "/1 WTS")

# Item 1 Name
tk.Label(tab1, text="Item:").grid(row=2, column=0, padx=5, pady=5)
item_one_name = tk.Entry(tab1, width=30)
item_one_name.grid(row=2, column=1, padx=5, pady=5, sticky="w")
# Item 1 Price
tk.Label(tab1, text="Price:").grid(row=2, column=2, padx=5, pady=5)
item_one_price = tk.Entry(tab1, width=7)
item_one_price.grid(row=2, column=3, padx=5, pady=5, sticky="w")
# Item 1 PC
tk.Button(tab1, text="Price Check", command=lambda: get_prices(item_one_name.get())).grid(row=2, column=4, padx=10)

# Item 2 Name
tk.Label(tab1, text="Item:").grid(row=3, column=0, padx=5, pady=5)
item_two_name = tk.Entry(tab1, width=30)
item_two_name.grid(row=3, column=1, padx=5, pady=5, sticky="w")
# Item 2 Price
tk.Label(tab1, text="Price:").grid(row=3, column=2, padx=5, pady=5)
item_two_price = tk.Entry(tab1, width=7)
item_two_price.grid(row=3, column=3, padx=5, pady=5, sticky="w")
# Item 2 PC
tk.Button(tab1, text="Price Check", command=lambda: get_prices(item_two_name.get())).grid(row=3, column=4, padx=10)

# Submit
submit = tk.Button(tab1, text="Submit", command=submit_action)
submit.grid(row=4, column=0, columnspan=4, pady=5)

# Separator One
separator_one = ttk.Separator(tab1, orient='horizontal')
separator_one.grid(row=5, column=0, columnspan=5, sticky='ew', pady=10)

# Output
tk.Label(tab1, text="Msg:").grid(row=6, column=0)
output = tk.Entry(tab1, width=30)
output.grid(row=6, column=1, padx=5, pady=20, sticky="w")
output.config(state=tk.DISABLED)
output.config(disabledbackground="#d3d3d3")

# Page Select
tk.Label(tab1, text="Page:").grid(row=7, column=0, pady=5)
page = tk.Entry(tab1, width=5)
page.grid(row=7, column=1, pady=5, sticky="w")
page.insert(0, "10")

# Button Select
tk.Label(tab1, text="Button:").grid(row=8, column=0, pady=5)
btn = tk.Entry(tab1, width=5)
btn.grid(row=8, column=1, pady=5, sticky="w")
btn.insert(0, "1")

# Line Select
tk.Label(tab1, text="Line:").grid(row=9, column=0, pady=5)
line = tk.Entry(tab1, width=5)
line.grid(row=9, column=1, pady=5, sticky="w")
line.insert(0, "1")

# Select Inv Dump
select_inv_dump_btn = tk.Button(tab2, text="Open Inventory File", command=select_inv_dump)
select_inv_dump_btn.grid(row=12, column=0, columnspan=2, pady=10, padx=10, sticky="w")

# Min Price Select
tk.Label(tab2, text="Min Plat Price:").grid(row=13, column=0, pady=10)
min_price_input = tk.Entry(tab2, width=10)
min_price_input.grid(row=13, column=1, pady=10, sticky="w")
min_price_input.insert(0, "100")

# Bag #
tk.Label(tab2, text="Bag Num (1-12):").grid(row=14, column=0, pady=10)
bag_num_input = tk.Entry(tab2, width=10)
bag_num_input.grid(row=14, column=1, pady=10, sticky="w", columnspan=2)
bag_num_input.insert(0, "All")

# Get Inv Prices
inv_prices_btn = tk.Button(tab2, text="Get Prices", command=get_inv_prices)
inv_prices_btn.grid(row=15, column=0, columnspan=2, pady=10, padx=10, sticky="w")

# Items to Track CSV
tk.Label(tab3, text="Enter item names to track\n(One item per line)").grid(row=0, column=0, pady=10)
items_to_track = tk.Text(tab3, wrap=tk.WORD, height=10, width=50)
items_to_track.grid(row=1, column=0)
items_to_track_btn = tk.Button(tab3, text="Track Items", command=start_track_items)
items_to_track_btn.grid(row=2, column=0, pady=10)

# In-game PC
select_logfile_btn = tk.Button(tab4, text="Open Log File", command=select_logfile)
select_logfile_btn.grid(row=1, column=0, pady=10, padx=10)


# Console/Log
console = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, cursor='xterm')
console.grid(row=20, column=0, padx=5, pady=15, columnspan=5)
console.insert(tk.END, "Welcome to EQ Link Generator!\n")
console.config(state=tk.DISABLED)
console.config(bg="#d3d3d3")


root.after(1, start_thread)
root.mainloop()
