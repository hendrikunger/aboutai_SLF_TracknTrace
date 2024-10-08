import json
import os
import sys
import panel as pn
import random
import asyncio
from os.path import isfile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, DataError
from watchfiles import awatch, watch

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData



TITLE = "Fertig messen"


# Load config file
configPath = "config.json"
if not isfile(configPath):
    configPath = "default_config.json"
    
with open(configPath, "r") as f:
    config = json.load(f)


pn.extension(notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config["DATABASE"]}", echo=False)

currentMeasurement = pn.rx("")
   

#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)



def write_to_DB(bearing_id, measurement):
    session = Session(engine)
    try:
        EntrytoUpdate = session.get_one(BearingData, bearing_id)
        print(F"Updating: {EntrytoUpdate}", flush=True)
        EntrytoUpdate.ueberstand = measurement
        session.flush()
    except NoResultFound:
        session.rollback()
        pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=0)
    except DataError:
        session.rollback()
        pn.state.notifications.error(f'Messwert ist keine Zahl', duration=2000)
    else:
        session.commit()
    session.close()
    return


async def watch_for_file(filepath):
    for changes in watch(os.path.dirname(filepath), recursive=False):
        for change_type, path in changes:
            print(f'change_type: {change_type}, path: {path}', flush=True)
            if (change_type == 1 or change_type== 2) and path.endswith(os.path.basename(filepath)):
                await getMeasurement(filepath)
                return


async def getMeasurement():
    #watch for test.csv file and read the first line after it is created
    if os.path.exists(config["FERTIGMESSEN_CSV"]):        
        with open(config["FERTIGMESSEN_CSV"], "r") as f:
            line = f.readlines()[-1]
            print(line, flush=True)
            value = line.split(";")[13]
            value = value.replace(",", ".")
            value =  float(value)
            currentMeasurement.rx.value = value
        os.remove(config["FERTIGMESSEN_CSV"])
    else:
        pn.state.notifications.error(f'{config["FERTIGMESSEN_CSV"]} nicht gefunden', duration=2000)


async def process(event):
    input_value = str(ti_Barcode.value)
    if input_value == "": return
    if not input_value.isdigit():
        pn.state.notifications.error('DMC ist keine Zahl', duration=2000)
        ti_Barcode.value = ""
        return   
    running_indicator.value = running_indicator.visible = True
    running_indicator.name = "Warte auf Messwert csv Datei"
    await getMeasurement()
    running_indicator.value = running_indicator.visible = False
    running_indicator.name = ""
    ti_Barcode.focus = False
    b_Reload.disabled = False
    b_Save.disabled = False
    return

def button_save_function(event):
    running_indicator.value = running_indicator.visible = True
    write_to_DB(ti_Barcode.value, currentMeasurement.rx.value)
    pn.state.notifications.success(f'Erfolgreich gespeichert', duration=3000)
    running_indicator.value = running_indicator.visible = False
    b_Save.disabled = True
    b_Reload.disabled = True
    ti_Barcode.focus = True
    currentMeasurement.rx.value = ""




b_Save = pn.widgets.Button(name='Messung speichern',
                           button_type='primary',
                           height=80,
                           sizing_mode="stretch_width",
                           disabled=True,)
b_Save.rx.watch(button_save_function)


b_Reload = pn.widgets.Button(    name="Laden",
                                 button_type='primary',
                                 disabled=False,
                                 height=80,
                                 )
b_Reload.on_click(lambda event: asyncio.create_task(process(event)))


ti_Barcode = FocusedInput(name="Barcode", value="",)
ti_Barcode.param.watch(lambda event: asyncio.create_task(process(event)), "value")

text_currentSerialID = pn.rx("{currentSerialID}").format(currentSerialID=ti_Barcode.param.value)
md_currentSerialID = pn.pane.Markdown(text_currentSerialID,
                                      width=250,
                                      styles={'text-align': 'center',
                                      'font-size': '24px'})
serialCardID = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"),
                                        md_currentSerialID,
                                        pn.Spacer(sizing_mode="stretch_width")),
                                        width=250,
                                        height=80,
                                        hide_header=True)

text_currentMeasurement = pn.rx("{currentMeasurement}").format(currentMeasurement=currentMeasurement)
md_currentMeasurement = pn.pane.Markdown(text_currentMeasurement,
                                         width=250,
                                         styles={'text-align': 'center',
                                         'font-size': '24px'})
serialCardMeasurement = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_currentMeasurement, pn.Spacer(sizing_mode="stretch_width")),
                                       width=250,
                                       height=80,
                                       hide_header=True)
   

running_indicator = pn.indicators.LoadingSpinner(value=False,
                                                 height=100,
                                                 width=100,
                                                 color="secondary",
                                                 visible=False,
                                                 margin=50)


column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardID, pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktueller Messwert:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardMeasurement, pn.Row(b_Reload, pn.Spacer(sizing_mode="stretch_width"))),
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