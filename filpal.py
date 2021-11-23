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
             self.params_path=self.printer.getstring("filament_parameters_file_location")
             self.params_file=os.path.expanduser(self.params_path)
        except:
            raise config.error("cannot locate filament parameters file")
        try:
             self.parse_commands=self.printer.get("parse_commands")
             self.parse_commands=ast.literal_eval(self.parse_commands)
        except:
            raise config.error("cannot locate parse_commands dict or dict is not formatted correctly")
        sd = config.get('path')
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd))
        self.cali_files=os.listdir(self.sdcard_dirname)
        self.coeffs=[]
        self.controller=[]
#        self.fila ={}
#        varfile = configparser.ConfigParser()
#        try:
#            varfile.read(self.params_file)
#            if varfile.has_section('Loaded'):
#                if varfile.has_section(varfile["Loaded"]["fila_ID"]):
#                    for name, val in varfile.items('Variables'):
#                        self.fila[name] = ast.literal_eval(val)    
#        except:
#            msg = "Unable to parse Loaded Filament paramters. Please run FILPAL_LOAD or update the parameters file"
#            logging.exception(msg)
#            raise self.printer.command_error(msg)

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
        self.load_name=gcmd.get("LOAD",False)
        load_temp=gcmd.get("LOAD_TEMP",False)
        un_temp=gcmd.getint("UNLOAD_TEMP",False)
        if self.load_name != False and load_temp == False:
            try:
                fila=cmd_FILPAL_UPDATER(self,{"lookup":True,"FILA_ID":self.load_name})
                if "M104" in fila:
                    load_temp=int(fila["M104"]["S"][math.floor(len(fila["M104"]["s"])/2)])
            except:
                msg = "New Filament does not have 'hotend_temp' defined. Please run FILPAL_LOAD or update the parameters file"
                logging.exception(msg)
                raise self.printer.command_error(msg)
        elif un_bool:
            try:
                fila=cmd_FILPAL_UPDATER(self,{"lookup":True})
                if "M104" in fila:
                    un_temp=int(fila["M104"]["S"][math.floor(len(fila["M104"]["s"])/2)])
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
        self.gcode.run_script_from_command("TEMPERATURE_WAIT SENSOR=%s MINIMUM=%d" % (heater_name,un_temp))
        self.gcode.run_script_from_command("G1 F100 E1")
        self.gcode.run_script_from_command("G1 F1000 E-500")

        if load_temp != False:
            cmd_FILPAL_UPDATER(self, {"NEW_LOAD":self.load_name})
            self.gcode.run_script_from_command("SET_HEATER_TEMPERATURE HEATER=%s TARGET=%d" % (heater_name,load_temp))
            self.gcode.respond_info("Insert new filament and use command LOAD_CONTUNUE when ready to extrude")
            self.gcode.register_command('LOAD_CONTINUE', self.cmd_LOAD_CONTINUE, desc=self.cmd_LOAD_CONTINUE_help)
            cmd_LOAD_CONTINUE_help = "contiunues the filament load of FILPAL_SWAP"
            def cmd_LOAD_CONTINUE(self,gcmd):
                self.gcode.run_script_from_command("G1 F100 E500")

                


    def cmd_FILPAL_PARSER(self, gcmd): #this command is used by filpal to parse through an existing gcode file and pull all of the numerical values associated with specfifc gcode commands. It then adds a line at the start of the gcode with a dictionary of these values
        filename=gcmd.get("FILE_NAME",False)
        fname = os.path.join(self.sdcard_dirname, filename.lower())
        fs = open(fname, 'r')
        trycodes=[]
        
        try:
            list_of_lines = fs.readlines()
            if ";PARSED" not in list_of_lines[0]:
                for command in self.parse_commands:
	                trycodes.append({"command" : command})
                for l in range(len(trycodes)):
                    for z in enumerate(list_of_lines):
                        if trycodes[l]["command"] in z[1]:
                            lineparams=z[1].split()
                            for m in range(len(lineparams)-1):
                                if lineparams[m+1][0] in trycodes[l].keys():
                                    trycodes[l][lineparams[m+1][0]].append(float(lineparams[m+1][1:]))
                                    trycodes[l][lineparams[m+1][0]].sort()
                                else:
                                    trycodes[l].update({lineparams[m+1][0] : [float(lineparams[m+1][1:])]})
                        elif "START_PRINT" in z[1]:
                            start_line=z[0]
                list_of_lines[0]=list_of_lines[0].split("\n")[0]+" ;PARSED\n"
                list_of_lines[start_line]=list_of_lines[start_line].split("\n")[0]+" parse_vals="+str(trycodes)+"\n"
                newvers=open(fname,"w")
                newvers.writelines(list_of_lines)
                newvers.close
            else:
                raise self.printer.command_error("File already Parsed")
            f = open(fname, 'rb')
            f.seek(0, os.SEEK_END)
            fsize = f.tell()
            f.seek(0)
        except:
            logging.exception("virtual_sdcard file open")
            raise gcmd.error(lineparams)
        gcmd.respond_raw("File opened:%s Parse Success" % (filename))


    def cmd_FILPAL_INJECTOR(self, gcmd):  #This command is used by filpal to intercept specific commands from the gcode and modify their numerical values using the dictionary before passing them on to klipper propper
        inj_list=self.parse_commands
        fila=cmd_FILPAL_UPDATER(self,{"lookup":True})
        stored=[]
        self.coeffs=[]
        try:
            parse_vals=gcmd.get('parse_vals')
            parse_vals=ast.literal_eval(parse_vals)
        except:
            msg = "Unable to retrieve file parse values"
            logging.exception(msg)
            raise self.printer.command_error(msg)
        for i in inj_list:
            if i in fila:
                stored.append([i,fila[i]])
            for j in parse_vals:
                if parse_vals[j]['command'] == i and inj_list[i] == True:
                    for k in parse_vals[j]:
                        if k in fila[i]:
                            stored[-1].append(parse_vals[k])
        for l in stored:
            self.coeffs.append=[l[0],curve_fit(l[1]['S'],l[2]['S'])]

            if l[0] == "M104" or "M109":
                heater = self.printer.lookup_object('toolhead').get_extruder().get_heater()
                old=heater.set_control("placehold")
                heater.set_control(filpal_hotend_controller(self,old,self.coeffs[-1]))
                class filpal_hotend_controller:
                    def __init__(self,old_control,coeff):
                        self.old_controller=old_control
                        self.coeff=coeff
                    
                    def temperature_update(self, read_time, temp, target_temp):
                        new_target=self.coeff[0]+self.coeff[1]*target_temp+self.coeff[2]*target_temp*target_temp
                        self.old_controller.temperature_update(self, read_time, temp, new_target)

                    def check_busy(self, eventtime, smoothed_temp, target_temp):
                        self.old_controller.check_busy(self, eventtime, smoothed_temp, target_temp)
                    
                    def reset(self):
                        return self.old_controller

        #switch statements for each command to create a new control class for each as formatted in Klipper
        #make another function called in END_GCODE to revert controllers back to normal

    def cmd_FILPAL_UPDATER(self, gcmd):  #this command is used to update the parameter values in fil.pal for the loaded filament. Also can create new parameters if in the accepted list
        fila ={}
        fil_id=gcmd.get("FILA_ID",False)
        new_load=gcmd.get("NEW_LOAD",False)
        allowed_params=["M104","M140","retraction","fan_min","fan_max","z_offset","filament_type","flowrate"]
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
                if new_load:
                    varfile.set("loaded","fila_id",str(new_load))
                    if varfile.has_section(str(new_load)) ==False:
                        varfile.add_section(str(new_load))
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
                varfile.set(id,param,str(param_val))  
            elif param in allowed_params:
                varfile.set(id,param,str(param_val))
            else:
                msg = "The parameter %s is not recognized. Please check spelling" % (param)
                logging.exception(msg)
                raise self.printer.command_error(msg)            
        f=open(self.params_file,"w")
        varfile.write(f)
        f.close()


    def curve_fit(self,stored_data,raw_data):
        raw=raw_data.sort()
        stored=stored_data.sort()
        c0=0
        c1=0
        c2=0

        if len(stored) == 1 or len(raw) == 1:
            raw_mid=math.floor(len(raw)/2)
            stored_mid=math.floor(len(stored)/2)
            c1=stored[stored_mid]/raw[raw_mid]
    
        elif len(stored) == 2:
	        for i in range(0,len(stored)-1):
		        c1=(stored[i+1]-stored[i])/(raw[i+1]-raw[i])
                c0=stored[0]-c1*raw[0]
        elif len(stored) == 3 and len(raw) < 3:
	        for i in range(0,len(raw)-1):
		        c1=(stored[i+1]-stored[i])/(raw[i+1]-raw[i])
                c0=stored[0]-c1*raw[0]
        elif len(stored) == 3 and len(raw) >=3:
            n=3
            x1=raw[0]+raw[1]+raw[2]
            x2=raw[0]**2+raw[1]**2+raw[2]**2
            x3=raw[0]**3+raw[1]**3+raw[2]**3
            x4=raw[0]**4+raw[1]**4+raw[2]**4
            y1=stored[0]+stored[1]+stored[2]
            x1y1=stored[0]*raw[0]+stored[1]*raw[1]+stored[2]*raw[2]
            x2y1=stored[0]*raw[0]*raw[0]+stored[1]*raw[1]*raw[1]+stored[2]*raw[2]*raw[2]
            det=n*(x2*x4-x3*x3)-x1*(x1*x4-x3*x2)+x2*(x1*x3-x2*x2)
            if det != 0:
                m11=x2*x4-x3*x3
                m12=x3*x2-x1*x4
                m13=x1*x3-x2*x2
                m21=x2*x3-x1*x4
                m22=n*x4-x2*x2
                m23=x1*x2-n*x3
                m31=x1*x3-x2*x2
                m32=x2*x1-n*x3
                m33=n*x2-x1*x1
                m11=m11/det
                m12=m12/det
                m13=m13/det
                m21=m21/det
                m22=m22/det
                m23=m23/det
                m31=m31/det
                m32=m32/det
                m33=m33/det
                c0=m11*y1+m12*x1y1+m13*x2y1
                c1=m21*y1+m22*x1y1+m23*x2y1
                c2=m31*y1+m32*x1y1+m33*x2y1 
        return c0,c1,c2


def load_config(config):
    return FILPAL(config)
