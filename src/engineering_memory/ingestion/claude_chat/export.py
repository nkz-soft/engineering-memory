"""Claude packaging policy over the existing local/ZIP transport, without extraction."""

from pathlib import Path

from engineering_memory.ingestion.chatgpt.export import Export as LocalExport
from engineering_memory.ingestion.source import SourceFormatError


class Export(LocalExport):
    def __init__(self, path: Path):
        super().__init__(path)
        if path.suffix.lower() != ".json" and self.names != ("conversations.json",):
            self.close()
            raise SourceFormatError("Claude exports require root conversations.json")

    @staticmethod
    def _open_archive(path):
        archive = LocalExport._open_archive(path)
        if archive.namelist().count("conversations.json") != 1:
            archive.close()
            raise SourceFormatError("Claude export requires one root conversations.json entry")
        return archive
