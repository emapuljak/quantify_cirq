import os
import argparse
import cirq
import pandas as pd
from pathlib import Path
from qramcircuits import bucket_brigade as bb
from qramcircuits.toffoli_decomposition import ToffoliDecompType, ToffoliDecomposition
from utils.counting_utils import *
from utils.help_utils import *

def bitstring(bits):
    return ''.join(str(int(b)) for b in bits)
    
def state_preparation(circuit, initial_state):
    """ Prepare initial quantum state of the quantum circuit.

    Parameters
    ----------
    circuit: :class:`BucketBrigade`
        Bucket Brigade instance circuit
    initial_state: str
        Binary string refering to quantum state ('000' = |0>|0>|0>)
    
    Returns
    -------
    circuit: :class:`BucketBrigade`
    """

    qubits = circuit.qubits
    init_ops = []
        
    for i, b in enumerate(initial_state):
        if b not in ['0', '1']:
            raise ValueError('Initial state must consist of 0s or 1s')

        # append gate X to qubit which corresponds to initial classical bit = 1
        if b == '1':
            init_ops.append(cirq.X(qubits[i]))
    # append inital quantum state to begining of circuit
    circuit.circuit.moments.insert(0, cirq.Moment(init_ops))

    return circuit

def execute_circuit(circuit, measurement_qubit_names, repetitions=1000):
    """ Execute quantum circuit on cirq.Simulator

    Parameters
    ----------
    circuit: :class:`cirq.Circuit`
        cirq.Circuit instance
    measurement_qubit_names: array of strings
        Names of qubits that need to be measured.
    repetitions: int
        Number of repetitions for execution of quantum circuit. Default = 1000.
    
    Returns
    -------
    result: Result from cirq.Simulator.run()
    frequencies: dictionary with frequencies for measurement of qubits
    """
    simulator = cirq.Simulator()
    result = simulator.run(circuit, repetitions=repetitions)
    # get frequencies for all measurements 
    frequencies = result.multi_measurement_histogram(keys=measurement_qubit_names, fold_func=bitstring)
    return result, frequencies

def verify_counts(circuit_1, circuit_2, decomp_scenario):
    """ Verify counts for several gates in quantum circuits

    Parameters
    ----------
    circuit_1: :class:`BucketBrigade`
        Bucket Brigade instance circuit 1
    circuit_2: :class:`BucketBrigade`
        Bucket Brigade instance circuit 2
    decomp_scenario: :class:`BucketBrigadeDecompType`
        Decomposition scenario

    
    """
    # circuit_1
    print('----- Counts for original circuit -----')
    print("Verify nqubits:      {}\n".format(circuit_1.verify_number_qubits()))
    print("Verify Depth:        {}\n".format(circuit_1.verify_depth(
        Alexandru_scenario=decomp_scenario.parallel_toffolis)))
    print("Verify T_count:      {}\n".format(circuit_1.verify_T_count()))
    print("Verify T_depth:      {}\n".format(circuit_1.verify_T_depth(
        Alexandru_scenario=decomp_scenario.parallel_toffolis)))
    print("Verify H_count:      {}\n".format(circuit_1.verify_hadamard_count(
        Alexandru_scenario=decomp_scenario.parallel_toffolis)))

    # circuit_2
    print('----- Counts for modified circuit -----')
    print("Verify nqubits:      {}\n".format(circuit_2.verify_number_qubits()))
    print("Verify Depth:        {}\n".format(circuit_2.verify_depth(
        Alexandru_scenario=decomp_scenario.parallel_toffolis)))
    print("Verify T_count:      {}\n".format(circuit_2.verify_T_count()))
    print("Verify T_depth:      {}\n".format(circuit_2.verify_T_depth(
        Alexandru_scenario=decomp_scenario.parallel_toffolis)))
    print("Verify H_count:      {}\n".format(circuit_2.verify_hadamard_count(
        Alexandru_scenario=decomp_scenario.parallel_toffolis)))
    
def test_remove_T(bbcircuit, initial_state, percentage=0.2, inplace=True, repetitions=1000):
    """ Function for testing removal of T gates.

    Parameters
    ----------
    circuit: :class:`BucketBrigade`
        Bucket Brigade instance circuit
    initial_state: str
        Binary string refering to quantum state ('000' = |0>|0>|0>)
    percentage: float
        Percentage specifying the amount of T gates removed. From range 0-1.
    inplace: bool
        Flag specifying is bbcircuit modified in place or the function for removing T gates returns modified circuit as parameter. Default=True.\
        Better to always keep True.
    repetitions: int
        Number of repetitions for execution of quantum circuit. Default = 1000.
    
    Returns
    -------
    bbcircuit: :class:`BucketBrigade` -> original circuit
    bbcircuit_modified: :class:`BucketBrigade` -> modified circuit
    freq_origin: dict() -> dictionary with frequencies for measurement of addressing qubits for original circuit
    freq_mod: dict() -> dictionary with frequencies for measurement of addressing qubits for modified circuit
    """

    # prepare initial state of circuit changing the value of addressing qubits
    bb_circuit = state_preparation(circuit = bbcircuit, initial_state=initial_state)

    # to keep copy of original circuit
    bbcircuit_modified = bbcircuit.copy()
    if inplace:
        bbcircuit_modified.remove_T_gates(percentage=percentage, inplace=inplace)
    else:
        circuit = bbcircuit_modified.remove_T_gates(percentage=percentage, inplace=inplace)
        bbcircuit_modified.set_circuit(circuit)
    
    # adding measurements to addressing qubits
    measure_names_o = []; measure_names_m = []
    for i, _ in enumerate(initial_state):
        # adding to original circuit
        bbcircuit.circuit.append(cirq.measure(bbcircuit.all_qubits()[i], key=bbcircuit.all_qubits()[i].name)) # original circuit
        measure_names_o.append(bbcircuit.all_qubits()[i].name)
        # adding to modified circuit
        bbcircuit_modified.circuit.append(cirq.measure(bbcircuit_modified.all_qubits()[i], key=bbcircuit_modified.all_qubits()[i].name)) # modified circuit
        measure_names_m.append(bbcircuit_modified.all_qubits()[i].name)
    
    # executing original circuit
    result_origin, freq_origin = execute_circuit(bbcircuit.circuit, repetitions=repetitions, measurement_qubit_names=measure_names_o)
    print("Results:")
    print(freq_origin)

    # executing modified circuit
    result_mod, freq_mod = execute_circuit(bbcircuit_modified.circuit, repetitions=repetitions, measurement_qubit_names=measure_names_m)
    print(f'Results when removing {percentage*100}% of T gates:')
    print(freq_mod)

    return bbcircuit, bbcircuit_modified, freq_origin, freq_mod

def choose_decomposition(decomp_ID):
    """Choose decomposition type based on decomposition ID.

    Parameters
    ----------
    decomp_ID: str
        Specifying decomposition ID.
    
    Returns
    -------
    :class:BucketBrigadeDecompType
    """
    if decomp_ID == '1':
        decomp_scenario = bb.BucketBrigadeDecompType(
            [
                ToffoliDecompType.ZERO_ANCILLA_TDEPTH_4_COMPUTE,    # fan_in_decomp
                ToffoliDecompType.ZERO_ANCILLA_TDEPTH_4,  # mem_decomp
                ToffoliDecompType.ZERO_ANCILLA_TDEPTH_0_UNCOMPUTE,    # fan_out_decomp
            ],
            True
        )
    elif decomp_ID == '2':
        decomp_scenario = bb.BucketBrigadeDecompType(
            [
                ToffoliDecompType.NO_DECOMP,  # fan_in_decomp
                ToffoliDecompType.ZERO_ANCILLA_TDEPTH_4,  # mem_decomp
                ToffoliDecompType.NO_DECOMP,  # fan_out_decomp
            ],
            True
        )
    elif decomp_ID == '3':
        decomp_scenario = bb.BucketBrigadeDecompType(
            [
                ToffoliDecompType.FOUR_ANCILLA_TDEPTH_1_A,    # fan_in_decomp
                ToffoliDecompType.FOUR_ANCILLA_TDEPTH_1_A,    # mem_decomp
                ToffoliDecompType.FOUR_ANCILLA_TDEPTH_1_A,    # fan_out_decomp
            ],
            False
        )
    else:
        raise ValueError('Decomposition scenario needs to have ID from {1, 2, 3}.')

    return decomp_scenario

def create_BB_circuit(n_qubits, decomp_scenario):
    """ Create BucketBrigade circuit

    Parameters
    ----------
    n_qubits: int
        Number of addressing qubits
    decomp_scenario: :class:BucketBrigadeDecompType
        Decomposition scenario
    
    Returns
    -------
    bbcircuit: :class:`BucketBrigade`
    """

    # Assign names to addressing qubits
    qubits = []
    for i in range(n_qubits):
        qubits.append(cirq.NamedQubit("a" + str(i)))
    
    # create instance of BucketBrigade circuit
    bbcircuit = bb.BucketBrigade(qubits, decomp_scenario = decomp_scenario)

    return bbcircuit
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Read arguments for testing removal of percentage of T gates in Bucket Brigate QRAM circuit."
    )
    parser.add_argument(
        "--decomp_scenario", dest="decomp_scenario", type=str, help="Decomposition scenario for creating BB circuit"
    )
    parser.add_argument(
        "--percentage", dest="percentage", type=float, default=0.2, help="Percentage of T gates to remove"
    )
    parser.add_argument(
        "--inplace", dest="inplace", type=bool, default=True, help="Removal of T gates happening inplace"
    )
    parser.add_argument(
        "--repetitions", dest="repetitions", type=int, default=1000, help="Repetitions for executing a quantum circuit"
    )
    parser.add_argument(
        "--save_dir", dest="save_dir", type=str, default='results', help="Directory for saving results"
    )

    args = parser.parse_args()

    # if save_dir doesn't exist create it
    if os.path.exists(args.save_dir) is False:
        os.system(f"mkdir {args.save_dir}")
        
    # check removal of T gates for number of qubits from 2 to 3
    for n_qubits in range(2, 4):
        print(f'-------- nqubits: {n_qubits} --------')
        # create decomposition scenario
        decomp_scenario = choose_decomposition(args.decomp_scenario)

        # create dictionary to store results
        save_data = dict()
        save_data['input'] = []; save_data['output original'] = []; save_data['output modified'] = []

        # for every binary string of n_qubits -> check removal of T gates
        for initial_state in create_binary_strings(n_qubits):
            print(f'-------- initial state: {initial_state} --------')

            # create BBcircuit with specified number of qubits
            bbcircuit = create_BB_circuit(n_qubits=n_qubits, decomp_scenario=decomp_scenario)

            # test removal of "percentage" of T gates
            bbcircuit, bbcircuit_modified, freq_origin, freq_mod = test_remove_T(bbcircuit, initial_state=initial_state, percentage=args.percentage, inplace=args.inplace, repetitions=args.repetitions)
            
            # gather results
            save_data['input'].append(initial_state)
            save_data['output original'].append(dict(freq_origin))
            save_data['output modified'].append(dict(freq_mod))
        
        # save results for specific qubit
        dataframe = pd.DataFrame(save_data)
        save_name = f'{args.save_dir}/nqubits_{n_qubits}_percentage_{args.percentage*100}.csv'
        dataframe.to_csv(save_name, index=False)  
        #verify_counts(bbcircuit, bbcircuit_modified, decomp_scenario)