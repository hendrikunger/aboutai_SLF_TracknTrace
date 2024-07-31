import json
import os
import sys
import panel as pn
import random
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


pn.extension(notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config["DATABASE"]}", echo=True)

currentMeasurement = pn.rx("")


#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)



def write_to_DB(bearing_id, aussenR, innenR):
    session = Session(engine)
    try:
        EntrytoUpdate = session.get_one(BearingData, bearing_id)
        print(F"Updating: {EntrytoUpdate}", flush=True)
        EntrytoUpdate.aussenR = aussenR
        EntrytoUpdate.innenR = innenR
        session.flush()
    except NoResultFound:
        session.rollback()
        pn.state.notifications.error(f'DMC nicht in der Datenbank {bearing_id}', duration=2000)
    else:
        session.commit()
    session.close()

def getMeasurement(event):
    currentMeasurement.rx.value =  random.randint(0, 100)



def process(event):
    if event.new == "": return
    if not event.new.isdigit():
        pn.state.notifications.error('DMC ist keine Zahl', duration=2000)
        ti_Barcode.value = ""
        return   
    running_indicator.value = running_indicator.visible = True
    getMeasurement(None)
    running_indicator.value = running_indicator.visible = False
    ti_Barcode.focus = False
    b_Save.disabled = False

async def button_save_function(event):
    running_indicator.value = running_indicator.visible = True
    write_to_DB(ti_Barcode.value, ar_group.value, ir_group.value)
    running_indicator.value = running_indicator.visible = False
    b_Save.disabled = True
    ti_Barcode.focus = True
    currentMeasurement.rx.value = ""



b_Save = pn.widgets.Button(name='Auswahl speichern',
                           button_type='primary',
                           height=80,
                           sizing_mode="stretch_width",
                           disabled=True,)
b_Save.rx.watch(button_save_function)


ar_group = pn.widgets.RadioButtonGroup(
    name='Radio Button Group',
    options=[1, 2, 3, 4, 5, 6, 7, 8, 9],
    button_type='primary',
    button_style="outline",
     height=80,
    align="center",
    width=600,
    margin=20)

ir_group  = pn.widgets.RadioButtonGroup(
    name="Innenring",
    options=[1, 2, 3, 4, 5, 6, 7, 8, 9],
    button_type='primary',
    button_style="outline",
    height=80,
    align="center",
    width=600,
    margin=20)

ti_Barcode = FocusedInput(name="Barcode", value="",)
ti_Barcode.param.watch(process, "value")

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


   

running_indicator = pn.indicators.LoadingSpinner(value=False,
                                                 height=100,
                                                 width=100,
                                                 color="secondary",
                                                 visible=False,
                                                 margin=50)


column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                   pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCardID, pn.Spacer(sizing_mode="stretch_width")),
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