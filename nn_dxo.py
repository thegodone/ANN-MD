"""
Train a neural network to approximate a function from DXOMARK.com
"""

import tensorflow as tf
import numpy as np
import sys
import datetime as time
import os
import shutil
import matplotlib.pyplot as plt

#import neuralNetworkModel as nn
import neuralNetworkXavier as nnx

# Data: https://www.dxomark.com/cameras#hideAdvancedOptions=false&viewMode=list&yDataType=rankDxo
# Extracted data: https://regex101.com/r/vF9pS7/1

x = np.loadtxt("values_dxo.dat"); y = len(x)/4
x = x.reshape((y,4))

totalDataPoints = x.shape[0] #(323, 4)

np.savetxt("values_array_dxo.dat",x,delimiter=',\t',fmt='%.1f')

# Pick out test data randomly from the data
randRows = np.random.choice(totalDataPoints, 80, replace=False)
global xRand
xRand = x[randRows,:]

# Pick out the rest for training data
leftoverRows = [i for i in range(totalDataPoints) if i not in randRows]

global trainData
trainData = x[leftoverRows,:]
np.random.shuffle(trainData) # Shuffle rows of the data to minimize impact of ordering of the data

def functionData(trainSize,testSize):
    """
    RIGHT:
    Create train input for NN and test data
    """
    x_train = trainData[:,1:]
    x_train = x_train.reshape([trainSize,3])
    y_train = trainData[:,0]
    y_train = y_train.reshape([trainSize,1])

    x_test  = xRand[:,1:]
    x_test = x_test.reshape([testSize,3])
    y_test  = xRand[:,0]
    y_test = y_test.reshape([testSize,1])
    return x_train, y_train, x_test, y_test

# reset so that variables are not given new names
tf.reset_default_graph()

# number of samples
trainSize = 323-80

batchSize = 323-80
testSize = 80

# get random input
xTrain, yTrain, xTest, yTest = functionData(trainSize,testSize)

# number of inputs and outputs
inputs  = 3
outputs = 1

x = tf.placeholder('float', [None, inputs],  name="x")
y = tf.placeholder('float', [None, outputs], name="y")


neuralNetwork = lambda data : nnx.modelSigmoid(data, nNodes=nNodes, hiddenLayers=hiddenLayers,
                                               wInitMethod='normal', bInitMethod='normal')

def train_neural_network(x,epochs, nNodes,hiddenLayers, plot=False, no_print=False, learning_rate_choice=0.001):

    # begin session
    with tf.Session() as sess:

        # pass data to network and receive output
        #prediction = neuralNetwork(x)
        prediction, weights, biases, neurons = neuralNetwork(x)

        cost = tf.nn.l2_loss( tf.sub(prediction, y) )

        optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate_choice).minimize(cost)

        # number of cycles of feed-forward and backpropagation
        numberOfEpochs = epochs; bestEpochTestLoss = -1

        # initialize variables or restore from file
        saver = tf.train.Saver(weights + biases, max_to_keep=None)
        sess.run(tf.initialize_all_variables())
        """if loadFlag:
            saver.restore(sess, loadFileName)
            print 'Model restored'"""


        bestTrainLoss = 1E100; bestTestLoss = 1E100
        # loop through epocs
        for epoch in range(numberOfEpochs):
            # loop through batches and cover whole data set for each epoch
            _, epochLoss = sess.run([optimizer, cost], feed_dict={x: xTrain, y: yTrain})

            # compute test set loss
            _, testCost = sess.run([optimizer, cost], feed_dict={x: xTest, y: yTest})

            if no_print:
                pass
            else:
                if (epoch+1)%int(numberOfEpochs/100.) == 0:
                    print 'Epoch %5d out of %5d trainloss/N: %10g, testloss/N: %10g' % \
                          (epoch+1, numberOfEpochs, epochLoss/float(trainSize), testCost/float(testSize))

            """if epochLoss < bestTrainLoss and epochLoss/float(trainSize) < 20.0:
                bestTrainLoss = epochLoss"""
            if testCost < bestTestLoss and testCost//float(testSize) < 20.0:
                bestTestLoss = testCost
                bestEpochTestLoss = epoch
                if plot:
                    yy = sess.run(prediction, feed_dict={x: xTest})
                    error = yy-yTest
                    break

        if plot:
            #yy = sess.run(prediction, feed_dict={x: xTest})
            try:
                error = yy-yTest
            except:
                print "To plot: Run for more epochs (maybe 100K?)! Error is too large!"; sys.exit()
            plt.hist(error,bins=13)
            plt.xlabel('Test case (number)')
            plt.ylabel('Error: Prediciton - Exact answer')
            np.savetxt("nndxo_err.dat",error)
            plt.show()


    return weights, biases, neurons, epochLoss/trainSize



##### main #####
print "---------------------------------------"

learning_rate_choice = 0.001 # Default for AdamOptimizer is 0.001
testCases = 0;
print "Learning rate:", learning_rate_choice

epochlossPerNPrev = 1e100   # "Guaranteed" worse than anything
nNodesBest = 0; hLBest = 0; epochBest = 0
for hiddenLayers in [10]:
    for nNodes in [12]:
        for epochs in [100000]:
            testCases += 1
            weights, biases, neurons, epochlossPerN = train_neural_network(x, epochs, \
                    nNodes, hiddenLayers,plot=True,no_print=False,learning_rate_choice=learning_rate_choice)
            print "\nHid.layers: %2.d, nodes/l: %2.d, epochs: %d, loss/N: %f" %(hiddenLayers,nNodes,epochs,epochlossPerN)
            if epochlossPerN < epochlossPerNPrev:
                epochlossPerNPrev = epochlossPerN
                nNodesBest = nNodes
                hLBest     = hiddenLayers
                epochBest  = epochs
if testCases > 1: # Print out testing different hdn layers and nmbr of nodes
    print "---------------------------------------"
    print "Best combination found after %d epochs:" %epochBest
    print "Layers: %d, nodes/layer: %d, loss/N: %e" %(hLBest,nNodesBest,epochlossPerNPrev)
    print "---------------------------------------"
