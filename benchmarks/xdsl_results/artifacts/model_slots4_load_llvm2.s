	.file	"<string>"
	.section	.ltext,"axl",@progbits
	.globl	adaptix_raw
	.p2align	4
	.type	adaptix_raw,@function
adaptix_raw:
	.cfi_startproc
	pushq	%rbp
	.cfi_def_cfa_offset 16
	pushq	%r15
	.cfi_def_cfa_offset 24
	pushq	%r14
	.cfi_def_cfa_offset 32
	pushq	%r13
	.cfi_def_cfa_offset 40
	pushq	%r12
	.cfi_def_cfa_offset 48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	subq	$56, %rsp
	.cfi_def_cfa_offset 112
	.cfi_offset %rbx, -56
	.cfi_offset %r12, -48
	.cfi_offset %r13, -40
	.cfi_offset %r14, -32
	.cfi_offset %r15, -24
	.cfi_offset %rbp, -16
	movq	$0, 16(%rsp)
	movq	$0, 8(%rsp)
	movq	$0, (%rsp)
	movq	%rdi, %rbx
	movabsq	$137892494218624, %rdi
	cmpq	$21907136, 8(%rbx)
	jne	.LBB0_4
	movq	32(%rbx), %rax
	cmpb	$1, 10(%rax)
	jne	.LBB0_4
	leaq	108360192(%rdi), %rsi
	movabsq	$PyDict_GetItemWithError, %rbp
	movq	%rdi, %r13
	movq	%rbx, %rdi
	callq	*%rbp
	testq	%rax, %rax
	je	.LBB0_3
	cmpq	$21901024, 8(%rax)
	movq	%r13, %rdi
	jne	.LBB0_4
	leaq	108360288(%rdi), %rsi
	movq	%rbx, %rdi
	movq	%rax, %r14
	callq	*%rbp
	testq	%rax, %rax
	je	.LBB0_3
	cmpq	$21901024, 8(%rax)
	movq	%r13, %rdi
	jne	.LBB0_4
	leaq	108360384(%rdi), %rsi
	movq	%rbx, %rdi
	movq	%rax, %r15
	callq	*%rbp
	testq	%rax, %rax
	je	.LBB0_3
	cmpq	$21901024, 8(%rax)
	movq	%r13, %rdi
	jne	.LBB0_4
	leaq	108360480(%rdi), %rsi
	movq	%rbx, %rdi
	movq	%rax, %r12
	callq	*%rbp
	testq	%rax, %rax
	je	.LBB0_3
	cmpq	$21901024, 8(%rax)
	movq	%r13, %rdi
	jne	.LBB0_4
	movl	(%r14), %edi
	movq	%r14, %rsi
	movq	%r15, %rdx
	movq	%r12, %rcx
	cmpl	$-1, %edi
	je	.LBB0_13
	incl	%edi
	movl	%edi, (%rsi)
.LBB0_13:
	movl	(%rdx), %edi
	cmpl	$-1, %edi
	je	.LBB0_14
	incl	%edi
	movl	%edi, (%rdx)
.LBB0_14:
	movl	(%rcx), %edi
	cmpl	$-1, %edi
	je	.LBB0_15
	incl	%edi
	movl	%edi, (%rcx)
.LBB0_15:
	movl	(%rax), %edi
	cmpl	$-1, %edi
	je	.LBB0_16
	incl	%edi
	movl	%edi, (%rax)
.LBB0_16:
	movq	%rsi, 24(%rsp)
	movq	%rdx, 32(%rsp)
	movq	%rcx, 40(%rsp)
	movq	%rax, %rbx
	movq	%rax, 48(%rsp)
	movabsq	$PyObject_Vectorcall, %rax
	leaq	24(%rsp), %rsi
	movl	$440674576, %edi
	movl	$4, %edx
	xorl	%ecx, %ecx
	callq	*%rax
	testq	%rax, %rax
	je	.LBB0_30
	cmpl	$0, (%rbx)
	js	.LBB0_20
	decq	(%rbx)
	movq	%rbx, %rdi
	jne	.LBB0_20
	movabsq	$_Py_Dealloc, %rcx
	movq	%rax, %rbx
	callq	*%rcx
	movq	%rbx, %rax
.LBB0_20:
	cmpl	$0, (%r12)
	js	.LBB0_23
	decq	(%r12)
	movq	%r12, %rdi
	jne	.LBB0_23
	movabsq	$_Py_Dealloc, %rcx
	movq	%rax, %rbx
	callq	*%rcx
	movq	%rbx, %rax
.LBB0_23:
	cmpl	$0, (%r15)
	js	.LBB0_26
	decq	(%r15)
	movq	%r15, %rdi
	jne	.LBB0_26
	movabsq	$_Py_Dealloc, %rcx
	movq	%rax, %rbx
	callq	*%rcx
	movq	%rbx, %rax
.LBB0_26:
	cmpl	$0, (%r14)
	js	.LBB0_29
	decq	(%r14)
	movq	%r14, %rdi
	jne	.LBB0_29
	movabsq	$_Py_Dealloc, %rcx
	movq	%rax, %rbx
	callq	*%rcx
	movq	%rbx, %rax
	jmp	.LBB0_29
.LBB0_3:
	movabsq	$PyErr_Occurred, %rax
	callq	*%rax
	movq	%r13, %rdi
	testq	%rax, %rax
	je	.LBB0_4
	movabsq	$PyErr_Fetch, %rax
	leaq	16(%rsp), %rdi
	leaq	8(%rsp), %rsi
	movq	%rsp, %rdx
	callq	*%rax
.LBB0_40:
	movq	16(%rsp), %rdi
	movq	8(%rsp), %rsi
	movq	(%rsp), %rdx
	movabsq	$PyErr_Restore, %rax
	callq	*%rax
	xorl	%eax, %eax
.LBB0_29:
	addq	$56, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%r12
	.cfi_def_cfa_offset 40
	popq	%r13
	.cfi_def_cfa_offset 32
	popq	%r14
	.cfi_def_cfa_offset 24
	popq	%r15
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	retq
.LBB0_4:
	.cfi_def_cfa_offset 112
	movabsq	$PyObject_CallOneArg, %rax
	movq	%rbx, %rsi
	addq	$56, %rsp
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	popq	%r12
	.cfi_def_cfa_offset 40
	popq	%r13
	.cfi_def_cfa_offset 32
	popq	%r14
	.cfi_def_cfa_offset 24
	popq	%r15
	.cfi_def_cfa_offset 16
	popq	%rbp
	.cfi_def_cfa_offset 8
	jmpq	*%rax
.LBB0_30:
	.cfi_def_cfa_offset 112
	movabsq	$PyErr_Fetch, %rax
	leaq	16(%rsp), %rdi
	leaq	8(%rsp), %rsi
	movq	%rsp, %rdx
	callq	*%rax
	cmpl	$0, (%rbx)
	js	.LBB0_33
	decq	(%rbx)
	movq	%rbx, %rdi
	jne	.LBB0_33
	movabsq	$_Py_Dealloc, %rax
	callq	*%rax
.LBB0_33:
	cmpl	$0, (%r12)
	js	.LBB0_36
	decq	(%r12)
	movq	%r12, %rdi
	jne	.LBB0_36
	movabsq	$_Py_Dealloc, %rax
	callq	*%rax
.LBB0_36:
	cmpl	$0, (%r15)
	js	.LBB0_39
	decq	(%r15)
	movq	%r15, %rdi
	jne	.LBB0_39
	movabsq	$_Py_Dealloc, %rax
	callq	*%rax
.LBB0_39:
	cmpl	$0, (%r14)
	js	.LBB0_40
	decq	(%r14)
	movq	%r14, %rdi
	jne	.LBB0_40
	movabsq	$_Py_Dealloc, %rax
	callq	*%rax
	jmp	.LBB0_40
.Lfunc_end0:
	.size	adaptix_raw, .Lfunc_end0-adaptix_raw
	.cfi_endproc

	.globl	adaptix_entry
	.p2align	4
	.type	adaptix_entry,@function
adaptix_entry:
	.cfi_startproc
	pushq	%r15
	.cfi_def_cfa_offset 16
	pushq	%r14
	.cfi_def_cfa_offset 24
	pushq	%rbx
	.cfi_def_cfa_offset 32
	.cfi_offset %rbx, -32
	.cfi_offset %r14, -24
	.cfi_offset %r15, -16
	movq	%rdx, %r15
	movq	%rsi, %rbx
	testq	%rcx, %rcx
	je	.LBB1_1
	movabsq	$PyTuple_Size, %rax
	movq	%rcx, %rdi
	movq	%rcx, %r14
	callq	*%rax
	testq	%rax, %rax
	je	.LBB1_1
	xorq	$1, %rax
	orq	%rax, %r15
	jne	.LBB1_6
	movabsq	$PyTuple_GetItem, %rax
	movq	%r14, %rdi
	xorl	%esi, %esi
	callq	*%rax
	movabsq	$PyUnicode_CompareWithASCIIString, %rcx
	movabsq	$137892497034224, %rsi
	movq	%rax, %rdi
	callq	*%rcx
	testl	%eax, %eax
	je	.LBB1_2
.LBB1_6:
	movabsq	$PyErr_SetString, %rax
	movabsq	$137888969985200, %rsi
	movl	$21852336, %edi
	callq	*%rax
	xorl	%eax, %eax
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	retq
.LBB1_1:
	.cfi_def_cfa_offset 32
	cmpq	$1, %r15
	jne	.LBB1_6
.LBB1_2:
	movq	(%rbx), %rdi
	movabsq	$adaptix_raw, %rax
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	jmpq	*%rax
.Lfunc_end1:
	.size	adaptix_entry, .Lfunc_end1-adaptix_entry
	.cfi_endproc

	.section	".note.GNU-stack","",@progbits
