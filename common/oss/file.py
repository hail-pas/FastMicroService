import time
import random

from common.utils import generate_random_string


class OssFile:
    _base_path: str = ""

    def get_real_path(
        self,
        filepath: str,
        base_path: str | None = None,
    ) -> str:
        prefix = base_path if base_path else ""
        if not filepath.startswith("/"):
            prefix += "/"
        return f"{prefix}{filepath}"

    @staticmethod
    def get_random_filename(filename: str) -> str:
        random_str = list("pity")
        random.shuffle(random_str)
        return f"{time.time_ns()}_{generate_random_string(4)}_{filename}"

    def create_file(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str]:
        """内容上传创建文件"""
        raise NotImplementedError

    def create_file_from_local(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str]:
        """上传本地文件"""
        raise NotImplementedError

    def exists(
        self,
        *args,
        **kwargs,
    ) -> bool:
        raise NotImplementedError

    def delete_file(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str]:
        """删除文件"""
        raise NotImplementedError

    def download_file(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str]:
        raise NotImplementedError

    def get_file_object(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, bytes | str]:
        raise NotImplementedError

    def get_download_url(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str] | tuple[bool, tuple[str, dict] | str]:
        """获取下载url"""
        raise NotImplementedError

    def get_perm_download_url(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str] | tuple[bool, tuple[str, dict] | str]:
        raise NotImplementedError

    def get_upload_url(
        self,
        *args,
        **kwargs,
    ) -> tuple[bool, str] | tuple[bool, tuple[str, dict] | str]:
        """获取上传url"""
        raise NotImplementedError

    def get_full_path(
        self,
        filepath: str,
        expires: int | None = None,
    ) -> tuple[bool, str]:
        raise NotImplementedError
