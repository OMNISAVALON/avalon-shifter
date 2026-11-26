#![no_std]
#![no_main]
#![no_builtins]

use core::ffi::c_void;
use core::panic::PanicInfo;

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    unsafe { ExitProcess(1) }
}

#[no_mangle]
pub unsafe extern "C" fn memcpy(
    dest: *mut c_void,
    src: *const c_void,
    n: usize,
) -> *mut c_void {
    let d = dest as *mut u8;
    let s = src as *const u8;
    let mut i = 0usize;
    while i < n {
        core::ptr::write_volatile(d.add(i), *s.add(i));
        i += 1;
    }
    dest
}

#[no_mangle]
pub unsafe extern "C" fn memset(
    dest: *mut c_void,
    val: i32,
    n: usize,
) -> *mut c_void {
    let d = dest as *mut u8;
    let b = val as u8;
    let mut i = 0usize;
    while i < n {
        core::ptr::write_volatile(d.add(i), b);
        i += 1;
    }
    dest
}

const INVALID_FILE_ATTRIBUTES: u32 = 0xFFFF_FFFF;
const FILE_ATTRIBUTE_DIRECTORY: u32 = 0x0000_0010;
const ATTACH_PARENT_PROCESS: u32 = 0xFFFF_FFFF;
const STD_OUTPUT_HANDLE: u32 = 0xFFFF_FFF5; // -11
const STD_ERROR_HANDLE: u32 = 0xFFFF_FFF4; // -12
const MB_OK: u32 = 0x0000_0000;
const MB_ICONERROR: u32 = 0x0000_0010;
const HKEY_CURRENT_USER: isize = 0x8000_0001u32 as i32 as isize;
const HKEY_LOCAL_MACHINE: isize = 0x8000_0002u32 as i32 as isize;
const RRF_RT_REG_SZ: u32 = 0x0000_0002;
const MAX_WPATH: usize = 1024;
const MAX_ARGS: usize = 64;

type PyMainFn = unsafe extern "C" fn(i32, *mut *mut u16) -> i32;

#[link(name = "kernel32")]
extern "system" {
    fn GetModuleFileNameW(hModule: *mut c_void, lpFilename: *mut u16, nSize: u32) -> u32;
    fn SetCurrentDirectoryW(lpPathName: *const u16) -> i32;
    fn GetCommandLineW() -> *const u16;
    fn AttachConsole(dwProcessId: u32) -> i32;
    fn GetStdHandle(nStdHandle: u32) -> *mut c_void;
    fn GetEnvironmentVariableW(lpName: *const u16, lpBuffer: *mut u16, nSize: u32) -> u32;
    fn SetEnvironmentVariableW(lpName: *const u16, lpValue: *const u16) -> i32;
    fn GetFileAttributesW(lpFileName: *const u16) -> u32;
    fn SetDllDirectoryW(lpPathName: *const u16) -> i32;
    fn SearchPathW(
        lpPath: *const u16,
        lpFileName: *const u16,
        lpExtension: *const u16,
        nBufferLength: u32,
        lpBuffer: *mut u16,
        lpFilePart: *mut *mut u16,
    ) -> u32;
    fn LoadLibraryW(lpLibFileName: *const u16) -> *mut c_void;
    fn GetProcAddress(hModule: *mut c_void, lpProcName: *const u8) -> *const c_void;
    fn LocalFree(hMem: *mut c_void) -> *mut c_void;
    fn ExitProcess(uExitCode: u32) -> !;
}

#[link(name = "shell32")]
extern "system" {
    fn CommandLineToArgvW(lpCmdLine: *const u16, pNumArgs: *mut i32) -> *mut *mut u16;
}

#[link(name = "user32")]
extern "system" {
    fn MessageBoxW(
        hWnd: *mut c_void,
        lpText: *const u16,
        lpCaption: *const u16,
        uType: u32,
    ) -> i32;
}

#[link(name = "advapi32")]
extern "system" {
    fn RegGetValueW(
        hkey: isize,
        lpSubKey: *const u16,
        lpValue: *const u16,
        dwFlags: u32,
        pdwType: *mut u32,
        pvData: *mut u8,
        pcbData: *mut u32,
    ) -> i32;
}

// Статические буферы (BSS) исключают рост стека и требование __chkstk при /NODEFAULTLIB
static mut EXE_PATH: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut EXE_DIR: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut APP_PY_PATH: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut PYTHON_DIR: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut PYTHON_DLL_PATH: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut ENV_BUF: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut AUX_PATH: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut PORTABLE_PROBE_DIR: [u16; MAX_WPATH] = [0; MAX_WPATH];
static mut PY_ARGV_PTRS: [*mut u16; MAX_ARGS] = [core::ptr::null_mut(); MAX_ARGS];
static ONE_WSTR: [u16; 2] = [b'1' as u16, 0];

unsafe fn w_len(ptr: *const u16) -> usize {
    if ptr.is_null() {
        return 0;
    }
    let mut i = 0usize;
    while i < MAX_WPATH && *ptr.add(i) != 0 {
        i += 1;
    }
    i
}

unsafe fn w_copy(dst: *mut u16, cap: usize, src: *const u16) -> usize {
    if cap == 0 || src.is_null() {
        return 0;
    }
    let mut i = 0usize;
    while i + 1 < cap {
        let ch = *src.add(i);
        if ch == 0 {
            break;
        }
        *dst.add(i) = ch;
        i += 1;
    }
    *dst.add(i) = 0;
    i
}

fn fill_ascii_w(buf: &mut [u16], ascii: &[u8]) -> *const u16 {
    let cap = buf.len();
    let mut i = 0usize;
    while i < ascii.len() && i + 1 < cap {
        buf[i] = ascii[i] as u16;
        i += 1;
    }
    if cap > 0 {
        buf[i] = 0;
    }
    buf.as_ptr()
}

unsafe fn w_eq_ascii(ws: *const u16, ascii: &[u8]) -> bool {
    if ws.is_null() {
        return false;
    }
    let mut i = 0usize;
    while i < ascii.len() {
        if *ws.add(i) != (ascii[i] as u16) {
            return false;
        }
        i += 1;
    }
    *ws.add(i) == 0
}

unsafe fn join_dir_ascii(dir: *const u16, suffix: &[u8], out: *mut u16, cap: usize) -> usize {
    let mut len = w_copy(out, cap, dir);
    while len > 3 && (*out.add(len - 1) == b'\\' as u16 || *out.add(len - 1) == b'/' as u16) {
        len -= 1;
        *out.add(len) = 0;
    }
    if len == 0 || cap <= 1 {
        return 0;
    }
    let need_slash = *out.add(len - 1) != b'\\' as u16 && *out.add(len - 1) != b'/' as u16;
    if need_slash && len + 1 < cap {
        *out.add(len) = b'\\' as u16;
        len += 1;
    }
    let mut i = 0usize;
    while i < suffix.len() && len + 1 < cap {
        *out.add(len) = suffix[i] as u16;
        len += 1;
        i += 1;
    }
    *out.add(len) = 0;
    len
}

unsafe fn is_regular_file(path: *const u16) -> bool {
    let attr = GetFileAttributesW(path);
    attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY) == 0
}

unsafe fn is_directory(path: *const u16) -> bool {
    let attr = GetFileAttributesW(path);
    attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY) != 0
}

unsafe fn show_error(msg_ascii: &[u8]) {
    let mut title = [0u16; 32];
    let mut body = [0u16; 256];
    let t_ptr = fill_ascii_w(&mut title, b"Avalon.Shifter");
    let b_ptr = fill_ascii_w(&mut body, msg_ascii);
    MessageBoxW(core::ptr::null_mut(), b_ptr, t_ptr, MB_OK | MB_ICONERROR);
}

unsafe fn try_dir_for_python(dir: *const u16) -> bool {
    if dir.is_null() || *dir == 0 {
        return false;
    }
    let dll_names: [&[u8]; 4] = [
        b"python312.dll",
        b"python313.dll",
        b"python311.dll",
        b"python314.dll",
    ];
    let py_dir = core::ptr::addr_of_mut!(PYTHON_DIR) as *mut u16;
    let dll_path = core::ptr::addr_of_mut!(PYTHON_DLL_PATH) as *mut u16;

    let mut dlen = w_copy(py_dir, MAX_WPATH, dir);
    while dlen > 3 && (*py_dir.add(dlen - 1) == b'\\' as u16 || *py_dir.add(dlen - 1) == b'/' as u16) {
        dlen -= 1;
        *py_dir.add(dlen) = 0;
    }

    let mut idx = 0usize;
    while idx < dll_names.len() {
        join_dir_ascii(py_dir, dll_names[idx], dll_path, MAX_WPATH);
        if is_regular_file(dll_path) {
            return true;
        }
        idx += 1;
    }
    false
}

unsafe fn try_registry_python(root_key: isize, subkey_ascii: &[u8]) -> bool {
    let mut subkey = [0u16; 96];
    let subkey_ptr = fill_ascii_w(&mut subkey, subkey_ascii);
    let env_buf = core::ptr::addr_of_mut!(ENV_BUF) as *mut u16;
    let mut cb_bytes: u32 = ((MAX_WPATH - 1) * 2) as u32;
    let status = RegGetValueW(
        root_key,
        subkey_ptr,
        core::ptr::null(),
        RRF_RT_REG_SZ,
        core::ptr::null_mut(),
        env_buf as *mut u8,
        &mut cb_bytes,
    );
    if status == 0 {
        return try_dir_for_python(env_buf);
    }
    false
}

unsafe fn discover_python(exe_dir: *const u16, used_portable: &mut bool) -> bool {
    *used_portable = false;
    let env_buf = core::ptr::addr_of_mut!(ENV_BUF) as *mut u16;
    let py_dir = core::ptr::addr_of_mut!(PYTHON_DIR) as *mut u16;
    let dll_path = core::ptr::addr_of_mut!(PYTHON_DLL_PATH) as *mut u16;
    let probe_dir = core::ptr::addr_of_mut!(PORTABLE_PROBE_DIR) as *mut u16;

    // 0. Встроенный Portable-рантайм: <exe_dir>\runtime или сам <exe_dir>
    join_dir_ascii(exe_dir, b"runtime", probe_dir, MAX_WPATH);
    if is_directory(probe_dir) && try_dir_for_python(probe_dir) {
        *used_portable = true;
        return true;
    }
    if try_dir_for_python(exe_dir) {
        *used_portable = true;
        return true;
    }

    // Честная проверка режима Portable-Only (блокирует откат на системный Python)
    let mut force_key = [0u16; 32];
    let fn_len = GetEnvironmentVariableW(
        fill_ascii_w(&mut force_key, b"AVALON_FORCE_PORTABLE_ONLY"),
        env_buf,
        MAX_WPATH as u32,
    );
    if fn_len > 0 && *env_buf != (b'0' as u16) {
        return false;
    }

    // 1. Явный приоритет через переменную AVALON_PYTHON_HOME
    let mut key_buf = [0u16; 32];
    let n = GetEnvironmentVariableW(
        fill_ascii_w(&mut key_buf, b"AVALON_PYTHON_HOME"),
        env_buf,
        MAX_WPATH as u32,
    );
    if n > 0 && n < MAX_WPATH as u32 && try_dir_for_python(env_buf) {
        return true;
    }

    // 2. Реестр Windows PythonCore (3.12 в приоритете, далее 3.13/3.11/3.14)
    let reg_paths: [&[u8]; 4] = [
        b"SOFTWARE\\Python\\PythonCore\\3.12\\InstallPath",
        b"SOFTWARE\\Python\\PythonCore\\3.13\\InstallPath",
        b"SOFTWARE\\Python\\PythonCore\\3.11\\InstallPath",
        b"SOFTWARE\\Python\\PythonCore\\3.14\\InstallPath",
    ];
    let mut r_idx = 0usize;
    while r_idx < reg_paths.len() {
        if try_registry_python(HKEY_CURRENT_USER, reg_paths[r_idx])
            || try_registry_python(HKEY_LOCAL_MACHINE, reg_paths[r_idx])
        {
            return true;
        }
        r_idx += 1;
    }

    // 3. Стандартные системные каталоги установки
    let common_dirs: [&[u8]; 3] = [
        b"C:\\Program Files\\Python312",
        b"C:\\Program Files\\Python313",
        b"C:\\Program Files\\Python311",
    ];
    let mut c_idx = 0usize;
    while c_idx < common_dirs.len() {
        let mut dir_w = [0u16; 64];
        let ptr = fill_ascii_w(&mut dir_w, common_dirs[c_idx]);
        if try_dir_for_python(ptr) {
            return true;
        }
        c_idx += 1;
    }

    // 4. Поиск python312.dll / python313.dll / python311.dll на PATH
    let dll_names: [&[u8]; 3] = [b"python312.dll", b"python313.dll", b"python311.dll"];
    let mut d_idx = 0usize;
    while d_idx < dll_names.len() {
        let mut fname = [0u16; 32];
        let found = SearchPathW(
            core::ptr::null(),
            fill_ascii_w(&mut fname, dll_names[d_idx]),
            core::ptr::null(),
            MAX_WPATH as u32,
            dll_path,
            core::ptr::null_mut(),
        );
        if found > 0 && found < MAX_WPATH as u32 {
            let plen = w_len(dll_path);
            let mut slash = plen;
            while slash > 0 {
                slash -= 1;
                if *dll_path.add(slash) == b'\\' as u16 || *dll_path.add(slash) == b'/' as u16 {
                    break;
                }
            }
            if slash > 0 {
                let mut i = 0usize;
                while i < slash {
                    *py_dir.add(i) = *dll_path.add(i);
                    i += 1;
                }
                *py_dir.add(slash) = 0;
                return true;
            }
        }
        d_idx += 1;
    }

    false
}

unsafe fn set_env_if_missing(name_ascii: &[u8], val: *const u16) {
    let mut name_w = [0u16; 32];
    let name_ptr = fill_ascii_w(&mut name_w, name_ascii);
    let mut probe = [0u16; 8];
    if GetEnvironmentVariableW(name_ptr, probe.as_mut_ptr(), 8) == 0 {
        SetEnvironmentVariableW(name_ptr, val);
    }
}

#[no_mangle]
pub unsafe extern "system" fn avalon_entry() -> ! {
    let exe_buf = core::ptr::addr_of_mut!(EXE_PATH) as *mut u16;
    let exe_dir = core::ptr::addr_of_mut!(EXE_DIR) as *mut u16;
    let app_py = core::ptr::addr_of_mut!(APP_PY_PATH) as *mut u16;

    let exe_len = GetModuleFileNameW(core::ptr::null_mut(), exe_buf, MAX_WPATH as u32) as usize;
    if exe_len == 0 || exe_len >= MAX_WPATH {
        show_error(b"Failed to resolve executable directory for Avalon.Shifter.");
        ExitProcess(1);
    }

    let mut slash = exe_len;
    while slash > 0 {
        slash -= 1;
        if *exe_buf.add(slash) == b'\\' as u16 || *exe_buf.add(slash) == b'/' as u16 {
            break;
        }
    }
    if slash == 0 {
        show_error(b"Invalid executable directory path.");
        ExitProcess(1);
    }

    let mut i = 0usize;
    while i < slash {
        *exe_dir.add(i) = *exe_buf.add(i);
        i += 1;
    }
    *exe_dir.add(slash) = 0;

    SetCurrentDirectoryW(exe_dir);
    join_dir_ascii(exe_dir, b"app.py", app_py, MAX_WPATH);
    if !is_regular_file(app_py) {
        show_error(b"app.py was not found next to AvalonShifter.exe.");
        ExitProcess(2);
    }

    let mut raw_argc: i32 = 0;
    let raw_argv = CommandLineToArgvW(GetCommandLineW(), &mut raw_argc);

    let mut wants_console = false;
    if !raw_argv.is_null() && raw_argc > 1 {
        let mut a = 1isize;
        while a < raw_argc as isize {
            if w_eq_ascii(*raw_argv.offset(a), b"--self-test") {
                wants_console = true;
                break;
            }
            a += 1;
        }
    }
    if wants_console {
        let std_out = GetStdHandle(STD_OUTPUT_HANDLE);
        let std_err = GetStdHandle(STD_ERROR_HANDLE);
        if std_out.is_null() && std_err.is_null() {
            AttachConsole(ATTACH_PARENT_PROCESS);
        }
    }

    let mut used_portable = false;
    if !discover_python(exe_dir, &mut used_portable) {
        if !raw_argv.is_null() {
            LocalFree(raw_argv as *mut c_void);
        }
        show_error(b"Python 3.12+ (python312.dll) was not found. Use Portable package or install Python 3.12.");
        ExitProcess(3);
    }

    let py_dir = core::ptr::addr_of!(PYTHON_DIR) as *const u16;
    let dll_path = core::ptr::addr_of!(PYTHON_DLL_PATH) as *const u16;
    let aux = core::ptr::addr_of_mut!(AUX_PATH) as *mut u16;

    set_env_if_missing(b"PYTHONHOME", py_dir);
    if used_portable {
        set_env_if_missing(b"PYTHONNOUSERSITE", ONE_WSTR.as_ptr());
        set_env_if_missing(b"PYTHONDONTWRITEBYTECODE", ONE_WSTR.as_ptr());
    }

    join_dir_ascii(py_dir, b"tcl\\tcl8.6", aux, MAX_WPATH);
    if is_directory(aux) {
        set_env_if_missing(b"TCL_LIBRARY", aux);
    }
    join_dir_ascii(py_dir, b"tcl\\tk8.6", aux, MAX_WPATH);
    if is_directory(aux) {
        set_env_if_missing(b"TK_LIBRARY", aux);
    }

    SetDllDirectoryW(py_dir);
    let h_py = LoadLibraryW(dll_path);
    if h_py.is_null() {
        if !raw_argv.is_null() {
            LocalFree(raw_argv as *mut c_void);
        }
        show_error(b"Failed to load python3xx.dll for Avalon.Shifter.");
        ExitProcess(4);
    }

    let proc_ptr = GetProcAddress(h_py, b"Py_Main\0".as_ptr());
    if proc_ptr.is_null() {
        if !raw_argv.is_null() {
            LocalFree(raw_argv as *mut c_void);
        }
        show_error(b"Py_Main entry point not found in loaded Python DLL.");
        ExitProcess(5);
    }
    let py_main: PyMainFn = core::mem::transmute(proc_ptr);

    let argv_out = core::ptr::addr_of_mut!(PY_ARGV_PTRS) as *mut *mut u16;
    *argv_out.add(0) = exe_buf;
    *argv_out.add(1) = app_py;
    let mut out_argc: usize = 2;

    if !raw_argv.is_null() && raw_argc > 1 {
        let mut a = 1isize;
        while a < raw_argc as isize && out_argc < MAX_ARGS {
            *argv_out.add(out_argc) = *raw_argv.offset(a);
            out_argc += 1;
            a += 1;
        }
    }

    let exit_code = py_main(out_argc as i32, argv_out);
    if !raw_argv.is_null() {
        LocalFree(raw_argv as *mut c_void);
    }
    ExitProcess(exit_code as u32);
}
