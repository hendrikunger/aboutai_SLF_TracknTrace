import panel as pn
import json
import csv
from datetime import datetime
#panel serve pages/*.py --autoreload --port 80 --admin  --static-dirs assets=./assets

TITLE = "AR DMC Lasern"

pn.extension()

allIDs = []
currentSerialID = pn.rx("Empty")
currentSerialindex = None

#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])
    print(text, flush=True)

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)

with open("config.json", "r") as f:
    config = json.load(f)


with open("allIDs.csv", newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        allIDs.append(row)

with open("cur_sequence.json", "r") as f:
    sequence = json.load(f)
    currentSerialindex = sequence["current"]
    currentSerialID.rx.value = str(allIDs[currentSerialindex][0])

def getSerialID():
    global currentSerialindex 
    print(f"getSerialID Index: {currentSerialindex}", flush=True)
    currentSerialindex = currentSerialindex + 1
    return str(allIDs[currentSerialindex-1][0])


def sendtoLaser():
    print("send to Laser")


def button_function(event):
    global currentSerialindex
    print("Button clicked", flush=True)
    sendtoLaser()
    currentSerialID.rx.value = getSerialID()
    with open("cur_sequence.json", "w") as f:
        sequence["current"] = currentSerialindex
        json.dump(sequence, f)
    


text_currentSerialID = pn.rx("# {currentSerialID}").format(currentSerialID=currentSerialID)


b_Start = pn.widgets.Button(name='Seriennummer zum Laser übertragen', button_type='primary', height=80, sizing_mode="stretch_width")
b_Start.rx.watch(button_function)

md_currentSerialID = pn.pane.Markdown(text_currentSerialID)
serialCard = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_currentSerialID, pn.Spacer(sizing_mode="stretch_width")), width=250, hide_header=True)


column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCard, pn.Spacer(sizing_mode="stretch_width")),
                   b_Start)


pn.template.BootstrapTemplate(
    title=TITLE,
    sidebar=[linklist],
    main=column,
    header_background=config["ACCENT"],
    theme=config["THEME"],
    logo=config["LOGO"],
    collapsed_sidebar=config["SIDEBAR_OFF"],
    sidebar_width = 200,
).servable()