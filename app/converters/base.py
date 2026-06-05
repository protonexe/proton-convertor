from abc import ABC, abstractmethod
from pathlib import Path

class BaseConverter(ABC):
    """
    Abstract base class for all file converters.
    Each converter is responsible for converting a file from one specific
    format to another.
    """

    @property
    @abstractmethod
    def source_format(self) -> str:
        """The file extension (without dot) this converter reads from."""
        pass

    @property
    @abstractmethod
    def target_format(self) -> str:
        """The file extension (without dot) this converter writes to."""
        pass

    @abstractmethod
    async def convert(self, input_path: Path, output_path: Path) -> Path:
        """
        Performs the conversion from source_format to target_format.
        Returns the path to the converted file.
        """
        pass
