
import json
import hashlib
import threading

from pathlib import Path
from datetime import datetime, timezone

import config


class ArchiveDatabase:

    def __init__(self, database_path=None):

        self.database_path = Path(
            database_path or config.ARCHIVE_DATABASE
        ).resolve()

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._lock = threading.RLock()

        self.data = self._load()


    def _empty_database(self):

        return {
            "version": 1,
            "created_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "updated_at": None,
            "files": []
        }


    def _load(self):

        if not self.database_path.exists():
            return self._empty_database()

        try:

            with self.database_path.open(
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Invalid database format.")

            if not isinstance(data.get("files"), list):
                raise ValueError("Invalid files collection.")

            if data.get("version") != 1:
                raise ValueError("Unsupported database version.")

            return data

        except (json.JSONDecodeError, OSError, ValueError) as error:

            raise RuntimeError(
                f"Could not load archive database: {error}"
            ) from error


    def _save(self):

        import os
        import tempfile

        self.data["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        temporary_path = None

        try:

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.database_path.parent,
                suffix=".tmp",
                delete=False
            ) as file:

                temporary_path = Path(file.name)

                json.dump(
                    self.data,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

                file.flush()
                os.fsync(file.fileno())

            os.replace(
                temporary_path,
                self.database_path
            )

        except Exception:

            if temporary_path and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

            raise


    @staticmethod
    def calculate_hash(file_path):

        sha256 = hashlib.sha256()

        with open(file_path, "rb") as file:

            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b""
            ):

                sha256.update(chunk)

        return sha256.hexdigest()


    def find_by_hash(self, sha256):

        with self._lock:

            for record in self.data["files"]:

                if record.get("sha256") == sha256:
                    return record.copy()

        return None


    def remove_by_hash(self, sha256):

        """
        Remove stale metadata records for a file hash.
        """

        with self._lock:

            matching_records = [
                record
                for record in self.data["files"]
                if record.get("sha256") == sha256
            ]

            if not matching_records:
                return False

            for record in matching_records:
                self.data["files"].remove(record)

            try:

                self._save()

            except Exception:

                self.data["files"].extend(matching_records)
                raise

            return True


    def add_file(
        self,
        original_name,
        archived_path,
        category,
        sha256,
        size_bytes,
        extension
    ):

        if self.find_by_hash(sha256):
            raise ValueError(
                "This file already exists in the archive."
            )

        record = {
            "original_name": original_name,
            "archived_path": archived_path,
            "category": category,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "extension": extension,
            "archived_at": datetime.now(
                timezone.utc
            ).isoformat()
        }

        with self._lock:

            if self.find_by_hash(sha256):
                raise ValueError(
                    "Duplicate file detected."
                )

            self.data["files"].append(record)

            try:
                self._save()

            except Exception:

                self.data["files"].remove(record)
                raise

        return record.copy()


    def get_all_files(self):

        with self._lock:

            return [
                record.copy()
                for record in self.data["files"]
            ]


    def get_file_by_path(self, archived_path):

        with self._lock:

            for record in self.data["files"]:

                if record.get("archived_path") == archived_path:
                    return record.copy()

        return None


    def count_files(self):

        with self._lock:
            return len(self.data["files"])


    def get_statistics(self):

        with self._lock:

            statistics = {
                "total_files": 0,
                "total_size_bytes": 0,
                "categories": {}
            }

            for record in self.data["files"]:

                category = record.get(
                    "category",
                    "uncategorized"
                )

                statistics["total_files"] += 1

                statistics["total_size_bytes"] += record.get(
                    "size_bytes",
                    0
                )

                statistics["categories"][category] = (
                    statistics["categories"].get(category, 0) + 1
                )

            return statistics
