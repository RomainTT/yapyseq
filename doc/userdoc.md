# Yapyseq user documentation

## Why yapyseq ?

If you have a bunch of Python functions in a bunch of files, which can be called
in various orders in function of the need, you have two choices:

* Call these functions in classic python files, ordering the calls and the
  successions of them in a script. You have to rewrite from scratch the
  conditional expressions, the multiprocessing management if necessary, and 
  eventually write a lot of code.
* Use yapyseq to write a sequence. A sequence file has its own syntax, it makes
  references to Python functions that must be called. The calls, the conditional
  transitions between them, the multiprocessing, the logging, all of these
  things are automatically done by yapyseq without writing a single line of
  Python code.

## Quickstart

Let's assume that you have a project in the directory `Project/` with a 
sub-directory `Project/Functions` containing some Python files like
 `Project/Functions/hello.py`, and some basic functions like:

```python
import os

def hello(name):
    print('Hello {}!'.format(name))

def list_path(path):
    print(os.listdir(path))
```

Now create a sequence anywhere, for instance `Project/my_sequence.yaml`. Here
is the content of the sequence to call `list_path`, and if no exception has been
raised then call `hello`:

```yaml
sequence:

  nodes:
    - id: 0
      type: start
      transitions:
    - target: 1

    - id: 1
      type: function
      function: list_path
      arguments:
        path: str('/tmp/')
      transitions:
      - target: 2
        condition: not results[1].exception.is_raised
      - target: 3
        condition: results[1].exception.is_raised

    - id: 2
      type: function
      function: hello
      arguments:
        name: John
      transitions:
      - target: 3
      
    - id: 3
      type: stop
```

## Sequences in details

### Node types


### Transitions


### Examples of sequence structures
