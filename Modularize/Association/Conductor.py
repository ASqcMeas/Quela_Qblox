import os, tomli
from Association.Soul import Exp_Encyclopedia
from Modularize.Association.Housekeeper import Maid
from Modularize.Association.FBI import Canvasser


class Coordinator(Exp_Encyclopedia):
    
    def __init__(self):
       pass


    def __ExpParasCollects__(self, *args, **kwargs):
        Agent = Canvasser("_",[])
        self.shared_settings, self.ro_elements, self.bias_elements = Agent.__toml_decoder__()
        self.exp = Agent.exp_type
        self.machine_IP:str = Agent.assigned_paras["machine_IP"]
        self.intrument_type:str = Agent.exp_machine_type

    def __ExpExecutes__(self, *args, **kwargs):
        pass

    def __ExpResultsAnalyzes__(self, *args, **kwargs):
        pass

    def MeasWorkFlow(self):
        self.__ExpParasCollects__()

        self.__ExpExecutes__()

        self.__ExpResultsAnalyzes__()



if __name__ == "__main__":
    pass