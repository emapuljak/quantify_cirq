import cirq
import numpy as np

def count_num_gates(circuit):
    num_gates = 0

    for moment in circuit:
        num_gates += len(moment)
        
    return num_gates

def count_op_depth(circuit, gate_types):
    op_depth = 0

    for moment in circuit:
        for operation in moment:
            # if a gate is found in this moment,
            #  then increase depth and break to the next moment
            if isinstance(operation, cirq.GateOperation) and operation.gate in gate_types:
                op_depth += 1
                break

    return op_depth


def count_ops(circuit, gate_types, return_indices=False):
    op_count = 0
    position = 0

    # if return indices is True then function will remove positions of gate_types in quantum circuit
    if return_indices:
        ops_indices=[]
        
    for moment in circuit:
        for operation in moment:
            position += 1
            # if a gate is found in this moment,
            #  then increase depth and break to the next moment
            if isinstance(operation, cirq.GateOperation) and operation.gate in gate_types:
                op_count += 1
                if return_indices:
                    ops_indices.append(position)
    if return_indices:
        return op_count, ops_indices
    return op_count

def count_t_depth_of_circuit(circuit):
    return count_op_depth(circuit, [cirq.ops.T, cirq.ops.T**-1])

def count_t_of_circuit(circuit):
    return count_ops(circuit, [cirq.T, cirq.T**-1])

def count_h_of_circuit(circuit):
    return count_ops(circuit, [cirq.H])

def count_cnot_of_circuit(circuit):
    return count_ops(circuit, [cirq.CNOT])

def count_toffoli_of_circuit(circuit):
    return count_ops(circuit, [cirq.TOFFOLI])