import json
import os
import sys
import panel as pn
from io import BytesIO
import asyncio
from pathlib import Path
import re
import subprocess
from os.path import isfile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound, DataError
from smb import smb_structs
from smb.SMBConnection import SMBConnection

class SMBManager:
    def __init__(self):
        self.conn = None

    def connect(self):
        if self.conn is None:
            self.conn = create_connection()
        return self.conn

    def get(self):
        try:
            self.conn.echo(b"ping")
        except Exception:
            self.conn = create_connection()
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

smb_manager = SMBManager()
pn.state.cache["smb"] = smb_manager


def delete_remote_file_smbclient(server, share, username, password, remote_path):
    remote_path = remote_path.lstrip("/")

    cmd = [
        "smbclient",
        f"//{server}/{share}",
        "-U", f"{username}%{password}",
        "--option=client min protocol=NT1",
        "-c", f'del "{remote_path}"'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"smbclient delete failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)

from components import FocusedInput
from db.models import BearingData

# Force SMB1 for this legacy server
smb_structs.SUPPORT_SMB2 = False

TITLE = "Fertig messen"

pattern = re.compile(r'_(\d+)\.csv$', re.IGNORECASE)
pn.state.cache["currentPath"]  = None

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

def create_connection():
    conn = SMBConnection(
        config["SMBUSER"],
        config["SMBPWD"],
        "ubuntu2404",
        config["SMBSERVER_IP"],
        use_ntlm_v2=False,   # often needed for older servers
        is_direct_tcp=True   # port 445
    )
    connected = conn.connect(config["SMBSERVER_IP"], 445, timeout=10)
    print("connected to SMB:", connected)
    return conn

def cleanup_session(session_context):
    pn.state.cache["smb"].close()

pn.state.on_session_destroyed(cleanup_session)


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
        return False
    except DataError:
        session.rollback()
        pn.state.notifications.error(f'Messwert ist keine Zahl', duration=2000)
        return False
    else:
        session.commit()
    session.close()
    return True



def clean_smb_name(name: str) -> str:
    return name.rstrip("\x00").strip()

def find_latest_remote_file(conn, share_name, remote_dir):
    max_file_number = -1
    best_name = None

    for entry in conn.listPath(share_name, remote_dir):
        if entry.isDirectory:
            continue

        clean_name = clean_smb_name(entry.filename)
        match = pattern.search(clean_name)

        if match:
            number = int(match.group(1))
            if number > max_file_number:
                max_file_number = number
                best_name = clean_name

    if best_name is None:
        return None

    return {
        "name": best_name,
        "path": f"{remote_dir}/{best_name}"
    }

async def getMeasurement():
    conn = pn.state.cache["smb"].get()
    file_info  = find_latest_remote_file(conn, config["SMBSHARENAME"], "/ExcelAusgabe")

    if file_info is None:
        pn.state.notifications.error("Keine CSV im Verzeichnis", duration=2000)
        return
    csv_path = file_info["path"]

    try:
        buffer = BytesIO()
        conn.retrieveFile(config["SMBSHARENAME"], csv_path, buffer)
        buffer.seek(0)

        text = buffer.read().decode("cp1252", errors="replace")
        lines = [line for line in text.splitlines() if line.strip()]

        if not lines:
            pn.state.notifications.error(f"{csv_path} ist leer", duration=2000)
            return

        last_line = lines[-1]
        print(last_line, flush=True)


        columns = last_line.split(";")
        value = float(columns[13].replace(",", "."))
        currentMeasurement.rx.value = value
        pn.state.cache["currentPath"] = csv_path

    except IndexError:
        pn.state.notifications.error(
            f"{csv_path} hat nicht genug Spalten",
            duration=2000
        )
    except ValueError as e:
        pn.state.notifications.error(
            f"Wert in {csv_path} konnte nicht in float umgewandelt werden: {e}",
            duration=3000
        )
    except Exception as e:
        print(e)
        pn.state.notifications.error(
            f"{csv_path} konnte nicht gelesen werden: {e}",
            duration=3000
        )

        
        

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

    
    result = write_to_DB(ti_Barcode.value, currentMeasurement.rx.value)
    if result:
        pn.state.notifications.success(f'Erfolgreich gespeichert', duration=3000)
        try:
            #Use subprocess because pysmb delete does not work with this server
            delete_remote_file_smbclient(
            server=config["SMBSERVER_IP"],
            share=config["SMBSHARENAME"],
            username=config["SMBUSER"],
            password=config["SMBPWD"],
            remote_path=pn.state.cache["currentPath"],
            )
        except Exception as e:
            print(e)
            
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