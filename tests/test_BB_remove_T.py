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
    # circuit = BB circuit instance

    qubits = circuit.qubits
    init_ops = []
        
    for i, b in enumerate(initial_state):
        if b not in ['0', '1']:
            raise ValueError('Initial state must consist of 0s or 1s')

        if b == '1':
            init_ops.append(cirq.X(qubits[i]))
    
    circuit.circuit.moments.insert(0, cirq.Moment(init_ops))

    return circuit

def execute_circuit(circuit, measurement_qubit_names, repetitions=1000):
    simulator = cirq.Simulator()
    result = simulator.run(circuit, repetitions=repetitions)
    frequencies = result.multi_measurement_histogram(keys=measurement_qubit_names, fold_func=bitstring)
    return result, frequencies

def verify_counts(circuit_1, circuit_2, decomp_scenario):
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
    bb_circuit = state_preparation(circuit = bbcircuit, initial_state=initial_state)

    bbcircuit_modified = bbcircuit.copy()
    if inplace:
        bbcircuit_modified.remove_T_gates(percentage=percentage, inplace=inplace)
    else:
        circuit = bbcircuit_modified.remove_T_gates(percentage=percentage, inplace=inplace)
        bbcircuit_modified.set_circuit(circuit)
    
    # measuring addressing qubits
    measure_names_o = []; measure_names_m = []
    for i, _ in enumerate(initial_state):
        bbcircuit.circuit.append(cirq.measure(bbcircuit.all_qubits()[i], key=bbcircuit.all_qubits()[i].name)) # original circuit
        measure_names_o.append(bbcircuit.all_qubits()[i].name)
        bbcircuit_modified.circuit.append(cirq.measure(bbcircuit_modified.all_qubits()[i], key=bbcircuit_modified.all_qubits()[i].name)) # modified circuit
        measure_names_m.append(bbcircuit_modified.all_qubits()[i].name)
    
    # for original circuit
    result_origin, freq_origin = execute_circuit(bbcircuit.circuit, repetitions=repetitions, measurement_qubit_names=measure_names_o)
    print("Results:")
    print(freq_origin)

    # for modified circuit
    result_mod, freq_mod = execute_circuit(bbcircuit_modified.circuit, repetitions=repetitions, measurement_qubit_names=measure_names_m)
    print(f'Results when removing {percentage*100}% of T gates:')
    print(freq_mod)

    return bbcircuit, bbcircuit_modified, freq_origin, freq_mod

def choose_decomposition(decomp_ID):

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
    qubits = []
    for i in range(n_qubits):
        qubits.append(cirq.NamedQubit("a" + str(i)))
    
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

        # for every binary string of n_qubits -> check results
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