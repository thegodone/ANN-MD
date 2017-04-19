from create_train_data import generate_symmfunc_input_Si_Behler
import numpy as np
from file_management import findPathToData, readXYZ_Files
from plot_tools import plotErrorEvolutionSWvsNN, plotEvolutionSWvsNN_N_diff_epochs, plotForcesSWvsNN, plotLAMMPSforces1atomEvo
from create_train_data import PES_Stillinger_Weber
import sys
from derivatives_symm_func import force_calculation, create_neighbour_list
from nn_evaluation import neural_network

def test_structure_N_atom(neigh_cube, neural_network, plot_single=False, last_timestep=-1):
    """
    Structure:
    xyz = [[0, 0, 0 ], <--- must be origo
           [x2,y2,z2],
           [x3,y3,z3],
           [........],
           [xN,yN,zN]]
    """
    # Will just be a list of numbers Ep
    Ep_SW_list   = []
    Ep_NN_list   = []

    # Will contain tuples (Fx, Fy, Fz)
    Fvec_SW_list = []
    Fvec_NN_list = []

    # Need Ep of all atoms in NN-calculation of forces:
    tot_nmbr_of_atoms = neigh_cube[0].shape[0]
    Ep_NN_all_atoms   = np.zeros(tot_nmbr_of_atoms)
    _, nmbr_G         = generate_symmfunc_input_Si_Behler()
    dNNdG_matrix      = np.zeros((tot_nmbr_of_atoms, nmbr_G))

    # Loop through all timesteps
    for t,xyz in enumerate(neigh_cube[0:last_timestep]):
        # Make certain that atoms are centered around (0,0,0):
        if not np.all(xyz[0,:] == 0):
            print "Atoms not properly centered to origo. Exiting!"
            sys.exit(0)
        # Pick out neighbor atoms
        xyz_only_neigh = xyz[1:,:]

        # Potential and forces computed by Stillinger Weber:
        Ep_SW   = PES_Stillinger_Weber(xyz_only_neigh)
        Fvec_SW = (0,0,0) # Only a placeholder! LAMMPS data filled in later

        # Potential and forces computed by trained neural network:
        for i_atom in range(tot_nmbr_of_atoms):
            xyz_atom_centered       = create_neighbour_list(xyz, i_atom, return_self=False)
            symm_vec                = neural_network.create_symvec_from_xyz(xyz_atom_centered)
            Ep_NN_all_atoms[i_atom] = neural_network(symm_vec) # Evaluates the NN
            dNNdG_matrix[i_atom,:]  = neural_network.derivative().reshape(nmbr_G,)
        # Now that we have all Ep of all atoms, run force calculation:
        f_tot = force_calculation(dNNdG_matrix, xyz)

        # Append all values to lists:
        Ep_SW_list.append(Ep_SW)
        Ep_NN_list.append(Ep_NN_all_atoms[0]) # Pick out first atom (for comparison)
        Fvec_SW_list.append(Fvec_SW)
        Fvec_NN_list.append(f_tot[0])         # Pick out first atom (for comparison)

        # Print out progress
        if t%20 == 0 and t > 50:
            sys.stdout.write("\rTimestep: %d" %t)
            sys.stdout.flush()
    print " "
    # sys.exit(0) # """#########################"""

    if plot_single:
        plotErrorEvolutionSWvsNN(Ep_SW_list, Ep_NN_list, tot_nmbr_of_atoms)
    # Return values for more plotting
    return Ep_SW_list, Ep_NN_list, tot_nmbr_of_atoms, Fvec_SW_list, Fvec_NN_list


if __name__ == '__main__':
    try:
        N = int(sys.argv[1])
        M = int(sys.argv[2])
        last_timestep = M
    except:
        print "Usage:\n>>> python force_verify.py N M"
        print "- N is the different NN-versions to visualize"
        print "- M is the last timestep"
        sys.exit(0)
    path_to_file = "Important_data/TestNN/enfil_sw_3p.xyz"
    neigh_cube   = readXYZ_Files(path_to_file, "no-save-file.txt", return_array=True)
    loadPath     = findPathToData(find_tf_savefile=True)
    master_list  = []

    # Activation functions with derivatives:
    sigmoid  = lambda x: 1.0/(1+np.exp(-x))
    ddx_sig  = lambda x: sigmoid(x)*(1-sigmoid(x))
    relu     = lambda x: np.maximum(x, 0, x) # (in-place of x --> quick!!)
    ddx_relu = lambda x: np.array((x >= 0), dtype=float)
    act_tanh = lambda x: np.tanh(x)
    ddx_tanh = lambda x: 1.0 - np.tanh(x)**2 #1.0/np.cosh(x)**2

    # If showing single NN-version (trained to a certain epoch), then plot
    if N == 1:
        plot_single = True
    else:
        plot_single = False

    # Loop over different trained versions of the NN:
    for i in range(N):
        nn_eval = neural_network(loadPath, sigmoid, ddx_sig)
        Ep_SW, Ep_NN, N_atoms, F_SW, F_NN = test_structure_N_atom(neigh_cube,
                                            nn_eval, plot_single=False, last_timestep=last_timestep)
        plot_info = [Ep_SW, Ep_NN, N_atoms, nn_eval.what_epoch]
        master_list.append(plot_info)

    # Plot each epoch in a new subplot:
    if N > 1:
        plotEvolutionSWvsNN_N_diff_epochs(N, master_list)

    # Grab LAMMPS force data
    # NB!!!
    F_LAMMPS = plotLAMMPSforces1atomEvo()[:len(F_NN)]

    # Plot comparison of forces
    plotForcesSWvsNN(F_LAMMPS, F_NN, show=True)
