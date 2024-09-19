import panel as pn
import json
import csv
import asyncio
import os
import sys
from os.path import isfile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)


from db.models import BearingData

#panel serve pages/*.py --autoreload --port 80 --admin  --static-dirs assets=./assets



TITLE = "AR DMC Lasern"

# Load config file
configPath = "config.json"
if not isfile(configPath):
    configPath = "default_config.json"
    print("loading default config", flush=True)
    
with open(configPath, "r") as f:
    config = json.load(f)


pn.extension(notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config["DATABASE"]}", echo=False)

allIDs = []
currentSerialID = pn.rx("Empty")
currentSerialindex = None

#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)



with open("allIDs.csv", newline='') as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        if row == []: continue
        allIDs.append(row)

def checkSerialID(index: int) -> str:
    if index >= len(allIDs):
        return "Alle IDs verarbeitet, bitte CSV aktualisieren und Seite neu laden"
    else:
        return str(allIDs[index - 1][0])


with open("cur_sequence.json", "r") as f:
    sequence = json.load(f)
    currentSerialindex = sequence["current"]
    currentSerialID.rx.value = checkSerialID(currentSerialindex)


def getSerialID():
    global currentSerialindex 

    if currentSerialindex >= len(allIDs):
        return "Alle IDs verarbeitet, bitte CSV aktualisieren und Seite neu laden"
    else:
        currentSerialindex = currentSerialindex + 1
        return str(allIDs[currentSerialindex-1][0])



async def laser_tcp_ip_communication(id: str):
    reader, writer = await asyncio.open_connection('127.0.0.1', 3000)
    print(f"send to Laser: {id}", flush=True)
    message = 'Hello, World!'
    print(f'Sending: {message} - for ID: {id}')
    writer.write(message.encode())
    await writer.drain()
    line = await reader.readline()
    data = line.decode('utf8').rstrip()
    print(f'Received: {data.decode()}')

    writer.close()
    await writer.wait_closed()



async def button_function(event):
    global currentSerialindex
    #disable button
    b_Start.disabled = True
    running_indicator.value = running_indicator.visible = True
    #await laser_tcp_ip_communication(currentSerialID.rx.value)
    running_indicator.value = running_indicator.visible = False
    b_Start.disabled = False
    #Save the Serial ID which has been lasered
    #Get next Serial ID
    write_to_DB(currentSerialID.rx.value)
    currentSerialID.rx.value = getSerialID()
    with open("cur_sequence.json", "w") as f:
        sequence["current"] = currentSerialindex
        json.dump(sequence, f)


def write_to_DB(bearing_id):
    session = Session(engine)
    try:
        newEntry = BearingData(id=bearing_id)
        session.add(newEntry)
        session.flush()
    except IntegrityError:
        session.rollback()
        pn.state.notifications.error(f'DMC schon in der Datenbank:', duration=0)
    else:
        session.commit()
    session.close()
    return
  


text_currentSerialID = pn.rx("{currentSerialID}").format(currentSerialID=currentSerialID)


b_Start = pn.widgets.Button(name='Seriennummer zum Laser übertragen', button_type='primary', height=80, sizing_mode="stretch_width")
b_Start.rx.watch(button_function)

md_currentSerialID = pn.pane.Markdown(text_currentSerialID, width=250, styles={'text-align': 'center', 'font-size': '24px'})
serialCard = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_currentSerialID, pn.Spacer(sizing_mode="stretch_width")), width=250, hide_header=True)

running_indicator = pn.indicators.LoadingSpinner(
    value=False, height=100, width=100, color="secondary", visible=False, margin=50)


column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCard, pn.Spacer(sizing_mode="stretch_width")),
                   b_Start,
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), running_indicator, pn.Spacer(sizing_mode="stretch_width")),)


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


