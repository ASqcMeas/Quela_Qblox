import os, sys, time, inspect, tomli
from Modularize.Association.MainBrain import Exp_Encyclopedia
from Modularize.Association.Housekeeper import Maid
from numpy import linspace, arange, ndarray
from types import FunctionType
from functools import partial

user = os.getlogin()
user_dep_config_folder = rf"C:/Users/{user}/MeasConfigs" # should all ways one file which name as "S?_ExpParasSurvey.toml"
machine_IP_table = r"C:\ExpMachineIP\MachineIP_rec.toml"

def owned_attribute(obj, attr):
    return hasattr(obj, attr) and attr in obj.__dict__


class Canvasser(Exp_Encyclopedia):
    def __init__(self,exp_type:str, target_qs:list):
        self.__exp_type__:str=exp_type
        self.__exp_target_qs__:list = target_qs

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
        super().__init__(self.__exp_type__)
        # Get all attributes of the class excluding built-in ones
        attributes = [name for name, _ in inspect.getmembers(self) if not name.startswith("__")]
        exclude_attrs = []
        attributes = [attr for attr in attributes if attr not in exclude_attrs]
        # Open a file to write the toml content
        self.__file_path__=f"{self.__exp_type__}_{self.__SurveyUniqueName__}.toml"
        with open(self.__file_path__, "w") as file:
            # For each target (q0 and q1), create a section with the same attributes
            file.write("# Measurement paras configs editor\n\n")
            if len(self.__exp_target_qs__) != 0:
                for attribute in self.__shared_attr__:
                    if owned_attribute(self, attribute):
                        if type(getattr(self, attribute)) == str:
                            file.write(f"{attribute} = '  ' # type in str \n")
                        elif type(getattr(self, attribute)) == FunctionType:
                            file.write(f"{attribute} = '  ' # linspace or arange \n")
                        else:
                            file.write(f"{attribute} =        # type in  { type(getattr(self, attribute))}\n")
                file.write("\n")
           
                for target in self.__exp_target_qs__:
                    file.write(f'[{target}]\n')  # Create a section for each target
                    for attribute in attributes:
                        if attribute not in self.__shared_attr__:
                            if type(getattr(self, attribute)) == str:
                                file.write(f"{attribute} = '  ' # type in str \n")
                            else:
                                file.write(f"  {attribute} =        # type in {type(getattr(self, attribute)) if type(getattr(self, attribute)) != list else 'list, rule: [ start, end, pts ] or [ fixed value ]'}\n")  # Inline comments
                            file.write("\n")  #
                    file.write("\n")  # Add a blank line between sections for readability
            else:
                for attribute in attributes:
                    if attribute not in self.__shared_attr__:
                        if type(getattr(self, attribute)) == str:
                            file.write(f"{attribute} = '  ' # type in str \n")
                        else:
                            file.write(f"{attribute} =        # type in {type(getattr(self, attribute)) if type(getattr(self, attribute)) != list else 'list, rule: [ start, end, pts ] or [ fixed value ]'}\n")  # Inline comments
                        file.write("\n")  #

    def __toml_decoder__(self,survey_path:str):
        # Load exp parameters from TOML file
        with open(survey_path, "rb") as file:
            toml_data = tomli.load(file)
        
        self.__exp_type__ = os.path.split(survey_path)[-1].split("_")[0]
        
        #! Get parameters
        self.__assined_paras__ = {}
        # Assign values to object attributes
        # Dynamically create attributes for each section in the TOML data
        for section, attributes in toml_data.items():
            self.__assined_paras__[section] = attributes

        if self.__exp_type__.lower() != 's0':
            #! Determine the instruments according to the given IP
            self.__exp_machine_type__:str = ""   # should be "Qblox" or "QM"
            with open(machine_IP_table, "rb") as file:
                machine_IPs = tomli.load(file)
            for IP, Machine_type in machine_IPs.items():
                if IP == self.__assined_paras__["machine_IP"].replace(" ",""):
                    self.__exp_machine_type__ = Machine_type.replace(" ","")
                
            if self.__exp_machine_type__ == "" :
                raise ValueError(f"Unknown machine IP was given = {self.__assined_paras__['machine_IP']}")
            print(f"Trying to use {self.__exp_machine_type__} to do the exp.")
            
            #! Trying to build up ro_elements for meas
            super().__init__(self.__exp_type__, self.__exp_machine_type__)   
            Paras_attr = [name for name, _ in inspect.getmembers(self) if (not name.startswith("__")) and (name not in self.__shared_attr__)]
            joint_qbs = [item for item in self.__assined_paras__ if item not in self.__shared_attr__]
            if "list_sampling_func" in self.__assined_paras__ and self.__assined_paras__["list_sampling_func"].replace(" ","") in ["linspace", "arange"]: sampling_func = eval(self.__assined_paras__["list_sampling_func"])
            else: sampling_func = linspace
            ro_elements = self.__buildROelements__(Paras_attr, joint_qbs,sampling_func)

            return ro_elements
        
        
    
    
    def __buildROelements__(self,attrs:list,joint_qubits:list,sampling_func:callable=None):
        if sampling_func is None: sampling_func = linspace
        match self.__exp_machine_type__.lower():
            case "qblox":
                kwargs_dict = {}
                for attr in attrs:
                    kwargs_dict[attr] = {}
                    for q in joint_qubits:
                        kwargs_dict[attr][q] = self.__assined_paras__[q][attr]
                sampler = partial(self.__listTypePara_decoder__, generate_samples_function =sampling_func)
                ro_elements = self.__CoordsDecode__(self.__ro_elements_coords__,joint_qubits,sampler,**kwargs_dict)
            case "qm":
                pass

            case "_":
                raise TypeError(f"Unsupported instrumenet type = {self.__exp_machine_type__}")

        return ro_elements


        
if __name__ == "__main__":

    # Create meas parameters survey
    # Survey = Canvasser('S0', [])
    # Survey.__generate_ExpParas_servey__()

    # get assigned meas parameters
    Survey = Canvasser("",[])
    Survey.__toml_decoder__(r"c:\Users\ASqcm\MeasConfigs\S0_ExpParasSurvey.toml")
    maid = Maid(Survey.__assined_paras__,True)
    # Survey.__toml_decoder__(r"C:\Users\ASqcm\MeasConfigs\S1_ExpParasSurvey.toml")

