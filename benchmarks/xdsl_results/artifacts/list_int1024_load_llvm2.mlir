builtin.module {
  llvm.func @PyList_New(i64) -> !llvm.ptr
  llvm.func @_Py_Dealloc(!llvm.ptr)
  llvm.func @PyObject_CallOneArg(!llvm.ptr, !llvm.ptr) -> !llvm.ptr
  llvm.func @PyErr_Fetch(!llvm.ptr, !llvm.ptr, !llvm.ptr)
  llvm.func @PyErr_Restore(!llvm.ptr, !llvm.ptr, !llvm.ptr)
  llvm.func @PyTuple_Size(!llvm.ptr) -> i64
  llvm.func @PyTuple_GetItem(!llvm.ptr, i64) -> !llvm.ptr
  llvm.func @PyUnicode_CompareWithASCIIString(!llvm.ptr, !llvm.ptr) -> i32
  llvm.func @PyErr_SetString(!llvm.ptr, !llvm.ptr)
  llvm.func @adaptix_raw(%0: !llvm.ptr) -> !llvm.ptr {
    %1 = llvm.mlir.constant(1) : i64
    %2 = llvm.mlir.constant(0) : i64
    %3 = llvm.inttoptr %2 : i64 to !llvm.ptr
    %4 = llvm.mlir.constant(1) : i64
    %5 = llvm.alloca %4 x !llvm.ptr {alignment = 8 : i64} : (i64) -> !llvm.ptr
    llvm.store %3, %5 : !llvm.ptr, !llvm.ptr
    %6 = llvm.mlir.constant(1) : i64
    %7 = llvm.alloca %6 x !llvm.ptr {alignment = 8 : i64} : (i64) -> !llvm.ptr
    llvm.store %3, %7 : !llvm.ptr, !llvm.ptr
    %8 = llvm.mlir.constant(1) : i64
    %9 = llvm.alloca %8 x !llvm.ptr {alignment = 8 : i64} : (i64) -> !llvm.ptr
    llvm.store %3, %9 : !llvm.ptr, !llvm.ptr
    %10 = llvm.mlir.constant(1) : i64
    %11 = llvm.alloca %10 x !llvm.ptr {alignment = 8 : i64} : (i64) -> !llvm.ptr
    llvm.store %3, %11 : !llvm.ptr, !llvm.ptr
    llvm.br ^bb1
  ^bb1:
    %12 = llvm.getelementptr %0[8] : (!llvm.ptr) -> !llvm.ptr, i8
    %13 = llvm.load %12 : !llvm.ptr -> !llvm.ptr
    %14 = llvm.mlir.constant(21898448) : i64
    %15 = llvm.inttoptr %14 : i64 to !llvm.ptr
    %16 = llvm.ptrtoint %13 : !llvm.ptr to i64
    %17 = llvm.ptrtoint %15 : !llvm.ptr to i64
    %18 = llvm.icmp "eq" %16, %17 : i64
    llvm.cond_br %18, ^bb4, ^bb2
  ^bb2:
    %19 = llvm.load %5 : !llvm.ptr -> !llvm.ptr
    %20 = llvm.ptrtoint %19 : !llvm.ptr to i64
    %21 = llvm.ptrtoint %3 : !llvm.ptr to i64
    %22 = llvm.icmp "ne" %20, %21 : i64
    llvm.cond_br %22, ^bb14, ^bb15
  ^bb3:
    llvm.call @PyErr_Fetch(%7, %9, %11) : (!llvm.ptr, !llvm.ptr, !llvm.ptr) -> ()
    %23 = llvm.load %5 : !llvm.ptr -> !llvm.ptr
    %24 = llvm.ptrtoint %23 : !llvm.ptr to i64
    %25 = llvm.ptrtoint %3 : !llvm.ptr to i64
    %26 = llvm.icmp "ne" %24, %25 : i64
    llvm.cond_br %26, ^bb19, ^bb20
  ^bb4:
    %27 = llvm.mlir.constant(137892791320736) : i64
    %28 = llvm.inttoptr %27 : i64 to !llvm.ptr
    %29 = llvm.getelementptr %28[8] : (!llvm.ptr) -> !llvm.ptr, i8
    %30 = llvm.load %29 : !llvm.ptr -> i64
    %31 = llvm.mlir.constant(42) : i64
    %32 = llvm.icmp "eq" %30, %31 : i64
    llvm.cond_br %32, ^bb5, ^bb2
  ^bb5:
    %33 = llvm.getelementptr %0[16] : (!llvm.ptr) -> !llvm.ptr, i8
    %34 = llvm.load %33 : !llvm.ptr -> i64
    %35 = llvm.call @PyList_New(%34) : (i64) -> !llvm.ptr
    llvm.store %35, %5 : !llvm.ptr, !llvm.ptr
    %36 = llvm.ptrtoint %35 : !llvm.ptr to i64
    %37 = llvm.ptrtoint %3 : !llvm.ptr to i64
    %38 = llvm.icmp "ne" %36, %37 : i64
    llvm.cond_br %38, ^bb6, ^bb3
  ^bb6:
    %39 = llvm.getelementptr %0[16] : (!llvm.ptr) -> !llvm.ptr, i8
    %40 = llvm.load %39 : !llvm.ptr -> i64
    %41 = llvm.icmp "uge" %34, %40 : i64
    llvm.cond_br %41, ^bb7, ^bb2
  ^bb7:
    %42 = llvm.getelementptr %0[24] : (!llvm.ptr) -> !llvm.ptr, i8
    %43 = llvm.load %42 : !llvm.ptr -> !llvm.ptr
    %44 = llvm.load %5 : !llvm.ptr -> !llvm.ptr
    %45 = llvm.getelementptr %44[24] : (!llvm.ptr) -> !llvm.ptr, i8
    %46 = llvm.load %45 : !llvm.ptr -> !llvm.ptr
    llvm.br ^bb8(%2 : i64)
  ^bb8(%47: i64):
    %48 = llvm.icmp "ult" %47, %40 : i64
    llvm.cond_br %48, ^bb10, ^bb9
  ^bb9:
    %49 = llvm.load %5 : !llvm.ptr -> !llvm.ptr
    %50 = llvm.getelementptr %49[16] : (!llvm.ptr) -> !llvm.ptr, i8
    llvm.store %40, %50 : i64, !llvm.ptr
    %51 = llvm.load %5 : !llvm.ptr -> !llvm.ptr
    llvm.return %51 : !llvm.ptr
  ^bb10:
    %52 = llvm.getelementptr %43[%47] : (!llvm.ptr, i64) -> !llvm.ptr, !llvm.ptr
    %53 = llvm.load %52 : !llvm.ptr -> !llvm.ptr
    %54 = llvm.getelementptr %53[8] : (!llvm.ptr) -> !llvm.ptr, i8
    %55 = llvm.load %54 : !llvm.ptr -> !llvm.ptr
    %56 = llvm.mlir.constant(21901024) : i64
    %57 = llvm.inttoptr %56 : i64 to !llvm.ptr
    %58 = llvm.ptrtoint %55 : !llvm.ptr to i64
    %59 = llvm.ptrtoint %57 : !llvm.ptr to i64
    %60 = llvm.icmp "eq" %58, %59 : i64
    llvm.cond_br %60, ^bb11, ^bb2
  ^bb11:
    %61 = llvm.getelementptr %53[0] : (!llvm.ptr) -> !llvm.ptr, i8
    %62 = llvm.load %61 : !llvm.ptr -> i32
    %63 = llvm.mlir.constant(-1 : i32) : i32
    %64 = llvm.icmp "ult" %62, %63 : i32
    llvm.cond_br %64, ^bb13, ^bb12
  ^bb12:
    %65 = llvm.getelementptr %46[%47] : (!llvm.ptr, i64) -> !llvm.ptr, !llvm.ptr
    llvm.store %53, %65 : !llvm.ptr, !llvm.ptr
    %66 = llvm.add %47, %1 : i64
    llvm.br ^bb8(%66 : i64)
  ^bb13:
    %67 = llvm.getelementptr %53[0] : (!llvm.ptr) -> !llvm.ptr, i8
    %68 = llvm.load %67 : !llvm.ptr -> i32
    %69 = llvm.mlir.constant(1 : i32) : i32
    %70 = llvm.add %68, %69 : i32
    %71 = llvm.getelementptr %53[0] : (!llvm.ptr) -> !llvm.ptr, i8
    llvm.store %70, %71 : i32, !llvm.ptr
    llvm.br ^bb12
  ^bb14:
    llvm.store %3, %5 : !llvm.ptr, !llvm.ptr
    %72 = llvm.getelementptr %19[0] : (!llvm.ptr) -> !llvm.ptr, i8
    %73 = llvm.load %72 : !llvm.ptr -> i32
    %74 = llvm.mlir.constant(0 : i32) : i32
    %75 = llvm.icmp "slt" %73, %74 : i32
    llvm.cond_br %75, ^bb16, ^bb17
  ^bb15:
    %76 = llvm.mlir.constant(137892598207712) : i64
    %77 = llvm.inttoptr %76 : i64 to !llvm.ptr
    %78 = llvm.call @PyObject_CallOneArg(%77, %0) : (!llvm.ptr, !llvm.ptr) -> !llvm.ptr
    llvm.return %78 : !llvm.ptr
  ^bb16:
    llvm.br ^bb15
  ^bb17:
    %79 = llvm.getelementptr %19[0] : (!llvm.ptr) -> !llvm.ptr, i8
    %80 = llvm.load %79 : !llvm.ptr -> i64
    %81 = llvm.mlir.constant(1) : i64
    %82 = llvm.sub %80, %81 : i64
    %83 = llvm.getelementptr %19[0] : (!llvm.ptr) -> !llvm.ptr, i8
    llvm.store %82, %83 : i64, !llvm.ptr
    %84 = llvm.mlir.constant(0) : i64
    %85 = llvm.icmp "eq" %82, %84 : i64
    llvm.cond_br %85, ^bb18, ^bb16
  ^bb18:
    llvm.call @_Py_Dealloc(%19) : (!llvm.ptr) -> ()
    llvm.br ^bb16
  ^bb19:
    llvm.store %3, %5 : !llvm.ptr, !llvm.ptr
    %86 = llvm.getelementptr %23[0] : (!llvm.ptr) -> !llvm.ptr, i8
    %87 = llvm.load %86 : !llvm.ptr -> i32
    %88 = llvm.mlir.constant(0 : i32) : i32
    %89 = llvm.icmp "slt" %87, %88 : i32
    llvm.cond_br %89, ^bb21, ^bb22
  ^bb20:
    %90 = llvm.load %7 : !llvm.ptr -> !llvm.ptr
    %91 = llvm.load %9 : !llvm.ptr -> !llvm.ptr
    %92 = llvm.load %11 : !llvm.ptr -> !llvm.ptr
    llvm.call @PyErr_Restore(%90, %91, %92) : (!llvm.ptr, !llvm.ptr, !llvm.ptr) -> ()
    llvm.return %3 : !llvm.ptr
  ^bb21:
    llvm.br ^bb20
  ^bb22:
    %93 = llvm.getelementptr %23[0] : (!llvm.ptr) -> !llvm.ptr, i8
    %94 = llvm.load %93 : !llvm.ptr -> i64
    %95 = llvm.mlir.constant(1) : i64
    %96 = llvm.sub %94, %95 : i64
    %97 = llvm.getelementptr %23[0] : (!llvm.ptr) -> !llvm.ptr, i8
    llvm.store %96, %97 : i64, !llvm.ptr
    %98 = llvm.mlir.constant(0) : i64
    %99 = llvm.icmp "eq" %96, %98 : i64
    llvm.cond_br %99, ^bb23, ^bb21
  ^bb23:
    llvm.call @_Py_Dealloc(%23) : (!llvm.ptr) -> ()
    llvm.br ^bb21
  }
  llvm.func @adaptix_entry(%100: !llvm.ptr, %101: !llvm.ptr, %102: i64, %103: !llvm.ptr) -> !llvm.ptr {
    %104 = llvm.mlir.constant(0) : i64
    %105 = llvm.inttoptr %104 : i64 to !llvm.ptr
    %106 = llvm.ptrtoint %103 : !llvm.ptr to i64
    %107 = llvm.ptrtoint %105 : !llvm.ptr to i64
    %108 = llvm.icmp "eq" %106, %107 : i64
    llvm.cond_br %108, ^bb1, ^bb2
  ^bb1:
    %109 = llvm.mlir.constant(1) : i64
    %110 = llvm.icmp "eq" %102, %109 : i64
    llvm.cond_br %110, ^bb4, ^bb3
  ^bb2:
    %111 = llvm.call @PyTuple_Size(%103) : (!llvm.ptr) -> i64
    %112 = llvm.mlir.constant(0) : i64
    %113 = llvm.icmp "eq" %111, %112 : i64
    llvm.cond_br %113, ^bb1, ^bb5
  ^bb3:
    %114 = llvm.mlir.constant(21852336) : i64
    %115 = llvm.inttoptr %114 : i64 to !llvm.ptr
    %116 = llvm.mlir.constant(137892598564144) : i64
    %117 = llvm.inttoptr %116 : i64 to !llvm.ptr
    llvm.call @PyErr_SetString(%115, %117) : (!llvm.ptr, !llvm.ptr) -> ()
    llvm.return %105 : !llvm.ptr
  ^bb4:
    %118 = llvm.load %101 : !llvm.ptr -> !llvm.ptr
    %119 = llvm.call @adaptix_raw(%118) : (!llvm.ptr) -> !llvm.ptr
    llvm.return %119 : !llvm.ptr
  ^bb5:
    %120 = llvm.mlir.constant(1) : i64
    %121 = llvm.icmp "eq" %111, %120 : i64
    %122 = llvm.mlir.constant(0) : i64
    %123 = llvm.icmp "eq" %102, %122 : i64
    %124 = llvm.and %121, %123 : i1
    llvm.cond_br %124, ^bb6, ^bb3
  ^bb6:
    %125 = llvm.mlir.constant(0) : i64
    %126 = llvm.call @PyTuple_GetItem(%103, %125) : (!llvm.ptr, i64) -> !llvm.ptr
    %127 = llvm.mlir.constant(137892598841808) : i64
    %128 = llvm.inttoptr %127 : i64 to !llvm.ptr
    %129 = llvm.call @PyUnicode_CompareWithASCIIString(%126, %128) : (!llvm.ptr, !llvm.ptr) -> i32
    %130 = llvm.mlir.constant(0 : i32) : i32
    %131 = llvm.icmp "eq" %129, %130 : i32
    llvm.cond_br %131, ^bb4, ^bb3
  }
}