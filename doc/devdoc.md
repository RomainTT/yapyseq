# Developer documentation

### Sequences description

Core data of a sequence is saved in one .yaml file in the directory named 
`sequences`. The template of one of these .yaml files can be found in 
`seq_template.yaml`.

### Nodes

Here are the different kinds of nodes:
  * start
  * stop
  * function
  * parallel_split
  * parallel_sync
  * variable
 
In any sequence, there is at least one start and one stop.
 
### Sub-sequences

Sub-sequences can be contained in one node. That means another sequence is
called in a node.

A single instance of `SequenceRunner` manages all the nodes of its sequence. If
a sub-sequence is called, a new instance of `SequenceRunner` is created to
manage the sub-sequence. This sub-sequence is considered as a standard node by
the parent sequence.

### Sequence execution management

An instance of `SequenceRunner` runs a new thread to run a node of type 
function. When the thread is ended, it means that the function is over. In that 
case, the `SequenceRunner` detects it, find the next node, and start a new 
thread for this next node. All kind of output from a node are given to the 
`SequenceRunner` through a shared memory (a Queue). These outputs can then be 
used for logging, for decision making, can be transferred to other nodes, etc.
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

```
O -> O ->| O -> O |-> O -> O
     ^   |-> O -> |        |
     |---------------------|
```

Sequence that won't work: a sequence with one of several parallel branches that
escape the synchronization point by using a transition directly to the outside
of the synchronization. The synchronization will be stuck and never be done.
This kind of sequence is hardly detectable (but not impossible) by yapyseq. User
must be aware of this danger.

### Sequence variables of a sequence

A sequence can hold a certain amount of variables possesses by the 
`SequenceRunner`. These variables can only be referenced in the sequence file.
Node functions cannot use them directly, but some sequence variables can be 
given to them through arguments. Only copies of variables are given to functions
not references themselves to prevent conflicting accesses to a same variables.

Sequence variables are fully managed by the `SequenceRunner`: creation,
transfer, deletion, update. This avoids access conflicts to sequences
variables, because there is only one thread which modifies them: the thread
of the `SequenceRunner`.

There are different kinds of sequence variables:
  * Built-in variables, created and managed by yapyseq. For instance, the return
    value of nodes. They are read-only for users.
  * User constants, defined in the sequence file or given by user when he
    runs the sequence. For instance, a comment about the run. They are read-only
    for users.
  * On-the-fly variables, created during the run of the sequence, for instance
    to manage loop counts. These variables are managed in special nodes of type
    `variable`. In these nodes, a dictionary is given to create/update the
    variables. In this dictionary, keys are the name of the variables and values
    are Python statements that will be evaluated and stored in their
    corresponding variable. These special nodes do not allow to modify built-in
    variables and user constants.
    
All of these variables can be used in conditions of transitions.

List of built-in variables:
  * returns: Return values of every nodes (last run only)
      A dedicated data structure is used to store the result of a node function.
      It contains the exception if it raised one, and the return object.
      Datastructure:
        
          result
              result.returned
              result.exception
                  result.exception.is_raised
                  result.exception.name
                  result.exception.args

## Python expressions in sequence files

There are two types of items in the sequence file for which the string value is
**always** evaluated as a Python expression:
  * The condition of the transitions
  * The variables of a node of type "variable"

It means that these values will be given to the Python built-in function 
`eval()`.

Unfortunately, yaml automatically removes quotes from values. It means that the
following yaml code:

    my_key: "my_value"

...is equivalent to the following one:

    my_key: my_value

It means that `eval()` will try to refer to the variable `my_value` instead of
the string `"my_value"`. In order to give a single string, it must be precised
in the sequence file, with one of the following syntax:

    my_key: str(my_value)
    my_key: u"my_value"


# Ideas

Set priorities on transitions. Priorities sharing the same source node must have
unique priorities among them. When evaluating transitions to find the next node,
priorities can be used to select only one transitions when several are possible.
Nodes of type "parallel_split" do not need priorities on their transitions.

FOR REFACTOR:
The SequenceAnalyzer becomes the SequenceReader, it only checks and parses the
sequence file, to return a dictionary of nodes.
The SequenceRunner now possesses the main dictionary of nodes, where each key
is a node id, and values are Node objects (like FunctionNode instance).
If actions can be written in the nodes themselves rather than in the
SequenceRunner, it is better. For example, the start of a new process to run 
a function can be in a public method of FunctionNode.
In any case, the SequenceRunner is the one that guaranties the right order of
execution, like a master of orchestra. The SequenceRunner still owns the
queues to store results. Keeping history, evaluate Python expressions, start
functions, every one of these actions can be coded in Node classes.
Sequence variables can still be owned by the SequenceRunner.