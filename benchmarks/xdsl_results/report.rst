On this host, LLVM reduces latency for short lists. Large-list loading is
close to x86 or slower; the nullable-union loader on Python 3.14 is about
22% slower. The same-algorithm model-loader control is within roughly 6% of
LLVM. Specialized production model loaders are about 2.4 to 4.6 times faster
than the experimental LLVM loaders. LLVM O3 gives no consistent improvement
over O2. These results do not establish a general backend ranking.


``P`` marks a Python root fallback, including ``as_is`` for int dumping.
Reference x86 is only meaningful for model loading; other reference entries
are omitted. Fallback results are included for completeness and are not
evidence of LLVM-generated performance.


Execution: CPython 3.13.15 (nanoseconds per call)
-------------------------------------------------


.. list-table::
   :header-rows: 1

   * - Case
     - Python
     - x86
     - Reference x86
     - LLVM O0
     - LLVM O2
     - LLVM O3
   * - int/load
     - 18.9
     - 9.4
     - —
     - 10.3
     - 10.2
     - 10.2
   * - int/dump
     - 11.8
     - 11.8 P
     - —
     - 11.8 P
     - 11.8 P
     - 11.8 P
   * - list_any32/load
     - 909.5
     - 34.3
     - —
     - 46.3
     - 30.2
     - 30.2
   * - list_any32/dump
     - 744.7
     - 33.2
     - —
     - 46.5
     - 29.7
     - 29.8
   * - list_int0/load
     - 175.8
     - 16.5
     - —
     - 14.8
     - 13.8
     - 13.9
   * - list_int0/dump
     - 91.7
     - 14.9
     - —
     - 14.7
     - 13.1
     - 13.2
   * - list_union0/load
     - 171.4
     - 16.1
     - —
     - 14.5
     - 13.4
     - 13.4
   * - list_union0/dump
     - 90.4
     - 14.8
     - —
     - 14.4
     - 13.0
     - 13.1
   * - list_int32/load
     - 1081.9
     - 39.7
     - —
     - 50.2
     - 35.8
     - 36.1
   * - list_int32/dump
     - 753.2
     - 32.7
     - —
     - 46.4
     - 29.8
     - 29.7
   * - list_union32/load
     - 6729.6
     - 45.3
     - —
     - 58.9
     - 40.1
     - 41.2
   * - list_union32/dump
     - 776.5
     - 34.7
     - —
     - 49.3
     - 31.5
     - 31.7
   * - list_int1024/load
     - 35134.3
     - 751.8
     - —
     - 1371.5
     - 791.4
     - 792.2
   * - list_int1024/dump
     - 26772.1
     - 632.2
     - —
     - 1235.2
     - 620.1
     - 620.4
   * - list_union1024/load
     - 219337.8
     - 889.1
     - —
     - 1539.3
     - 953.8
     - 978.4
   * - list_union1024/dump
     - 27382.1
     - 652.6
     - —
     - 1295.0
     - 658.3
     - 656.8
   * - model_dict4/load
     - 178.9
     - 30.6
     - 77.6
     - 81.6
     - 77.8
     - 78.1
   * - model_dict4/dump
     - 64.9
     - 32.2
     - —
     - 64.4 P
     - 64.4 P
     - 64.5 P
   * - model_dict16/load
     - 592.9
     - 52.8
     - 213.9
     - 217.5
     - 223.2
     - 223.2
   * - model_dict16/dump
     - 243.0
     - 48.4
     - —
     - 237.7 P
     - 235.2 P
     - 234.6 P
   * - model_dict64/load
     - 2824.8
     - 350.4
     - 1156.3
     - 1301.7
     - 1112.7
     - 1128.5
   * - model_dict64/dump
     - 1235.1
     - 290.6
     - —
     - 1239.0 P
     - 1233.3 P
     - 1233.9 P
   * - model_slots4/load
     - 196.9
     - 30.1
     - 78.7
     - 80.7
     - 76.2
     - 77.3
   * - model_slots4/dump
     - 64.2
     - 32.0
     - —
     - 37.8
     - 34.0
     - 33.7
   * - model_slots16/load
     - 632.0
     - 48.6
     - 216.3
     - 215.7
     - 212.4
     - 211.3
   * - model_slots16/dump
     - 237.5
     - 48.6
     - —
     - 152.0
     - 136.9
     - 137.1
   * - model_slots64/load
     - 2420.3
     - 165.5
     - 801.4
     - 921.2
     - 755.3
     - 753.9
   * - model_slots64/dump
     - 1254.0
     - 178.2
     - —
     - 622.1
     - 504.2
     - 500.7


Execution: CPython 3.14.4 (nanoseconds per call)
------------------------------------------------


.. list-table::
   :header-rows: 1

   * - Case
     - Python
     - x86
     - Reference x86
     - LLVM O0
     - LLVM O2
     - LLVM O3
   * - int/load
     - 17.1
     - 9.6
     - —
     - 10.1
     - 9.2
     - 9.1
   * - int/dump
     - 11.5
     - 11.5 P
     - —
     - 11.6 P
     - 11.5 P
     - 11.5 P
   * - list_any32/load
     - 875.2
     - 34.8
     - —
     - 47.6
     - 30.6
     - 31.8
   * - list_any32/dump
     - 813.2
     - 33.6
     - —
     - 48.3
     - 31.2
     - 31.1
   * - list_int0/load
     - 179.6
     - 17.8
     - —
     - 15.8
     - 15.0
     - 14.4
   * - list_int0/dump
     - 93.0
     - 17.2
     - —
     - 15.6
     - 14.5
     - 14.5
   * - list_union0/load
     - 180.7
     - 18.2
     - —
     - 16.2
     - 15.0
     - 14.8
   * - list_union0/dump
     - 94.8
     - 16.2
     - —
     - 15.7
     - 14.4
     - 14.8
   * - list_int32/load
     - 1066.5
     - 39.6
     - —
     - 52.1
     - 35.5
     - 35.3
   * - list_int32/dump
     - 788.8
     - 34.3
     - —
     - 47.9
     - 30.6
     - 30.4
   * - list_union32/load
     - 7321.4
     - 39.7
     - —
     - 60.5
     - 38.9
     - 38.3
   * - list_union32/dump
     - 784.1
     - 36.4
     - —
     - 51.5
     - 33.6
     - 32.6
   * - list_int1024/load
     - 30739.1
     - 816.3
     - —
     - 1417.8
     - 839.7
     - 837.7
   * - list_int1024/dump
     - 24511.2
     - 746.4
     - —
     - 1273.2
     - 650.2
     - 652.2
   * - list_union1024/load
     - 234675.1
     - 810.6
     - —
     - 1565.6
     - 990.2
     - 977.7
   * - list_union1024/dump
     - 24721.8
     - 795.9
     - —
     - 1305.9
     - 675.5
     - 677.1
   * - model_dict4/load
     - 198.5
     - 33.1
     - 83.8
     - 85.9
     - 83.1
     - 83.4
   * - model_dict4/dump
     - 70.6
     - 24.8
     - —
     - 68.5 P
     - 69.6 P
     - 67.7 P
   * - model_dict16/load
     - 583.0
     - 60.4
     - 204.0
     - 212.7
     - 202.5
     - 201.3
   * - model_dict16/dump
     - 244.4
     - 36.0
     - —
     - 240.9 P
     - 240.2 P
     - 242.3 P
   * - model_dict64/load
     - 2910.7
     - 340.7
     - 1169.9
     - 1322.7
     - 1123.4
     - 1142.3
   * - model_dict64/dump
     - 1480.0
     - 262.7
     - —
     - 1489.2 P
     - 1488.8 P
     - 1490.6 P
   * - model_slots4/load
     - 190.6
     - 30.9
     - 77.7
     - 77.4
     - 74.0
     - 73.7
   * - model_slots4/dump
     - 68.3
     - 26.0
     - —
     - 39.0
     - 35.6
     - 35.6
   * - model_slots16/load
     - 561.2
     - 49.6
     - 193.2
     - 195.6
     - 184.1
     - 188.8
   * - model_slots16/dump
     - 233.2
     - 35.5
     - —
     - 142.5
     - 132.1
     - 131.8
   * - model_slots64/load
     - 2447.6
     - 156.1
     - 678.6
     - 818.6
     - 650.7
     - 648.3
   * - model_slots64/dump
     - 1245.7
     - 185.2
     - —
     - 580.0
     - 473.2
     - 497.3


Converter creation (milliseconds)
---------------------------------


These are post-import builds with artifact capture disabled. The full CSV
and JSON contain creation times for every measured case.


.. list-table::
   :header-rows: 1

   * - CPython
     - Case
     - Python
     - x86
     - LLVM O2
   * - 3.13.15
     - int/load
     - 0.14
     - 0.66
     - 12.79
   * - 3.13.15
     - list_int32/load
     - 0.30
     - 2.30
     - 29.77
   * - 3.13.15
     - list_union32/load
     - 0.41
     - 2.94
     - 67.70
   * - 3.13.15
     - model_slots4/load
     - 1.16
     - 5.75
     - 60.97
   * - 3.13.15
     - model_slots16/load
     - 2.20
     - 19.77
     - 155.42
   * - 3.13.15
     - model_slots64/load
     - 6.51
     - 92.02
     - 824.13
   * - 3.13.15
     - model_slots16/dump
     - 2.00
     - 18.58
     - 127.15
   * - 3.14.4
     - int/load
     - 0.14
     - 0.54
     - 12.89
   * - 3.14.4
     - list_int32/load
     - 0.17
     - 2.37
     - 30.30
   * - 3.14.4
     - list_union32/load
     - 0.43
     - 2.92
     - 68.34
   * - 3.14.4
     - model_slots4/load
     - 0.97
     - 5.23
     - 75.39
   * - 3.14.4
     - model_slots16/load
     - 2.00
     - 19.37
     - 161.55
   * - 3.14.4
     - model_slots64/load
     - 5.99
     - 85.55
     - 781.28
   * - 3.14.4
     - model_slots16/dump
     - 2.47
     - 17.19
     - 129.38


Generated-code quality (CPython 3.13, LLVM O2)
----------------------------------------------


The fairer model comparison uses the same-algorithm reference encoder.
LLVM emits 38–41% fewer text bytes for the two inspected model loaders and
uses fewer stack operands. The list comparison also differs in allocation
and failure-path lowering: LLVM uses PyList_New and publishes final length
once, while production x86 retains its existing lowering. Code-size
differences with production x86 therefore cannot be attributed only to LLVM.


.. list-table::
   :header-rows: 1

   * - Artifact
     - Text bytes
     - Instructions
     - Stack operands
     - Call instructions
   * - model_slots4_load_reference
     - 1566
     - 399
     - 120
     - 27
   * - model_slots4_load_llvm2
     - 923
     - 239
     - 15
     - 21
   * - model_dict64_load_reference
     - 16866
     - 3879
     - 1140
     - 267
   * - model_dict64_load_llvm2
     - 10482
     - 2256
     - 735
     - 201
   * - list_int1024_load_x86
     - 6493
     - 1552
     - 404
     - 97
   * - list_int1024_load_llvm2
     - 466
     - 122
     - 9
     - 8


Counts cover the whole emitted text, including cold fallback/error paths
and both public and raw entries. They are static counts, not instructions
executed per call. All text bytes were decoded. No inspected artifact uses
xmm, ymm or zmm registers. LLVM promotes most ownership slots into SSA and
reduces spills, but large models still spill and retain CPython dict calls
and a normal constructor call. In the production model backend, fused field
reads and specialized object construction provide the larger runtime gain.


Where compilation time goes
---------------------------


A separately captured CPython 3.13 O2 model loader with 64 fields spent
333 ms building and initially verifying xDSL IR, 333 ms canonicalizing,
verifying and translating it, 110 ms parsing/verifying/optimizing LLVM IR,
and 31 ms in JIT code generation. The additional 128 ms of diagnostic
printing and assembly/object emission is excluded from creation benchmarks.
The Python-side frontend is a major cost, beyond LLVM optimization itself.


.. list-table::
   :header-rows: 1

   * - Loader
     - Canonicalize on, ms
     - Off, ms
     - On, ns/call
     - Off, ns/call
   * - list_int32
     - 30.4
     - 29.1
     - 35.4
     - 35.4
   * - model_slots4
     - 60.5
     - 52.6
     - 77.1
     - 77.3
   * - model_slots64
     - 833.3
     - 749.8
     - 743.6
     - 742.7


A separate nine-round probe with ``canonicalize=False`` leaves execution
close to the default while saving roughly 10–13% of model creation time.
It does not remove the larger frontend and JIT cost. Raw samples are saved
in ``benchmarks/xdsl_results/canonicalization313.json``.


Imports and process memory
--------------------------


Each backend is measured in three fresh subprocesses pinned to CPU 16,
creating one slots-model loader with 16 int fields. RSS is sampled after GC
with the loader alive, and again after releasing it and the retort. Peak RSS
is the operating-system high-water mark. These are whole-process numbers,
including the interpreter, imported compiler libraries and allocator caches;
the difference is not a per-loader memory estimate. Much of LLVM
initialization remains resident after the loader is released.


.. list-table::
   :header-rows: 1

   * - CPython
     - Backend
     - Import/setup, ms
     - Before build, MiB
     - Live loader, MiB
     - Released, MiB
     - Peak, MiB
   * - 3.13.15
     - python
     - 59.9
     - 26.0
     - 28.0
     - 28.0
     - 28.0
   * - 3.13.15
     - x86
     - 75.5
     - 29.2
     - 34.4
     - 33.5
     - 34.4
   * - 3.13.15
     - llvm2
     - 156.1
     - 76.2
     - 115.7
     - 114.9
     - 115.7
   * - 3.14.4
     - python
     - 62.1
     - 27.8
     - 29.5
     - 29.5
     - 29.5
   * - 3.14.4
     - x86
     - 77.6
     - 31.0
     - 36.7
     - 34.5
     - 36.7
   * - 3.14.4
     - llvm2
     - 154.6
     - 80.6
     - 122.1
     - 120.9
     - 122.1


Review artifacts
----------------


The source lives in ``src/adaptix/_internal/morphing/native/xdsl``.
Full timing and quality data live in ``benchmarks/xdsl_results``. To inspect
representative generated code, the experiment retains these snapshots:


* :download:`xDSL LLVM-dialect IR for list loading <../../benchmarks/xdsl_results/artifacts/list_int1024_load_llvm2.mlir>`
* :download:`Optimized LLVM IR for list loading <../../benchmarks/xdsl_results/artifacts/list_int1024_load_llvm2.optimized.ll>`
* :download:`LLVM assembly for list loading <../../benchmarks/xdsl_results/artifacts/list_int1024_load_llvm2.s>`
* :download:`Optimized LLVM IR for a four-field model <../../benchmarks/xdsl_results/artifacts/model_slots4_load_llvm2.optimized.ll>`
* :download:`LLVM assembly for the model <../../benchmarks/xdsl_results/artifacts/model_slots4_load_llvm2.s>`
* :download:`Same-algorithm x86 assembly for the model <../../benchmarks/xdsl_results/artifacts/model_slots4_load_reference.s>`


Snapshots contain process-local object addresses and serve as diagnostics;
they are not relocatable converter binaries to reuse in another process.
The complete reproducible artifacts, including relocatable LLVM object files,
are produced by ``--artifacts`` and kept out of version control.


Conclusion
----------


This experiment establishes a working xDSL/LLVM path behind the existing
DI interface. LLVM is useful for compact code and register allocation, but
this conservative subset is not a faster replacement for the production
model backend. A next experiment should lower the shared optimizer
operations, including fused reads and constructor fast paths, through LLVM
and reduce frontend construction/verification work. The default backend
remains unchanged.
