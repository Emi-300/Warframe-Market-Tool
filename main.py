import requests
import pandas as pd
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
from tkinter import * 
from tkinter import ttk
from tkinter.ttk import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

background_color = "#3B2D39"
background_color_2 = "#34354B"
test_color = "#69d928"
test_color_2 = "#d70e0e"

lines_in_set_list = 47

def search(itemName):
    itemName = itemName.lower()
    slug = itemName.replace(" ","_")
    url = f"https://api.warframe.market/v2/orders/item/{slug}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        # Process the data (e.g., get the 90-day average price)
        # The structure will be data['payload']['statistics_live']['48hours'][...]
        return(data)
    else:
        print(f"Error: {response.status_code}")
        return(f"Error: {response.status_code}")
    

def parse(data,itemRank=0):

    orderList = data["data"]
    
    df = pd.json_normalize(orderList)

    if toggleOnline.get():
        df = df[df["user.status"] == "ingame"]

    if "rank" in df.columns:
        # filter the DataFrame by rank (don't try to index the original JSON dict)
        df = df[df["rank"] == itemRank]
        df = df[["type","platinum","rank","user.ingameName","user.status","updatedAt"]]
    else:
        df = df[["type","platinum","user.ingameName","user.status","updatedAt"]]

    df = df[df["type"] == "sell"]

    df = df.sort_values(by="platinum")

    df = df[df["platinum"] > 1]

    return df    

def getStatistics(data,rank=0):

    if "rank" in data.columns:
        data = data[data["rank"] == rank]

    lowestPrice = data["platinum"].min()
    avgPrice = round(data["platinum"].mean(),2)
    medPrice = data["platinum"].median()
    standDev = round(data["platinum"].std(),2)

    return {"lowest price":lowestPrice, "average price":avgPrice, "median price": medPrice}

# FOR UI

def grofitLookupItem(input):
    lowestSum = 0
    inputSet = input.replace(" set","")
    parts = ["neuroptics blueprint","chassis blueprint","systems blueprint","blueprint"]
    for part in parts:

        partInput = f"{inputSet} {part}"
        partData = search(partInput)
        if(type(partData) == dict):
            partPrice= getStatistics(parse(partData))
        else:
            partPrice = {'average price' : "Erorr fetching data", "lowest price" : "Error fetching data"}
            
        lowestSum += partPrice['lowest price'] if partPrice['lowest price'] != "Erorr fetching data" else 0

    data = getStatistics(parse(search(input)))

    return {"average": data["average price"], "lowest": data["lowest price"],"median": data["median price"],"parts sum": lowestSum,"set_to_parts_ratio": round(data["median price"]/lowestSum,3) if lowestSum > 0 else 0}

def lookupItem():
    input = itemEntry.get()
    # convert rank input to int, default to 0 on bad input
    rankInput = rankEntry.get()
    try:
        rank_val = int(rankInput)
    except Exception:
        rank_val = 0

    partsDisplay.config(text="")  # Clear previous parts display
    #look for the price of individual parts
    if(input.find("set") != -1):
        displayText = ""
        avgSum = 0
        lowestSum = 0
        inputSet = input.replace(" set","")
        parts = ["neuroptics blueprint","chassis blueprint","systems blueprint","blueprint"]
        for part in parts:

            partInput = f"{inputSet} {part}"
            partData = search(partInput)
            if(type(partData) == dict):
                partPrice= getStatistics(parse(partData))
            else:
                partPrice = {'average price' : "Erorr fetching data", "lowest price" : "Error fetching data"}
            

            avgSum += partPrice['average price'] if isinstance(partPrice['average price'], (int, float)) else 0
            lowestSum += partPrice['lowest price'] if partPrice['lowest price'] != "Erorr fetching data" else 0
            print(lowestSum)

            displayText += f"{part}: {partPrice['average price']} platinum, lowest {partPrice['lowest price']} platinum\n"
        
        displayText += f"Total - Average: {avgSum}, Lowest: {lowestSum}"
        partsDisplay.config(text=displayText)


    data = parse(search(input), rank_val)
    text = " | ".join([f"{key}: {value}" for key, value in getStatistics(data, rank_val).items()])
    stats.config(text=text)

    #table
    tableData = data[["platinum","user.ingameName"]]
    table.delete("1.0","end")
    table.insert("end", tableData.to_string())

    # graphs

    # keep full data for the time-series and make a separate hist dataset
    full = data.copy()

    # remove outliers for histogram (95th percentile)
    hist_data = full[full["platinum"] < full["platinum"].quantile(0.95)][["platinum"]]

    # histogram: guard empty data
    if hist_data.empty or hist_data["platinum"].dropna().empty:
        ax1.clear()
        ax1.text(0.5, 0.5, "No sell data to plot", ha="center", va="center")
    else:
        # set bins (use scalar min/max so np.arange gets scalars)
        desired_bin_width = 5
        min_val = np.floor(hist_data["platinum"].min())
        max_val = np.ceil(hist_data["platinum"].max())
        bins = np.arange(min_val, max_val + desired_bin_width, desired_bin_width)

        ax1.clear()
        ax1.hist(hist_data["platinum"], bins=bins)
        ax1.set_xlabel("Platinum")
        ax1.set_ylabel("# selling")
        fig.tight_layout()

    # time-series: price vs updatedAt


    time_df = full[["platinum", "updatedAt"]].dropna()
    if time_df.empty:
        ax2.clear()
        ax2.text(0.5, 0.5, "No time data to plot", ha="center", va="center")
    else:
        # parse timestamps and drop invalid rows
        time_df["updatedAt"] = pd.to_datetime(time_df["updatedAt"], errors='coerce')
        time_df = time_df.dropna(subset=["updatedAt", "platinum"]).sort_values("updatedAt")
        if time_df.empty:
            ax2.clear()
            ax2.text(0.5, 0.5, "No valid time data to plot", ha="center", va="center")
        else:
            # remove outliers from the time-series using IQR method
            ax2.clear()
            time_df_for_plot = time_df.copy()
            q1 = time_df_for_plot['platinum'].quantile(0.25)
            q3 = time_df_for_plot['platinum'].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            time_df_for_plot = time_df_for_plot[(time_df_for_plot['platinum'] >= lower) & (time_df_for_plot['platinum'] <= upper)]

            if time_df_for_plot.empty:
                ax2.text(0.5, 0.5, "No valid time data to plot after outlier removal", ha="center", va="center")
            else:
                # compute weekly averages (after outlier removal)
                df_week = time_df_for_plot.set_index('updatedAt').resample('W')
                weekly_avg = df_week['platinum'].mean().dropna()

                if weekly_avg.empty:
                    ax2.text(0.5, 0.5, "No weekly data to plot after outlier removal", ha="center", va="center")
                else:
                    # plot weekly average as a line with markers
                    ax2.plot(weekly_avg.index, weekly_avg.values, marker='o', linestyle='-')
                    ax2.set_xlabel("Time (monthly)")
                    ax2.set_ylabel("Average Platinum")
                    # format x-axis dates
                    import matplotlib.dates as mdates
                    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    # rotate and align date labels; use autofmt and tight_layout to avoid clipping
                    fig2.autofmt_xdate(rotation=45, ha='right')
                    fig2.tight_layout()

    # redraw the Tk canvases so the new plots appear
    graph1.draw()
    graph2.draw()
    
def grofitSearch():
    grofitWindow = tk.Toplevel(root)
    grofitWindow.title("Grofit Search")
    grofitWindow.geometry("400x300")

    #read set list from file
    df = pd.DataFrame()

    grofit_progress = ttk.Progressbar(grofitWindow, orient="horizontal", length=300, mode="determinate")
    grofit_progress.pack(pady=10)
    grofit_progress["maximum"] = lines_in_set_list

    grofitWindow.update_idletasks()       # ensure widgets are created
    grofitWindow.wait_visibility()       # block until shown

    with open("prime_set_list.txt","r") as f:
        for line in f:
            setName = f"{line.strip()} prime set"
            result = grofitLookupItem(setName)
            result.update({"name": setName})
            
            df = pd.concat([df,pd.DataFrame([result])],ignore_index=True)
            print(f"{setName} - Average: {result['average']} platinum, Median {result['median']} platinum, Lowest: {result['lowest']} platinum, Parts Sum Lowest: {result['parts sum']} platinum")
            grofit_progress.step(1)
            grofitWindow.update_idletasks()
    
    df = df.sort_values(by="set_to_parts_ratio", ascending=False)


    grofitText = tk.Text(grofitWindow, bg=background_color,fg="white",width=50,wrap=tk.NONE)
    grofitText.pack(fill=BOTH, expand=True)

    grofitText.insert("end", df.to_string())






root = tk.Tk()
root.title("Market manipulator 3000") # Set the window title
root.geometry("1000x700") # Set the initial window size (width x height)
root.configure(bg=background_color) 

#search bar

toggleOnline = tk.BooleanVar()

searchBar = tk.Frame(root, bg=background_color)
searchBar.pack(side=tk.TOP,fill = BOTH, expand = False)

itemEntry = tk.Entry(searchBar, width=30,fg="white",bg=background_color)
itemEntry.pack(padx=5, pady=20,side=tk.LEFT)

rankText = tk.Label(searchBar, text="Rank:", bg=background_color,fg="white")
rankText.pack(padx=5, pady=20,side=tk.LEFT)

rankEntry = tk.Entry(searchBar, width=5,fg="white",bg=background_color)
rankEntry.pack(padx=5, pady=20,side=tk.LEFT)

button = tk.Button(searchBar, text="Search", command=lookupItem)
button.pack(padx=5, pady=20,side=tk.LEFT)

onlineButton = ttk.Checkbutton(searchBar, text="Online", variable = toggleOnline, style='My.TCheckbutton')
onlineButton.pack(padx=5, pady=20,side=tk.LEFT)

style = ttk.Style(searchBar)
style.theme_use('clam')
# configure custom checkbutton style (don't pass unknown kwargs to configure)
style.configure('My.TCheckbutton', background=background_color, foreground='white')
style.map('My.TCheckbutton',
          background=[('selected', '#3cb371'), ('active', '#ff8c00')],
          foreground=[('selected', 'black')])

#overall stats
infoFrame= tk.Frame(root, bg=background_color)
infoFrame.pack(side=tk.BOTTOM,fill = BOTH, expand = True)

statFrame = tk.Frame(infoFrame, bg=background_color)
statFrame.pack(side=tk.TOP,fill = BOTH, expand = False)

stats = tk.Label(statFrame, bg=background_color,fg= "white")
stats.pack(side=tk.LEFT, pady=5)

#prime sets
partsFrame = tk.Frame(infoFrame, bg=background_color)
partsFrame.pack(side=tk.RIGHT,fill = BOTH, expand = False)

partsDisplay = tk.Label(statFrame, text="", bg=background_color,fg="white")
partsDisplay.pack(side=tk.RIGHT, pady=5)

#graphs

graphFrame = tk.Frame(infoFrame, bg=background_color)
graphFrame.pack(side=tk.LEFT,fill = BOTH, expand = False, pady=5)


params = {"ytick.color" : "w",
          "xtick.color" : "w",
          "axes.labelcolor" : "w",
          "axes.edgecolor" : "w"}
plt.rcParams.update(params)


fig = Figure(figsize=(6,3), dpi=100)
fig.patch.set_facecolor(background_color)

ax1 = fig.add_subplot(111)
ax1.set_facecolor(background_color)


fig2 = Figure(figsize=(6,3), dpi=100)
fig2.patch.set_facecolor(background_color)

ax2 = fig2.add_subplot(111)
ax2.set_facecolor(background_color)


graph1 = FigureCanvasTkAgg(fig, master=graphFrame)
graph1_widget = graph1.get_tk_widget()
graph1_widget.grid(row=0, column=0, sticky="nsew",padx=2,pady=2)

graph2 = FigureCanvasTkAgg(fig2, master=graphFrame)
graph2_widget = graph2.get_tk_widget()
graph2_widget.grid(row=1, column=0, sticky="nsew",padx=2,pady=2)

# data display

tableFrame = tk.Frame(infoFrame, bg=background_color)
tableFrame.pack(side=tk.RIGHT,fill = BOTH, expand = True, pady=5)

table = tk.Text(tableFrame, bg=background_color,fg="white",width=10,wrap=tk.NONE)
table.grid(row=0, column=0, sticky="nsew",padx=2,pady=2)

tableScrollBar = tk.Scrollbar(tableFrame, orient=VERTICAL,command=table.yview,bg=background_color)
tableScrollBar.grid(row=0,column=1,sticky="nsew")

tableFrame.columnconfigure(0,weight=1)
tableFrame.rowconfigure(0,weight=1)
tableFrame.rowconfigure(1,weight=1)

table.config(yscrollcommand=tableScrollBar.set)

#grofit set calculator

grofitButton = tk.Button(searchBar, text="Run Grofit Search", command=grofitSearch)
grofitButton.pack(padx=5, pady=20,side=tk.RIGHT)





    

root.mainloop()





pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
#pd.set_option('display.width', None)    






