import json
import os
import sys
import panel as pn
import pandas as pd
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound


main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData

TITLE = "Ringe verpaaren"

with open("config.json", "r") as f:
    config = json.load(f)


pn.extension('tabulator', notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config['DATABASE']}", echo=True)

if "currentSerialIDs" not in pn.state.cache:
    pn.state.cache["currentSerialIDs"] =  pn.rx([""])

currentSerialIDs = pn.state.cache["currentSerialIDs"]

#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)



async def write_to_DB(bearing_ids, aussenR, innenR):
    session = Session(engine)
    for bearing_id in bearing_ids:
        try:
            EntrytoUpdate = session.get_one(BearingData, bearing_id)
            print(F"Updating: {EntrytoUpdate}", flush=True)
            EntrytoUpdate.aussenR = aussenR
            EntrytoUpdate.innenR = innenR
            session.flush()
        except NoResultFound:
            session.rollback()
            pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=0)
        else:
            session.commit()
    session.close()
    return


def update_currentSerialIDs(event):
    currentSerialIDs.rx.value = [event.new]

def onCurrentSerialIDsChange(newIDs):
    print(f"New IDs: {newIDs}", flush=True)
    #if len(newIDs) == 0: return
    for dmc in newIDs:
        print(f"DMC: {dmc}", flush=True)
        if not dmc.isdigit():
            pn.state.notifications.error(f'DMC {dmc} ist keine Zahl', duration=2000)
            print(f"DMC {dmc} is not a number", flush=True)
            return

    df = pd.DataFrame({"SerialID": newIDs})
    tabulator_widget.value = df
    ti_Barcode.focus = False
    b_Save.disabled = False

async def button_save_function(event):
    running_indicator.value = True
    running_indicator.visible = True
    await write_to_DB(currentSerialIDs.rx.value, ar_group.value, ir_group.value)
    running_indicator.value = False
    running_indicator.visible = False
    b_Save.disabled = True
    ti_Barcode.focus = True


# Define an asynchronous function to handle TCP/IP communication
async def tcp_ip_client():
    currentSerialIDs = pn.state.cache["currentSerialIDs"]
    while True:
        #callback =  pn.state.add_periodic_callback(lambda: setattr(currentSerialIDs.rx, 'value', data), period=200)

        reader, writer = await asyncio.open_connection('localhost', 3000)
        while True:
                line = await reader.readline()
                if not line:
                    break
                data = line.decode('utf8').rstrip()
                print(f'Received: {data}', flush=True)
                #data = data.replace(",", "\n")
                data = data.split(",")
                data = [d.split(":")[1] for d in data]
                data = [d for d in data if d.isdigit()]
                callback =  pn.state.add_periodic_callback(lambda: setattr(currentSerialIDs.rx, 'value', data), period=200, count=1)
            
                await asyncio.sleep(0.1)

        if writer:
            writer.close()
            await writer.wait_closed()
        if callback:
            await callback.stop()
        # Wait before attempting to reconnect
        print("Reconnecting in 10 seconds...", flush=True)
        await asyncio.sleep(10)

# Function to start the asyncio event loop
async def run_asyncio():
    await tcp_ip_client()


    

b_Save = pn.widgets.Button(name='Auswahl speichern',
                           button_type='primary',
                           height=80,
                           sizing_mode="stretch_width",
                           disabled=True,)
b_Save.rx.watch(button_save_function)


ar_group = pn.widgets.RadioButtonGroup(
    name='Radio Button Group',
    options=[-1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -15, -16, -17, -18, -19, -20, -21, -22, -23, -25, -27, -29, -33, -38],
    button_type='primary',
    button_style="outline",
     height=80,
    align="center",
    width=1200,
    margin=20)

ir_group  = pn.widgets.RadioButtonGroup(
    name="Innenring",
    options=[-1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -15, -16, -17, -18, -19, -20, -21, -22, -23, -25, -27, -29, -33, -38],
    button_type='primary',
    button_style="outline",
    height=80,
    align="center",
    width=1200,
    margin=20)



ti_Barcode = FocusedInput(name="Barcode", value="",)
ti_Barcode.param.watch(update_currentSerialIDs, "value")


currentSerialIDs.rx.watch(onCurrentSerialIDsChange, "value")


# md_currentSerialIDs = pn.pane.Markdown(currentSerialIDs,
#                                       width=250,
#                                       styles={'text-align': 'center',
#                                       'font-size': '24px'})

df = pd.DataFrame({"SerialID": ["34534534","33345"]})
tabulator_options = {
    "headerVisible": False
}

custom_css = """
.tabulator-cell, .tabulator-header {
    font-size: 20px; /* Change this value to your desired text size */
}
"""

pn.config.raw_css.append(custom_css)
tabulator_widget = pn.widgets.Tabulator(df, width=400, show_index=False, theme="site", widths={"SerialID": 400},configuration=tabulator_options)

# serialCardID = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"),
#                                         md_currentSerialIDs,
#                                         pn.Spacer(sizing_mode="stretch_width")),
#                                         width=250,
#                                         height=80,
#                                         hide_header=True)



   

running_indicator = pn.indicators.LoadingSpinner(value=False,
                                                 height=100,
                                                 width=100,
                                                 color="secondary",
                                                 visible=False,
                                                 margin=50)



column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), tabulator_widget, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Außenring Gruppe:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),ar_group, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Innenring Gruppe:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),ir_group, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Spacer(sizing_mode="stretch_width", height=100),
                   b_Save,
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), running_indicator, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Spacer(sizing_mode="stretch_width", height=100),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), ti_Barcode, pn.Spacer(sizing_mode="stretch_width")),
                   )

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


#Ensure the asyncio event loop runs in the background
if not hasattr(pn.state, 'asyncio_task'):
    loop = asyncio.get_event_loop()
    pn.state.asyncio_task = loop.create_task(run_asyncio())
    print("Asyncio task started.", flush=True)

