import asyncio
import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from os.path import isfile
import panel as pn
from watchfiles import awatch, Change

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

main_project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if main_project_dir not in sys.path:
    sys.path.append(main_project_dir)


from db.models import BearingData

pn.extension(sizing_mode="stretch_width")


TITLE = "AR DMC Lasern"

# Load config file
configPath = "config.json"
if not isfile(configPath):
    configPath = "default_config.json"
    print("loading default config", flush=True)
    print("loading default config", flush=True)
    
with open(configPath, "r") as f:
    config = json.load(f)

pn.extension(notifications=True)
pn.state.notifications.position = 'top-right'
engine = create_engine(f"postgresql+psycopg2://{config["DATABASE"]}", echo=False)

allIDs = []
currentSerialID = pn.rx("Leer")
currentSerialindex = None

#read links from json file
with open("links.json", "r") as f:
    links = json.load(f)
    text="\n".join([f"- [{key}]({value})" for key,value in links.items()])

linklist = pn.pane.Markdown(
    "\n".join([f"## [{key}]({value})" for key,value in links.items()]),
    sizing_mode="stretch_width",
)

# --- CONFIG -------------------------------------------------------------------
# Folder to watch and the CSV filename to react to.
# If CSV_NAME is None, the app will react to the first *.csv file that changes.
WATCH_DIR = Path(config.get("DMC_LASERN_CSV", "./watchtest"))
CSV_NAME: Optional[str] = None



# --- Helpers ------------------------------------------------------------------
def extract_last_nonempty_line(text: str) -> Optional[str]:
    for line in reversed(text.splitlines()):
        s = line.strip()
        if s:
            return s
    return None

async def read_last_line_and_delete(file_path: Path) -> Optional[str]:
    # brief retries in case writer still has handle open
    for attempt in range(5):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            last_line = extract_last_nonempty_line(content) or ""
            try:
                os.remove(file_path)
            except PermissionError:
                await asyncio.sleep(0.2)
                os.remove(file_path)
            return last_line
        except (PermissionError, OSError) as e:
            append_log(f"⚠️ Versuch {attempt+1}/5 beim Zugriff auf Datei: {e}")
            await asyncio.sleep(0.2)
    return None

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

# --- Async watcher task -------------------------------------------------------
async def watch_loop():
    watch_dir = WATCH_DIR.resolve()
    target = (watch_dir / CSV_NAME).resolve() if CSV_NAME else None

    watch_dir.mkdir(parents=True, exist_ok=True)
    append_log(f"Überwachtes Verzeichnis: {watch_dir}")
    if target:
        append_log(f"Überwachte Datei: {target.name}")

    status.object = "- Status: **watching**"

    try:
        async for changes in awatch(watch_dir, recursive=False, stop_event=None):
            for change, path in changes:
                
                p = Path(path).resolve()
                if p.suffix.lower() != ".csv":
                    continue
                if target and p != target:
                    continue
                if change not in (Change.added, Change.modified):
                    continue
                if not p.exists():
                    continue 
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                append_log(f"{now} -  Datei erkannt: {p.name}")
                status.object = "- Status: **processing**"

                last_line = await read_last_line_and_delete(p)
                if last_line is not None:
                    currentSerialID.rx.value = int(last_line.split(';')[1].strip())
                    write_to_DB(currentSerialID.rx.value)
                    append_log(f"Serialnummer ausgelesen: {currentSerialID.rx.value}")
                else:
                    append_log("❌ Fehler beim Lesen / Löschen der Datei.")
                status.object = "- Status: **watching**"
    except asyncio.CancelledError:
        append_log("🛑 Dateiüberwachung beendet.")
        raise
    finally:
        status.object = "- Status: **idle**"

# --- Session lifecycle (async-safe) -------------------------------------------
def _start_task_onload():
    """
    Called by Panel after the document is ready. We *then* schedule task creation
    on the document's running asyncio loop via add_next_tick_callback.
    """
    def _spawn():
        sess = pn.state.curdoc.session_context
        # store task on the session_context so each browser tab has its own
        if not hasattr(sess, "_watch_task") or getattr(sess, "_watch_task").done():
            sess._watch_task = asyncio.create_task(watch_loop())
            append_log("✅ Verzeichnisüberwachung gestartet.")
    # Ensure we’re on the document’s event loop:
    pn.state.curdoc.add_next_tick_callback(_spawn)

def _stop_task(session_context):
    """
    Required signature for on_session_destroyed. Cancel the per-session task.
    """
    task = getattr(session_context, "_watch_task", None)
    if task and not task.done():
        task.cancel()
        append_log("⏹️ Cancellation requested.")

# Register hooks (safe inside app script)
pn.state.onload(_start_task_onload)
pn.state.on_session_destroyed(_stop_task)


text_currentSerialID = pn.rx("{currentSerialID}").format(currentSerialID=currentSerialID)


md_currentSerialID = pn.pane.Markdown(text_currentSerialID, width=250, styles={'text-align': 'center', 'font-size': '24px'})
serialCard = pn.Card(pn.Row(pn.Spacer(sizing_mode="stretch_width"), md_currentSerialID, pn.Spacer(sizing_mode="stretch_width")), width=250, hide_header=True)

running_indicator = pn.indicators.LoadingSpinner(
    value=False, height=100, width=100, color="secondary", visible=False, margin=50)

status = pn.pane.Markdown("- Status: **idle**")
log = pn.widgets.TextAreaInput(value="", height=240, sizing_mode="stretch_width", disabled=True)

def append_log(msg: str) -> None:
    # safe to call from event loop; keep bounded
    log.value = (log.value + msg + "\n")[-8000:]



column = pn.Column(pn.Row(pn.Spacer(sizing_mode="stretch_width"),pn.pane.Markdown("# Aktuelle Seriennummer:"), pn.Spacer(sizing_mode="stretch_width")),
                    pn.Row(pn.Spacer(sizing_mode="stretch_width"), serialCard, pn.Spacer(sizing_mode="stretch_width")),
                    pn.Spacer(height=8),
                    pn.pane.Markdown("### Log"),
                    log,
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