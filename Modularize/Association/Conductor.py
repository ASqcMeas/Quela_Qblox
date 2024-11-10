import os, tomli
from Modularize.Association.MainBrain import Exp_Encyclopedia
from Modularize.Association.Housekeeper import Maid
from Modularize.Association.FBI import Canvasser


class Coordinator(Exp_Encyclopedia):
    
    def __init__(self):
        Agent = Canvasser("_",[])
        self.ro_elements:dict = Agent.__toml_decoder__(r"C:\Users\ASqcm\MeasConfigs\S1_ExpParasSurvey.toml")
        machine_IP:str = Agent.__assined_paras__["machine_IP"]
        self.intrument_type:str = Agent.__exp_machine_type__


    def __prepareAmeas__(self):
        pass



if __name__ == "__main__":
    pass