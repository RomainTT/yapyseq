#!/usr/bin/env python
# coding: utf-8

from time import sleep, time


def return_timestamp_after_sleep(sleep_time: int) -> float:
    sleep(sleep_time)
    return time()


def return_hello_world() -> str:
    return "Hello world!"
