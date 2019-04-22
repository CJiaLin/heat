import os
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegressionCV
from sklearn.model_selection import StratifiedShuffleSplit, ShuffleSplit
from sklearn.multiclass import OneVsRestClassifier
from sklearn.metrics import f1_score

from heat.utils import load_data, hyperboloid_to_klein, load_embedding

import functools
import fcntl
import argparse

def evaluate_node_classification(klein_embedding, labels,
	label_percentages=np.arange(0.02, 0.11, 0.01), n_repeats=10):

	print ("Evaluating node classification")

	num_nodes, dim = klein_embedding.shape

	f1_micros = np.zeros((n_repeats, len(label_percentages)))
	f1_macros = np.zeros((n_repeats, len(label_percentages)))
	
	model = LogisticRegressionCV()
	split = StratifiedShuffleSplit

	if len(labels.shape) > 1: # multilabel classification
		model = OneVsRestClassifier(model)
		split = ShuffleSplit

	n = len(klein_embedding)

	for seed in range(n_repeats):
	
		for i, label_percentage in enumerate(label_percentages):

			sss = split(n_splits=1, test_size=1-label_percentage, random_state=seed)
			split_train, split_test = next(sss.split(klein_embedding, labels))
			model.fit(klein_embedding[split_train], labels[split_train])
			predictions = model.predict(klein_embedding[split_test])
			f1_micro = f1_score(labels[split_test], predictions, average="micro")
			f1_macro = f1_score(labels[split_test], predictions, average="macro")
			f1_micros[seed,i] = f1_micro
			f1_macros[seed,i] = f1_macro
		print ("completed repeat {}".format(seed+1))

	return label_percentages, f1_micros.mean(axis=0), f1_macros.mean(axis=0)

def touch(path):
	with open(path, 'a'):
		os.utime(path, None)

def read_edgelist(fn):
	edges = []
	with open(fn, "r") as f:
		for line in (l.rstrip() for l in f.readlines()):
			edge = tuple(int(i) for i in line.split("\t"))
			edges.append(edge)
	return edges

def lock_method(lock_filename):
	''' Use an OS lock such that a method can only be called once at a time. '''

	def decorator(func):

		@functools.wraps(func)
		def lock_and_run_method(*args, **kwargs):

			# Hold program if it is already running 
			# Snippet based on
			# http://linux.byexamples.com/archives/494/how-can-i-avoid-running-a-python-script-multiple-times-implement-file-locking/
			fp = open(lock_filename, 'r+')
			done = False
			while not done:
				try:
					fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
					done = True
				except IOError:
					pass
			return func(*args, **kwargs)

		return lock_and_run_method

	return decorator 

def threadsafe_fn(lock_filename, fn, *args, **kwargs ):
	lock_method(lock_filename)(fn)(*args, **kwargs)

def save_test_results(filename, seed, data, ):
	d = pd.DataFrame(index=[seed], data=data)
	if os.path.exists(filename):
		test_df = pd.read_csv(filename, sep=",", index_col=0)
		test_df = d.combine_first(test_df)
	else:
		test_df = d
	test_df.to_csv(filename, sep=",")

def threadsafe_save_test_results(lock_filename, filename, seed, data):
	threadsafe_fn(lock_filename, save_test_results, filename=filename, seed=seed, data=data)

def parse_args():

	parser = argparse.ArgumentParser(description='Load Hyperboloid Embeddings and evaluate node classification')
	
	parser.add_argument("--edgelist", dest="edgelist", type=str, default="datasets/cora_ml/edgelist.tsv",
		help="edgelist to load.")
	parser.add_argument("--features", dest="features", type=str, default="datasets/cora_ml/feats.csv",
		help="features to load.")
	parser.add_argument("--labels", dest="labels", type=str, default="datasets/cora_ml/labels.csv",
		help="path to labels")

	parser.add_argument('--directed', action="store_true", help='flag to train on directed graph')


	parser.add_argument("--embedding", dest="embedding_filename",  
		help="path of embedding to load.")

	parser.add_argument("--test-results-dir", dest="test_results_dir",  
		help="path to save results.")

	parser.add_argument("--seed", type=int, default=0)

	return parser.parse_args()

def main():

	args = parse_args()

	graph, features, node_labels = load_data(args)
	print ("Loaded dataset")

	hyperboloid_embedding_df = load_embedding(args.embedding_filename)
	hyperboloid_embedding = hyperboloid_embedding_df.values

	klein_embedding = hyperboloid_to_klein(hyperboloid_embedding)

	label_percentages, f1_micros, f1_macros = evaluate_node_classification(klein_embedding, node_labels)

	test_results = {}
	for label_percentage, f1_micro, f1_macro in zip(label_percentages, f1_micros, f1_macros):
		test_results.update({"{:.2f}_micro".format(label_percentage): f1_micro})
		test_results.update({"{:.2f}_macro".format(label_percentage): f1_macro})

	test_results_dir = args.test_results_dir
	if not os.path.exists(test_results_dir):
		os.makedirs(test_results_dir)
	test_results_filename = os.path.join(test_results_dir, "test_results.csv")
	test_results_lock_filename = os.path.join(test_results_dir, "test_results.lock")

	touch (test_results_lock_filename)

	print ("saving test results to {}".format(test_results_filename))
	threadsafe_save_test_results(test_results_lock_filename, test_results_filename, args.seed, data=test_results )

	
if __name__ == "__main__":
	main()