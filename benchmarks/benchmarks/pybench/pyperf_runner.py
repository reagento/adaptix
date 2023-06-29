# pylint: disable=import-error,no-name-in-module
import gc
import json
import os

import pyperf

from benchmarks.pybench.utils import load_by_object_ref


def main():
    bench_name = os.environ['PYBENCH_NAME']
    func = load_by_object_ref(os.environ['PYBENCH_ENTRYPOINT'])
    params = json.loads(os.environ['PYBENCH_PARAMS'])

    benchmark_plan = func(*params)

    gc.collect()
    runner = pyperf.Runner()
    runner.bench_func(
        bench_name,
        benchmark_plan.func,
        *benchmark_plan.args,
    )


if __name__ == '__main__':
    main()
