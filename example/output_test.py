""" Script to test the ML model. Takes a database of candidates from a GA
    search with target values set in atoms.info['key_value_pairs'][key] and
    returns the errors for a random test and training dataset.
"""
from __future__ import print_function

import numpy as np

from ase.ga.data import DataConnection
from atoml.data_setup import (get_unique, get_train, data_split,
                              target_standardize, remove_outliers)
from atoml.fingerprint_setup import standardize, normalize, return_fpv
from atoml.feature_select import sure_independence_screening, iterative_sis
from atoml.particle_fingerprint import ParticleFingerprintGenerator
from atoml.predict import FitnessPrediction


# Connect database generated by a GA search.
db = DataConnection('../data/gadb.db')

# Get all relaxed candidates from the db file.
print('Getting candidates from the database')
all_cand = db.get_all_relaxed_candidates(use_extinct=False)

# Setup the test and training datasets.
testset = get_unique(candidates=all_cand, testsize=500, key='raw_score')
trainset = get_train(candidates=all_cand, trainsize=500,
                     taken_cand=testset['taken'], key='raw_score')
split = data_split(candidates=all_cand, nsplit=3, key='raw_score')
rm = remove_outliers(candidates=all_cand, key='raw_score')
std = target_standardize(trainset['target'])

# Get the list of fingerprint vectors and normalize them.
print('Getting the fingerprint vectors')
fpv = ParticleFingerprintGenerator(get_nl=False, max_bonds=13)
test_fp = return_fpv(testset['candidates'], [fpv.bond_count_fpv])
train_fp = return_fpv(trainset['candidates'], [fpv.bond_count_fpv],
                      writeout=True)
sfp = standardize(train=train_fp, test=test_fp)
nfp = normalize(train=train_fp, test=test_fp)

sis = sure_independence_screening(target=trainset['target'],
                                  train_fpv=nfp['train'], size=4,
                                  writeout=True)
sis = iterative_sis(target=trainset['target'], train_fpv=nfp['train'], size=4,
                    step=1)

# Set up the prediction routine.
krr = FitnessPrediction(ktype='gaussian',
                        kwidth=0.5,
                        regularization=0.001)

# Do the predictions.
cvm = krr.get_covariance(train_matrix=nfp['train'])
cinv = np.linalg.inv(cvm)
print('Making the predictions')
pred = krr.get_predictions(train_fp=nfp['train'],
                           test_fp=nfp['test'],
                           cinv=cinv,
                           train_target=trainset['target'],
                           test_target=testset['target'],
                           get_validation_error=True,
                           get_training_error=True)
