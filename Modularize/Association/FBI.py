import os, sys, time, inspect, tomli
from Association.Soul import Exp_Encyclopedia
from Modularize.Association.Housekeeper import Maid
from numpy import linspace, arange, ndarray
from types import FunctionType
from functools import partial

user = os.getlogin()
user_dep_config_folder = rf"C:/Users/{user}/MeasConfigs" # should all ways one file which name as "S?_ExpParasSurvey.toml"
machine_IP_table = r"C:\ExpMachineIP\MachineIP_rec.toml"

def owned_attribute(obj, attr):
    return hasattr(obj, attr) and attr in obj.__dict__


class Canvasser():
    def __init__(self,exp_type:str, target_qs:list):
        self.exp_type:str=exp_type
        self.exp_target_qs:list = target_qs if exp_type.lower() != 's0' else []

    def __listTypePara_decoder__(self,list_type_para:list,generate_samples_function:callable=None):
        if generate_samples_function is None: generate_samples_function = linspace
        match len(list_type_para):
            case 3:
                return generate_samples_function(*list_type_para)
            case 1:
                return list_type_para[0]
            case _:
                raise ValueError("Check your assigned paras in the toml, the list type para shoud be given in length = 1 or 3.")

        
    def __generate_ExpParas_servey__(self):
        self.brain = Exp_Encyclopedia(self.exp_type)
        # Get all attributes of the class excluding built-in ones
        attributes = [name for name, _ in inspect.getmembers(self.brain) if not name.startswith("__")]
        exclude_attrs = []
        attributes = [attr for attr in attributes if attr not in exclude_attrs]
        # Open a file to write the toml content
        self.file_path=f"{self.exp_type}_{self.brain.__SurveyUniqueName__}.toml"
        with open(self.file_path, "w") as file:
            # For each target (q0 and q1), create a section with the same attributes
            file.write("# Please avoid the space between your world, you can use '_' replace it if it's necessary.\n")
            file.write("# Measurement paras configs editor\n\n")
            if len(self.exp_target_qs) != 0:
                for attribute in self.brain.__shared_attr__:
                    if owned_attribute(self.brain, attribute):
                        if type(getattr(self.brain, attribute)) == str:
                            file.write(f"{attribute} = '  ' # type in str \n")
                        elif type(getattr(self.brain, attribute)) == FunctionType:
                            file.write(f"{attribute} = '  ' # linspace or arange \n")
                        else:
                            file.write(f"{attribute} =        # type in  { type(getattr(self.brain, attribute))}\n")
                file.write("\n")
           
                for target in self.exp_target_qs:
                    file.write(f'[{target}]\n')  # Create a section for each target
                    for attribute in attributes:
                        if attribute not in self.brain.__shared_attr__:
                            if type(getattr(self.brain, attribute)) == str:
                                file.write(f"{attribute} = '  ' # type in str \n")
                            else:
                                file.write(f"  {attribute} =        # type in {type(getattr(self.brain, attribute)) if type(getattr(self.brain, attribute)) != list else 'list, rule: [ start, end, pts ] or [ fixed value ]'}\n")  # Inline comments
                            file.write("\n")  #
                    file.write("\n")  # Add a blank line between sections for readability
            else:
                for attribute in attributes:
                    if attribute not in self.brain.__shared_attr__:
                        if type(getattr(self.brain, attribute)) == str:
                            file.write(f"{attribute} = '  ' # type in str \n")
                        else:
                            file.write(f"{attribute} =        # type in {type(getattr(self.brain, attribute)) if type(getattr(self.brain, attribute)) != list else 'list, rule: [ start, end, pts ] or [ fixed value ]'}\n")  # Inline comments
                        file.write("\n")  #

    def __toml_decoder__(self,survey_path:str=None):
        if survey_path is None:
            survey_path = [os.path.join(user_dep_config_folder,name) for name in os.listdir(user_dep_config_folder) if (os.path.isfile(os.path.join(user_dep_config_folder,name)) and name.split(".")[0].split("_")[-1]==Exp_Encyclopedia("").__SurveyUniqueName__)][0]

        # Load exp parameters from TOML file
        with open(survey_path, "rb") as file:
            toml_data = tomli.load(file)
        
        self.exp_type = os.path.split(survey_path)[-1].split("_")[0]
        
        #! Get parameters
        self.assigned_paras = {}
        
        # Assign values to object attributes
        # Dynamically create attributes for each section in the TOML data
        for section, attributes in toml_data.items():
            self.assigned_paras[section] = attributes
        
        if self.exp_type.lower() != 's0':
            #! Determine the instruments according to the given IP
            self.exp_machine_type:str = ""   # should be "Qblox" or "QM"
            with open(machine_IP_table, "rb") as file:
                machine_IPs = tomli.load(file)
            for IP, Machine_type in machine_IPs.items():
                if IP == self.assigned_paras["machine_IP"].replace(" ",""):
                    self.exp_machine_type = Machine_type.replace(" ","")
                
            if self.exp_machine_type == "" :
                raise ValueError(f"Unknown machine IP was given = {self.assined_paras['machine_IP']}")
            print(f"Trying to use {self.exp_machine_type} to do the exp.")
            
            #! Trying to build up ro_elements for meas
            self.brain = Exp_Encyclopedia(self.exp_type, self.exp_machine_type)   
            Paras_attr = [name for name, _ in inspect.getmembers(self.brain) if (not name.startswith("__")) and (name not in self.brain.__shared_attr__)]
            joint_qbs = [item for item in self.assigned_paras if item not in self.brain.__shared_attr__]
            if "list_sampling_func" in self.assigned_paras and self.assigned_paras["list_sampling_func"].replace(" ","") in ["linspace", "arange"]: sampling_func = eval(self.assigned_paras["list_sampling_func"])
            else: sampling_func = linspace
            
            # 3 main roles for Exp execution
            shared_settings = self.__buildGeneralSettings__()
            ro_elements = self.__buildROelements__(Paras_attr, joint_qbs, sampling_func)
            bias_elements = self.__buildZelements__() if self.brain.__bias_elements_coords__ != {} else {}

            return shared_settings, ro_elements, bias_elements
        
        
        
    def __buildGeneralSettings__(self):
        shared_settings = {}
        for item_name in self.assigned_paras:
            if item_name in self.brain.__shared_attr__:
                shared_settings[item_name] = self.assigned_paras[item_name]

        return shared_settings
    
    def __buildROelements__(self,attrs:list,joint_qubits:list,sampling_func:callable=None):
        if sampling_func is None: sampling_func = linspace
        match self.exp_machine_type.lower():
            case "qblox":
                kwargs_dict = {}
                for attr in attrs:
                    kwargs_dict[attr] = {}
                    for q in joint_qubits:

                        kwargs_dict[attr][q] = self.assigned_paras[q][attr]
                sampler = partial(self.__listTypePara_decoder__, generate_samples_function =sampling_func)
                ro_elements = self.brain.__CoordsDecode__(self.brain.__ro_elements_coords__,joint_qubits,sampler,**kwargs_dict)
            case "qm":
                pass

            case "_":
                raise TypeError(f"Unsupported instrumenet type = {self.exp_machine_type}")

        return ro_elements
    
    def __buildZelements__(self):
        #TODO 
        pass


        
if __name__ == "__main__":

    # Create meas parameters survey
    # Survey = Canvasser('S1', ['q0','q1'])
    # Survey.__generate_ExpParas_servey__()

    # get assigned meas parameters
    Survey = Canvasser("",[])
    # Survey.__toml_decoder__(r"c:\Users\ASqcm\MeasConfigs\S0_ExpParasSurvey.toml")
    # maid = Maid(Survey.__assined_paras__,True) # register a new sample
    # data_folder_path = maid.sample_data_folder # to be saved into your config or QD_file
    S1_main_roles = Survey.__toml_decoder__()
    print(S1_main_roles)

