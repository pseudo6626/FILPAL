# FILPAL

FILPAL is a klipper enviroment comprised of macros, modified python files, and stored gcode files which collectively allow klipper to calibrate and store filament specific parameters on the machine side of the printing workflow. This allows klipper to automatically adjust firmware and print settings for sliced gcode, superceding those in the gcode. Parameters that FILPAL can calibrate, record, and inject includes:

- **Temperature** (bed, hotend, as well as varying temperatures such as initial layer temps)
- **Fan Speeds** (again, with varying speeds adjusted accordingly)
- **Z offset** (for plastics which require different levels of "squish")
- **Flowrate** (see caviats for details, but TLDR requires slicer flowrate to be set to 100% to work properly)
- **Retraction** (provided firmware retraction is enabled)


In addition to storing and injecting this information, FILPAL allows for onboard calibration of the above parameters *without any slicing needed*.  This is due to presliced calibration files stored in the Klipper Pi itself that can be called/started from the klipper command prompt. 

Finally, FILPAL also comes with prebuilt macros for Nozzle Swaps and Filament Loading/Unloading. (the latter is how FILPAL knows which plastic is currently being used). 


Why use FILPAL? 

1) Allowing Klipper to calibrate and store settings of the printer is one of it's major attractions. This is already done for PID and Input Shaper. If one allows filament to be considered part of the machine system, then it is only natural that calibration and storage of filament related parameters be a task handled by the firmware. 

2) By removing filament specific parameters from the slicers, it allows for much greater freedom of slicer usage. No longer is there the inertia of "cura would handle these supports better but it is too much of a hassle to create a profile for this filament". Instead just slice ignoring all filament settings and then let FILPAL inject all the necessary values! Slicers become just that, slicers. 

3) You no longer have to remember to adjust settings between plastic, or rather never have the frustrating of forgetting until halfway through a print!


FILPAL is currently under development. Further documentation and installation instructions will be added once it is up and opperational. 

