#!/bin/bash

TASKIQ_PROCESS=1 taskiq worker config.taskiq_app:taskiq_broker --workers=2 --fs-discover --max-async-tasks=5 --max-prefetch=0 &
wait