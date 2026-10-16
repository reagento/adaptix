.intel_syntax noprefix
model_loader_Model4Slots:
    endbr64
    push rbp; mov rbp, rsp
    sub rsp, 240
    xor eax, eax
    mov [rbp-16], rax
    mov [rbp-88], rax
    mov [rbp-96], rax
    mov [rbp-104], rax
    mov [rbp-112], rax
    mov [rbp-152], rax
    mov [rbp-160], rax
    test rcx, rcx
    jnz keyword_call_1
    cmp rdx, 1
    jnz invalid_arguments_2
    mov rax, [rsi]
    mov [rbp-8], rax
argument_ready_3:
    mov rax, [rbp-8]
    mov rax, [rax+8]  # ob_type
    mov r11d, 0x14e46c0
    cmp rax, r11
    jnz reference_fallback_4
    mov rax, [rbp-8]
    load dictionary keys
    check unicode dictionary
    jnz reference_fallback_4
    mov rdi, [rbp-8]
    mov rsi, 0x7d699f980780
    xor eax, eax
    mov r11d, 0x1858580
    call r11  # PyDict_GetItemWithError
    mov [rbp-24], rax
    mov rax, [rbp-24]
    test rax, rax
    jnz reference_field_present_6
    xor eax, eax
    mov r11d, 0x19aefda
    call r11  # PyErr_Occurred
    mov [rbp-32], rax
    test rax, rax
    jnz error
    jmp reference_fallback_4
reference_field_present_6:
    mov rax, [rbp-24]
    mov rax, [rax+8]  # ob_type
    mov r11d, 0x14e2ee0
    cmp rax, r11
    jz reference_type_ok_7
    jmp reference_fallback_4
reference_type_ok_7:
    mov rdi, [rbp-8]
    mov rsi, 0x7d699f9807e0
    xor eax, eax
    mov r11d, 0x1858580
    call r11  # PyDict_GetItemWithError
    mov [rbp-40], rax
    mov rax, [rbp-40]
    test rax, rax
    jnz reference_field_present_8
    xor eax, eax
    mov r11d, 0x19aefda
    call r11  # PyErr_Occurred
    mov [rbp-48], rax
    test rax, rax
    jnz error
    jmp reference_fallback_4
reference_field_present_8:
    mov rax, [rbp-40]
    mov rax, [rax+8]  # ob_type
    mov r11d, 0x14e2ee0
    cmp rax, r11
    jz reference_type_ok_9
    jmp reference_fallback_4
reference_type_ok_9:
    mov rdi, [rbp-8]
    mov rsi, 0x7d699f980840
    xor eax, eax
    mov r11d, 0x1858580
    call r11  # PyDict_GetItemWithError
    mov [rbp-56], rax
    mov rax, [rbp-56]
    test rax, rax
    jnz reference_field_present_10
    xor eax, eax
    mov r11d, 0x19aefda
    call r11  # PyErr_Occurred
    mov [rbp-64], rax
    test rax, rax
    jnz error
    jmp reference_fallback_4
reference_field_present_10:
    mov rax, [rbp-56]
    mov rax, [rax+8]  # ob_type
    mov r11d, 0x14e2ee0
    cmp rax, r11
    jz reference_type_ok_11
    jmp reference_fallback_4
reference_type_ok_11:
    mov rdi, [rbp-8]
    mov rsi, 0x7d699f9808a0
    xor eax, eax
    mov r11d, 0x1858580
    call r11  # PyDict_GetItemWithError
    mov [rbp-72], rax
    mov rax, [rbp-72]
    test rax, rax
    jnz reference_field_present_12
    xor eax, eax
    mov r11d, 0x19aefda
    call r11  # PyErr_Occurred
    mov [rbp-80], rax
    test rax, rax
    jnz error
    jmp reference_fallback_4
reference_field_present_12:
    mov rax, [rbp-72]
    mov rax, [rax+8]  # ob_type
    mov r11d, 0x14e2ee0
    cmp rax, r11
    jz reference_type_ok_13
    jmp reference_fallback_4
reference_type_ok_13:
    mov rdi, [rbp-24]
    test rdi, rdi
    jz incref_done_14
    load reference count
    cmp eax, 0xffffffff
    jae incref_done_14
    increment reference count
incref_done_14:
    mov rax, [rbp-24]
    mov [rbp-88], rax
    mov rdi, [rbp-40]
    test rdi, rdi
    jz incref_done_15
    load reference count
    cmp eax, 0xffffffff
    jae incref_done_15
    increment reference count
incref_done_15:
    mov rax, [rbp-40]
    mov [rbp-96], rax
    mov rdi, [rbp-56]
    test rdi, rdi
    jz incref_done_16
    load reference count
    cmp eax, 0xffffffff
    jae incref_done_16
    increment reference count
incref_done_16:
    mov rax, [rbp-56]
    mov [rbp-104], rax
    mov rdi, [rbp-72]
    test rdi, rdi
    jz incref_done_17
    load reference count
    cmp eax, 0xffffffff
    jae incref_done_17
    increment reference count
incref_done_17:
    mov rax, [rbp-72]
    mov [rbp-112], rax
    mov rax, [rbp-88]
    mov [rbp-144], rax
    mov rax, [rbp-96]
    mov [rbp-136], rax
    mov rax, [rbp-104]
    mov [rbp-128], rax
    mov rax, [rbp-112]
    mov [rbp-120], rax
    mov edi, 0x1a442910
    lea rsi, [rbp-144]
    mov edx, 0x4
    mov ecx, 0x0
    xor eax, eax
    mov r11d, 0x186a09a
    call r11  # PyObject_Vectorcall
    mov [rbp-152], rax
    test rax, rax
    jz error
    mov rdi, [rbp-112]
    xor eax, eax
    mov [rbp-112], rax
    load reference count
    test eax, eax
    js decref_done_19
    sub QWORD reference count, 1
    jnz decref_done_19
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_19:
released_18:
    mov rdi, [rbp-104]
    xor eax, eax
    mov [rbp-104], rax
    load reference count
    test eax, eax
    js decref_done_22
    sub QWORD reference count, 1
    jnz decref_done_22
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_22:
released_21:
    mov rdi, [rbp-96]
    xor eax, eax
    mov [rbp-96], rax
    load reference count
    test eax, eax
    js decref_done_25
    sub QWORD reference count, 1
    jnz decref_done_25
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_25:
released_24:
    mov rdi, [rbp-88]
    xor eax, eax
    mov [rbp-88], rax
    load reference count
    test eax, eax
    js decref_done_28
    sub QWORD reference count, 1
    jnz decref_done_28
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_28:
released_27:
    mov rax, [rbp-152]
    mov [rbp-16], rax
    xor eax, eax
    mov [rbp-152], rax
    jmp reference_done_5
reference_fallback_4:
    mov rdi, 0x7d69992284a0
    mov rsi, [rbp-8]
    xor eax, eax
    mov r11d, 0x18a6bc0
    call r11  # PyObject_CallOneArg
    mov [rbp-160], rax
    test rax, rax
    jz error
    mov rax, [rbp-160]
    mov [rbp-16], rax
    xor eax, eax
    mov [rbp-160], rax
reference_done_5:
successful_exit_32:
    mov rax, [rbp-16]
    leave; ret
error:
    lea rdi, [rbp-216]
    lea rsi, [rbp-224]
    lea rdx, [rbp-232]
    xor eax, eax
    mov r11d, 0x7e07a0
    call r11  # PyErr_Fetch
    mov rax, [rbp-160]
    test rax, rax
    jz released_34
    mov rdi, [rbp-160]
    xor eax, eax
    mov [rbp-160], rax
    load reference count
    test eax, eax
    js decref_done_35
    sub QWORD reference count, 1
    jnz decref_done_35
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_35:
released_34:
    mov rax, [rbp-152]
    test rax, rax
    jz released_37
    mov rdi, [rbp-152]
    xor eax, eax
    mov [rbp-152], rax
    load reference count
    test eax, eax
    js decref_done_38
    sub QWORD reference count, 1
    jnz decref_done_38
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_38:
released_37:
    mov rax, [rbp-112]
    test rax, rax
    jz released_40
    mov rdi, [rbp-112]
    xor eax, eax
    mov [rbp-112], rax
    load reference count
    test eax, eax
    js decref_done_41
    sub QWORD reference count, 1
    jnz decref_done_41
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_41:
released_40:
    mov rax, [rbp-104]
    test rax, rax
    jz released_43
    mov rdi, [rbp-104]
    xor eax, eax
    mov [rbp-104], rax
    load reference count
    test eax, eax
    js decref_done_44
    sub QWORD reference count, 1
    jnz decref_done_44
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_44:
released_43:
    mov rax, [rbp-96]
    test rax, rax
    jz released_46
    mov rdi, [rbp-96]
    xor eax, eax
    mov [rbp-96], rax
    load reference count
    test eax, eax
    js decref_done_47
    sub QWORD reference count, 1
    jnz decref_done_47
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_47:
released_46:
    mov rax, [rbp-88]
    test rax, rax
    jz released_49
    mov rdi, [rbp-88]
    xor eax, eax
    mov [rbp-88], rax
    load reference count
    test eax, eax
    js decref_done_50
    sub QWORD reference count, 1
    jnz decref_done_50
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_50:
released_49:
    mov rax, [rbp-16]
    test rax, rax
    jz released_52
    mov rdi, [rbp-16]
    xor eax, eax
    mov [rbp-16], rax
    load reference count
    test eax, eax
    js decref_done_53
    sub QWORD reference count, 1
    jnz decref_done_53
    mov r11d, 0x1a19cca
    call r11  # _Py_Dealloc
decref_done_53:
released_52:
    mov rdi, [rbp-216]
    mov rsi, [rbp-224]
    mov rdx, [rbp-232]
    xor eax, eax
    mov r11d, 0x7e0140
    call r11  # PyErr_Restore
    xor eax, eax
    leave; ret
keyword_call_1:
    mov [rbp-168], rsi
    mov [rbp-176], rdx
    mov [rbp-184], rcx
    mov rdi, [rbp-184]
    xor eax, eax
    mov r11d, 0x19d8f42
    call r11  # PyTuple_Size
    mov [rbp-192], rax
    test rax, rax
    jz positional_argument_30
    cmp rax, 1
    jnz invalid_arguments_2
    mov rax, [rbp-176]
    test rax, rax
    jnz invalid_arguments_2
    mov rdi, [rbp-184]
    mov esi, 0x0
    xor eax, eax
    mov r11d, 0x19d8ac6
    call r11  # PyTuple_GetItem
    mov [rbp-200], rax
    mov rax, [rbp-200]
    mov r11d, 0x1540d58
    cmp rax, r11
    jz matched_keyword_31
    mov rdi, [rbp-200]
    mov rsi, 0x7d69984358a0
    xor eax, eax
    mov r11d, 0x183da4c
    call r11  # PyUnicode_CompareWithASCIIString
    mov [rbp-208], rax
    test eax, eax
    jnz invalid_arguments_2
matched_keyword_31:
    mov rax, [rbp-168]
    mov rax, [rax]
    mov [rbp-8], rax
    jmp argument_ready_3
positional_argument_30:
    mov rax, [rbp-176]
    cmp rax, 1
    jnz invalid_arguments_2
    mov rax, [rbp-168]
    mov rax, [rax]
    mov [rbp-8], rax
    jmp argument_ready_3
invalid_arguments_2:
    mov edi, 0x14d70b0
    mov rsi, 0x7d6999310300
    xor eax, eax
    mov r11d, 0x19d500a
    call r11  # PyErr_SetString
    jmp error
native_unary_entry:
    endbr64
    push rbp; mov rbp, rsp
    sub rsp, 240
    xor eax, eax
    mov [rbp-16], rax
    mov [rbp-88], rax
    mov [rbp-96], rax
    mov [rbp-104], rax
    mov [rbp-112], rax
    mov [rbp-152], rax
    mov [rbp-160], rax
    mov [rbp-8], rdi
    jmp native_body
