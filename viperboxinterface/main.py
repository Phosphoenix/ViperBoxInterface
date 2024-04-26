from __future__ import annotations

import logging
import logging.handlers
import multiprocessing
import os
import threading
import time

import psutil
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from viperboxinterface import VB_logger, gui
from viperboxinterface.api_classes import (
    Connect,
    apiRecSettings,
    apiStartRec,
    apiStartStim,
    apiStimSettings,
    apiVerifyXML,
)
from viperboxinterface.ViperBox import ViperBox

# TODO: all return values should be caught and logged

session_datetime = time.strftime("%Y%m%d_%H%M%S")
use_mapping = True

multiprocessing.Process(
    target=VB_logger.start_log_server,
    args=(session_datetime,),
    daemon=True,
).start()

multiprocessing.Process(
    target=gui.run_gui, kwargs={"use_mapping": use_mapping}, daemon=True
).start()

logger = logging.getLogger("SERVER")
logger.setLevel(logging.DEBUG)
socketHandler = logging.handlers.SocketHandler(
    "localhost",
    logging.handlers.DEFAULT_TCP_LOGGING_PORT,
)
logger.addHandler(socketHandler)


docs = """
# Short tutorial

To start using the the API, first connect the viperbox to the computer and switch it on.
To start using it, you need to
- /connect (click the dropdown > Try it out > Execute). Wait until you can read \
    result: true, feedback: Viperbox initialized successfully with ...
- /recording_settings, upload recording settings, by default this is set to true.
- /start_recording, first change the recording name to your desired name, then click \
    Execute.
- [OPTIONAL] /stimulation_settings, upload stimulation settings, by default this is \
    set to false.
- [OPTIONAL] /start_stimulation, start the stimulation, by default this is set to false.
- /stop_recording, to stop the recording.

Recording files will show up in the /Recordings folder.
Stimulation records will show up in the /Stimulations folder.
"""

app = FastAPI(
    title="ViperBox API",
    description=docs,
    summary="API to manage stimulation and recording of the ViperBox, built for \
    NeuraViPeR.",
    version="0.0.1",
    contact={
        "name": "Stijn Balk",
        "email": "stijn@phosphoenix.nl",
    },
    license_info={
        "name": "GPL-2.0 license",
        "url": "https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html",
    },
)

VB = ViperBox(
    _session_datetime=session_datetime, start_oe=True, use_mapping=use_mapping
)


@app.post("/connect")  # , tags=["connect"]
async def init(connect: Connect):
    """Initializes the ViperBoxInterface.

    Args:
    ----
    - probes (default: "1") list of connected ASIC's (also called probes). "1" for
    only one probe, "1,2" for two probes, etc. Max 4 probes.
    - emulation (default: false): whether data should be emulated (true) or real data
    should be sent (false).
    - boxless (default: false): only for testing the software without a box connected
    to the computer.

    Returns:
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info(f"/connect called with {connect.__dict__}")
    result, feedback = VB.connect(
        probe_list=connect.probes,
        emulation=connect.emulation,
        boxless=connect.boxless,
    )
    logger.info(f"/connect returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/connect_oe")
async def connect_oe():
    """Starts Open Ephys, creates data thread and connects to OE."""
    logger.info("/connect_oe called")
    result, feedback = VB.connect_oe()
    logger.info(f"/connect_oe returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/connect_oe_reset")
async def connect_oe_reset():
    """Starts Open Ephys, creates data thread and connects to OE."""
    logger.info("/connect_oe_reset called")
    result, feedback = VB.connect_oe(reset=True)
    logger.info(f"/connect_oe_reset returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/disconnect")  # , tags=["disconnect"])
async def disconnect():
    """Disconnects from the ViperBox.

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info("/disconnect called")
    result, feedback = VB.disconnect()
    logger.info(f"/disconnect returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/shutdown")  # , tags=["shutdown"])
async def shutdown():
    """Shuts down the ViperBoxInterface, apart from disconnect, it also tries to close
    Open Ephys.

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info("/shutdown called")
    result, feedback = VB.shutdown()
    logger.info(f"/shutdown returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/verify_xml/")  # , tags=["verify_xml"])
async def verify_xml(api_verify_xml: apiVerifyXML):
    """Verify XML in string format (plain text). The settings that are in the uploaded
    XML are also checked with the existing settings. For example, if they contain
    settings for probes that are not connected, an error will be thrown.

    Args:
    ----
    - XML: Settings XML to be checked.
    - check_topic: must be one of 'all', 'recording' or 'stimulation'. This says
    something about which part of the settings will be checked. If 'stimulation'
    is selected, both the settings in StimulationWaveformSettings and in
    StimulationMappingSettings will be checked.

    Returns:
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info(f"/verify_xml called with {api_verify_xml.__dict__}")
    try:
        result, feedback = VB.verify_xml_with_local_settings(
            api_verify_xml.dictionary,
            api_verify_xml.XML,
            api_verify_xml.check_topic,
        )
    except ValueError as e:
        result, feedback = False, f"Incorrect value provided: {e!s}"
    logger.info(f"/verify_xml returned with {result}; {feedback}")
    # TODO: add default value to feedback
    return {"result": result, "feedback": feedback}


@app.post("/recording_settings/")  # , tags=["recording_settings"])
async def recording_settings(api_rec_settings: apiRecSettings):
    """Upload recording settings.

    Parameters
    ----------
    - recording_XML (string): Recording settings XML.
    - reset (boolean): To do a reset of all settings and start with a clean slate;
    select true, else select false (default).
    - default_values (boolean): if this is 'true', the input from recording_XML will
    be ignored and default recording settings will be uploaded from
    /defaults/default_recording_settings.xml

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info(f"/recording_settings called with {api_rec_settings.__dict__}")
    result, feedback = VB.recording_settings(
        xml_string=api_rec_settings.recording_XML,
        reset=api_rec_settings.reset,
        default_values=api_rec_settings.default_values,
    )
    logger.info(f"/recording_settings returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/stimulation_settings/")  # , tags=["stimulation_settings"])
async def stimulation_settings(api_stim_settings: apiStimSettings):
    """Upload stimulation settings.

    Parameters
    ----------
    - stimulation_XML (string): Stimulation settings XML.
    - reset (boolean): To do a reset of all settings and start with a clean slate;
    select true, else select false (default).
    - default_values (boolean): if this is 'true', the input from stimulation_XML will
    be ignored and default stimulation settings will be uploaded from
    /defaults/default_stimulation_settings.xml

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info(f"/stimulation_settings called with {api_stim_settings.__dict__}")
    result, feedback = VB.stimulation_settings(
        xml_string=api_stim_settings.stimulation_XML,
        reset=api_stim_settings.reset,
        default_values=api_stim_settings.default_values,
    )
    logger.info(f"/stimulation_settings returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/default_settings/")
async def default_settings():
    """Upload default settings.

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info("/default_settings called")
    result, feedback = VB.default_settings()
    logger.info(f"/default_settings returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/start_recording")  # , tags=["start_recording"])
async def start_recording(api_start_rec: apiStartRec):
    """Starts recording with the specified recording name. Recording is saved in
    /Recordings. Also creates a record of all the actions and stimulations that have
    been performed by the user in /Stimulations.

    Parameters
    ----------
    - recording_name (string): Recording name.

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info(f"/start_recording called with {api_start_rec.__dict__}")
    result, feedback = VB.start_recording(recording_name=api_start_rec.recording_name)
    logger.info(f"/start_recording returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/stop_recording")  # , tags=["stop_recording"])
async def stop_recording():
    """Stops the recording.

    Returns
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info("/stop_recording called")
    result, feedback = VB.stop_recording()
    logger.info(f"/stop_recording returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


@app.post("/start_stimulation/")  # , tags=["start_stimulation"])
async def start_stimulation(api_start_stim: apiStartStim):
    """Triggers the selected stimulation units.

    Args:
    ----
    - boxes (string) (default: "1", only implemented for 1): All ViperBoxes on
    which stimulation should occur. "1" for only one ViperBox, "1,2" for two boxes,
    etc. Max 3 boxes.
    - probes (string) (default: "1"): All ASIC's/probes on which stimulation should
    occur. Max 4 probes.
    - SU_input (string) (default: "1,2,3,4,5,6,7,8"): All Stimulation Units (SU's) on
    which stimulation should occur. Max 8 SU's.

    Returns:
    -------
    - boolean: true if correctly executed, otherwise false.
    - feedback: More information on execution.
    """
    logger.info(f"/start_stimulation called with {api_start_stim.__dict__}")
    result, feedback = VB.start_stimulation(
        boxes=api_start_stim.boxes,
        probes=api_start_stim.probes,
        SU_input=api_start_stim.SU_input,
    )
    logger.info(f"/start_stimulation returned with {result}; {feedback}")
    return {"result": result, "feedback": feedback}


# @app.post("/TTL_start/")#, tags=["TTL_start"])
# async def TTL_start(api_TTL_start: apiTTLStart):
#     result, feedback = VB.TTL_start(
#         api_TTL_start.TTL_channel,
#         api_TTL_start.TTL_XML,
#         api_TTL_start.SU_bit_mask,
#     )
#     return {"result": result, "feedback": feedback}


# @app.post("/TTL_stop/")#, tags=["TTL_stop"])
# async def TTL_stop(api_TTL_stop: apiTTLStop):
#     result, feedback = VB.TTL_stop(apiTTLStop.TTL_channel)
#     return {"result": result, "feedback": feedback}


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")
    # return RedirectResponse(url="/redoc")


def self_terminate():
    # time.sleep(2)
    parent = psutil.Process(psutil.Process(os.getpid()).ppid())
    parent.kill()


@app.post("/kill")
async def kill():
    threading.Thread(target=self_terminate, daemon=True).start()
    return {"success": True}


@app.post("/developer_select_permanent_discharge")
async def select_permanent_discharge(oss: str):
    """Send stimulation current over these OS's."""
    logger.info(f"/select_permanent_discharge called with {oss}")
    if oss == "all":
        VB.set_permanent_discharge([int(item + 1) for item in range(128)])
    elif oss == "none":
        VB.set_permanent_discharge([])
    elif "-" in oss:
        start, end = oss.split("-")
        VB.set_permanent_discharge(
            [int(item) for item in range(int(start), int(end) + 1)]
        )
    else:
        VB.set_permanent_discharge([int(item) for item in oss.split(",")])
    return {"success": True, "feedback": f"Set OS to {oss}"}


if __name__ == "__main__":
    print("##############################you shouldn't see this")
    logger.warning("You shouldn't see this either")
    uvicorn.run(app, host="127.0.0.1", port=8000)
