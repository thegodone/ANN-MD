from math import *
import numpy as np
from file_management import findPathToData, readXYZ_Files
from symmetry_transform import symmetryTransformBehler
from create_train_data import generate_symmfunc_input_Si_Behler
from plot_tools import plotErrorEvolutionSWvsNN, plotEvolutionSWvsNN_N_diff_epochs
import sys
from create_train_data import PES_Stillinger_Weber
import glob
import os

def test_structure_N_atom(neigh_cube, nn_eval, plot_single=False):
    """
    Structure:
    xyz = [[0, 0, 0 ], <--- must be origo
           [x2,y2,z2],
           [x3,y3,z3],
           [........],
           [xN,yN,zN]]
    """
    # Verbose flags
    EpFlag = False
    FFlag  = False

    Ep_SW_list   = []
    Ep_NN_list   = []

    for t,xyz in enumerate(neigh_cube[0:]):
        xyz      = xyz[1:,:] # Only neighbor atoms
        Ep_SW     = PES_Stillinger_Weber(xyz)
        xyz_symm = nn_eval.create_symvec_from_xyz(xyz)
        Ep_NN    = nn_eval(xyz_symm)
        Ep_NN_list.append(Ep_NN)
        Ep_SW_list.append(Ep_SW)
        if t%50 == 0:
            # Print out progress
            sys.stdout.write("\rTimestep: %d" %t)
            sys.stdout.flush()
    print " "
    nmbr_of_atoms = neigh_cube[0].shape[0]
    if plot_single:
        plotErrorEvolutionSWvsNN(Ep_SW_list, Ep_NN_list, nmbr_of_atoms)
    else:
        return Ep_SW_list, Ep_NN_list, nmbr_of_atoms

class load_NN_from_file():
    """
    Loads and stores the neural network of choice
    """
    def __init__(self, loadPath):
        node_w_list, node_biases, what_epoch = read_NN_from_file(loadPath)
        G_funcs, nmbr_G = generate_symmfunc_input_Si_Behler()
        self.what_epoch  = what_epoch
        self.node_w_list = node_w_list
        self.node_biases = node_biases
        self.G_funcs     = G_funcs
        self.nmbr_G      = nmbr_G
        # self.act_func    = lambda x: 1.0/(1+np.exp(-x)) # sigmoid
        # self.act_func    = lambda x: np.maximum(x, 0, x) # relu (in-place, quick!)
        self.act_func    = lambda x: np.tanh(x) # tanh
    def __call__(self, sym_vec):
        """
        Evaluates the neural network and returns the energy
        """
        vec_prev_layer = sym_vec # First input
        # Evaluate the neural network:
        for i,w_mat in enumerate(self.node_w_list):
            out_layer  = np.dot(vec_prev_layer, w_mat)
            out_layer += self.node_biases[i]
            if i != len(self.node_w_list)-1: # We dont use act_func on output layer
                vec_prev_layer = self.act_func(out_layer)
        return float(out_layer)
    def create_symvec_from_xyz(self, xyz):
        symm_vec = symmetryTransformBehler(self.G_funcs, xyz)
        return symm_vec
    def what_epoch(self):
        return self.what_epoch

def evaluate_SW_forces(xyz, EpFlag, FFlag):
    """
    Stillinger and Weber,  Phys. Rev. B, v. 31, p. 5262, (1985)

    epsilon, sigma, a, lambda, gamma, costheta0, A, B, p, q
    2.1683 , 2.0951,  1.80,  21.0, 1.20,  -1.0/, 7.049556277,  0.6022245584,  4.0,  0.0
    """
    eps   = 2.1683
    sig   = 2.0951
    a     = 1.80
    lamb  = 21.0
    gam   = 1.2
    A     = 7.049556277
    B     = 0.6022245584
    p     = 4.0
    q     = 0.0
    cos0 = -1.0/3.0

    f_vec = np.zeros(3)

    r  = np.linalg.norm(xyz[1:,:], axis=1) # Only j != i

    def U2_serial(r):
        if (r < a*sig):
            return A*eps*(B*(sig/r)**p-(sig/r)**q) * np.exp(sig/(r-a*sig))
        else:
            return 0.0
    # U2 = np.array([U2_serial(r[0]), U2_serial(r[1])])
    # dU2dR = -A*eps*sig*(B*(sig/r)**p - (sig/r)**q)*np.exp(sig/(-a*sig + r))/(-a*sig + r)**2 + A*eps*(-B*p*(sig/r)**p/r + q*(sig/r)**q/r)*np.exp(sig/(-a*sig + r))
    # for j in [1,2]:
        # print xyz[j,:]*dU2dR[j-1]/r[j-1]
        # f_vec += xyz[j,:]*dU2dR[j-1]/r[j-1]
    # print dU2dR, sum(dU2dR)

    # rij           = r[0]
    # rik           = r[1]
    # rjk           = np.linalg.norm(xyz[1,:]-xyz[2,:])
    # cos_theta_jik = np.dot(xyz[1],xyz[2])                / (rij*rik)
    # cos_theta_ijk = np.dot(xyz[0]-xyz[1], xyz[2]-xyz[1]) / (rij*rjk)
    # cos_theta_ikj = np.dot(xyz[0]-xyz[2], xyz[1]-xyz[2]) / (rik*rjk)
    # print "cos Theta:",cos_theta_jik, cos_theta_ijk, cos_theta_ikj

    # xyz /= sig
    # rij /= sig
    # rik /= sig
    # rjk /= sig
    # xyz_jk = xyz[2]-xyz[1]
    #
    # def h(r1, r2, cos_theta):
    #     if (r1 < a) and (r2 < a):
    #         term = eps * lamb * exp(gam/(r1-a)) * exp(gam/(r2-a)) * (cos_theta - cos0)**2
    #     else:
    #         term = 0.0
    #     return term
    #
    # h_jik = h(rij, rik, cos_theta_jik)
    # h_ijk = h(rij, rjk, cos_theta_ijk)
    # h_ikj = h(rik, rjk, cos_theta_ikj)

    """dhjik_dri = -gam*h_jik*((xyz[1]/rij)*1/(rij-a)**2 + (xyz[2]/rik)*1/(rik-a)**2) \
                + 2*lamb*np.exp(gam/(rij-a) + gam/(rik-a))*(cos_theta_jik - cos0)  \
                * ((xyz[1]/rij)*(1/rik) + (xyz[2]/rik)*(1/rij) - (xyz[1]/(rij*rik)+xyz[2]/(rik*rij))*cos_theta_jik)

    dhijk_dri = -gam*h_ijk*((xyz[1]/rij)*1/(rij-a)**2) \
                + 2*lamb*np.exp(gam/(rij-a) + gam/(rjk-a))*(cos_theta_ijk - cos0) \
                * ((xyz_jk/rjk)*(1/rij) + (xyz[1]/rij)*(1/rij)*cos_theta_ijk)

    dhikj_dri = -gam*h_ikj*((xyz[2]/rik)*1/(rik-a)**2) \
                + 2*lamb*np.exp(gam/(rik-a) + gam/(rjk-a))*(cos_theta_ikj - cos0) \
                *((-xyz_jk/rjk)*(1/rik) + (xyz[2]/rik)*(1/rik)*cos_theta_ikj)"""
    if FFlag:
        print "Tot 2-body force:", f_vec
        print "Tot 3-body force:", dhjik_dri + dhijk_dri + dhikj_dri
        print "Total force     :", f_vec + dhjik_dri + dhijk_dri + dhikj_dri

    # U2_sum = np.sum(U2)/2.
    # U3_sum = h_jik/3.

    # print "Potential E (SW):", U_SW
    # if abs(U3_sum + U2_sum) - abs(U_SW) > 1E-10:
    #     print "Pot. E (SW v2)  :", U3_sum + U2_sum
    return None #U3_sum + U2_sum

def evaluate_NN_forces(xyz, nn_eval, EpFlag, FFlag):
    """
    Evaluation checked and found bug free
    """
    xyz_symm = nn_eval.create_symvec_from_xyz(xyz)
    Ep_NN    = nn_eval(xyz_symm)
    if EpFlag:
        print "Potential E (NN):", float(Ep_NN)
    if FFlag:
        print "Forces (NN):", "N/A"
    return Ep_NN


def read_NN_from_file(loadPath):
    which_graph_file = loadPath + "graph.dat"
    # Remove filename at the end (variable length)
    for i,letter in enumerate(reversed(loadPath)):
        if letter == "/": # Find index i of last letter "/" in path
            break
    loadPath = loadPath[:-i] # Now points to the folder, not the file
    folder_list = glob.glob(loadPath + "graph*")
    folder_list = sorted(folder_list, key=os.path.getmtime)# Sort by time created
    if len(folder_list) == 1:
        which_graph_file = loadPath + folder_list[0]
    else:
        print "\nFound multiple graph_EPOCHS.dat-files. Choose one:"
        for i,graph_file in enumerate(folder_list):
            print " %d)"%i, graph_file[61:]
        i = int(raw_input("Input an integer: "))
        which_graph_file = folder_list[i] # Dont use loadPath, since glob-list has entire (relative) path
        what_epoch       = int(which_graph_file[66:-4])
    with open(which_graph_file, "r") as nn_file:
        hdn_layers, nodes, act_func, nn_inp, nn_out = nn_file.readline().strip().split()
        hdn_layers   = int(hdn_layers); nodes = int(nodes); nn_inp = int(nn_inp); nn_out = int(nn_out)
        tot_w_lines  = (hdn_layers-1)*nodes + nn_inp + 1 # Last one from output layer
        node_weights = np.zeros((tot_w_lines,nodes))
        node_biases  = []
        line_index = 0 # We dont care about first line, already taken care of above
        for line in nn_file:
            line = line.strip().split() # Remove newline and spaces. Then split into list of numbers
            if not line:
                continue # Skip line between W and B
            line = np.array(line, dtype=float) # Convert list of strings to array of floats
            if line_index < tot_w_lines: # Reading node weights
                # print "W",line_index,line[0] # Error checking
                node_weights[line_index,:] = line
            else:
                # print "B",line_index,line[0] # Error checking
                node_biases.append(line)
            line_index += 1
    """
    Convert to proper matrices
    """
    node_w_list = []
    node_w_list.append(node_weights[0:nn_inp,:])
    # print node_weights[nn_inp:nn_inp+nodes,:]
    # raw_input("ASDF")
    for i in range(nn_inp, tot_w_lines-1, nodes): # Loop over hidden layer 2 -->
        node_w_list.append(node_weights[i:i+nodes,:])
    node_w_list.append(node_weights[-1,:]) # This is output node
    return node_w_list, node_biases, what_epoch



if __name__ == '__main__':
    try:
        N = int(sys.argv[1])
    except:
        print "Usage:\n>>> python force_verify.py 5"
        sys.exit(0)
    path_to_file = "Important_data/TestNN/enfil_sw_4p.xyz"
    neigh_cube   = readXYZ_Files(path_to_file, "no-save-file.txt", return_array=True)
    loadPath     = findPathToData(find_tf_savefile=True)
    master_list  = []
    for i in range(N):
        nn_eval  = load_NN_from_file(loadPath)
        Ep_SW, Ep_NN, N_atoms = test_structure_N_atom(neigh_cube, nn_eval)
        master_list.append( [Ep_SW, Ep_NN, N_atoms, nn_eval.what_epoch] )

    # Plot each epoch on new subplot:
    plotEvolutionSWvsNN_N_diff_epochs(N, master_list)
