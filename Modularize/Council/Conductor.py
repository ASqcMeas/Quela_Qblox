import os, tomli
from Modularize.Council.MainBrain import Exp_Encyclopedia
user = os.getlogin()
user_dep_config_folder = f"C:/Users/{user}/MeasConfigs" # should all ways one file which name as "S?_ExpParasSurvey.toml"

class Coordinator(Exp_Encyclopedia):
    def __init__(self, specific_config_path:str=None):
        super().__init__(exp_type="_")
        self.__toml_path__ =  [os.path.join(user_dep_config_folder,name) for name in os.listdir(user_dep_config_folder) if (os.path.isfile(os.path.join(user_dep_config_folder,name)) and name.split(".")[0].split("_")[-1]==self.__SurveyUniqueName__)][0] if specific_config_path is None else specific_config_path
        self.__toml_decoder__()

    
    def __toml_decoder__(self):
        # Load data from TOML file
        with open(self.__toml_path__, "rb") as file:
            toml_data = tomli.load(file)
        
        # Assign values to object attributes
        # Dynamically create attributes for each section in the TOML data
        for section, attributes in toml_data.items():
            setattr(self, section, attributes)
        
        paras = {}
        shared_paras = {}
        for attribute, value in vars(self).items():
            if not attribute.startswith("__"):
                if attribute not in self.__shared_attr__:
                    paras[attribute] = value
                else:
                    shared_paras[attribute] = value
        print("Unique paras: ",paras)
        print("\nShared paras: ",shared_paras)


if __name__ == "__main__":
    SurveyResults = Coordinator()