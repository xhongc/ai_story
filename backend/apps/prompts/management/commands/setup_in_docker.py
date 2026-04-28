import logging
import multiprocessing
import os
import re
import shutil
import sys
from pathlib import Path

from distutils.core import setup

from Cython.Build import cythonize
from django.core.management.base import BaseCommand


NB_COMPILE_JOBS = multiprocessing.cpu_count()
LOGGER = logging.getLogger("encrypt-py")

FORMATTER = logging.Formatter("%(asctime)s|%(levelname)s| %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setFormatter(FORMATTER)

if not LOGGER.handlers:
    LOGGER.addHandler(HANDLER)
LOGGER.setLevel(logging.DEBUG)

EXCLUDED_DIRS = {
    "__pycache__",
    "migrations",
    "tests",
}
EXCLUDED_FILES = {
    "__init__.py",
    "manage.py",
}


def walk_python_files(target_path):
    path = Path(target_path)
    if path.is_file() and path.suffix == ".py":
        yield str(path)
        return

    for current_path, dir_names, file_names in os.walk(path):
        dir_names[:] = [name for name in dir_names if name not in EXCLUDED_DIRS]
        for file_name in file_names:
            if not file_name.endswith(".py"):
                continue
            if file_name in EXCLUDED_FILES:
                continue
            yield str(Path(current_path) / file_name)


def delete_generated_c_files(py_files):
    for py_file in py_files:
        c_file = Path(py_file).with_suffix(".c")
        if c_file.exists():
            c_file.unlink()


def delete_build_cache(path):
    target_path = Path(path)
    for current_path, dir_names, _ in os.walk(target_path):
        for dir_name in list(dir_names):
            if dir_name != "__pycache__":
                continue
            shutil.rmtree(Path(current_path) / dir_name, ignore_errors=True)


def rename_compiled_extensions(path):
    for extension in Path(path).rglob("*.so"):
        stem = extension.name[:-len(extension.suffix)]
        new_name = f"{stem.split('.', 1)[0]}{extension.suffix}"
        if new_name != extension.name:
            os.replace(str(extension), str(extension.with_name(new_name)))
    for extension in Path(path).rglob("*.pyd"):
        stem = extension.name[:-len(extension.suffix)]
        new_name = f"{stem.split('.', 1)[0]}{extension.suffix}"
        if new_name != extension.name:
            os.replace(str(extension), str(extension.with_name(new_name)))


def chunk_list(items, chunk_count):
    if not items:
        return []

    chunk_count = max(1, min(chunk_count, len(items)))
    size = len(items) // chunk_count
    remainder = len(items) % chunk_count
    result = []
    start = 0
    for index in range(chunk_count):
        end = start + size + (1 if index < remainder else 0)
        result.append(items[start:end])
        start = end
    return [chunk for chunk in result if chunk]


def compile_python_files(py_files, build_path):
    compiled_files = []
    total_count = len(py_files)

    for index, py_file in enumerate(py_files, start=1):
        file_name = os.path.basename(py_file)
        success = False

        for attempt in range(1, 4):
            try:
                LOGGER.debug("编译进行中 %s/%s, %s (try %s)", index, total_count, file_name, attempt)
                setup(
                    ext_modules=cythonize([py_file], quiet=True, language_level=3),
                    script_args=["build_ext", "-t", str(build_path), "--inplace"],
                )
                compiled_files.append(py_file)
                LOGGER.debug("编译成功 %s", py_file)
                success = True
                break
            except Exception as exc:
                LOGGER.exception("编译失败 %s, 错误 %s (try %s)", py_file, exc, attempt)
                c_file = Path(py_file).with_suffix(".c")
                if c_file.exists():
                    c_file.unlink()

        if not success:
            LOGGER.error("编译最终失败，尝试了3次: %s", py_file)

    return compiled_files


def run_compile(args):
    file_list, build_path = args
    return compile_python_files(file_list, build_path)


class Command(BaseCommand):
    help = "在 docker 环境中编译 agent 和 mcp 应用为 so/pyd 文件，并保留源码"

    def handle(self, *args, **options):
        base_dir = Path(__file__).resolve().parents[4]
        build_path = base_dir / "build"
        target_dirs = [
            base_dir / "apps" / "agent",
            base_dir / "apps" / "mcp",
        ]

        build_path.mkdir(parents=True, exist_ok=True)
        py_files = []
        for target_dir in target_dirs:
            if not target_dir.exists():
                LOGGER.warning("目标目录不存在，跳过: %s", target_dir)
                continue
            py_files.extend(walk_python_files(target_dir))

        py_files = sorted(set(py_files))

        if not py_files:
            LOGGER.warning("未找到可编译的 Python 文件，目标目录: %s", ", ".join(str(path) for path in target_dirs))
            return

        LOGGER.debug(">>> 开始编译，总共 %s 个进程，目标文件 %s 个", NB_COMPILE_JOBS, len(py_files))
        tasks = [(chunk, build_path) for chunk in chunk_list(py_files, NB_COMPILE_JOBS)]

        if len(tasks) == 1:
            compiled_groups = [run_compile(tasks[0])]
        else:
            with multiprocessing.Pool(processes=len(tasks)) as pool:
                compiled_groups = pool.map(run_compile, tasks)

        compiled_files = [file_path for group in compiled_groups for file_path in group]
        delete_generated_c_files(compiled_files)

        for target_dir in target_dirs:
            rename_compiled_extensions(target_dir)
            delete_build_cache(target_dir)

        LOGGER.debug("删除 build 目录 %s", build_path)
        shutil.rmtree(build_path, ignore_errors=True)
        LOGGER.debug(">>> 编译完成，生成扩展文件 %s 个，源码已保留", len(compiled_files))
