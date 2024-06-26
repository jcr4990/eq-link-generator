import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk
import sqlite3
import pyperclip
from tkinter import scrolledtext
import urllib.parse
from datetime import datetime


conn = sqlite3.connect("items.db")


def copy(msg):
    pyperclip.copy(msg)
    log("Info", "Copied to Clipboard!")


def log(logtype, msg):
    console.config(state=tk.NORMAL)
    console.insert(tk.END, f"[{logtype}] {msg}\n")
    console.update_idletasks()
    console.see(tk.END)
    console.config(state=tk.DISABLED)


def INSERT(id, name, hash):
    fname = name.lower().strip()
    cur = conn.cursor()
    cur.execute('INSERT INTO items (id, name, hash) VALUES (?, ?, ?)', (id, fname, hash))
    conn.commit()
    print(f"{name} added to database")
    log("Info", f"{name} added to items.db")


def SELECT(name):
    name = name.lower().strip()
    cur = conn.cursor()
    cur.execute('SELECT * FROM items WHERE name=?', (name,))
    result = cur.fetchall()
    return result


def DELETE(name):
    name = name.lower().strip()
    cur = conn.cursor()
    cur.execute('DELETE FROM items WHERE name=?', (name,))
    conn.commit()
    print(f"{name} deleted from database")


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


def get_prices(name):
    r = requests.get("https://api.tlp-auctions.com/KronoPrice?serverName=Teek")
    krono_price = int(r.text.split(".")[0])
    search_text = urllib.parse.quote(name)
    r = requests.get("https://api.tlp-auctions.com/PriceCheck?serverName=Teek&searchText=" + search_text)
    results = r.json()

    try:
        log("Info", f"Price Checking: {name}")
        log("Info", f"Current Krono Price: {krono_price}")
        for result in results['auctions']:
            timestamp = datetime.fromisoformat(result['auctionDate']).strftime('%m/%d %I:%M%p')
            auctioneer = result['auctioneer']
            avg_price = format_price(krono_price, results['averagePrice'])
            price = format_price(krono_price, result['price'])
            log(f"{timestamp}", f"{auctioneer}: {price}")
        log("Info", f"Average Price {avg_price}")
    except KeyError:
        log("Error", "Price check failed")


def get_link_hash(name):
    log("Info", f"Fetching link for {name}")
    if name.isdigit() == False:
        r = requests.get("https://items.sodeq.org/itemsearch.php?name=" + name.replace(" ", "+"))
        soup = BeautifulSoup(r.content, features="html.parser")
        results = soup.findAll("a", string=str(name))

        if len(results) == 0:
            itemid = r.url.replace("http://items.sodeq.org/item.php?id=", "")
        elif len(results) == 1:
            itemid = results[0]['href'].replace("item.php?id=", "")
    elif name.isdigit():
        itemid = name

    # Fix searching by itemid to show proper name when inserting to items.db

    # try:
    #     int(itemid)
    # except ValueError:
    #     return None

    r = requests.get("https://items.sodeq.org/itemh.php?id=" + itemid)
    oldhash = r.text
    zeros = "0" * 35
    hash = oldhash[:7] + zeros + oldhash[7:]
    INSERT(int(itemid), name, hash)
    return hash


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
            entry = SELECT(name)
            if entry == []:
                hash = get_link_hash(name)
                if hash is None:
                    log("Error", "Link could not be generated")
                    return None
            else:
                hash = entry[0][2]
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
    tk.Button(root, text="Copy to Clipboard", command=lambda: copy(msg)).grid(row=3, column=2, columnspan=2, pady=5)
    log("Info", "Links generated!")


# Create the main window
root = tk.Tk()
root.title("EQ Link Generator")

# WTS/WTB Checkboxes
tk.Label(root, text="Prefix:").grid(row=0, column=0, padx=5, pady=5)
prefix = tk.Entry(root, width=30)
prefix.grid(row=0, column=1, padx=5, pady=5)
prefix.insert(0, "WTS")

# Item 1 Name
tk.Label(root, text="Item:").grid(row=1, column=0, padx=5, pady=5)
item_one_name = tk.Entry(root, width=30)
item_one_name.grid(row=1, column=1, padx=5, pady=5)
# Item 1 Price
tk.Label(root, text="Price:").grid(row=1, column=2, padx=5, pady=5)
item_one_price = tk.Entry(root, width=7)
item_one_price.grid(row=1, column=3, padx=5, pady=5)
# Item 1 PC
tk.Button(root, text="Price Check", command=lambda: get_prices(item_one_name.get())).grid(row=1, column=4, padx=10)

# Item 2 Name
tk.Label(root, text="Item:").grid(row=2, column=0, padx=5, pady=5)
item_two_name = tk.Entry(root, width=30)
item_two_name.grid(row=2, column=1, padx=5, pady=5)
# Item 2 Price
tk.Label(root, text="Price:").grid(row=2, column=2, padx=5, pady=5)
item_two_price = tk.Entry(root, width=7)
item_two_price.grid(row=2, column=3, padx=5, pady=5)
# Item 2 PC
tk.Button(root, text="Price Check", command=lambda: get_prices(item_two_name.get())).grid(row=2, column=4, padx=10)

# Output
tk.Label(root, text="Output:").grid(row=3, column=0)
output = tk.Entry(root, width=30)
output.grid(row=3, column=1, padx=5, pady=20)
output.config(state=tk.DISABLED)
output.config(disabledbackground="#d3d3d3")

# Console/Log
console = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15, cursor='xterm')
console.grid(row=4, column=0, padx=5, pady=5, columnspan=5)
console.insert(tk.END, "Welcome to EQ Link Generator!\n")
console.config(state=tk.DISABLED)
console.config(bg="#d3d3d3")

# Submit
submit = tk.Button(root, text="Submit", command=submit_action)
submit.grid(row=7, column=0, columnspan=4, pady=5)

root.mainloop()
