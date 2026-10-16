	.file	"<string>"
	.section	.ltext,"axl",@progbits
	.globl	adaptix_raw
	.p2align	4
	.type	adaptix_raw,@function
adaptix_raw:
	.cfi_startproc
	pushq	%r15
	.cfi_def_cfa_offset 16
	pushq	%r14
	.cfi_def_cfa_offset 24
	pushq	%rbx
	.cfi_def_cfa_offset 32
	subq	$32, %rsp
	.cfi_def_cfa_offset 64
	.cfi_offset %rbx, -32
	.cfi_offset %r14, -24
	.cfi_offset %r15, -16
	movq	$0, 24(%rsp)
	movq	$0, 16(%rsp)
	movq	$0, 8(%rsp)
	movq	%rdi, %rbx
	movabsq	$137892598207712, %rdi
	cmpq	$21898448, 8(%rbx)
	jne	.LBB0_16
	cmpq	$42, 193113032(%rdi)
	jne	.LBB0_16
	movq	16(%rbx), %r14
	movabsq	$PyList_New, %rax
	movq	%rdi, %r15
	movq	%r14, %rdi
	callq	*%rax
	testq	%rax, %rax
	je	.LBB0_10
	movq	16(%rbx), %rcx
	movq	%r15, %rdi
	cmpq	%rcx, %r14
	jae	.LBB0_4
.LBB0_13:
	cmpl	$0, (%rax)
	js	.LBB0_16
	decq	(%rax)
	jne	.LBB0_16
	movabsq	$_Py_Dealloc, %rcx
	movq	%rax, %rdi
	callq	*%rcx
	movq	%r15, %rdi
.LBB0_16:
	movabsq	$PyObject_CallOneArg, %rax
	movq	%rbx, %rsi
	addq	$32, %rsp
	.cfi_def_cfa_offset 32
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	jmpq	*%rax
.LBB0_10:
	.cfi_def_cfa_offset 64
	movabsq	$PyErr_Fetch, %rax
	leaq	24(%rsp), %rdi
	leaq	16(%rsp), %rsi
	leaq	8(%rsp), %rdx
	callq	*%rax
	movq	24(%rsp), %rdi
	movq	16(%rsp), %rsi
	movq	8(%rsp), %rdx
	movabsq	$PyErr_Restore, %rax
	callq	*%rax
	xorl	%eax, %eax
	jmp	.LBB0_11
.LBB0_4:
	testq	%rcx, %rcx
	je	.LBB0_9
	movq	24(%rbx), %rdx
	movq	24(%rax), %rsi
	xorl	%r8d, %r8d
	jmp	.LBB0_6
	.p2align	4
.LBB0_8:
	movq	%r9, (%rsi,%r8,8)
	incq	%r8
	cmpq	%r8, %rcx
	je	.LBB0_9
.LBB0_6:
	movq	(%rdx,%r8,8), %r9
	cmpq	$21901024, 8(%r9)
	jne	.LBB0_13
	movl	(%r9), %r10d
	cmpl	$-1, %r10d
	je	.LBB0_8
	incl	%r10d
	movl	%r10d, (%r9)
	jmp	.LBB0_8
.LBB0_9:
	movq	%rcx, 16(%rax)
.LBB0_11:
	addq	$32, %rsp
	.cfi_def_cfa_offset 32
	popq	%rbx
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	retq
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
	movabsq	$137892598564144, %rsi
	movabsq	$PyUnicode_CompareWithASCIIString, %rcx
	movq	%rax, %rdi
	addq	$277664, %rsi
	callq	*%rcx
	testl	%eax, %eax
	je	.LBB1_2
.LBB1_6:
	movabsq	$PyErr_SetString, %rax
	movabsq	$137892598564144, %rsi
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
