from quantify_scheduler.json_utils import SchedulerJSONDecoder
from typing import Tuple
import warnings
from pathlib import Path
from typing import List, Union, Literal
import matplotlib.pyplot as plt
import ipywidgets as widgets
import numpy as np
from numpy.random import randint
import quantify_core.data.handling as dh
from IPython.display import display
from qblox_instruments import Cluster, ClusterType, PlugAndPlay
from qcodes import Instrument
from qcodes.parameters import ManualParameter
from quantify_core.analysis.single_qubit_timedomain import (
    RabiAnalysis,
    RamseyAnalysis,
    T1Analysis,
)
from quantify_core.measurement.control import MeasurementControl
from quantify_core.visualization.pyqt_plotmon import PlotMonitor_pyqt as PlotMonitor
from quantify_scheduler.device_under_test.quantum_device import QuantumDevice
from quantify_scheduler.device_under_test.transmon_element import BasicTransmonElement
from quantify_scheduler.gettables import ScheduleGettable
from quantify_scheduler.instrument_coordinator import InstrumentCoordinator
from quantify_scheduler.instrument_coordinator.components.qblox import ClusterComponent
from quantify_scheduler.operations.gate_library import Measure, Reset
from quantify_scheduler.operations.pulse_library import SetClockFrequency, SquarePulse, DRAGPulse
from quantify_scheduler.resources import ClockResource
from quantify_scheduler.schedules import heterodyne_spec_sched_nco, rabi_sched, t1_sched
from quantify_scheduler.schedules.timedomain_schedules import ramsey_sched
from quantify_scheduler.schedules.schedule import Schedule
from quantify_core.analysis.spectroscopy_analysis import ResonatorSpectroscopyAnalysis, QubitSpectroscopyAnalysis
from quantify_core.analysis.base_analysis import Basic2DAnalysis
from utils.tutorial_analysis_classes import (
    QubitFluxSpectroscopyAnalysis,
    ResonatorFluxSpectroscopyAnalysis,
)
from quantify_scheduler.operations.gate_library import X90, Measure, Reset, Rxy, X, Y
from utils.tutorial_utils import (
    set_drive_attenuation,
    set_readout_attenuation,
    show_args,
    show_drive_args,
    show_readout_args,
)

def quadratic(x,a,b,c):
    return a*(x**2)+b*x+c

# TODO: Test this class to store the bias info
# dict to save the filux bias information
class FluxBiasDict():
    """
    This class helps to memorize the flux bias. 
    """
    from numpy import ndarray
    def __init__(self,qb_number:int):
        self.__bias_dict = {}
        self.q_num = qb_number
        self.float_cata = ["SweetSpot","TuneAway","Period"]
        self.list_cata = ["cavFitParas","qubFitParas"] # For the fitting functions access
        self.dict_cata = {"qubFitData":["bias_data","XYF_data"]} # For XYF-Flux fitting data storing

        self.init_bias()

    def sin_for_cav(self,target_q:str,bias_ary:ndarray):
        """
        Return the ROF curve data fit by the Quantify's sin model about the target_q with the bias array. 
        """
        def Sin(x,amp,w,phs,offset):
            return float(amp)*np.sin(float(w)*x+float(phs))+float(offset)
        return Sin(bias_ary,*self.__bias_dict[target_q]["cavFitParas"])
    
    def quadra_for_qub(self,target_q:str,bias_ary:ndarray):
        """
        Return the XYF curve data fit by quadratic about target_q with the bias array.
        """
        return quadratic(bias_ary,*self.__bias_dict[target_q]["qubFitParas"])


    def get_bias_dict(self)->dict:
        """
        Return the dictionary contain the bias info.
        """
        return self.__bias_dict
    
    def init_bias(self):
        """
        Initialize the dict when you create this object.
        """
        for i in range(self.q_num):
            self.__bias_dict[f"q{i}"] = {}
            for bias_position in self.float_cata:
                self.__bias_dict[f"q{i}"][bias_position] = 0.0
            
            for para_cata in self.list_cata:
                self.__bias_dict[f"q{i}"][para_cata] = []
            
            for dict_cata in self.dict_cata:
                self.__bias_dict[f"q{i}"][dict_cata] = {}
                for subcata in self.dict_cata[dict_cata]: 
                    self.__bias_dict[f"q{i}"][dict_cata][subcata] = []


    def save_sweetspotBias_for(self,target_q:str='q0',bias:float=0.0):
        """
            Set the sweet spot bias for the given qubit, target_q label starts from 0.\n
            Ex. target_q = 'q0'
        """
        self.__bias_dict[target_q]["SweetSpot"] = bias

    def save_tuneawayBias_for(self,mode:str,target_q:str='q0',bias:float=0.0):
        """
            Set the tune away bias for the given qubit, target_q label starts from 0.\n
            Ex. target_q = 'q0'\n
            mode = 'manual' | 'auto'. `'manual'` get the given bias in args, `'auto'` calculated by the stored offset and period. 
        """
        if mode == 'manual':
            self.__bias_dict[target_q]["TuneAway"] = bias
        elif mode == 'auto':
            offset = self.get_sweetBiasFor(target_q)
            T = self.get_PeriodFor(target_q)
            tuneaway = offset + T/2 if abs(offset + T/2) < abs(offset - T/2) else offset - T/2
            self.__bias_dict[target_q]["TuneAway"] = tuneaway
        else:
            raise KeyError("Wrong mode!")
        
    def save_period_for(self,target_q:str,period:float):
        """
        Save the period for the target_q with that given period.
        """
        self.__bias_dict[target_q]["Period"] = period

    def save_cavFittingParas_for(self,target_q:str,amp:float,f:float,phi:float,offset:float):
        """
        Save the fitting fuction parameters for flux dep cavity, includes amplitude, frequency, phase and offset for a sin in the form:\n
        `A*sin(fx+phi)+offset`
        """
        self.__bias_dict[target_q]["cavFitParas"] = [f,amp,phi,offset]

    def save_qubFittingParas_for(self,target_q:str,a:float,b:float,c:float):
        """
        Save the fitting function parameters for flux dep qubit, includes a, b, c for the quadratic form:\n
        `ax**2+bx+c`
        """
        #TODO:
        self.__bias_dict[target_q]["qubFitParas"] = [a,b,c]
    
    def activate_from_dict(self,old_bias_dict:dict):
        """
        Activate the dict which super from the old record.
        """
        for q_old in old_bias_dict:
            for catas in old_bias_dict[q_old]:
                self.__bias_dict[q_old][catas] = old_bias_dict[q_old][catas]

    def get_sweetBiasFor(self,target_q:str):
        """
        Return the sweetSpot bias for the target qubit.
        """
        return self.__bias_dict[target_q]["SweetSpot"]
    
    def get_tuneawayBiasFor(self,target_q:str):
        """
        Return the tuneAway bias for the target qubit.
        """
        return self.__bias_dict[target_q]["TuneAway"]
    
    def get_PeriodFor(self,target_q:str):
        """
        Return the period for the target_q.
        """
        return self.__bias_dict[target_q]["Period"]
    
class Notebook():
    def __init__(self,q_number:str):
        self.__dict = {}
        self.q_num = q_number
        self.cata = ["bareF","T1","T2"] # all in float

        self.init_dict()

    def init_dict(self):
        for i in range(self.q_num):
            self.__dict[f"q{i}"] = {}
            for float_cata in self.cata:
                self.__dict[f"q{i}"][float_cata] = 0.0
    ## About get
    def get_notebook(self,target_q:str=''):
        if target_q != '':
            return self.__dict[target_q]
        else:
            return self.__dict
    ## About write and save   
    # For bare cavity freq
    def save_bareFreq_for(self,bare_freq:float,target_q:str="q1"):
        self.__dict[target_q]["bareF"] = bare_freq
    def get_bareFreqFor(self,target_q:str="q1"):
        return self.__dict[target_q]["bareF"]
    # For T1
    def save_T1_for(self,T1:float,target_q:str="q1"):
        self.__dict[target_q]["T1"] = T1
    def get_T1For(self,target_q:str="q1"):
        return self.__dict[target_q]["T1"]
    # For T2
    def save_T2_for(self,T2:float,target_q:str="q1"):
        self.__dict[target_q]["T2"] = T2
    def get_T2For(self,target_q:str="q1"):
        return self.__dict[target_q]["T2"]
    
    # Activate notebook
    def activate_from_dict(self,old_notebook:dict):
        for qu in old_notebook:
            for cata in self.cata:
                self.__dict[qu][cata] = old_notebook[qu][cata]



class QDmanager():
    def __init__(self,QD_path:str=''):
        self.path = QD_path
        self.refIQ = {}
        self.Hcfg = {}
        self.Log = "" 
        self.Identity=""

    def register(self,cluster_ip_adress:str,which_dr:str):
        """
        Register this QDmanager according to the cluster ip and in which dr.
        """
        specifier = cluster_ip_adress.split(".")[-1] # 192.168.1.specifier
        self.Identity = which_dr.upper()+"#"+specifier # Ex. DR2#171

    def memo_refIQ(self,ref_dict:dict):
        """
        Memorize the reference IQ according to the given ref_dict, which the key named in "q0"..., and the value is composed in list by IQ values.\n
        Ex. ref_dict={"q0":[0.03,-0.004],...} 
        """
        for q in ref_dict:
            self.refIQ[q] = ref_dict[q]
    
    def refresh_log(self,message:str):
        """
        Leave the message for this file.
        """
        self.Log = message

    def QD_loader(self):
        """
        Load the QuantumDevice, Bias config, hardware config and Flux control callable dict from a given json file path contain the serialized QD.
        """
        import pickle
        with open(self.path, 'rb') as inp:
            gift = pickle.load(inp)
        # string and int
        self.Identity = gift["ID"]
        self.Log = gift["Log"]
        self.q_num = len(list(gift["Flux"].keys()))
        # class    
        self.Fluxmanager :FluxBiasDict = FluxBiasDict(qb_number=self.q_num)
        self.Fluxmanager.activate_from_dict(gift["Flux"])
        self.Notewriter: Notebook = Notebook(q_number=self.q_num)
        self.Notewriter.activate_from_dict(gift["Note"])
        self.quantum_device :QuantumDevice = gift["QD"]
        # dict
        self.Hcfg = gift["Hcfg"]
        self.refIQ = gift["refIQ"]
   

        self.quantum_device.hardware_config(self.Hcfg)
        print("Old friends loaded!")
    
    def QD_keeper(self, special_path:str=''):
        """
        Save the merged dictionary to a json file with the given path. \n
        Ex. merged_file = {"QD":self.quantum_device,"Flux":self.Fluxmanager.get_bias_dict(),"Hcfg":Hcfg,"refIQ":self.refIQ,"Log":self.Log}
        """
        import pickle, os, datetime
        if self.path == '' or self.path.split("/")[-2].split("_")[-1] != datetime.datetime.now().day:
            from Modularize.path_book import qdevice_backup_dir
            qd_folder = build_folder_today(qdevice_backup_dir)
            self.path = os.path.join(qd_folder,f"{self.Identity}_SumInfo.pkl")
        Hcfg = self.quantum_device.generate_hardware_config()
        # TODO: Here is onlu for the hightlighs :)
        merged_file = {"ID":self.Identity,"QD":self.quantum_device,"Flux":self.Fluxmanager.get_bias_dict(),"Hcfg":Hcfg,"refIQ":self.refIQ,"Note":self.Notewriter.get_notebook(),"Log":self.Log}
        
        with open(self.path if special_path == '' else special_path, 'wb') as file:
            pickle.dump(merged_file, file)
            print(f'Summarized info had successfully saved to the given path!')
    
    def build_new_QD(self,qubit_number:int,Hcfg:dict,cluster_ip:str,dr_loc:str):
        """
        Build up a new Quantum Device, here are something must be given about it:\n
        (1) qubit_number: how many qubits is in the chip.\n
        (2) Hcfg: the hardware configuration between chip and cluster.\n
        (3) cluster_ip: which cluster is connected. Ex, cluster_ip='192.168.1.171'\n
        (4) dr_loc: which dr is this chip installed. Ex, dr_loc='dr4'
        """
        print("Building up a new quantum device system....")
        self.q_num = qubit_number
        self.Hcfg = Hcfg
        self.register(cluster_ip_adress=cluster_ip,which_dr=dr_loc)
        self.quantum_device = QuantumDevice("academia_sinica_device")
        self.quantum_device.hardware_config(self.Hcfg)
        
        # store references
        self.quantum_device._device_elements = list()

        for i in range(qubit_number):
            qubit = BasicTransmonElement(f"q{i}")
            qubit.measure.acq_channel(i)
            self.quantum_device.add_element(qubit)
            self.quantum_device._device_elements.append(qubit)

        self.Fluxmanager :FluxBiasDict = FluxBiasDict(self.q_num)
        self.Notewriter: Notebook = Notebook(self.q_num)


# initialize a measurement
def init_meas(QuantumDevice_path:str='',dr_loc:str='',cluster_ip:str='170',qubit_number:int=5, mode:str='new',vpn:bool=False)->Tuple[QDmanager, Cluster, MeasurementControl, InstrumentCoordinator]:
    """
    Initialize a measurement by the following 2 cases:\n
    ### Case 1: QD_path isn't given, create a new QD accordingly.\n
    ### Case 2: QD_path is given, load the QD with that given path.\n
    args:\n
    cluster_ip: '170' for DR3 (default), '171' for DR2.
    mode: 'new'/'n' or 'load'/'l'. 'new' need a self defined hardware config. 'load' load the given path. 
    """
    import quantify_core.data.handling as dh
    meas_datadir = '.data'
    dh.set_datadir(meas_datadir)
    if mode.lower() in ['new', 'n']:
        from Experiment_setup import hcfg_map
        cfg, pth = hcfg_map[cluster_ip], ''
        if dr_loc == '':
            raise ValueError ("arg 'dr_loc' should not be ''!")
    elif mode.lower() in ['load', 'l']:
        cfg, pth = {}, QuantumDevice_path 
    else:
        raise KeyError("The given mode can not be recognized!")
    
    # Connect to the Qblox cluster
    if not vpn:
        # connect, ip = connect_clusters() ## Single cluster online
        # cluster = Cluster(name = "cluster0", identifier = ip.get(connect.value))
        ip, ser = connect_clusters_withinMulti(cluster_ip)
        cluster = Cluster(name = "cluster0", identifier = ip)
    else:
        cluster = Cluster(name = "cluster0",identifier = f"qum.phys.sinica.edu.tw", port=5025)
        ip = "192.168.1.171"
    
    Qmanager = QDmanager(pth)
    if pth == '':
        Qmanager.build_new_QD(qubit_number,cfg,ip,dr_loc)
        Qmanager.refresh_log("new-born!")
    else:
        Qmanager.QD_loader()

    meas_ctrl, ic = configure_measurement_control_loop(Qmanager.quantum_device, cluster)
    
    return Qmanager, cluster, meas_ctrl, ic

# Configure_measurement_control_loop
def configure_measurement_control_loop(
    device: QuantumDevice, cluster: Cluster, live_plotting: bool = False
) ->Tuple[MeasurementControl,InstrumentCoordinator]:
    # Close QCoDeS instruments with conflicting names
    for name in [
        "PlotMonitor",
        "meas_ctrl",
        "ic",
        "ic_generic",
        f"ic_{cluster.name}",
    ] + [f"ic_{module.name}" for module in cluster.modules]:
        try:
            Instrument.find_instrument(name).close()
        except KeyError as kerr:
            pass

    meas_ctrl = MeasurementControl("meas_ctrl")
    ic = InstrumentCoordinator("ic")
    ic.timeout(60*60)

    # Add cluster to instrument coordinator
    ic_cluster = ClusterComponent(cluster)
    ic.add_component(ic_cluster)

    if live_plotting:
        # Associate plot monitor with measurement controller
        plotmon = PlotMonitor("PlotMonitor")
        meas_ctrl.instr_plotmon(plotmon.name)

    # Associate measurement controller and instrument coordinator with the quantum device
    device.instr_measurement_control(meas_ctrl.name)
    device.instr_instrument_coordinator(ic.name)

    return (meas_ctrl, ic)


def two_tone_spec_sched_nco(
    qubit_name: str,
    spec_pulse_amp: float,
    spec_pulse_duration: float,
    spec_pulse_port: str,
    spec_pulse_clock: str,
    spec_pulse_frequencies: np.ndarray,
    repetitions: int = 1,
) -> Schedule:
    """
    Generate a batched schedule for performing fast two-tone spectroscopy using the
    `SetClockFrequency` operation for doing an NCO sweep.

    Parameters
    ----------
    spec_pulse_amp
        Amplitude of the spectroscopy pulse in Volt.
    spec_pulse_duration
        Duration of the spectroscopy pulse in seconds.
    spec_pulse_port
        Location on the device where the spectroscopy pulse should be applied.
    spec_pulse_clock
        Reference clock used to track the spectroscopy frequency.
    spec_pulse_frequencies
        Sample frequencies for the spectroscopy pulse in Hertz.
    repetitions
        The amount of times the Schedule will be repeated.
    """
    sched = Schedule("two-tone", repetitions)
    sched.add_resource(ClockResource(name=spec_pulse_clock, freq=spec_pulse_frequencies.flat[0]))

    for acq_idx, spec_pulse_freq in enumerate(spec_pulse_frequencies):
        sched.add(Reset(qubit_name))
        sched.add(SetClockFrequency(clock=spec_pulse_clock, clock_freq_new=spec_pulse_freq))
        sched.add(
            SquarePulse(
                duration=spec_pulse_duration,
                amp=spec_pulse_amp,
                port=spec_pulse_port,
                clock=spec_pulse_clock,
            )
        )
        sched.add(Measure(qubit_name, acq_index=acq_idx))

    return sched

# close all instruments
def shut_down(cluster:Cluster,flux_map:dict):
    '''
        Disconnect all the instruments.
    '''
    reset_offset(flux_map)
    cluster.reset() 
    Instrument.close_all() 
    print("All instr are closed and zeroed all flux bias!")

# connect to clusters
def connect_clusters():
    with PlugAndPlay() as p:            # Scan for available devices and display
        device_list = p.list_devices()  # Get info of all devices

    names = {dev_id: dev_info["description"]["name"] for dev_id, dev_info in device_list.items()}
    ip_addresses = {dev_id: dev_info["identity"]["ip"] for dev_id, dev_info in device_list.items()}
    connect_options = widgets.Dropdown(         # Create widget for names and ip addresses *** Should be change into other interface in the future
        options=[(f"{names[dev_id]} @{ip_addresses[dev_id]}", dev_id) for dev_id in device_list],
        description="Select Device",
    )
    display(connect_options)
    
    return connect_options, ip_addresses

# Multi-clusters online version connect_clusters()
def connect_clusters_withinMulti(ip_last_posi:str='170'):
    """
    This function is only for who doesn't use jupyter notebook to connect cluster.
    args: \n
    ip_last_posi: '170' for DR3 (default), '171' for DR2.\n
    So far the ip for Qblox cluster is named with 192.168.1.170 and 192.168.1.171
    """
    permissions = {}
    with PlugAndPlay() as p:            # Scan for available devices and display
        device_list = p.list_devices()
    for devi, info in device_list.items():
        permissions[info["identity"]["ip"]] = info["identity"]["ser"]
    if f"192.168.1.{ip_last_posi}" in permissions:
        print(f"192.168.1.{ip_last_posi} is available to connect to!")
        return f"192.168.1.{ip_last_posi}", permissions[f"192.168.1.{ip_last_posi}"]
    else:
        raise KeyError(f"192.168.1.{ip_last_posi} is NOT available now!")
 
# def set attenuation for all qubit
def set_atte_for(quantum_device:QuantumDevice,atte_value:int,mode:str,target_q:list=['q1']):
    """
        Set the attenuations for RO/XY by the given mode and atte. values.\n
        atte_value: integer multiple of 2,\n
        mode: 'ro' or 'xy',\n
        target_q: ['q1']
    """
    # Check atte value
    if atte_value%2 != 0:
        raise ValueError(f"atte_value={atte_value} is not the multiple of 2!")
    # set atte.
    if mode.lower() == 'ro':
        for q_name in target_q:
            set_readout_attenuation(quantum_device, quantum_device.get_element(q_name), out_att=atte_value, in_att=0)
    elif mode.lower() == 'xy':
        for q_name in target_q:
            set_drive_attenuation(quantum_device, quantum_device.get_element(q_name), out_att=atte_value)
    else:
        raise KeyError (f"The mode='{mode.lower()}' is not 'ro' or 'xy'!")
    
def CSresults_alignPlot(quantum_device:QuantumDevice, results:dict):
    item_num = len(list(results.keys()))
    fig, ax = plt.subplots(1,item_num,figsize=plt.figaspect(1/item_num), sharey = False)
    for idx, q in enumerate(list(results.keys())):
        fr = results[q].run().quantities_of_interest["fr"].nominal_value
        dh.to_gridded_dataset(results[q].dataset).y0.plot(ax = ax[idx])
        ax[idx].axvline(fr, color = "red", ls = "--")
        ax[idx].set_title(f"{q} resonator")
    
    fig.suptitle(f"Resonator spectroscopy, {quantum_device.cfg_sched_repetitions()} repetitions")
    fig.tight_layout()
    plt.show()
    
def PDresults_alignPlot(quantum_device:QuantumDevice, results:dict, show_mode:str='pha'):
    item_num = len(list(results.keys()))

    fig, ax = plt.subplots(1,item_num,figsize=plt.figaspect(1/item_num), sharey = False)
    for idx, q in enumerate(list(results.keys())):
        if show_mode == 'pha':
            dh.to_gridded_dataset(results[q].dataset).y1.plot(ax = ax[idx])
        else:
            dh.to_gridded_dataset(results[q].dataset).y0.plot(ax = ax[idx])
        ax[idx].axhline(quantum_device.get_element(q).clock_freqs.readout(), color = "red", ls = "--")
        ax[idx].set_title(f"{q} resonator")
        
    fig.suptitle(f"Resonator Dispersive, {quantum_device.cfg_sched_repetitions()} repetitions")
    fig.tight_layout()
    plt.show()

def FD_results_alignPlot(quantum_device:QuantumDevice, results:dict, show_mode:str='pha'):
    item_num = len(list(results.keys()))
    fig, ax = plt.subplots(1,item_num,figsize=plt.figaspect(1/item_num), sharey = False)
    for idx, q in enumerate(list(results.keys())):
        dressed_f = results[q].quantities_of_interest["freq_0"]
        offset = results[q].quantities_of_interest["offset_0"].nominal_value
        if show_mode == 'pha':
            dh.to_gridded_dataset(results[q].dataset).y1.plot(ax = ax[idx])
        else:
            dh.to_gridded_dataset(results[q].dataset).y0.plot(ax = ax[idx])
        ax[idx].axhline(dressed_f, color = "red", ls = "--")
        ax[idx].axvline(offset, color = "red", ls = "--")
        ax[idx].set_title(f"{q} resonator")
        
    fig.suptitle(f"Resonator Flux dependence, {quantum_device.cfg_sched_repetitions()} repetitions")
    fig.tight_layout()
    plt.show()

def reset_offset(flux_callable_map:dict):
    for i in flux_callable_map:
        flux_callable_map[i](0.0)





# TODO: ToTest ZZinteractions
def ZZinteractions_sched(
    times: Union[np.ndarray, float],
    ctrl_qubit: str,
    meas_qubit: str,
    artificial_detuning: float = 0,
    repetitions: int = 1,
) -> Schedule:
    r"""
    Generate a schedule for performing a Ramsey experiment to measure the
    dephasing time :math:`T_2^{\star}`.

    Schedule sequence
        .. centered:: Reset -- pi/2 -- Idle(tau) -- pi/2 -- Measure

    See section III.B.2. of :cite:t:`krantz_quantum_2019` for an explanation of the Bloch-Redfield
    model of decoherence and the Ramsey experiment.

    Parameters
    ----------
    times
        an array of wait times tau between the pi/2 pulses.
    artificial_detuning
        frequency in Hz of the software emulated, or ``artificial`` qubit detuning, which is
        implemented by changing the phase of the second pi/2 (recovery) pulse. The
        artificial detuning changes the observed frequency of the Ramsey oscillation,
        which can be useful to distinguish a slow oscillation due to a small physical
        detuning from the decay of the dephasing noise.
    qubit
        the name of the qubit e.g., :code:`"q0"` to perform the Ramsey experiment on.
    repetitions
        The amount of times the Schedule will be repeated.

    Returns
    -------
    :
        An experiment schedule.

    """
    # ensure times is an iterable when passing floats.
    times = np.asarray(times)
    times = times.reshape(times.shape or (1,))

    schedule = Schedule("Ramsey", repetitions)

    if isinstance(times, float):
        times = [times]

    for i, tau in enumerate(times):
        schedule.add(Reset(meas_qubit,ctrl_qubit), label=f"Reset {i}")
        schedule.add(X(ctrl_qubit))
        schedule.add(X90(meas_qubit))

        # the phase of the second pi/2 phase progresses to propagate
        recovery_phase = np.rad2deg(2 * np.pi * artificial_detuning * tau)
        schedule.add(
            Rxy(theta=90, phi=recovery_phase, qubit=meas_qubit), ref_pt="start", rel_time=tau
        )
        schedule.add(Measure(meas_qubit, acq_index=i), label=f"Measurement {i}")
    return schedule      

# TODO: RB
def SQRB_schedule(
    qubit:str,
    gate_num:int,
    repetitions: int=1,
) -> Schedule:

    sched = Schedule('RB',repetitions)
    sched.add(Reset(qubit))
    for idx in range(gate_num):
        pass
    sched.add(Measure(qubit))
    
    return sched

# generate time label for netCDF file name
def get_time_now()->str:
    """
    Since we save the Xarray into netCDF, we use the current time to encode the file name.\n
    Ex: 19:23:34 return H19M23S34 
    """
    import datetime
    current_time = datetime.datetime.now()
    return f"H{current_time.hour}M{current_time.minute}S{current_time.second}"

# build the folder for the data today
def build_folder_today(parent_path:str):
    """
    Build up and return the folder named by the current date in the parent path.\n
    Ex. parent_path='D:/Examples/'
    """
    import os
    import datetime
    current_time = datetime.datetime.now()
    folder = f"{current_time.year}_{current_time.month}_{current_time.day}"
    new_folder = os.path.join(parent_path, folder) 
    if not os.path.isdir(new_folder):
        os.mkdir(new_folder) 
        print(f"Folder {current_time.year}_{current_time.month}_{current_time.day} had been created!")
    else:
        print(f"Folder {current_time.year}_{current_time.month}_{current_time.day} exist!")
    return new_folder



# def add log message into the sumInfo
def leave_LogMSG(MSG:str,sumInfo_path:str):
    """
    Leave the log message in the sumInfo with the given path.
    """
    import pickle
    with open(sumInfo_path, 'rb') as inp:
        gift = pickle.load(inp)
    gift["Log"] = MSG
    with open(sumInfo_path, 'wb') as file:
        pickle.dump(gift, file)
        print("Log message had been added!")


# set attenuations
def init_system_atte(quantum_device:QuantumDevice,qb_list:list,ro_out_att:int=40,xy_out_att:int=20):
    """
    Attenuation setting includes XY and RO. We don't change it once we set it.
    """
    # atte. setting
    set_atte_for(quantum_device,ro_out_att,'ro',qb_list)
    set_atte_for(quantum_device,xy_out_att,'xy',qb_list) 