# yapyseq

Yet Another Python Sequencer

| Item          | master        | dev   |
| ------------- | ------------- | ----- |
| CI status     | [![Build Status](https://travis-ci.com/RomainTT/yapyseq.svg?branch=master)](https://travis-ci.com/RomainTT/yapyseq) | [![Build Status](https://travis-ci.com/RomainTT/yapyseq.svg?branch=dev)](https://travis-ci.com/RomainTT/yapyseq) |
| version       | [![Pypi](https://img.shields.io/pypi/v/yapyseq.svg)](https://pypi.org/project/yapyseq/)      |  N/A  |

## Why yapyseq ?

If you have a bunch of Python functions in a bunch of files, which can be called
in various orders in function of the need, you have two choices:

* Call these functions in classic python scripts, ordering the calls with
  Python statements. You have to write from scratch the conditional structures,
  the multiprocessing management if necessary, and eventually write a lot of 
  code.
* Use yapyseq to write a sequence. A sequence file has its own syntax, it makes
  references to Python functions that must be called. The calls, the conditional
  transitions between them, the multiprocessing, the logging, all of these
  things are automatically done by yapyseq without writing a single line of
  Python code.

## How to use ?

Please read the [user documentation](doc/userdoc.md).

## How to contribute ?

Please read the [developer documentation](doc/devdoc.md).
