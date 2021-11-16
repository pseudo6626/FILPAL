# FILPAL is a filament parameter calibration, storage, and injection system for klipper programs
#
# Copyright (C) 2016-2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import math, os, logging, ast, configparser
#from . import tuning_tower

class FILPAL:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        try:
             self.params_path=self.printer.getstring("filament_parameters_file_location:")
             self.params_file=os.path.expanduser(self.params_path)
        except:
            raise config.error("cannot locate filament parameters file")
        sd = config.get('path')
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd))
        sd = config.get('path')
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd))
        self.cali_files=os.listdir(self.sdcard_dirname)
        self.fila ={}
        varfile = configparser.ConfigParser()
        try:
            varfile.read(self.params_file)
            if varfile.has_section('Loaded'):
                if varfile.has_section(varfile["Loaded"]["fila_ID"]):
                    for name, val in varfile.items('Variables'):
                        self.fila[name] = ast.literal_eval(val)    
        except:
            msg = "Unable to parse Loaded Filament paramters. Please run FILPAL_LOAD or update the parameters file"
            logging.exception(msg)
            raise self.printer.command_error(msg)

        self.gcode.register_command('FILPAL_CALIBRATE', self.cmd_FILPAL_CALIBRATE, desc=self.cmd_FILPAL_CALIBRATE_help)
        cmd_FILPAL_CALIBRATE_help = "Runs calibration tests for filament parameters"
        self.gcode.register_command('FILPAL_PARSE', self.cmd_FILPAL_CONVERTER, desc=self.cmd_FILPAL_CONVERTER_help)
        cmd_FILPAL_CONVERTER_help = "Converts gcode files and inserts a conversion key at top of file"
        self.gcode.register_command('FILPAL_INJECTOR', self.cmd_FILPAL_INJECTOR, desc=self.cmd_FILPAL_INJECTOR_help)
        cmd_FILPAL_INJECTOR_help = "Runs converted gcode files and acts as a middle man for the commands"
        self.gcode.register_command('FILPAL_UPDATER', self.cmd_FILPAL_UPDATER, desc=self.cmd_FILPAL_UPDATER_help)
        cmd_FILPAL_UPDATER_help = "Updates your fil.pal file with new parameter settings for a given plastic."

    def cmd_FILPAL_CALIBRATE(self, gcmd):  #this command is used by filpal to run calibration tests for the different filament parameters it can regulate
        test = gcmd.get('TEST')
        if test+".gcode" not in self.cali_files:
            raise gcmd.error("cannot locate calibration file for this test")
        else:
            try:
                tester(self,test,gcmd)
            except:
                raise gcmd.error("test not found as written. Check spelling")
        
    def tester(self, test, gcmd):
        tests_list=["extruder_temp","bed_temp","z_offset","flowrate","fan_speed","retraction"]
        
        if test == "extruder_temp":
            tmin=gcmd.get("MIN",self.fila['hotend_min_temp'])
            tmax=gcmd.get("MAX",self.fila['hotend_max_temp'])
            fil_type=gcmd.get("TYPE",self.fila['filament_type'])
            if test+"_"+fil_type+".gcode" in self.cali_files:
                test+"_"+fil_type+".gcode"
            else:
                test=test+".gcode"
            bands=gcmd.get("MIN",10)
            factor= -(tmax-tmin)/(bands*10)
            start= tmax+5*(-factor)
            self.gcode.run_script_from_command("TUNING_TOWER COMMAND='SET_HEATER_TEMPERATURE HEATER=extruder' PARAMETER=TARGET START=%d FACTOR=%f BAND=%d" % (start,factor,bands))
            self.gcode.run_script_from_command("SDCARD_PRINT_FILE FILENAME=%s" % (test))
            self.gcode.respond_info("Once the calibration print is completed, use the FILPAL_UPDATER to record the new value for extruder_temp (and extruder_temp_initial if applicable)")

        #if test == "z_offset":




    def cmd_FILPAL_SWAP(self, gcmd): #this command is used by filpal to swap between filaments
        un_bool=gcmd.get("UNLOAD",True)
        load_name=gcmd.get("LOAD",False)
        load_temp=gcmd.get("LOAD_TEMP",False)
        un_temp=gcmd.getint("UNLOAD_TEMP",False)
        if load_name != False and load_temp == False:
            try:
                fila=cmd_FILPAL_UPDATER(self,{"lookup":True,"FILA_ID":load_name})
                if "hotend_temp" in fila:
                    load_temp=int(fila["hotend_temp"])
            except:
                msg = "New Filament does not have 'hotend_temp' defined. Please run FILPAL_LOAD or update the parameters file"
                logging.exception(msg)
                raise self.printer.command_error(msg)
        elif un_bool:
            try:
                fila=cmd_FILPAL_UPDATER(self,{"lookup":True})
                if "hotend_temp" in fila:
                    un_temp=int(fila["hotend_temp"])
            except:
                msg = "Loaded Filament does not have 'hotend_temp' defined. Please run FILPAL_LOAD or update the parameters file"
                logging.exception(msg)
                raise self.printer.command_error(msg)
        heater_name=gcmd.get("HEATER")
        pheaters = self.printer.lookup_object('heaters')
        try:
            heater = pheaters.lookup_heater(heater_name)
        except self.printer.config_error as e:
            raise gcmd.error(str(e))
        self.gcode.run_script_from_command("SET_HEATER_TEMPERATURE HEATER=%s TARGET=%d" % (heater_name,un_temp))
        curtemp=0
        while curtemp < un_temp:
            temp_call=heater.get_temp(self,self.eventtime)
            curtemp=temp_call[0]
        self.gcode.run_script_from_command("G1 F100 E1")
        self.gcode.run_script_from_command("G1 F1000 E-500")

        if load_temp != False:
            self.gcode.run_script_from_command("SET_HEATER_TEMPERATURE HEATER=%s TARGET=%d" % (heater_name,load_temp))
            self.gcode.respond_info("Insert new filament and use command LOAD_CONTUNUE when ready to extrude")
            self.gcode.register_command('LOAD_CONTINUE', self.cmd_LOAD_CONTINUE, desc=self.cmd_LOAD_CONTINUE_help)
            cmd_LOAD_CONTINUE_help = "contiunues the filament load of FILPAL_SWAP"
            def cmd_LOAD_CONTINUE(self,gcmd):
                self.gcode.run_script_from_command("G1 F100 E500")
                #add code to update the current loaded fillament in fil.pal file


    def cmd_FILPAL_CONVERTER(self, gcmd): #this command is used by filpal to parse through an existing gcode file and pull all of the numerical values associated with specfifc gcode commands. It then adds a line at the start of the gcode with a dictionary of these values
        SD


    def cmd_FILPAL_INJECTOR(self, gcmd):  #This command is used by filpal to intercept specific commands from the gcode and modify their numerical values using the dictionary before passing them on to klipper propper
        SDFSFF

    def cmd_FILPAL_UPDATER(self, gcmd):  #this command is used to update the parameter values in fil.pal for the loaded filament. Also can create new parameters if in the accepted list
        fila ={}
        fil_id=gcmd.get("FILA_ID",False)
        allowed_params=["hotend_min_temp","hotend_max_temp","hotend_initial_temp","hotend_temp","retraction","fan_min","fan_max","z_offset","filament_type","flowrate"]
        if gcmd.get("lookup") != True:    
            param=gcmd.get("PARAM",False)
            param_val=gcmd.getfloat("VALUE",False)
            params_raw=gcmd.get("PARAMS",False)
            params=ast.literal_eval(params_raw)
        varfile = configparser.ConfigParser()
        try:
            f=open(self.params_file)
            varfile.read(self.params_file)
            f.close()
            if varfile.has_section('loaded'):
                if fil_id == False:
                    id=ast.literal_eval(varfile["loaded"]["fila_id"])
                else:
                    id=ast.literal_eval(fil_id)
                if varfile.has_section(id):
                    for name, val in varfile.items(id):
                        fila[name]=ast.literal_eval(val)  
                else:
                    msg = "Unable to parse Loaded Filament paramters. Please run FILPAL_LOAD or update the parameters file"
                    logging.exception(msg)
                    raise self.printer.command_error(msg)
        except:
            msg = "Unable to parse Loaded Filament paramters. Please run FILPAL_LOAD or update the parameters file"
            logging.exception(msg)
            raise self.printer.command_error(msg)

        if gcmd =="lookup":
            return fila

        if params:
            for paras in params:
                if paras in fila:
                    varfile.set(id,paras,str(params[paras]))
                elif paras in allowed_params:
                    varfile.set(id,paras,str(params[paras]))
                else:
                    msg = "The parameter %s is not recognized. Please check spelling" % (paras)
                    logging.exception(msg)
                    raise self.printer.command_error(msg)
        if param:
            if param in fila:
                varfile.set(id,param,str(param_val))  #this isnt the correct way to update the file. need to write to actual file
            elif param in allowed_params:
                varfile.set(id,param,str(param_val))
            else:
                msg = "The parameter %s is not recognized. Please check spelling" % (param)
                logging.exception(msg)
                raise self.printer.command_error(msg)            
        f=open(self.params_file,"w")
        varfile.write(f)
        f.close()

def load_config(config):
    return FILPAL(config)
