#!/bin/bash

TASKIQ_PROCESS=1 taskiq scheduler config.taskiq_app:scheduler --log-level=INFO --fs-discover &
wait