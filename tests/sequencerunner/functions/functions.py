#!/usr/bin/env python
# coding: utf-8

from time import sleep, time
from typing import Any


def return_timestamp_after_sleep(sleep_time: int) -> float:
    sleep(sleep_time)
    return time()


def return_hello_world() -> str:
    return "Hello world!"


def write_arg_in_file(arg: Any, file: str) -> None:
    with open(file, 'a') as f:
        f.write("{}\n".format(arg))


def return_arg(arg: Any) -> any:
    return arg
