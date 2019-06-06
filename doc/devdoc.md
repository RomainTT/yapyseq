# Yapyseq developer documentation

TODO: catch and display internal errors of yapyseq inside sub-processes.
	  Today, processes die and runner waits for the queue forever.

## Internal architecture

Here are the main classes of yapyseq:
* `SequenceRunner`: the aim of an instance of this class is to run the nodes 
  and manage the transitions.
* `SequenceReader`: the aim of an instance of this class is to read a `.yaml` 
  file that describes a sequence, create Node objects using parameters from this 
  file, and make them available through its API.
* `FunctionGrabber`: the aim of an instance of this class is:
   * to import the python files containing the functions that can be
     called in a given sequence.
   * Provide these functions on demand through its API

When running a sequence, a `SequenceRunner` is created first and this object 
creates its own `SequenceReader` and `FunctionGrabber` during its 
initialization.

## Node management

### Function node

An instance of `SequenceRunner` runs a new thread to run a node of type 
"function". When the thread is ended, it means that the function is over. In 
that case the `SequenceRunner` detects it, finds the next node, and starts a new 
thread for this next node. All kind of output from a node are given to the 
`SequenceRunner` through a shared memory (a Queue). These outputs can then be 
used for logging, for decision making, can be transferred to other nodes, etc.
At any time, a `SequenceRunner` has an overview of all the nodes that are
running in its sequence.

### Parallel split and sync nodes

To manage "parallel split" nodes, the `SequenceRunner` simply starts several 
nodes instead of one after the transition.

To manage "parallel sync" nodes, the `SequenceRunner` keeps a history of the
transitions that have already been performed to this node, and when all
necessary transitions are done, it can continue the sequence and run the
following nodes.

### Sub-sequence node

Sub-sequences can be contained in one node. That means another sequence is
called in a node.

A single instance of `SequenceRunner` manages all the nodes of its sequence. If
a sub-sequence is called, a new instance of `SequenceRunner` is created to
manage the sub-sequence. This sub-sequence is considered as a standard node by
the parent sequence.
