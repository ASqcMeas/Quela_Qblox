from numpy import ndarray
from types import FunctionType
from abc import abstractmethod

def empty_func():FunctionType

class Exp_Encyclopedia():
    def __init__(self,exp_type:str,machine_type:str=None):
        """
        exp_type should be in the following:\n
            S0. MeasInitializer
            S1. BroadBandCS,
            S2. ZoomCS,
            S3. PowerCavity,
            S4. FluxCavity,
            S5. Conti2Tone,
            S6. FluxQubit,
            S7. Rabi,
            S8. OneShot,
            S9. T2,
            S10. T1,
            ----------------
            C1. ROFcali,
            C2. XYFcali,
            C3. PIampcali,
            C4. HalfPIcali,
            ----------------
            A1. TimeMonitor,
            A2. ZgateT1
        """
        self.__SurveyUniqueName__:str = "ExpParasSurvey"
        
        self.__machine_type__ = machine_type
        self.__exp__ = exp_type.lower()
        self.__expVarable_Reminder__()
        self.__shared_attr__ = ["avg_n", "machine_IP", "list_sampling_func"] # importanat 

    def __setMeasInit__(self):
        self.Instrument_IP:str = "" 
        self.how_many_couplers:int = 0
        self.how_many_qubits:int = 0
        self.cool_down_date:str = ""
        self.cool_down_dr:str = ""
        self.sample_name:str = ""
        self.chip_type:str = ""

    def __setMachineIP__(self):
        """ `<class, 'str'>`, Single value """
        self.machine_IP:str = ""

    def __setExpAVGn__(self):
        """ `<class, 'int'>`,  Single fixed value """
        self.avg_n:int = 0

    def __setFreqRange__(self):
        """ `<class, 'list'>`,  rule: [freq_start, freq_end, freq_pts], or a single value inside a list like [4e9] """
        self.freq_range = list([])
    
    def __setSamplingFunc__(self):
        """ sampling function, `linspace` or `arange` from `numpy`"""
        self.list_sampling_func:FunctionType = empty_func

    def __expVarable_Reminder__(self):
        match self.__exp__:
            case "s0" | "init" | "measinitializer":
                self.__setMeasInit__()

            case "s1" | "broadbandcs" | "bbcs":
                self.__setMachineIP__()
                self.__setSamplingFunc__()
                self.__setFreqRange__()
                self.__setExpAVGn__()
                if self.__machine_type__ is not None:
                    match self.__machine_type__.lower():
                        case 'qblox':
                            self.__ro_elements_coords__:dict = {"layer":2,"1F":{"name":"joint_qbs","value":"2F"},"2F":[{"name":"freq_samples","value":"freq_range"}]} # The value in "2F" shoud exist in the ExpParasSurvey.toml 
                            self.__bias_elements_coords__:dict = {}
                        case 'qm':
                            pass
                
            case "s2" | "cs" | "zoomcs":
                self.__setMachineIP__()
                self.__setFreqRange__()
                self.__setExpAVGn__()

    def __CoordsDecode__(self,coordsProtocol:dict,joint_qbs:list,function:callable=None,**kwargs):
        result = {}
        layer_2_configs = coordsProtocol["2F"]
    
        for qb in joint_qbs:
            result[qb] = {}

            for config in layer_2_configs:
                field_name = config["name"]
                variable_name = config["value"]

                if variable_name in kwargs:
                    result[qb][field_name] = kwargs[variable_name][qb] if type(kwargs[variable_name][qb]) != list else function(kwargs[variable_name][qb])
                else:
                    raise KeyError(f"Missing the variable {variable_name} for layer '2F' in kwargs !")
            
        return result  



class ExpSpirit():
    def __init__(self):
        self.set_variables()
        self.ro_elements, self.machine_type = "", ""# FBI.decode()
        self.set_pulseSchedule()
        self.set_analysis()

    @abstractmethod
    def set_variables(self,*args):
        pass

    @abstractmethod
    def set_pulseSchedule(self,system:str,*args):
        pass

    @abstractmethod
    def set_analysis(self,*args):
        pass


class S0_MeasInit():
    def __init__(self):
        self.Instrument_IP:str = "" 
        self.how_many_couplers:int = 0
        self.how_many_qubits:int = 0
        self.cool_down_date:str = ""
        self.cool_down_dr:str = ""
        self.sample_name:str = ""
        self.chip_type:str = ""


class S1_CS(ExpSpirit):
    def __init__(self):
        super().__init__()
        self.workflow()


    def set_variables(self):
        self.freq_range = list([])
    

    def set_pulseSchedule(self,):
        match self.machine_type:
            case qblox:
                from A import B_ps, B_ana
                self.raw_data = []

    
    def set_analysis(self,*args):
        fig = B_ana(self.raw_data)

    
    def workflow(self):
        self.set_variables()
        self.ro_elements, self.machine_type = FBI.decode()
        self.set_pulseSchedule()
        self.set_analysis()


