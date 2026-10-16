from benchmarks.pybench.director_api import BenchmarkDirector, BenchSchema, CheckParams


def test_resume_runs_missing_cases_with_pyperf_options(monkeypatch):
    existing = BenchSchema(entry_point=lambda: None, base="existing", tags=[], kwargs={}, used_distributions=[])
    missing = BenchSchema(entry_point=lambda: None, base="missing", tags=[], kwargs={}, used_distributions=[])
    director = BenchmarkDirector(
        benchmark="resume",
        env_spec={},
        check_params=lambda env_spec: CheckParams(stdev_rel_threshold=0.04),
        schemas=[existing, missing],
    )
    accessor = director.make_accessor()
    runner = director.make_bench_runner(accessor, director.make_bench_checker(accessor))
    calls = []
    monkeypatch.setattr(accessor, "get_case_result", lambda schema: {} if schema is existing else None)
    monkeypatch.setattr(runner, "run_one_benchmark", lambda schema, **kwargs: calls.append((schema, kwargs)))

    runner.run_benchmarks(missing=True, pyperf_arg=["--affinity=2", "--processes=6"])

    assert calls == [(missing, {"pyperf_args": ["--affinity=2", "--processes=6"]})]  # noqa: S101
