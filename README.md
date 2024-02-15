# 🧠 ViperBoxInterface
<figure align="center">
    <img src="imgs\viperboxinterface.png" style="width: 50%; height: auto;">
    <!-- <figcaption>Overview of all the settings for one ViperBox</figcaption> -->
</figure>


> ViperBoxInterface is a piece of software that streamlines interaction with the ViperBox developed for the NeuraViPeR project.
> It streams data through [Open Ephys](#open-ephys).

# 📚 Table of Contents
<!-- TOC -->

- [🧠 ViperBoxInterface](#-viperboxinterface)
- [📚 Table of Contents](#-table-of-contents)
- [📦 Installation](#-installation)
    - [Starting up](#starting-up)
- [🔥 Using the API](#-using-the-api)
- [🛠️ Overview of ViperBox settings](#-overview-of-viperbox-settings)
- [📝 XML scripts](#-xml-scripts)
    - [RecordingSettings](#recordingsettings)
    - [Stimulation settings](#stimulation-settings)
- [👨‍💻 Related software](#%E2%80%8D-related-software)
    - [Open Ephys](#open-ephys)
    - [Anaconda](#anaconda)
    - [Git](#git)

<!-- /TOC -->


# 📦 Installation

The computer needs to run Windows 64-bit.

Installation instructions:
1. Download the files
Open Windows Powershell (Windows key, then type Windows Powershell)
    1. type `cd Downloads` to navigate to the downloads folder. If you prefer, you can also choose `cd Documents`. This is the location where the installation will be performed.
    2. copy+paste this into the powershell: `curl.exe -L https://github.com/sbalk/ViperBoxInterface/archive/dev.zip --output viperboxinterface.zip`
2. Run the installation script
    1. Navigate to the folder you chose in step 1.1
    2. unzip viperboxinterface.zip
    3. navigate to the folder called 'setup'
    4. right-click 'installation_script.ps1' > 'Run with PowerShell'


## Starting up
The script creates a shortcut on the desktop called "ViperBoxAPI", this will start the software.

Alternatively, you can start the software by navigating to the folder where the software is downloaded and double-click start_app.bat.

After starting up, you have access to the API functionality from http://127.0.0.1:8000.

# 🔥 Using the API

The API can be used to communicate with the ViperBox. It can be used to connect to the ViperBox, upload recording and stimulation settings and start and stop recordings and stimulations.
The API can be manually controlled from the web interface by clicking the dropdown next to the function, then clicking "Try it out" and then clicking the blue "Execute" button.
The typical workflow to do a recording and stimulation is to run the following commands:
- `/connect`: to connect to the ViperBox
<figure align="center">
    <img src="imgs\connect.gif" style="width: 100%; height: auto;">
    <!-- <figcaption>Overview of all the settings for one ViperBox</figcaption> -->
</figure>

- `/upload_recording_settings`: to upload the recording settings. Default [XML settings](#xml-scripts) are selected by default.
    - To edit the settings, open an editor and copy the default settings from the defaults folder into it. Adjust them and copy and paste everything into the ViperBox API. See below.
<figure align="center">
    <img src="imgs\recording_settings.gif" style="width: 100%; height: auto;">
    <!-- <figcaption>Overview of all the settings for one ViperBox</figcaption> -->
</figure>

- `/upload_stimulation_settings`: to upload the stimulation settings. Default settings are selected by default. XML settings can be added here, too.
- `/start_recording`: to start the recording. Don't forget to give up a name.
- `/start_stimulation`: to start the stimulation.
- `/stop_recording`: to stop the recording. The recording will be saved in the Recordings folder. The settings that you used to record will be saved in the Settings folder under the same name but as XML file.

During a recording, new stimulation settings can be uploaded and a new stimulation can be started.

> **IMPORTANT**: There is a problem with the driver that is necassary to connect to the ViperBox. An incompatible driver is installed automatically overnight. Every time you start the ViperBoxInterface, you need to reinstall the driver. This can be done by following these steps:
> 1.	Connect ViperBox to PC and power on
> 2.	Navigate to setup/DowngradeFTDI, and run the downgrade.bat batch file
> 3.	Power cycle ViperBox
> 4.	Optionally: verify driver version in Device Manager


# 🛠️ Overview of ViperBox settings

<figure align="center">
    <img src="imgs\settings_mindmap.png" style="width: 100%; height: auto;">
    <figcaption>Overview of all the settings for one ViperBox</figcaption>
</figure>

- box: there are up to 3 boxes
- probes: each box can have up to 4 probes connected to them
- stimunit waveform settings: define the waveform that the stimunit generates
- stimunit connected electrodes: each stimunit can be connected to any or all of the 128 electrodes.
- recording channels: each box has 64 recording channels that each have several settings 

# 📝 XML scripts
The way to communicate settings with the ViperBox is through XML scripts. These scripts can be used to define settings and to start and stop recording and stimulation. The XML scripts can be sent to the ViperBox through the API.

## RecordingSettings
Here is an example for setting the recording settings in XML format. The default recording settings are the following:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Program>
    <Settings>
        <RecordingSettings>
            <Channel box="-" probe="-" channel="-" references="-" gain="1" input="0"/>
        </RecordingSettings>
    </Settings>
</Program>
```
In the above code, the default recording settings are stored in the `Channel` element. The first part defines for which component the settings are meant, the second part describes the settings. 
- `box="-"` means for all boxes that are connected.
- `probe="-"` means for all probes that are connected.
- `channel="-"` means for all recording channels (always 64).
- `references="-"` means all reference, this means the Body reference and references 1-8.
- `gain="1"` means the channel gain. The possible values are:
    - "0": x 60
    - "1": x 24
    - "2": x 12
    - "3": x 0.16
- `input="0"` means which electrode should be connected to the recording channel. Each of the 64 channels can be connected to 1 electrode. Furthermore, this electrode can be chosen from a subset of 4 of the total 128 electrodes. An updated mapping should be added to this repository for the use of the MZIPA.

<figure align="center">
    <img src="imgs\references.png" style="width: 50%; height: auto;">
    <figcaption>Connection of recording channel (left) with recording electrodes (top right) and references (bottom right)</figcaption>
</figure>

You can also specify the settings more precisely. For example, if you want recording channels 1, 6, 7 and 8 to have fewer references, namely only reference 'b' (body) and '3':
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Program>
    <Settings>
        <RecordingSettings>
            <Channel box="-" probe="-" channel="-" references="-" gain="1" input="0"/>
            <Channel box="-" probe="-" channel="1,6-8" references="b,3" gain="1" input="0"/>
        </RecordingSettings>
    </Settings>
</Program>
```
In the above case, the first line will be loaded to the ViperBox first and then the latter channel settings will be overwritten to the specific channels.

## Stimulation settings
The default stimulation settings are the following:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Program>
    <Settings>
        <StimulationWaveformSettings>
            <Configuration box="-" probe="-" stimunit="-" polarity="0" pulses="20" prephase="0"
                amplitude1="5" width1="170" interphase="60" amplitude2="5" width2="170"
                discharge="200" duration="600" aftertrain="1000" />
        </StimulationWaveformSettings>
        <StimulationMappingSettings>
            <Mapping box="-" probe="-" stimunit="-" electrodes="-" />
        </StimulationMappingSettings>
    </Settings>
</Program>
```
In StimulationWaveformSettings, `stimunit` means stimulation unit which is a waveform generator, there are 8 stimulation units per probe.
In StimulationMappingSettings, these stimulation units can be connected to any or all of the electrodes.

<figure>
    <img src="imgs\stimulation_timing.png" style="width: 90%; height: auto;">
    <figcaption align="center">Stimulation timing</figcaption>
</figure>

The possible parameters for the stimulation units are:

| Setting      | Description                                              | Unit    | Range     | Step size | Default |
| ------------ | -------------------------------------------------------- | ------- | --------- | --------- | ------- |
| `polarity`   | Polarity of the stimulation waveform                     | boolean | 0-1       | 1         | 0       |
| `pulses`     | Number of pulses in the waveform                         | number   | 1-255     | 1         | 20      |
| `prephase`   | Time in microseconds before the first pulse              | μs      | 100-25500 | 100       | 0       |
| `amplitude1` | Amplitude of the first phase                             | μA      | 0-255     | 1         | 5       |
| `width1`     | Width of the first phase                                 | μs      | 10-2550   | 10        | 170     |
| `interphase` | Time between the first and second phase                  | μs      | 10-25500  | 10        | 60      |
| `amplitude2` | Amplitude of the second phase                            | μA      | 0-255     | 1         | 5       |
| `width2`     | Width of the second phase                                | μs      | 10-2550   | 10        | 170     |
| `discharge`  | Time in microseconds after the last pulse                | μs      | 100-25500 | 100       | 200     |
| `duration`   | Duration of the entire train                             | μs      | 100-25500 | 100       | 600     |
| `aftertrain` | Time in microseconds after the entire train has finished | μs      | 100-25500 | 100       | 1000    |



<!-- ## XML control scripts
XML scripts can have full or partial control over the ViperBox. They can be used for:
- defining settings
- starting and stopping recording and stimulation

The format is as follows:
```xml
<Program>
    <Settings>
        <RecordingSettings>
            <Channel box="-" probe="-" channel="-" references="100000000" gain="1" input="0" />
        </RecordingSettings>
        <StimulationWaveformSettings>
            <Configuration box="-" probe="-" stimunit="-" polarity="0" pulses="20"
                prephase="0" amplitude1="1" width1="170" interphase="60" amplitude2="1" width2="170"
                discharge="200" duration="600" aftertrain="1000" />
        </StimulationWaveformSettings>
        <StimulationMappingSettings>
            <Mapping box="-" probe="-" stimunit="-" electrodes="-" />
        </StimulationMappingSettings>
    </Settings>
</Program>
```

As can be seen from the sample, at the highest level there is the program element. Below that there are settings or instructions. In settings there are RecordingSettings, StimulationWaveformSettings and StimulationMapping settings. -->


# 👨‍💻 Related software
## Open Ephys
ViperBoxInterface uses Open Ephys to show the recorded data. Please refer to the documentation 
of Open Ephys for instructions on how to use it. It has various possibilities to visualize and 
analyze the data. The documentation can be found [here](https://open-ephys.github.io/gui-docs/User-Manual/Exploring-the-user-interface.html).

## Anaconda
Anaconda is used to set up and run the Python environment that is needed for the 
ViperBoxInterface to run.

## Git
Git is used to download the latest version of the software.
