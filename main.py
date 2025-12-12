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

lines_in_warframe_list = 47
numGalvanizedItems = 12

#TODO click on username to generate warframe chat message for item
#TODO add the guns to prime set list

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

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

    if type(data) == str:
        return data
    
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


    df = df.sort_values(by="platinum")

    #remove lowest price & 1 plat prices (most often not real listings)

    df = df.iloc[1:]
    df = df[df["platinum"] > 1]

    return df    

def getStatistics(data,rank=0):

    if type(data) == str:
        return data
    
    if "rank" in data.columns:
        data = data[data["rank"] == rank]

    data = data[data["type"] == "sell"]

    lowestPrice = data["platinum"].min()
    avgPrice = round(data["platinum"].mean(),2)
    medPrice = data["platinum"].median()
    standDev = round(data["platinum"].std(),2)

    return {"lowest":lowestPrice, "average":avgPrice, "median": medPrice}

def getTimeStatistics(data,rank=0):

    if type(data) == str:
        return data
    
    if "rank" in data.columns:
        data = data[data["rank"] == rank]

    # Ensure updatedAt is a valid datetime and drop invalid rows
    data["updatedAt"] = pd.to_datetime(data["updatedAt"], errors='coerce')
    data = data.dropna(subset=["updatedAt"])
    data["updatedAt"] = data["updatedAt"].dt.tz_localize(None)
    one_week_ago = pd.Timestamp.now().normalize() - pd.Timedelta(days=7)
    one_month_ago = pd.Timestamp.now().normalize() - pd.Timedelta(days=30)

    recent_data = data[data["updatedAt"] >= one_week_ago]
    recent_buy_orders = recent_data[recent_data["type"] == "buy"].shape[0]
    recent_sell_orders = recent_data[recent_data["type"] == "sell"].shape[0]

    less_recent_data = data[data["updatedAt"] >= one_month_ago]
    less_recent_buy_orders = less_recent_data[less_recent_data["type"] == "buy"].shape[0]
    less_recent_sell_orders = less_recent_data[less_recent_data["type"] == "sell"].shape[0]


    return {"buy orders (7d)": recent_buy_orders, "sell orders (7d)": recent_sell_orders, 
            "buy orders (30d)": less_recent_buy_orders, "sell orders (30d)": less_recent_sell_orders}
    
# FOR UI

def grofitLookupItem(input,parts):
    lowestSum = 0
    inputSet = input.replace(" set","")
    
    for part in parts:

        partInput = f"{inputSet} {part}"
        partData = search(partInput)

        if(type(partData) == dict):
            partData = parse(partData)
            partData = partData[partData["type"] == "sell"]
            partPrice= getStatistics(partData)
        else:
            partPrice = {'average' : "Erorr fetching data", "lowest" : "Error fetching data"}
            
        lowestSum += partPrice['lowest'] if partPrice['lowest'] != "Erorr fetching data" else 0

    data = getStatistics(parse(search(input)))

    setToPartsRatioMedian = round(data["median"]/lowestSum,3) if lowestSum > 0 else 0
    setToPartsRatioLowest = round(data["lowest"]/lowestSum,3) if lowestSum > 0 else 0

    return {"average": data["average"], "lowest": data["lowest"],"median": data["median"],"parts sum": lowestSum,"STP (median)": setToPartsRatioMedian, "STP (lowest)": setToPartsRatioLowest}

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
                partPrice = {'average' : "Erorr fetching data", "lowest" : "Error fetching data"}
            

            avgSum += partPrice['average'] if isinstance(partPrice['average'], (int, float)) else 0
            lowestSum += partPrice['lowest'] if partPrice['lowest'] != "Erorr fetching data" else 0

            displayText += f"{part}: {partPrice['average']} platinum, lowest {partPrice['lowest']} platinum\n"
        
        displayText += f"Total - Average: {avgSum}, Lowest: {lowestSum}"
        partsDisplay.config(text=displayText)
    
    #Stats
    
    data = parse(search(input), rank_val)

    if type(data) == str:
        stats.config(text=data)
    else:
        text = " | ".join([f"{key}: {value}" for key, value in getStatistics(data, rank_val).items()])
        text += "\n"
        text += " | ".join([f"{key}: {value}" for key, value in getTimeStatistics(data, rank_val).items()])
        stats.config(text=text)


    #table
    table.delete("1.0","end")

    if type(data) == str:
        table.insert("end", data)
    else:
        data = data[data["type"] == "sell"]
        tableData = data[["platinum","user.ingameName"]]
        table.insert("end", tableData.to_string())


    # graphs
    if type(data) == str:
        return
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

def baseLookupItem(itemName, rank_val=0):
    data = parse(search(itemName), rank_val)
    return getStatistics(data, rank_val)
  
def grofitWarframeSearch():

    parts = ["neuroptics blueprint","chassis blueprint","systems blueprint","blueprint"]
    grofitWindow = tk.Toplevel(root)
    grofitWindow.title("Grofit Warframe Search")
    grofitWindow.geometry("350x50")

    #read set list from file
    df = pd.DataFrame()

    grofit_progress = ttk.Progressbar(grofitWindow, orient="horizontal", length=300, mode="determinate")
    grofit_progress.pack(pady=10)
    grofit_progress["maximum"] = lines_in_warframe_list

    grofitWindow.update_idletasks()       # ensure widgets are created
    grofitWindow.wait_visibility()       # block until shown

    with open("prime_set_list.txt","r") as f:
        for line in f:
            setName = f"{line.strip()} prime set"
            result = grofitLookupItem(setName,parts)
            result.update({"name": setName})

            df = pd.concat([df,pd.DataFrame([result])],ignore_index=True)
            print(f"{setName} - Average: {result['average']} platinum, Median {result['median']} platinum, Lowest: {result['lowest']} platinum, Parts Sum Lowest: {result['parts sum']} platinum")
            grofit_progress.step(1)
            grofitWindow.update_idletasks()

    def changeRatioMode(data,gText,gButton):
        print("changing mode")
        gText.delete("1.0","end")
        if( toggleGrofitMode.get()):
            toggleGrofitMode.set(False)
            gButton.config(text="lowest")
            data = data.sort_values(by="STP (lowest)", ascending=False)
        else:
            toggleGrofitMode.set(True)
            gButton.config(text="Median")
            data = data.sort_values(by="STP (median)", ascending=False)
        gText.insert("end", data.to_string())

    grofitWindow.geometry("900x800")

    grofitText = tk.Text(grofitWindow, bg=background_color,fg="white",width=50,wrap=tk.NONE)
    grofitText.pack(fill=BOTH, expand=True)

    grofitModeButton2 = tk.Button(grofitWindow, text="this will work now")
    grofitModeButton2.pack(padx=5, pady=20,side=tk.TOP)
    grofitModeButton2.config(command=lambda: changeRatioMode(df,grofitText,grofitModeButton2))

    changeRatioMode(df,grofitText,grofitModeButton2)

def grofitGalvanizedSearch():
    grofitWindow = tk.Toplevel(root)
    grofitWindow.title("Grofit Galvanized Search")
    grofitWindow.geometry("350x50")

    #read set list from file
    df = pd.DataFrame()

    grofit_progress = ttk.Progressbar(grofitWindow, orient="horizontal", length=300, mode="determinate")
    grofit_progress.pack(pady=10)
    grofit_progress["maximum"] = numGalvanizedItems

    grofitWindow.update_idletasks()       # ensure widgets are created
    grofitWindow.wait_visibility()       # block until shown

    with open("galvanized_item_list.txt","r") as f:
        for line in f:
            modName = f"galvanized {line.strip()}"
            result = baseLookupItem(modName)
            result.update({"name": modName})

            df = pd.concat([df,pd.DataFrame([result])],ignore_index=True)
            print(f"{modName} - Average: {result['average']} platinum, Median {result['median']} platinum, Lowest: {result['lowest']} platinum")
            grofit_progress.step(1)
            grofitWindow.update_idletasks()

    def changeRatioMode(data,gText,gButton):
        print("changing mode")
        gText.delete("1.0","end")
        if( toggleGrofitMode.get()):
            toggleGrofitMode.set(False)
            gButton.config(text="lowest")
            data = data.sort_values(by="lowest")
        else:
            toggleGrofitMode.set(True)
            gButton.config(text="Median")
            data = data.sort_values(by="median")
        gText.insert("end", data.to_string())

    grofitWindow.geometry("450x500")

    grofitText = tk.Text(grofitWindow, bg=background_color,fg="white",width=50,wrap=tk.NONE)
    grofitText.pack(fill=BOTH, expand=True)

    grofitModeButton2 = tk.Button(grofitWindow, text="this will work now")
    grofitModeButton2.pack(padx=5, pady=20,side=tk.TOP)
    grofitModeButton2.config(command=lambda: changeRatioMode(df,grofitText,grofitModeButton2))

    changeRatioMode(df,grofitText,grofitModeButton2)
        



    

root = tk.Tk()
root.title("Market manipulator 3000") # Set the window title
root.geometry("1000x700") # Set the initial window size (width x height)
root.configure(bg=background_color) 

#search bar

toggleOnline = tk.BooleanVar()
toggleGrofitMode = tk.BooleanVar()

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

grofitButton = tk.Button(searchBar, text="Run Grofit Search", command=grofitWarframeSearch)
grofitButton.pack(padx=5, pady=20,side=tk.RIGHT)

galvaniedButton = tk.Button(searchBar, text="Run Galvanized Search",command=grofitGalvanizedSearch)
galvaniedButton.pack(padx=5, pady=20,side=tk.RIGHT)







    

root.mainloop()





pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
#pd.set_option('display.width', None)    






