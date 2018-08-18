# Developer documentation

## Sequences

Core data of a sequence is saved in one .yaml file in the directory named 
`sequences`. The template of one of these .yaml files can be found in 
`seq_template.yaml`.

### Special nodes

Some special nodes, managed by yapyseq:
  * parallel_split
  * parallel_sync
 
### Sub-sequences

Sub-sequences can be contained in one node. That means another sequence is
called in a node.

A single instance of `SequenceRunner` manages all the nodes of its sequence. If
a sub-sequence is called, a new instance of `SequenceRunner` is created to
manage the sub-sequence. This sub-sequence is considered as a standard node by
the parent sequence.

### Sequence execution management

An instance of `SequenceRunner` runs a new thread to run a node. When the thread
is ended, it means that the node has finished its action. In that case, the 
`SequenceRunner` detects it, ask for the next node to the `SequenceAnalyzer` and
start a new thread for this next node. All kind of output from a node are given
to the `SequenceRunner` through a shared memory. These outputs can then be used
for logging, for decision making, can be transferred to other nodes, etc.
At any time, a `SequenceRunner` has an overview of all the nodes that are
running in its sequence.

To manage "parallel split" nodes, the `SequenceRunner` simply starts several 
nodes instead of one after the transition.
To manage "parallel sync" nodes, the `SequenceRunner` keeps a history of the
transitions that have already been performed to this node, and when all
necessary transitions are done, it can continue the sequence and run the
following nodes.

A tricky phenomenon can appear if 2 parallel branches that sync at some point
are started several times in loop. If the execution of the branches is quicker 
than the loop iteration, then no problem. But else, the synchronization node can
be lost. That is why each passage in a "parallel split" node gives a "color" to
the nodes that are started. Each new passage in this "parallel split" gives a 
different color. Afterwards, the "parallel sync" will only synchronize branches
of the same color. It means that the `SequenceRunner` will keep history of the
transitions that have already been performed to the synchronization node, 
keeping also their colors.

O -> O ->| O -> O |-> O -> O
     ^   |-> O -> |        |
     |---------------------|

Sequence that won't work: a sequence with one of several parallel branches that
escape the synchronization point by using a transition directly to the outside
of the synchronization. The synchronization will be stuck and never be done.
This kind of sequence is hardly detectable (but not impossible) by yapyseq. User
must be aware of this danger.

### Global variables of a sequence

TODO: explain how it works.