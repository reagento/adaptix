; ModuleID = '<string>'
source_filename = "<string>"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
target triple = "x86_64-unknown-linux-gnu"

declare ptr @PyList_New(i64) local_unnamed_addr

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
  %const = bitcast i64 137892598207712 to i64
  %.31 = alloca ptr, align 8
  store ptr null, ptr %.31, align 8
  %.33 = alloca ptr, align 8
  store ptr null, ptr %.33, align 8
  %.35 = alloca ptr, align 8
  store ptr null, ptr %.35, align 8
  %.38 = getelementptr i8, ptr %.1, i64 8
  %.39 = load ptr, ptr %.38, align 8
  %.43 = icmp eq ptr %.39, inttoptr (i64 21898448 to ptr)
  br i1 %.43, label %.7, label %.18

.6:                                               ; preds = %.8
  call void @PyErr_Fetch(ptr nonnull %.31, ptr nonnull %.33, ptr nonnull %.35)
  %.132 = load ptr, ptr %.31, align 8
  %.133 = load ptr, ptr %.33, align 8
  %.134 = load ptr, ptr %.35, align 8
  call void @PyErr_Restore(ptr %.132, ptr %.133, ptr %.134)
  br label %common.ret

.7:                                               ; preds = %.3
  %const_mat = add i64 %const, 193113032
  %0 = inttoptr i64 %const_mat to ptr
  %.58 = load i64, ptr %0, align 8
  %.59 = icmp eq i64 %.58, 42
  br i1 %.59, label %.8, label %.18

.8:                                               ; preds = %.7
  %.61 = getelementptr i8, ptr %.1, i64 16
  %.62 = load i64, ptr %.61, align 8
  %.63 = tail call ptr @PyList_New(i64 %.62)
  %.67.not = icmp eq ptr %.63, null
  br i1 %.67.not, label %.6, label %.9

.9:                                               ; preds = %.8
  %sunkaddr = getelementptr i8, ptr %.1, i64 16
  %.70 = load i64, ptr %sunkaddr, align 8
  %.71.not = icmp ult i64 %.62, %.70
  br i1 %.71.not, label %.17, label %.10

.10:                                              ; preds = %.9
  %.73 = getelementptr i8, ptr %.1, i64 24
  %.74 = load ptr, ptr %.73, align 8
  %.76 = getelementptr i8, ptr %.63, i64 24
  %.77 = load ptr, ptr %.76, align 8
  %.797.not = icmp eq i64 %.70, 0
  br i1 %.797.not, label %.12, label %.13.preheader

.13.preheader:                                    ; preds = %.10
  br label %.13

common.ret:                                       ; preds = %.6, %.12
  %common.ret.op = phi ptr [ %.63, %.12 ], [ null, %.6 ]
  ret ptr %common.ret.op

.12:                                              ; preds = %.15, %.10
  %.82 = getelementptr i8, ptr %.63, i64 16
  store i64 %.70, ptr %.82, align 8
  br label %common.ret

.13:                                              ; preds = %.13.preheader, %.15
  %.278 = phi i64 [ %.101, %.15 ], [ 0, %.13.preheader ]
  %1 = shl i64 %.278, 3
  %scevgep9 = getelementptr i8, ptr %.74, i64 %1
  %.87 = load ptr, ptr %scevgep9, align 8
  %.88 = getelementptr i8, ptr %.87, i64 8
  %.89 = load ptr, ptr %.88, align 8
  %.93 = icmp eq ptr %.89, inttoptr (i64 21901024 to ptr)
  br i1 %.93, label %.14, label %.17

.14:                                              ; preds = %.13
  %.96 = load i32, ptr %.87, align 4
  %.97.not = icmp eq i32 %.96, -1
  br i1 %.97.not, label %.15, label %.16

.15:                                              ; preds = %.16, %.14
  %2 = shl i64 %.278, 3
  %scevgep = getelementptr i8, ptr %.77, i64 %2
  store ptr %.87, ptr %scevgep, align 8
  %.101 = add nuw i64 %.278, 1
  %exitcond.not = icmp eq i64 %.70, %.101
  br i1 %exitcond.not, label %.12, label %.13

.16:                                              ; preds = %.14
  %.105 = add nuw i32 %.96, 1
  store i32 %.105, ptr %.87, align 4
  br label %.15

.17:                                              ; preds = %.13, %.9
  %.111 = load i32, ptr %.63, align 4
  %.112 = icmp slt i32 %.111, 0
  br i1 %.112, label %.18, label %.20

.18:                                              ; preds = %.3, %.7, %.17, %.20, %.21
  %3 = inttoptr i64 %const to ptr
  %.115 = tail call ptr @PyObject_CallOneArg(ptr nonnull %3, ptr %.1)
  ret ptr %.115

.20:                                              ; preds = %.17
  %.119 = load i64, ptr %.63, align 8
  %.120 = add i64 %.119, -1
  store i64 %.120, ptr %.63, align 8
  %.123 = icmp eq i64 %.120, 0
  br i1 %.123, label %.21, label %.18

.21:                                              ; preds = %.20
  tail call void @_Py_Dealloc(ptr nonnull %.63)
  br label %.18
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
  %const1 = bitcast i64 137892598564144 to i64
  %0 = inttoptr i64 %const1 to ptr
  tail call void @PyErr_SetString(ptr nonnull inttoptr (i64 21852336 to ptr), ptr nonnull %0)
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
  %const = bitcast i64 137892598564144 to i64
  %.34 = tail call ptr @PyTuple_GetItem(ptr nonnull %.4, i64 0)
  %const_mat = add i64 %const, 277664
  %1 = inttoptr i64 %const_mat to ptr
  %.36 = tail call i32 @PyUnicode_CompareWithASCIIString(ptr %.34, ptr nonnull %1)
  %.37 = icmp eq i32 %.36, 0
  br i1 %.37, label %.10, label %.9
}
