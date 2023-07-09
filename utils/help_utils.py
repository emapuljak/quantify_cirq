import itertools
def create_binary_strings(n):
    bin_array = list(itertools.product([0, 1], repeat=n))
    bin_strings = []
    for item in bin_array:
        string = ''
        for i in item:
            string = string + str(i)
        bin_strings.append(string)
    return bin_strings