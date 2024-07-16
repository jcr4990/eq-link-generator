import requests
import tkinter as tk
from tkinter import ttk
import pyperclip
from tkinter import scrolledtext, filedialog
from urllib.parse import quote
from datetime import datetime
import configparser
import time
import os
import gzip
import shutil
import threading
import pyttsx3


# Initialize config parser
config_parser = configparser.ConfigParser(interpolation=None, delimiters=("=", ":"))
config_parser.optionxform = str


def start_thread():
    """Start a thread to load items."""
    thread = threading.Thread(target=load_items)
    thread.daemon = True
    thread.start()


def extract_gz():
    """Extract items.txt from items.txt.gz if it doesn't exist."""
    files = os.listdir()
    if "items.txt" not in files:
        with gzip.open("items.txt.gz", 'rb') as f_in:
            with open('items.txt', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)


def load_items():
    """Load item data from items.txt."""
    global db
    log("Info", "Loading item data...")
    extract_gz()
    import pandas as pd
    db = pd.read_csv('items.txt', delimiter='|', on_bad_lines='skip', low_memory=False)
    log("Info", "Item data loaded!")


def start_track_items():
    """Start a thread to track items."""
    track_thread = threading.Thread(target=track_items)
    track_thread.daemon = True
    track_thread.start()
    items_to_track_btn.config(state=tk.DISABLED)
    items_to_track_btn.config(text="Tracking...")


def track_items():
    """Track items and notify when they are being sold."""
    items = items_to_track.get("1.0", tk.END).split("\n")
    track_timestamp = datetime.now()
    processed = []
    while True:
        print("Tracking...")
        for item in items:
            if not item:
                continue
            search_text = quote(item)
            url = f'https://api.tlp-auctions.com/SalesLog?serverName=Teek&exact=true&searchTerm={search_text}'
            r = requests.get(url)
            results = r.json().get('items', [])
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
    """Text-to-speech function."""
    engine = pyttsx3.init()
    engine.setProperty('voice', engine.getProperty('voices')[0].id)
    engine.setProperty('rate', 170)
    engine.setProperty('volume', 1)
    engine.say(msg)
    engine.runAndWait()


def get_inv_prices():
    """Fetch inventory price data."""
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
    for line in lines:
        cols = line.split("\t")
        item_loc = cols[0]
        item_name = cols[1]
        bag_num = bag_num_input.get().lower()
        if bag_num == "all":
            bag_num = ""
        if f"General {bag_num}" in item_loc and "Empty" not in item_name:
            if item_name not in items_to_pc:
                items_to_pc.append(item_name)

    for i, item in enumerate(items_to_pc):
        progress_bar['maximum'] = len(items_to_pc)
        progress_bar['value'] = i
        progress_bar.update()
        search_text = quote(item)
        r = requests.get(f"https://api.tlp-auctions.com/PriceCheck?serverName=Teek&searchText={search_text}")
        results = r.json()
        try:
            avg_price = results['averagePrice']
            if avg_price:
                avg_price = avg_price.split(".")[0]
                min_price = min_price_input.get() or 0
                if int(avg_price) > int(min_price):
                    avg_price = format_price(krono_price, avg_price)
                    log("Info", f"{item} - {avg_price}")
        except KeyError:
            pass
        time.sleep(.5)
    progress_bar['value'] = progress_bar['maximum']
    log("Info", "Inventory Price Check Complete")


def select_inv_dump():
    """Select inventory dump file."""
    global inv_dump_file
    inv_dump_file = filedialog.askopenfilename(
        filetypes=[(".txt Files", "*.txt")],
        title="Select a file"
    )
    if inv_dump_file:
        file_name = os.path.basename(inv_dump_file)
        log("Info", f"Selected inventory dump file {file_name}")
        select_inv_dump_btn.config(text=file_name)


def select_logfile():
    """Select log file."""
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
    """Monitor log file for price check commands."""
    with open(log_file, "r") as f:
        f.seek(0, 2)
        while True:
            data = f.readline()
            if not data:
                continue
            data = data[27:]
            if data.startswith("You") and "'pc" in data:
                pc_item = data.split("'pc")[-1].strip().rstrip("'")
                print("PC Item: " + pc_item)
                get_prices(pc_item, tts_flag=True)


def select_ini():
    """Select ini file."""
    global ini_file
    ini_file = filedialog.askopenfilename(
        filetypes=[(".ini Files", "*.ini")],
        title="Select a file"
    )
    if ini_file:
        log("Info", f"Selected ini {ini_file}")


def write_ini(msg):
    """Write message to ini file."""
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
        file = f.read().replace("\n\n", "\n").replace(" = ", "=")
    with open(ini_file, "w") as f:
        f.write(file)
    log("Info", f"Macro saved to page {pagenum} button {btnnum} line {linenum}")


def copy(msg):
    """Copy message to clipboard."""
    pyperclip.copy(msg)
    log("Info", "Copied to Clipboard!")


def log(logtype, msg):
    """Log messages to the console."""
    console.config(state=tk.NORMAL)
    console.insert(tk.END, f"[{logtype}] {msg}\n")
    console.update_idletasks()
    console.see(tk.END)
    console.config(state=tk.DISABLED)


def format_price(krono_price, raw_price):
    """Format price based on krono price."""
    raw_price = int(raw_price.split(".")[0])
    krono_price = int(krono_price)
    kr = raw_price // krono_price
    pp = raw_price % krono_price

    if kr >= 1:
        if pp > 100:
            price = f"{kr}kr {pp}pp"
        else:
            price = f"{kr}kr"
    else:
        price = f"{pp}pp"

    return price


def format_tts_price(price):
    """Format price for TTS."""
    parts = price.split()
    formatted_parts = []
    for part in parts:
        if part.endswith("pp"):
            number = int(part[:-2])
            rounded_number = round(number, -2)
            formatted_parts.append(f"{rounded_number:,} platinum")
        elif part.endswith("kr"):
            number = int(part[:-2])
            formatted_parts.append(f"{number:,} krono")
        else:
            formatted_parts.append(part)
    return ' '.join(formatted_parts)


def get_prices(name, tts_flag=False):
    """Get prices for a given item."""
    r = requests.get("https://api.tlp-auctions.com/KronoPrice?serverName=Teek")
    krono_price = int(r.text.split(".")[0])
    search_text = quote(name)
    r = requests.get(f"https://api.tlp-auctions.com/PriceCheck?serverName=Teek&searchText={search_text}")
    results = r.json()

    try:
        log("Info", f"Price Checking: {name}")
        log("Info", f"Current Krono Price: {krono_price}")
        if results.get('auctions'):
            for result in results['auctions']:
                timestamp = datetime.fromisoformat(result['auctionDate']).strftime('%m/%d %I:%M%p')
                auctioneer = result['auctioneer']
                avg_price = format_price(krono_price, results['averagePrice'])
                price = format_price(krono_price, result['price'])
                log(f"{timestamp}", f"{auctioneer}: {price}")
            log("Info", f"Average Price {avg_price}")
            if tts_flag:
                tts_avg_price = format_tts_price(avg_price)
                tts(f"{name}, average price, {tts_avg_price}")
        else:
            log("Info", "No pricing found")
    except KeyError:
        log("Error", "Price check failed")


def submit_action():
    """Submit action to generate link."""
    msg = prefix.get()
    items = [
        {"name": item_one_name, "price": item_one_price},
        {"name": item_two_name, "price": item_two_price}
    ]

    for item in items:
        name = item['name'].get()
        price = item['price'].get()
        if name:
            for i, entry in enumerate(db['name']):
                if entry == name:
                    hash = "\x12" + db['itemlink'][i] + "\x12"
                    break

            if hash:
                msg += f" {hash}"
                if price:
                    msg += f" {price}"
                msg += ","

    msg = msg.rstrip(",")
    print(msg)

    if len(msg) > 255:
        log("Error", "Output longer than 255 character limit")
        return None

    output.config(state=tk.NORMAL)
    output.insert(0, msg)
    output.config(state=tk.DISABLED)
    tk.Button(tabs["Link Creator"], text="Copy to Clipboard", command=lambda: copy(msg)).grid(row=6, column=2, columnspan=2, pady=5)
    tk.Button(tabs["Link Creator"], text="Write ini", command=lambda: write_ini(msg)).grid(row=7, column=1, rowspan=2, pady=5)
    log("Info", "Link generated!")


def create_labeled_entry(parent, label_text, row, column, width=30, default_text=""):
    label = ttk.Label(parent, text=label_text)
    label.grid(row=row, column=column, padx=5, pady=5, sticky="e")
    entry = ttk.Entry(parent, width=width)
    entry.grid(row=row, column=column + 1, padx=5, pady=5, sticky="w")
    entry.insert(0, default_text)
    return entry


# def read_settings():
#     global log_file
#     try:
#         with open("settings.ini", "r") as f:
#             config_parser.read_file(f)
#     except FileNotFoundError:
#         with open("settings.ini", "w") as f:
#             config_parser.write(f)
#         if "Socials" not in config_parser.sections():
#             config_parser.add_section("Settings")
#         config_parser["Settings"]["LogFile"] = input("Log File Path:")
#         config_parser["Settings"]["InvDumpFile"] = input("Inventory Dump File Path:")
#         with open("settings.ini", "w") as f:
#             config_parser.write(f)

#     print(config_parser.sections())
#     log_file = config_parser["Settings"]["LogFile"]
#     if log_file:
#         log("Info", f"Selected log file {log_file}")
#         monitor_log_thread = threading.Thread(target=monitor_log)
#         monitor_log_thread.daemon = True
#         monitor_log_thread.start()


# Create the main window
root = tk.Tk()
root.title("EQ Link Generator")
root.iconbitmap('eqlink.ico')
style = ttk.Style()
root.tk.call("source", "themes/azure.tcl")
root.tk.call("set_theme", "light")
notebook = ttk.Notebook(root)

tabs = {
    "Link Creator": ttk.Frame(notebook),
    "Inventory Price Checker": ttk.Frame(notebook),
    "Item Tracker": ttk.Frame(notebook),
    "In-Game Price Check": ttk.Frame(notebook)
}

for tab_name, tab_frame in tabs.items():
    notebook.add(tab_frame, text=tab_name)
notebook.grid(row=0, column=0, padx=10, pady=10)

style.configure('TNotebook.Tab',
                padding=[10, 10],
                borderwidth=0,
                background='#f0f0f0',
                foreground='#333333',
                font=('Helvetica', 12, 'bold'),
                relief='flat')

# Menu
menubar = tk.Menu(root)
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Select .ini File", command=select_ini)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=file_menu)
root.config(menu=menubar)

# Prefix
prefix = create_labeled_entry(tabs["Link Creator"], "Prefix:", 1, 0, default_text="/1 WTS")

# Item 1
item_one_name = create_labeled_entry(tabs["Link Creator"], "Item:", 2, 0)
item_one_price = create_labeled_entry(tabs["Link Creator"], "Price:", 2, 2, width=7)
ttk.Button(tabs["Link Creator"], text="Price Check", command=lambda: get_prices(item_one_name.get())).grid(row=2, column=4, padx=10)

# Item 2
item_two_name = create_labeled_entry(tabs["Link Creator"], "Item:", 3, 0)
item_two_price = create_labeled_entry(tabs["Link Creator"], "Price:", 3, 2, width=7)
ttk.Button(tabs["Link Creator"], text="Price Check", command=lambda: get_prices(item_two_name.get())).grid(row=3, column=4, padx=10)

# Submit
submit = ttk.Button(tabs["Link Creator"], text="Submit", command=submit_action)
submit.grid(row=4, column=0, columnspan=4, pady=5)

# Separator One
separator_one = ttk.Separator(tabs["Link Creator"], orient='horizontal')
separator_one.grid(row=5, column=0, columnspan=5, sticky='ew', pady=10)

# Output
ttk.Label(tabs["Link Creator"], text="Msg:").grid(row=6, column=0)
output = ttk.Entry(tabs["Link Creator"], width=30)
output.grid(row=6, column=1, padx=5, pady=20, sticky="w")
output.config(state=tk.DISABLED)

# Page Select
page = create_labeled_entry(tabs["Link Creator"], "Page:", 7, 0, width=5, default_text="10")

# Button Select
btn = create_labeled_entry(tabs["Link Creator"], "Button:", 8, 0, width=5, default_text="1")

# Line Select
line = create_labeled_entry(tabs["Link Creator"], "Line:", 9, 0, width=5, default_text="1")

# Select Inv Dump
select_inv_dump_btn = ttk.Button(tabs["Inventory Price Checker"], text="Open Inventory File", command=select_inv_dump)
select_inv_dump_btn.grid(row=12, column=0, columnspan=2, pady=10, padx=10, sticky="w")

# Min Price Select
min_price_input = create_labeled_entry(tabs["Inventory Price Checker"], "Min Plat Price:", 13, 0, width=10, default_text="100")

# Bag #
bag_num_input = create_labeled_entry(tabs["Inventory Price Checker"], "Bag Num (1-12):", 14, 0, width=10, default_text="All")

# Get Inv Prices
inv_prices_btn = ttk.Button(tabs["Inventory Price Checker"], text="Get Prices", command=get_inv_prices)
inv_prices_btn.grid(row=15, column=0, columnspan=2, pady=10, padx=10, sticky="w")

# Items to Track CSV
ttk.Label(tabs["Item Tracker"], text="Enter item names to track\n(One item per line)").grid(row=0, column=0, pady=10)
items_to_track = tk.Text(tabs["Item Tracker"], wrap=tk.WORD, height=10, width=50)
items_to_track.grid(row=1, column=0, padx=10, pady=10)
items_to_track_btn = ttk.Button(tabs["Item Tracker"], text="Track Items", command=start_track_items)
items_to_track_btn.grid(row=2, column=0, pady=10)

# In-game PC
ttk.Label(tabs["In-Game Price Check"], text="Select a log file then type \"pc itemname\" in chat").grid(row=1, column=0, pady=10, padx=10)
select_logfile_btn = ttk.Button(tabs["In-Game Price Check"], text="Open Log File", command=select_logfile)
select_logfile_btn.grid(row=2, column=0, pady=10, padx=10)

# Console/Log
console = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, cursor='xterm')
console.grid(row=20, column=0, padx=10, pady=15, columnspan=5)
console.insert(tk.END, "Welcome to EQ Link Generator!\n")
console.config(state=tk.DISABLED, bg="#f0f0f0")


root.after(1, start_thread)
root.mainloop()
