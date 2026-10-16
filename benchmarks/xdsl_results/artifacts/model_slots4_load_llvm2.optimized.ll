; ModuleID = '<string>'
source_filename = "<string>"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

declare ptr @PyDict_GetItemWithError(ptr, ptr) local_unnamed_addr

declare ptr @PyErr_Occurred() local_unnamed_addr

declare ptr @PyObject_Vectorcall(ptr, ptr, i64, ptr) local_unnamed_addr

declare void @_Py_Dealloc(ptr) local_unnamed_addr

declare ptr @PyObject_CallOneArg(ptr, ptr) local_unnamed_addr

declare void @PyErr_Fetch(ptr, ptr, ptr) local_unnamed_addr

declare void @PyErr_Restore(ptr, ptr, ptr) local_unnamed_addr

declare i64 @PyTuple_Size(ptr) local_unnamed_addr

declare ptr @PyTuple_GetItem(ptr, i64) local_unnamed_addr

declare i32 @PyUnicode_CompareWithASCIIString(ptr, ptr) local_unnamed_addr

declare void @PyErr_SetString(ptr, ptr) local_unnamed_addr

define ptr @adaptix_raw(ptr %.1) local_unnamed_addr {
.3:
  %const = bitcast i64 137892494218624 to i64
  %.1091 = alloca [4 x ptr], align 8
  %.112 = alloca ptr, align 8
  store ptr null, ptr %.112, align 8
  %.114 = alloca ptr, align 8
  store ptr null, ptr %.114, align 8
  %.116 = alloca ptr, align 8
  store ptr null, ptr %.116, align 8
  %.119 = getelementptr i8, ptr %.1, i64 8
  %.120 = load ptr, ptr %.119, align 8
  %.124 = icmp eq ptr %.120, inttoptr (i64 21907136 to ptr)
  br i1 %.124, label %.7, label %.71

.7:                                               ; preds = %.3
  %.137 = getelementptr i8, ptr %.1, i64 32
  %.138 = load ptr, ptr %.137, align 8
  %.139 = getelementptr i8, ptr %.138, i64 10
  %.140 = load i8, ptr %.139, align 1
  %.141 = icmp eq i8 %.140, 1
  br i1 %.141, label %.8, label %.71

.8:                                               ; preds = %.7
  %const_mat = add i64 %const, 108360192
  %0 = inttoptr i64 %const_mat to ptr
  %.144 = tail call ptr @PyDict_GetItemWithError(ptr nonnull %.1, ptr nonnull %0)
  %.147.not = icmp eq ptr %.144, null
  br i1 %.147.not, label %.9, label %.10

.9:                                               ; preds = %.8
  %.149 = tail call ptr @PyErr_Occurred()
  %.152 = icmp eq ptr %.149, null
  br i1 %.152, label %.71, label %.91

.10:                                              ; preds = %.8
  %.154 = getelementptr i8, ptr %.144, i64 8
  %.155 = load ptr, ptr %.154, align 8
  %.159 = icmp eq ptr %.155, inttoptr (i64 21901024 to ptr)
  br i1 %.159, label %.11, label %.71

.11:                                              ; preds = %.10
  %const_mat34 = add i64 %const, 108360288
  %1 = inttoptr i64 %const_mat34 to ptr
  %.162 = tail call ptr @PyDict_GetItemWithError(ptr nonnull %.1, ptr nonnull %1)
  %.165.not = icmp eq ptr %.162, null
  br i1 %.165.not, label %.12, label %.13

.12:                                              ; preds = %.11
  %.167 = tail call ptr @PyErr_Occurred()
  %.170 = icmp eq ptr %.167, null
  br i1 %.170, label %.71, label %.91

.13:                                              ; preds = %.11
  %.172 = getelementptr i8, ptr %.162, i64 8
  %.173 = load ptr, ptr %.172, align 8
  %.177 = icmp eq ptr %.173, inttoptr (i64 21901024 to ptr)
  br i1 %.177, label %.14, label %.71

.14:                                              ; preds = %.13
  %const_mat35 = add i64 %const, 108360384
  %2 = inttoptr i64 %const_mat35 to ptr
  %.180 = tail call ptr @PyDict_GetItemWithError(ptr nonnull %.1, ptr nonnull %2)
  %.183.not = icmp eq ptr %.180, null
  br i1 %.183.not, label %.15, label %.16

.15:                                              ; preds = %.14
  %.185 = tail call ptr @PyErr_Occurred()
  %.188 = icmp eq ptr %.185, null
  br i1 %.188, label %.71, label %.91

.16:                                              ; preds = %.14
  %.190 = getelementptr i8, ptr %.180, i64 8
  %.191 = load ptr, ptr %.190, align 8
  %.195 = icmp eq ptr %.191, inttoptr (i64 21901024 to ptr)
  br i1 %.195, label %.17, label %.71

.17:                                              ; preds = %.16
  %const_mat36 = add i64 %const, 108360480
  %3 = inttoptr i64 %const_mat36 to ptr
  %.198 = tail call ptr @PyDict_GetItemWithError(ptr nonnull %.1, ptr nonnull %3)
  %.201.not = icmp eq ptr %.198, null
  br i1 %.201.not, label %.18, label %.19

.18:                                              ; preds = %.17
  %.203 = tail call ptr @PyErr_Occurred()
  %.206 = icmp eq ptr %.203, null
  br i1 %.206, label %.71, label %.91

.19:                                              ; preds = %.17
  %.208 = getelementptr i8, ptr %.198, i64 8
  %.209 = load ptr, ptr %.208, align 8
  %.213 = icmp eq ptr %.209, inttoptr (i64 21901024 to ptr)
  br i1 %.213, label %.20, label %.71

.20:                                              ; preds = %.19
  %.216 = load i32, ptr %.144, align 4
  %.217.not = icmp eq i32 %.216, -1
  br i1 %.217.not, label %.21, label %.22

.21:                                              ; preds = %.22, %.20
  %.221 = load i32, ptr %.162, align 4
  %.222.not = icmp eq i32 %.221, -1
  br i1 %.222.not, label %.23, label %.24

.22:                                              ; preds = %.20
  %.226 = add nuw i32 %.216, 1
  store i32 %.226, ptr %.144, align 4
  br label %.21

.23:                                              ; preds = %.24, %.21
  %.232 = load i32, ptr %.180, align 4
  %.233.not = icmp eq i32 %.232, -1
  br i1 %.233.not, label %.25, label %.26

.24:                                              ; preds = %.21
  %.237 = add nuw i32 %.221, 1
  store i32 %.237, ptr %.162, align 4
  br label %.23

.25:                                              ; preds = %.26, %.23
  %.243 = load i32, ptr %.198, align 4
  %.244.not = icmp eq i32 %.243, -1
  br i1 %.244.not, label %.27, label %.28

.26:                                              ; preds = %.23
  %.248 = add nuw i32 %.232, 1
  store i32 %.248, ptr %.180, align 4
  br label %.25

.27:                                              ; preds = %.28, %.25
  store ptr %.144, ptr %.1091, align 8
  %.255 = getelementptr inbounds nuw i8, ptr %.1091, i64 8
  store ptr %.162, ptr %.255, align 8
  %.257 = getelementptr inbounds nuw i8, ptr %.1091, i64 16
  store ptr %.180, ptr %.257, align 8
  %.259 = getelementptr inbounds nuw i8, ptr %.1091, i64 24
  store ptr %.198, ptr %.259, align 8
  %.262 = call ptr @PyObject_Vectorcall(ptr nonnull inttoptr (i64 440674576 to ptr), ptr nonnull %.1091, i64 4, ptr null)
  %.266.not = icmp eq ptr %.262, null
  br i1 %.266.not, label %.80, label %.30

.28:                                              ; preds = %.25
  %.270 = add nuw i32 %.243, 1
  store i32 %.270, ptr %.198, align 4
  br label %.27

.30:                                              ; preds = %.27
  %.282 = load i32, ptr %.198, align 4
  %.283 = icmp slt i32 %.282, 0
  br i1 %.283, label %.35, label %.33

.33:                                              ; preds = %.30
  %.292 = load i64, ptr %.198, align 8
  %.293 = add i64 %.292, -1
  store i64 %.293, ptr %.198, align 8
  %.296 = icmp eq i64 %.293, 0
  br i1 %.296, label %.34, label %.35

.34:                                              ; preds = %.33
  call void @_Py_Dealloc(ptr nonnull %.198)
  br label %.35

.35:                                              ; preds = %.34, %.33, %.30
  %.302 = load i32, ptr %.180, align 4
  %.303 = icmp slt i32 %.302, 0
  br i1 %.303, label %.40, label %.38

.38:                                              ; preds = %.35
  %.312 = load i64, ptr %.180, align 8
  %.313 = add i64 %.312, -1
  store i64 %.313, ptr %.180, align 8
  %.316 = icmp eq i64 %.313, 0
  br i1 %.316, label %.39, label %.40

.39:                                              ; preds = %.38
  call void @_Py_Dealloc(ptr nonnull %.180)
  br label %.40

.40:                                              ; preds = %.39, %.38, %.35
  %.322 = load i32, ptr %.162, align 4
  %.323 = icmp slt i32 %.322, 0
  br i1 %.323, label %.45, label %.43

.43:                                              ; preds = %.40
  %.332 = load i64, ptr %.162, align 8
  %.333 = add i64 %.332, -1
  store i64 %.333, ptr %.162, align 8
  %.336 = icmp eq i64 %.333, 0
  br i1 %.336, label %.44, label %.45

.44:                                              ; preds = %.43
  call void @_Py_Dealloc(ptr nonnull %.162)
  br label %.45

.45:                                              ; preds = %.44, %.43, %.40
  %.342 = load i32, ptr %.144, align 4
  %.343 = icmp slt i32 %.342, 0
  br i1 %.343, label %common.ret, label %.48

common.ret:                                       ; preds = %.45, %.48, %.49, %.96
  %common.ret.op = phi ptr [ null, %.96 ], [ %.262, %.48 ], [ %.262, %.45 ], [ %.262, %.49 ]
  ret ptr %common.ret.op

.48:                                              ; preds = %.45
  %.348 = load i64, ptr %.144, align 8
  %.349 = add i64 %.348, -1
  store i64 %.349, ptr %.144, align 8
  %.352 = icmp eq i64 %.349, 0
  br i1 %.352, label %.49, label %common.ret

.49:                                              ; preds = %.48
  call void @_Py_Dealloc(ptr nonnull %.144)
  br label %common.ret

.71:                                              ; preds = %.3, %.7, %.9, %.10, %.12, %.13, %.15, %.16, %.18, %.19
  %4 = inttoptr i64 %const to ptr
  %.442 = tail call ptr @PyObject_CallOneArg(ptr nonnull %4, ptr nonnull %.1)
  ret ptr %.442

.80:                                              ; preds = %.27
  call void @PyErr_Fetch(ptr nonnull %.112, ptr nonnull %.114, ptr nonnull %.116)
  %.476 = load i32, ptr %.198, align 4
  %.477 = icmp slt i32 %.476, 0
  br i1 %.477, label %.85, label %.83

.83:                                              ; preds = %.80
  %.486 = load i64, ptr %.198, align 8
  %.487 = add i64 %.486, -1
  store i64 %.487, ptr %.198, align 8
  %.490 = icmp eq i64 %.487, 0
  br i1 %.490, label %.84, label %.85

.84:                                              ; preds = %.83
  call void @_Py_Dealloc(ptr nonnull %.198)
  br label %.85

.85:                                              ; preds = %.84, %.83, %.80
  %.496 = load i32, ptr %.180, align 4
  %.497 = icmp slt i32 %.496, 0
  br i1 %.497, label %.90, label %.88

.88:                                              ; preds = %.85
  %.506 = load i64, ptr %.180, align 8
  %.507 = add i64 %.506, -1
  store i64 %.507, ptr %.180, align 8
  %.510 = icmp eq i64 %.507, 0
  br i1 %.510, label %.89, label %.90

.89:                                              ; preds = %.88
  call void @_Py_Dealloc(ptr nonnull %.180)
  br label %.90

.90:                                              ; preds = %.85, %.88, %.89
  %.516 = load i32, ptr %.162, align 4
  %.517 = icmp slt i32 %.516, 0
  br i1 %.517, label %.95, label %.93

.91:                                              ; preds = %.9, %.12, %.15, %.18
  call void @PyErr_Fetch(ptr nonnull %.112, ptr nonnull %.114, ptr nonnull %.116)
  br label %.96

.93:                                              ; preds = %.90
  %.526 = load i64, ptr %.162, align 8
  %.527 = add i64 %.526, -1
  store i64 %.527, ptr %.162, align 8
  %.530 = icmp eq i64 %.527, 0
  br i1 %.530, label %.94, label %.95

.94:                                              ; preds = %.93
  call void @_Py_Dealloc(ptr nonnull %.162)
  br label %.95

.95:                                              ; preds = %.90, %.93, %.94
  %.536 = load i32, ptr %.144, align 4
  %.537 = icmp slt i32 %.536, 0
  br i1 %.537, label %.96, label %.98

.96:                                              ; preds = %.91, %.95, %.98, %.99
  %.539 = load ptr, ptr %.112, align 8
  %.540 = load ptr, ptr %.114, align 8
  %.541 = load ptr, ptr %.116, align 8
  call void @PyErr_Restore(ptr %.539, ptr %.540, ptr %.541)
  br label %common.ret

.98:                                              ; preds = %.95
  %.546 = load i64, ptr %.144, align 8
  %.547 = add i64 %.546, -1
  store i64 %.547, ptr %.144, align 8
  %.550 = icmp eq i64 %.547, 0
  br i1 %.550, label %.99, label %.96

.99:                                              ; preds = %.98
  call void @_Py_Dealloc(ptr nonnull %.144)
  br label %.96
}

define ptr @adaptix_entry(ptr readnone captures(none) %.1, ptr readonly captures(none) %.2, i64 %.3, ptr %.4) local_unnamed_addr {
.6:
  %.16 = icmp eq ptr %.4, null
  br i1 %.16, label %.7, label %.8

.7:                                               ; preds = %.8, %.6
  %.18 = icmp eq i64 %.3, 1
  br i1 %.18, label %.10, label %.9

.8:                                               ; preds = %.6
  %.20 = tail call i64 @PyTuple_Size(ptr nonnull %.4)
  %.21 = icmp eq i64 %.20, 0
  br i1 %.21, label %.7, label %.11

.9:                                               ; preds = %.12, %.11, %.7
  tail call void @PyErr_SetString(ptr nonnull inttoptr (i64 21852336 to ptr), ptr nonnull inttoptr (i64 137888969985200 to ptr))
  ret ptr null

.10:                                              ; preds = %.12, %.7
  %.27 = load ptr, ptr %.2, align 8
  %.28 = tail call ptr @adaptix_raw(ptr %.27)
  ret ptr %.28

.11:                                              ; preds = %.8
  %.30 = icmp eq i64 %.20, 1
  %.31 = icmp eq i64 %.3, 0
  %.32 = and i1 %.31, %.30
  br i1 %.32, label %.12, label %.9

.12:                                              ; preds = %.11
  %.34 = tail call ptr @PyTuple_GetItem(ptr nonnull %.4, i64 0)
  %.36 = tail call i32 @PyUnicode_CompareWithASCIIString(ptr %.34, ptr nonnull inttoptr (i64 137892497034224 to ptr))
  %.37 = icmp eq i32 %.36, 0
  br i1 %.37, label %.10, label %.9
}
