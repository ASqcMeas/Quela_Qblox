import sys, os, time, tomli
data_folder = "C:\ExpData"

class Maid():
    """ Connected to Conductor.Coordinator, it's responsible for build up some folders like Data-saving, """
    def __init__(self, exp_paras:dict, sample_register:bool=False):
        self.__exp_paras__ = exp_paras
        if sample_register:
            self.__registerSample__()

    def __registerSample__(self):
        # Create sample data folder
        sample_data_folder = os.path.join(data_folder,self.__exp_paras__["sample_name"].replace(" ",""))
        if os.path.exists(sample_data_folder):
            raise NameError("This sample name had been registered, please try the other name to register it like add '_v2' after the name.")
        else :
            os.mkdir(sample_data_folder)
        # build up sample info toml
        with open(os.path.join(sample_data_folder,"sample_info.toml"), "w") as file:
            for item in self.__exp_paras__:
                file.write(f"{item} = {self.__exp_paras__[item]}\n")  # Inline comments
                file.write("\n")  #
        
        print(f"sample '{self.__exp_paras__['sample_name'].replace(' ','')}' successfully registered !")
        return sample_data_folder

    def __getSampleInfo__(self):
        pass
    


if __name__ == "__main__":
    pass



