# Packages/LSP-gopls/plugin.py

from typing import Tuple
import sublime

from LSP.plugin import AbstractPlugin, register_plugin, unregister_plugin
from LSP.plugin.core.typing import Any, Optional

from shutil import which
import subprocess
import os
import re

'''
Current version of gopls that the plugin installs
Review gopls settings when updating TAG to see if
new settings exist
'''
TAG = "0.7.3"
GOPLS_BASE_URL = 'golang.org/x/tools/gopls@v{tag}'

RE_VER = re.compile(r"go(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


class Gopls(AbstractPlugin):

    @classmethod
    def name(cls):
        return "gopls"

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), __package__)

    @classmethod
    def server_version(cls) -> str:
        return TAG

    @classmethod
    def current_server_version(cls) -> Optional[str]:
        try:
            with open(os.path.join(cls.basedir(), "VERSION"), "r") as fp:
                return fp.read()
        except:
            return None

    @classmethod
    def _is_gopls_installed(cls) -> bool:
        gopls_binary = get_setting(
            'command', [os.path.join(cls.basedir(), 'bin', 'gopls')])
        return _is_binary_available(gopls_binary[0])

    @classmethod
    def _is_go_installed(cls) -> bool:
        return _is_binary_available('go')

    @classmethod
    def _get_go_version(cls) -> Tuple[int, int, int]:
        go_binary = str(which('go'))
        stdout, stderr, return_code = run_go_command(go=go_binary, sub_command='version', env_vars=cls._set_env_vars())
        if return_code != 0:
            raise ValueError(
                'go version error', stderr, 'returncode', return_code)

        if stdout == '':
            return (0, 0, 0)

        matches = RE_VER.search(stdout)
        if matches is None:
            return (0, 0, 0)
        return (to_int(matches.group(1)), to_int(matches.group(2)), to_int(matches.group(3)))

    @classmethod
    def _set_env_vars(cls) -> dict:
        env_vars = dict(os.environ)
        env_vars['GO111MODULE'] = 'on'
        env_vars['GOPATH'] = cls.basedir()
        env_vars['GOBIN'] = os.path.join(cls.basedir(), 'bin')
        env_vars['GOCACHE'] = os.path.join(cls.basedir(), 'go-build')
        return env_vars

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        return not cls._is_gopls_installed() or (cls.server_version() != cls.current_server_version())

    @classmethod
    def install_or_update(cls) -> None:
        if not cls._is_go_installed():
            raise ValueError('go binary not found in $PATH')

        os.makedirs(cls.basedir(), exist_ok=True)

        go_binary = str(which('go'))
        go_version = cls._get_go_version()
        go_sub_command = 'get' if go_version[1] < 16 else 'install'
        stdout, stderr, return_code = run_go_command(
            go=go_binary, sub_command=go_sub_command, env_vars=cls._set_env_vars())
        if return_code != 0:
            raise ValueError(
                'go installation error', stderr, 'returncode', return_code)

        with open(os.path.join(cls.basedir(), "VERSION"), "w") as fp:
            fp.write(cls.server_version())


def run_go_command(go: str, sub_command: str = 'install', env_vars: dict = {}) -> Tuple[str, str, int]:
    startupinfo = None
    if sublime.platform() == 'Windows':
        startupinfo = subprocess.STARTUPINFO()  # type: ignore
        startupinfo.dwFlags |= subprocess.SW_HIDE | subprocess.STARTF_USESHOWWINDOW  # type: ignore

    process = subprocess.Popen([go, sub_command, GOPLS_BASE_URL.format(tag=TAG)],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               env=env_vars,
                               startupinfo=startupinfo)
    stdout, stderr = process.communicate()
    return str(stdout), str(stderr), process.returncode,

def to_int(value: Any[str, None] = '') -> int:
    if value is None:
        return 0
    return int(value)

def _is_binary_available(path) -> bool:
    return bool(which(path))


def get_setting(key: str, default=None) -> Any:
    settings = sublime.load_settings(
        'LSP-gopls.sublime-settings').get("settings", {})
    return settings.get(key, default)


def plugin_loaded():
    register_plugin(Gopls)


def plugin_unloaded():
    unregister_plugin(Gopls)
