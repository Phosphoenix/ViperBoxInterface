from __future__ import annotations

import json
import logging
import logging.handlers
import os
import subprocess
import time
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import PySimpleGUI as sg
import requests
from lxml import etree
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# matplotlib.use("TkAgg")


def run_gui():
    visibility_swap = True

    logger = logging.getLogger("GUI")
    logger.setLevel(logging.DEBUG)
    socketHandler = logging.handlers.SocketHandler(
        "localhost",
        logging.handlers.DEFAULT_TCP_LOGGING_PORT,
    )
    logger.addHandler(socketHandler)

    batch_script_path = os.getcwd() + "\\setup\\update.bat"

    gui_start_vals = {
        "anodic_cathodic": ("Anodic", "polarity"),
        "number_of_pulses": (20, "pulses"),
        "pulse_delay": (0, "prephase"),
        "pulse_amplitude_anode": (5, "amplitude1"),
        "first_pulse_phase_width": (170, "width1"),
        "pulse_interphase_interval": (60, "interphase"),
        "pulse_amplitude_cathode": (5, "amplitude2"),
        "second_pulse_phase_width": (170, "width2"),
        "discharge_time": (200, "discharge"),
        "pulse_duration": (600, "duration"),
        "discharge_time_extra": (1000, "aftertrain"),
    }

    def collapse(layout, key):
        return sg.pin(
            sg.Column(
                layout,
                key=key,
                visible=manual_stim,
                element_justification="r",
                expand_x=True,
            ),
        )

    def LEDIndicator(key=None, radius=15):
        return sg.Graph(
            canvas_size=(radius, radius),
            graph_bottom_left=(-radius, -radius),
            graph_top_right=(radius, radius),
            pad=(0, 0),
            key=key,
        )

    def SetLED(window, key, status):
        graph = window[key]
        graph.erase()
        if status is True:
            graph.draw_circle((0, 0), 12, fill_color="green", line_color="green")
        elif status is None:
            graph.draw_circle((0, 0), 12, fill_color="red", line_color="red")
        elif status is False:
            graph.draw_circle((0, 0), 12, fill_color="gray", line_color="gray")

    sg.theme("SystemDefaultForReal")

    # ------------------------------------------------------------------
    # CF STIMULATION PULSE FRAME

    def generate_plot(
        # biphasic: int = 1,
        anodic_cathodic: int = 0,
        pulse_delay: int = 0,
        first_pulse_phase_width: int = 170,
        pulse_interphase_interval: int = 60,
        second_pulse_phase_width: int = 170,
        discharge_time: int = 200,
        pulse_amplitude_anode: int = 5,
        pulse_amplitude_cathode: int = 5,
        # pulse_amplitude_equal: int = 0,
        pulse_duration: int = 600,
    ):
        # if bool(pulse_amplitude_equal):
        #     pulse_amplitude_cathode = pulse_amplitude_anode
        # if not bool(biphasic):
        #     pulse_amplitude_cathode = 0
        if anodic_cathodic == 1:
            pulse_amplitude_anode *= -1
            pulse_amplitude_cathode *= -1
        time = np.linspace(0, pulse_duration, pulse_duration)
        current = np.zeros_like(time)
        tp1 = pulse_delay
        tp2 = tp1 + first_pulse_phase_width
        tp3 = tp2 + pulse_interphase_interval
        tp4 = tp3 + second_pulse_phase_width
        tp5 = tp4 + discharge_time
        current[(time >= 0) & (time <= tp1)] = 0
        current[(time > tp1) & (time <= tp2)] = pulse_amplitude_anode
        current[(time > tp2) & (time <= tp3)] = 0
        current[(time > tp3) & (time <= tp4)] = -pulse_amplitude_cathode
        current[(time > tp4) & (time <= tp5)] = 0

        fig = matplotlib.figure.Figure(figsize=(4, 3), dpi=100)
        ax = fig.add_subplot(111)
        fig.get_axes()[0].set_xlabel("Time [μs]")
        fig.get_axes()[0].set_ylabel("Pulse amplitude [μA]")
        ax.yaxis.get_major_locator().set_params(integer=True)
        ax.plot(time, current)
        fig.tight_layout()
        return fig

    def draw_figure(canvas, figure):
        if not hasattr(draw_figure, "canvas_packed"):
            draw_figure.canvas_packed = {}
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        widget = figure_canvas_agg.get_tk_widget()
        if widget not in draw_figure.canvas_packed:
            draw_figure.canvas_packed[widget] = figure
            widget.pack(side="top", fill="both", expand=1)
        return figure_canvas_agg

    def delete_figure_agg(figure_agg):
        figure_agg.get_tk_widget().forget()
        try:
            draw_figure.canvas_packed.pop(figure_agg.get_tk_widget())
        except Exception as e:
            logger.info(f"Error removing {figure_agg} from list", e)
        plt.close("all")

    plot_frame = sg.Frame(
        "Pulse preview",
        [
            [sg.Canvas(key="-CANVAS-")],
            [sg.Button("Reload", key="button_reload", disabled=True)],
        ],
        size=(420, 360),
        visible=visibility_swap,
        expand_y=True,
    )

    # ------------------------------------------------------------------
    # CF: VIPERBOX CONTROL FRAME

    viperbox_control_frame = sg.Column(
        # "Viperbox connection",
        # [
        [
            [sg.VPush()],
            [
                sg.Push(),
                sg.Column(
                    # [
                    #     [
                    #         sg.Text("ViperBox connected"),  # , size=(10, 0)),
                    #         LEDIndicator("led_connect_probe"),
                    #     ],
                    #     [
                    #         sg.Button("Connect", key="button_connect", disabled=True),
                    #         sg.Button(
                    #             "Disconnect", key="button_disconnect", disabled=True
                    #         ),
                    #     ],
                    # ],
                    [
                        [
                            sg.Button(
                                "Connect ViperBox",
                                key="button_connect",
                                size=(18, 1),
                                disabled=True,
                            ),
                        ],
                        [
                            sg.Button(
                                "Connect Open Ephys",
                                key="button_connect_oe",
                                size=(18, 1),
                                disabled=True,
                            ),
                        ],
                    ],
                ),
                sg.Push(),
            ],
            [sg.VPush()],
        ],
        # ],
        expand_y=True,
    )

    viperbox_recording_settings_frame = sg.Column(
        # "ViperBox control",
        [
            [
                sg.Text("Subject"),
                sg.Input("Recording", key="input_filename", size=(15, 1)),
                sg.Button(
                    "Change folder",
                    key="button_select_recording_folder",
                    disabled=True,
                ),
            ],
            [
                sg.Button("Start acq.", size=(10, 1), key="button_rec", disabled=True),
                sg.Button("Stop acq.", size=(10, 1), key="button_stop", disabled=True),
                sg.Button(
                    "Stimulate",
                    size=(10, 1),
                    key="button_stim",
                    disabled=True,
                    tooltip="Start recording before stimulating",
                ),
            ],
            [
                sg.Column(
                    [
                        [
                            sg.Text("Recording status:"),
                            LEDIndicator("led_rec"),
                        ],
                    ],
                ),
            ],
        ],
        expand_x=True,
        element_justification="c",
    )

    sg.Frame(
        "Open ephys data viewer",
        [[sg.Button("Start Open Ephys", key="button_start_oe")]],
        expand_x=True,
    )

    # ------------------------------------------------------------------
    # CF: GAIN AND REFERENCE FRAME

    ref_MAX_COL = 8
    reference_switch_matrix = ["off" for _ in range(ref_MAX_COL + 1)]
    reference_switch_matrix[0] = "on"
    reference_button_matrix = [
        sg.Button(
            "B",
            size=(10, 1),
            key=(f"reference_{0}"),
            pad=(1, 1),
            button_color="red",
            disabled=True,
        ),
    ]
    reference_button_matrix.extend(
        [
            sg.Button(
                f"{i+1}",
                size=(2, 1),
                key=(f"reference_{i+1}"),
                pad=(1, 1),
                button_color="light gray",
                disabled=True,
            )
            for i in range(ref_MAX_COL)
        ],
    )
    reference_button_matrix = [reference_button_matrix]

    gain_MAX_COL = 4
    gain_switch_matrix = ["off" for _ in range(gain_MAX_COL)]
    gain_switch_matrix[0] = "on"
    gain_dict = {
        "x60": 0,
        "x24": 1,
        "x12": 2,
        # "x0.16": 3,
    }
    gain_button_matrix = [
        [
            sg.Button(
                i,
                size=(8, 1),
                key=(f"gain_{j}"),
                pad=(1, 1),
                button_color="red" if i == "x60" else "light gray",
                disabled=True,
            )
            for i, j in gain_dict.items()
        ],
    ]

    reference_frame = sg.Column(
        # "Reference selection",
        [[sg.Text("Ref. selection", size=(10, 0)), sg.Column(reference_button_matrix)]],
        expand_x=True,
    )

    gain_frame = sg.Column(
        # "Gain selection",
        [[sg.Text("Gain selection", size=(10, 0)), sg.Column(gain_button_matrix)]],
        expand_x=True,
        vertical_alignment="bottom",
    )

    upload_rec_button = sg.Button(
        "Recording settings",
        key="upload_recording_settings",
        disabled=True,
    )

    upload_stim_button = sg.Button(
        "Stimulation settings",
        key="upload_stimulation_settings",
        disabled=True,
    )

    upload_defaults_button = sg.Button(
        "Default settings",
        key="upload_defaults",
        disabled=True,
    )

    recording_settings_frame = sg.Frame(
        "Recording settings",
        [
            [reference_frame],
            [gain_frame],
        ],
        expand_x=True,
        # expand_y=True,
    )

    upload_settings_frame = sg.Column(
        # "Upload settings to ViperBox",
        [
            [sg.Text("Upload settings to ViperBox")],
            [upload_rec_button, upload_stim_button],
            [upload_defaults_button],
        ],
        expand_x=True,
        element_justification="c",
    )

    def toggle_1d_color(event, reference_switch_matrix):
        row = int(event[-1])

        if reference_switch_matrix[row] == "off":
            reference_switch_matrix[row] = "on"
            return "red"
        else:
            reference_switch_matrix[row] = "off"
            if reference_switch_matrix.count("off") == 9:
                logger.warning("At least one reference needs to be selected.")
                reference_switch_matrix[row] = "on"
                return "red"
            return "light gray"

    def toggle_gain_color(event, gain_switch_matrix):
        row = int(event[-1])

        gain_switch_matrix = ["off"] * 4
        gain_switch_matrix[row] = "on"
        return "red"

    def get_references(reference_switch_matrix):
        bin_input_list = "".join(
            ["1" if item == "on" else "0" for item in reference_switch_matrix],
        )
        # ref_integer = int(bin_input_list, 2)
        ref_list = [str(i) for i in range(9) if bin_input_list[i] == "1"]
        ref_string = ", ".join(ref_list)
        return ref_string

    # ------------------------------------------------------------------
    # CF: ELECTRODE SELECTION FRAME

    MAX_ROWS = 15
    MAX_COL = 4

    electrode_switch_matrix = [["on" for i in range(MAX_COL)] for j in range(MAX_ROWS)]
    electrode_button_matrix = [
        [
            sg.Button(
                f"{i*MAX_ROWS+j+1}",
                size=(2, 1),
                key=(f"el_button_{i*MAX_ROWS+j+1}"),
                pad=(10, 1),
                button_color="red",
                disabled=True,
            )
            for i in range(MAX_COL)
        ]
        for j in range(MAX_ROWS)
    ]
    electrode_button_matrix = electrode_button_matrix[::-1]
    electrode_frame = sg.Frame(
        "Stimulation electrode selection",
        [
            [sg.Column(electrode_button_matrix)],
            [
                sg.Column(
                    [
                        [
                            sg.Button(
                                "All",
                                size=(4, 0),
                                expand_x=True,
                                key="button_all",
                                button_color="red",
                                disabled=True,
                            ),
                            sg.Button(
                                "None",
                                size=(4, 0),
                                expand_x=True,
                                key="button_none",
                                disabled=True,
                            ),
                        ],
                    ],
                    expand_x=True,
                ),
            ],
        ],
        expand_y=True,
    )

    def toggle_2d_color(event, electrode_switch_matrix):
        electrode = int(event[10:])
        row = (electrode - 1) % MAX_ROWS
        col = (electrode - 1) // MAX_ROWS

        if electrode_switch_matrix[row][col] == "off":
            electrode_switch_matrix[row][col] = "on"
            return "red"
        else:
            electrode_switch_matrix[row][col] = "off"
            return "light gray"

    def get_electrodes(electrode_switch_matrix, save_purpose=False):
        # TMPFIX uncomment
        # probe_mapping = Mappings("defaults/electrode_mapping_short_cables.xlsx")
        rows, cols = np.where(np.asarray(electrode_switch_matrix) == "on")
        if save_purpose:
            electrode_list = [
                str(i * MAX_ROWS + j + 1) for i, j in zip(cols, rows, strict=False)
            ]
            electrode_list.sort()
            return electrode_list
        else:
            electrode_list = [
                i * MAX_ROWS + j + 1 for i, j in zip(cols, rows, strict=False)
            ]
            os_list = electrode_list
            # TMPFIX uncomment
            # os_list = [probe_mapping.probe_to_os_map[i] for i in electrode_list]
            os_list.sort()
            os_list = [str(i) for i in os_list]
            if os_list == []:
                return None
            return ", ".join(os_list)

    def set_reference_matrix(electrode_list):
        electrode_switch_matrix = [
            ["off" for i in range(MAX_COL)] for j in range(MAX_ROWS)
        ]
        for electrode in electrode_list:
            row = (int(electrode) - 1) % MAX_ROWS
            col = (int(electrode) - 1) // MAX_ROWS
            electrode_switch_matrix[row][col] = "on"
        return electrode_switch_matrix

    # ------------------------------------------------------------------
    # CF: LOG FRAME

    sg.Frame(
        "Log",
        [
            [
                sg.Multiline(
                    key="mul_log",
                    expand_y=True,
                    expand_x=True,
                    autoscroll=True,
                    horizontal_scroll=True,
                    disabled=True,
                    font=("Cascadia Mono", 8),
                    default_text="Initializing ViperBox...",
                ),
            ],
        ],
        size=(420, 200),
        expand_y=True,
        expand_x=True,
    )

    # ------------------------------------------------------------------
    # CF: STIMULATION SETTINGS FRAME

    unit_h, unit_w = (4, 1)
    inpsize_w, inpsize_h = (10, 1)

    # stimulation_settings = sg.Frame(
    #     "Pre-load settings",
    #     [
    #         [
    #             sg.Button(
    #                 "Select settings folder",
    #                 key="button_select_settings_folder",
    #                 expand_x=True,
    #             )
    #         ],
    #         [
    #             sg.Text("Filter:"),
    #             sg.Input(
    #                 "",
    #                 size=(15, 1),
    #                 key="input_filter_name",
    #                 # enable_events=True,
    #                 expand_x=True,
    #             ),
    #         ],
    #         [
    #             sg.Listbox(
    #                 size=(10, 6),
    #                 key="listbox_settings",
    #                 expand_y=True,
    #                 expand_x=True,
    #                 values=settings_list,
    #                 enable_events=True,
    #             ),
    #         ],
    #         [
    #             sg.Button("Save settings", size=(10, 1), key="button_save_set"),
    #             sg.Input("sett_name", size=(15, 1), key="input_set_name"),
    #         ],
    #         [
    #             sg.Button("Load", size=(10, 1), key="button_load_set"),
    #             sg.Button("Delete", size=(10, 1), key="button_del_set"),
    #         ],
    #     ],
    #     expand_x=True,
    #     expand_y=True,
    #     vertical_alignment="t",
    #     visible=False,
    # )

    def save_settings(location, filename, settings):
        existing_settings = load_settings_folder(location)
        answer = "OK"
        if filename in existing_settings:
            answer = sg.popup_ok_cancel(
                f'Setting "{filename}" already exists, if you want to continue, \
press OK',
            )
        if answer == "OK":
            filename = filename + ".cfg"
            settings_save = settings.copy()
            delete = [
                # "led_connect_hardware",
                # "led_connect_BS",
                # "led_connect_probe",
                "input_filename",
                "led_rec",
                "checkbox_rec_wo_stim",
                # "input_filter_name",
                # "listbox_settings",
                "input_set_name",
                "-CANVAS-",
                "mul_log",
            ]
            for key in delete:
                del settings_save[key]
            with open(location + "\\" + filename, "w") as f:
                json.dump(settings_save, f)

    def read_saved_settings(location, filename):
        full_path = Path.joinpath(Path(location), filename + ".cfg")
        with open(full_path) as f:
            return json.load(f)

    def load_settings_folder(location):
        settings_list = [path.stem for path in Path(location).glob("*.cfg")]
        return settings_list

    def update_settings_listbox(settings_folder_path):
        # settings_list = load_settings_folder(settings_folder_path)
        # window["listbox_settings"].update(settings_list)
        pass

    # ------------------------------------------------------------------
    # CF: PULSE SHAPE FRAME

    manual_stim = True
    pulse_shape_col_settings = sg.Column(
        [
            # [
            #     sg.Text("Biphasic / Monophasic"),
            #     sg.Drop(
            #         key="biphasic",
            #         size=(inpsize_w - 2, inpsize_h),
            #         values=("Biphasic", "Monophasic"),
            #         auto_size_text=True,
            #         default_value="Biphasic",
            #         # enable_events=True,
            #     ),
            #     sg.T(" ", size=(unit_h, unit_w)),
            # ],
            [
                sg.Text("Anodic / cathodic first"),
                sg.Drop(
                    key="anodic_cathodic",
                    size=(inpsize_w - 2, inpsize_h),
                    values=("Anodic", "Cathodic"),
                    auto_size_text=True,
                    default_value="Anodic",
                    # enable_events=True,
                ),
                sg.T(" ", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Pulse duration"),
                sg.Input(
                    gui_start_vals["pulse_duration"][0],
                    size=(inpsize_w, inpsize_h),
                    key="pulse_duration",
                    # enable_events=True,
                ),
                sg.T("μSec", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Prephase"),
                sg.Input(
                    gui_start_vals["pulse_delay"][0],
                    size=(inpsize_w, inpsize_h),
                    key="pulse_delay",
                    # enable_events=True
                ),
                sg.T("μSec", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("1st pulse phase width"),
                sg.Input(
                    gui_start_vals["first_pulse_phase_width"][0],
                    size=(inpsize_w, inpsize_h),
                    key="first_pulse_phase_width",
                    # enable_events=True,
                ),
                sg.T("μSec", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Pulse interphase interval"),
                sg.Input(
                    gui_start_vals["pulse_interphase_interval"][0],
                    size=(inpsize_w, inpsize_h),
                    key="pulse_interphase_interval",
                    # enable_events=True,
                ),
                sg.T("μSec", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("2nd pulse phase width"),
                sg.Input(
                    gui_start_vals["second_pulse_phase_width"][0],
                    size=(inpsize_w, inpsize_h),
                    key="second_pulse_phase_width",
                    # enable_events=True,
                ),
                sg.T("μSec", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Interpulse interval (discharge)"),
                sg.Input(
                    gui_start_vals["discharge_time"][0],
                    size=(inpsize_w, inpsize_h),
                    key="discharge_time",
                    # enable_events=True,
                ),
                sg.T("μSec", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Pulse amplitude anode"),
                sg.Input(
                    gui_start_vals["pulse_amplitude_anode"][0],
                    size=(inpsize_w, inpsize_h),
                    key="pulse_amplitude_anode",
                    # enable_events=True,
                ),
                sg.T("μA", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Pulse amplitude cathode"),
                sg.Input(
                    gui_start_vals["pulse_amplitude_cathode"][0],
                    size=(inpsize_w, inpsize_h),
                    key="pulse_amplitude_cathode",
                    # enable_events=True,
                ),
                sg.T("μA", size=(unit_h, unit_w)),
            ],
            [sg.HorizontalSeparator()],
            [
                sg.Text("Number of pulses"),
                sg.Input(
                    gui_start_vals["number_of_pulses"][0],
                    size=(inpsize_w, inpsize_h),
                    key="number_of_pulses",
                    # enable_events=True,
                ),
                sg.T(" ", size=(unit_h, unit_w)),
            ],
            [
                sg.Text("Train interval (discharge)"),
                sg.Input(
                    gui_start_vals["discharge_time_extra"][0],
                    size=(inpsize_w, inpsize_h),
                    key="discharge_time_extra",
                    # enable_events=True,
                ),
                sg.T("mSec", size=(unit_h, unit_w)),
            ],
        ],
        element_justification="r",
        expand_x=True,
    )
    waveform_settings_frame = sg.Frame(
        "Waveform settings",
        [
            [sg.VPush()],
            [pulse_shape_col_settings],
            [sg.VPush()],
        ],
        element_justification="r",
        expand_x=True,
        expand_y=True,
    )

    # ------------------------------------------------------------------
    # CF: PULSE TRAIN FRAME

    # pulse_train_frame = sg.Frame(
    #     "Pulse train parameters",
    #     [
    #         [
    #             sg.Text("Number of pulses"),
    #             sg.Input(
    #                 gui_start_vals["number_of_pulses"][0],
    #                 size=(inpsize_w, inpsize_h),
    #                 key="number_of_pulses",
    #                 # enable_events=True,
    #             ),
    #             sg.T(" ", size=(unit_h, unit_w)),
    #         ],
    #         # [
    #         #     sg.Text("Frequency of pulses"),
    #         #     sg.Input(
    #         #         200,
    #         #         size=(inpsize_w, inpsize_h),
    #         #         key="frequency_of_pulses",
    #         #         # enable_events=True,
    #         #     ),
    #         #     sg.T("Hz", size=(unit_h, unit_w)),
    #         # ],
    #         # [
    #         #     sg.Text("Number of trains"),
    #         #     sg.Input(
    #         #         5,
    #         #         size=(inpsize_w, inpsize_h),
    #         #         key="number_of_trains",
    #         #         # enable_events=True,
    #         #     ),
    #         #     sg.T(" ", size=(unit_h, unit_w)),
    #         # ],
    #         [
    #             sg.Text("Train interval (discharge)"),
    #             sg.Input(
    #                 gui_start_vals["discharge_time_extra"][0],
    #                 size=(inpsize_w, inpsize_h),
    #                 key="discharge_time_extra",
    #                 # enable_events=True,
    #             ),
    #             sg.T("mSec", size=(unit_h, unit_w)),
    #         ],
    #         # [
    #         #     sg.Text("On-set onset_jitter"),
    #         #     sg.Input(
    #         #         0,
    #         #         size=(inpsize_w, inpsize_h),
    #         #         key="onset_jitter",
    #         #         # enable_events=True
    #         #     ),
    #         #     sg.T("Sec", size=(unit_h, unit_w)),
    #         # ],
    #     ],
    #     element_justification="r",
    #     expand_x=True,
    # )

    # ------------------------------------------------------------------
    # CF: PARAMETER SWEEP FRAME

    # parameter_sweep = sg.Frame(
    #     "Stimulation sweep parameters",
    #     [
    #         [
    #             sg.Text("Pulse amplitude min"),
    #             sg.Input(
    #                 1,
    #                 size=(inpsize_w, inpsize_h),
    #                 key="pulse_amplitude_min",
    #                 # enable_events=True,
    #             ),
    #             sg.T("μA", size=(unit_h, unit_w)),
    #         ],
    #         [
    #             sg.Text("Pulse amplitude max"),
    #             sg.Input(
    #                 20,
    #                 size=(inpsize_w, inpsize_h),
    #                 key="pulse_amplitude_max",
    #                 # enable_events=True,
    #             ),
    #             sg.T("μA", size=(unit_h, unit_w)),
    #         ],
    #         [
    #             sg.Text("Pulse amplitude step"),
    #             sg.Input(
    #                 1,
    #                 size=(inpsize_w, inpsize_h),
    #                 key="pulse_amplitude_step",
    #                 # enable_events=True,
    #             ),
    #             sg.T("μA", size=(unit_h, unit_w)),
    #         ],
    #         [
    #             sg.Text("Repetitions"),
    #             sg.Input(
    #                 1,
    #                 size=(inpsize_w, inpsize_h),
    #                 key="repetitions",
    #                 # enable_events=True
    #             ),
    #             sg.T(" ", size=(unit_h, unit_w)),
    #         ],
    #         [sg.Checkbox("Randomize", key="randomize")],
    #     ],
    #     element_justification="r",
    #     expand_x=True,
    #     visible=not manual_stim,
    #     key="key_parameter_sweep",
    # )

    menu_def = [["&Application", ["&Update"]]]
    layout = [[sg.Menu(menu_def, key="-MENU-", tearoff=False)]]

    # ------------------------------------------------------------------
    # INTEGRATION OF COMPONENTS

    col_el_frame = sg.Column(
        [[electrode_frame]],
        k="col_el_frame",
        expand_y=True,
        visible=visibility_swap,
    )

    control_frame = sg.Frame(
        "ViperBox control",
        [
            [
                viperbox_control_frame,
                sg.VSeparator(),
                viperbox_recording_settings_frame,
                sg.VSeparator(),
                upload_settings_frame,
            ],
        ],
        expand_y=True,
        expand_x=True,
        element_justification="c",
    )

    pulse_col = sg.Column(
        [[waveform_settings_frame, plot_frame]],
        expand_x=True,
        expand_y=True,
    )

    rec_pulse_col = sg.Column(
        [[recording_settings_frame], [pulse_col]],
        expand_x=True,
        expand_y=True,
    )

    settings_col = sg.Column(
        [[rec_pulse_col, col_el_frame]],
        expand_x=True,
        expand_y=True,
    )

    layout += [
        [
            sg.Column(
                [
                    [control_frame],
                    [settings_col],
                ],
                expand_x=True,
                expand_y=True,
            ),
        ],
    ]

    def to_settings_xml_string(settings_input: dict) -> str:
        program = etree.Element("Program")
        settings = etree.SubElement(program, "Settings")
        settings_type = {
            "Channel": "RecordingSettings",
            "Configuration": "StimulationWaveformSettings",
            "Mapping": "StimulationMappingSettings",
        }
        logger.info(f"settings in to_setting fct: {settings}")

        for sub_type, dct in settings_input.items():
            recording_settings = etree.SubElement(settings, settings_type[sub_type])
            _ = etree.SubElement(recording_settings, sub_type, attrib=dct)

        return etree.tostring(program).decode("utf-8")

    def handle_response(response, message):
        if response.status_code != 200:
            logger.debug(
                f"Server error: {response.status_code}. Response: {response.__dict__}",
            )
            sg.popup_ok(
                f"Something went wrong:  {response.status_code}. {response.__dict__}",
            )
            return False
        else:
            # logger.debug(f"Server reply: {response.json()}")
            if response.json()["result"] is False:
                logger.debug(f"Server reply: {response.json()['feedback']}")
                sg.popup_ok(f"{response.json()['feedback']}")
                return False
            else:
                logger.info(message)
                return True

    def convert_anodic_cathodic(values):
        if values["anodic_cathodic"] == "Anodic":
            values["anodic_cathodic"] = 0
        else:
            values["anodic_cathodic"] = 1
        return values

    logger.debug("Starting GUI")

    gain = 0

    window = sg.Window(
        "ViperBox Control",
        layout,
        finalize=False,
        icon=r"..\\setup\\logo.ico",
    )

    url = "http://127.0.0.1:8000/"
    tmp_path = ""
    _, values = window.read(timeout=0)
    # SetLED(window, "led_connect_probe", False)
    SetLED(window, "led_rec", False)
    fig = generate_plot()
    figure_agg = draw_figure(window["-CANVAS-"].TKCanvas, fig)

    focus_out_elements = [
        "anodic_cathodic",
        "number_of_pulses",
        "pulse_delay",
        "pulse_amplitude_anode",
        "first_pulse_phase_width",
        "pulse_interphase_interval",
        "pulse_amplitude_cathode",
        "second_pulse_phase_width",
        "discharge_time",
        "pulse_duration",
        "discharge_time_extra",
    ]
    elements = [window[key] for key in focus_out_elements]

    for element in elements:
        element.bind("<FocusOut>", "+FOCUS OUT")

    # Initialize viperbox with default settings
    if __name__ != "__main__":
        # Connect to ViperBox
        data = {"probe_list": "1", "emulation": "False", "boxless": "False"}
        response = requests.post(url + "connect", json=data)
        if handle_response(response, "Connected to ViperBox"):
            # SetLED(window, "led_connect_probe", True)
            SetLED(window, "led_rec", False)
        else:
            # SetLED(window, "led_connect_probe", False)
            SetLED(window, "led_rec", False)
        # Upload default settings
        try:
            response = requests.post(url + "default_settings", timeout=5)
            if handle_response(response, "Default settings uploaded"):
                pass
        except requests.exceptions.Timeout:
            sg.popup_ok("Connection to ViperBox timed out, is the ViperBox busy?")
        # Start OE and connect to it
        response = sg.popup_ok_cancel(
            "After you press OK here, you have 10 seconds to press 'CONNECT' \
in Ephys Socket, in Open Ephys",
        )
        if response == "OK":
            response = requests.post(url + "connect_oe", timeout=10)
            if handle_response(response, "Connected to Open Ephys"):
                pass

    disabled_startup_buttons = [
        # "button_disconnect",
        "button_connect",
        "button_connect_oe",
        "button_rec",
        "button_stop",
        "upload_recording_settings",
        "upload_stimulation_settings",
        "upload_defaults",
        "button_select_recording_folder",
        "button_all",
        "button_none",
        "button_reload",
    ]
    disabled_startup_buttons.extend([f"reference_{i}" for i in range(9)])
    disabled_startup_buttons.extend([f"gain_{i}" for i in range(3)])
    disabled_startup_buttons.extend([f"el_button_{i+1}" for i in range(60)])

    [window[item].update(disabled=False) for item in disabled_startup_buttons]

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            try:
                _ = requests.put(
                    "http://localhost:37497/api/status",
                    json={"mode": "IDLE"},
                )
                _ = requests.put(
                    "http://localhost:37497/api/window",
                    json={"command": "quit"},
                    timeout=1,
                )
            except requests.exceptions.RequestException:
                pass
            _ = response = requests.post(url + "disconnect")
            time.sleep(5)
            _ = response = requests.post(url + "kill")
            logger.info("Closing GUI")
            break
        elif event == "button_connect":
            data = {"probe_list": "1", "emulation": "False", "boxless": "False"}
            response = requests.post(url + "connect", json=data)
            if handle_response(response, "Connected to ViperBox"):
                SetLED(window, "led_rec", False)
            else:
                SetLED(window, "led_rec", False)
        elif event == "button_connect_oe":
            response = sg.popup_ok_cancel(
                "After you press OK here, you have 10 seconds to press 'CONNECT' \
    in Ephys Socket, in Open Ephys",
            )
            if response == "OK":
                response = requests.post(url + "connect_oe_reset", timeout=10)
                if handle_response(response, "Connected to Open Ephys"):
                    pass
        elif event == "button_select_recording_folder":
            tmp_path = sg.popup_get_folder("Select recording folder")
            logger.info(f"Updated recordings file path to: {tmp_path}")
        elif event == "button_rec":
            if tmp_path:
                data = {"recording_name": f"{tmp_path}/{values['input_filename']}"}
            else:
                data = {"recording_name": f"{values['input_filename']}"}
            logger.info("Start recording button pressed")
            try:
                response = requests.post(url + "start_recording", json=data, timeout=5)
            except requests.exceptions.Timeout:
                sg.popup_ok(
                    "ViperBox is hanging when trying to restart recording?\
Please do the following: \n\
1. restart the Viperbox\
2. install ViperBox driver patch located in setup>DowngradeFTDI>downgrade.bat\
3. restart the Viperbox",
                )
                continue
            if handle_response(response, "Recording started"):
                window["button_stim"].update(disabled=False)
            SetLED(window, "led_rec", True)
        elif event == "button_stop":
            logger.info("Stop recording button pressed")
            response = requests.post(url + "stop_recording")
            if handle_response(response, "Recording stopped"):
                pass
            SetLED(window, "led_rec", False)
        elif event == "button_stim":
            logger.info("Stimulate button pressed")
            data = {"boxes": "1", "probes": "-", "SU_input": "1"}
            response = requests.post(url + "start_stimulation", json=data, timeout=5)
            if handle_response(response, "Stimulation started"):
                pass
        elif event[:3] == "el_":
            window[event].update(
                button_color=toggle_2d_color(event, electrode_switch_matrix),
            )
        elif event == "button_all":
            electrode_switch_matrix = [
                ["on" for i in range(MAX_COL)] for j in range(MAX_ROWS)
            ]
            for electrode in range(1, 61):
                window[f"el_button_{electrode}"].update(button_color="red")
        elif event == "button_none":
            electrode_switch_matrix = [
                ["off" for i in range(MAX_COL)] for j in range(MAX_ROWS)
            ]
            for electrode in range(1, 61):
                window[f"el_button_{electrode}"].update(button_color="light gray")
        elif event[:3] == "ref":
            window[event].update(
                button_color=toggle_1d_color(event, reference_switch_matrix),
            )
        elif event[:3] == "gai":
            window["gain_0"].update(button_color="light grey")
            window["gain_1"].update(button_color="light grey")
            window["gain_2"].update(button_color="light grey")
            window[event].update(
                button_color=toggle_gain_color(event, gain_switch_matrix),
            )
            gain = int(event[-1])
        elif event == "Reload":
            # Implementation from https://github.com/PySimpleGUI/PySimpleGUI/blob/
            # master/DemoPrograms/Demo_Matplotlib_Browser.py
            if figure_agg:
                delete_figure_agg(figure_agg)
            values = convert_anodic_cathodic(values)
            plot_vals = {k: int(values[k]) for k in generate_plot.__annotations__}
            fig = generate_plot(**plot_vals)
            figure_agg = draw_figure(window["-CANVAS-"].TKCanvas, fig)
        elif event == "upload_recording_settings":
            recording_xml = to_settings_xml_string(
                settings_input={
                    "Channel": {
                        "box": "-",
                        "probe": "-",
                        "channel": "-",
                        "references": get_references(reference_switch_matrix),
                        "gain": str(gain),
                        "input": "0",
                    },
                },
            )
            data = {
                "recording_XML": recording_xml,
                "reset": "False",
                "default_values": "False",
            }
            try:
                response = requests.post(
                    url + "recording_settings",
                    json=data,
                    timeout=5,
                )
                if handle_response(response, "Recording settings uploaded"):
                    pass
            except requests.exceptions.Timeout:
                sg.popup_ok("Connection to ViperBox timed out, is the ViperBox busy?")
        elif event == "upload_stimulation_settings":
            values = convert_anodic_cathodic(values)
            electrode_list = get_electrodes(electrode_switch_matrix)
            if electrode_list is None:
                sg.popup_ok("At least one electrode needs to be selected")
                continue
            stimulation_xml = to_settings_xml_string(
                settings_input={
                    "Configuration": {
                        "box": "-",
                        "probe": "-",
                        "stimunit": "1",
                        "polarity": str(values["anodic_cathodic"]),
                        "pulses": str(values["number_of_pulses"]),
                        "prephase": str(values["pulse_delay"]),
                        "amplitude1": str(values["pulse_amplitude_anode"]),
                        "width1": str(values["first_pulse_phase_width"]),
                        "interphase": str(values["pulse_interphase_interval"]),
                        "amplitude2": str(values["pulse_amplitude_cathode"]),
                        "width2": str(values["second_pulse_phase_width"]),
                        "discharge": str(values["discharge_time"]),
                        "duration": str(values["pulse_duration"]),
                        "aftertrain": str(values["discharge_time_extra"]),
                    },
                    "Mapping": {
                        "box": "-",
                        "probe": "-",
                        "stimunit": "1",
                        "electrodes": electrode_list,
                    },
                },
            )
            data = {
                "stimulation_XML": stimulation_xml,
                "reset": "False",
                "default_values": "False",
            }
            try:
                response = requests.post(
                    url + "stimulation_settings",
                    json=data,
                    timeout=5,
                )
                if handle_response(response, "Stimulation settings uploaded"):
                    pass
            except requests.exceptions.Timeout:
                sg.popup_ok("Connection to ViperBox timed out, is the ViperBox busy?")
        elif event == "upload_defaults":
            try:
                response = requests.post(url + "default_settings", timeout=5)
                if handle_response(response, "Default settings uploaded"):
                    pass
            except requests.exceptions.Timeout:
                sg.popup_ok("Connection to ViperBox timed out, is the ViperBox busy?")
        elif event.endswith("+FOCUS OUT"):
            event = event.split("+")[0]
            values = convert_anodic_cathodic(values)
            settings_input = {
                gui_start_vals[event][1]: str(values[event]),
            }
            data = {"dictionary": settings_input, "XML": "", "check_topic": "all"}
            try:
                response = requests.post(url + "verify_xml", json=data, timeout=0.5)
                if handle_response(
                    response,
                    f"Successfully checked waveform parameter {event}",
                ):
                    pass
                else:
                    window[event].update(value=gui_start_vals[event][0])
            except requests.exceptions.Timeout:
                sg.popup_ok("Connection to ViperBox timed out, is the ViperBox busy?")
        elif event == "Update":
            if sg.popup_ok_cancel("Are you sure? This will close the application."):
                if not os.path.exists("update_blocker"):
                    logger.error("Update requested")
                    subprocess.Popen(
                        batch_script_path,
                        shell=True,
                        stdin=None,
                        stdout=None,
                        stderr=None,
                        close_fds=True,
                        creationflags=subprocess.DETACHED_PROCESS,
                    )
                    try:
                        _ = requests.put(
                            "http://localhost:37497/api/status",
                            json={"mode": "IDLE"},
                        )
                        _ = requests.put(
                            "http://localhost:37497/api/window",
                            json={"command": "quit"},
                            timeout=1,
                        )
                    except requests.exceptions.RequestException:
                        pass
                    _ = requests.post(url + "disconnect", timeout=1)
                    time.sleep(0.5)
                    _ = requests.post(url + "kill", timeout=1)
                    logger.info("Closing GUI")
                    break
                else:
                    sg.popup_ok("Update is blocked")
        else:
            logger.info(f"Unknown event happened: {event}")


if __name__ == "__main__":
    run_gui()
