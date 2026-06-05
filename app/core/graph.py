from collections import deque
from pathlib import Path
import tempfile
import shutil
import os
from typing import List, Optional, Tuple
from app.core.registry_instance import registry
from app.converters.base import BaseConverter

class ConversionEngine:
    """
    Engine that manages the conversion process using a graph of converters.
    It finds the shortest path between formats and executes the pipeline.
    """

    def find_path(self, start_format: str, end_format: str) -> Optional[List[BaseConverter]]:
        """
        Uses Breadth-First Search (BFS) to find the shortest path of converters
        to get from start_format to end_format.
        """
        start = start_format.lower()
        end = end_format.lower()

        if start == end:
            return []

        queue = deque([(start, [])])
        visited = {start}

        while queue:
            current_format, path = queue.popleft()

            for converter in registry.get_converters_for_format(current_format):
                target = converter.target_format.lower()
                if target == end:
                    return path + [converter]
                if target not in visited:
                    visited.add(target)
                    queue.append((target, path + [converter]))

        return None

    async def convert(self, input_path: Path, target_format: str) -> Path:
        """
        Executes the conversion pipeline from the input file's format to the target format.
        Manages temporary files automatically.
        """
        start_format = input_path.suffix[1:].lower()
        path = self.find_path(start_format, target_format)

        if path is None:
            raise ValueError(f"No conversion path found from {start_format} to {target_format}")

        if not path:
            # Start and end formats are the same, just return a copy (or the original if acceptable)
            # For professionality, we create a copy with the correct extension.
            final_path = input_path.with_suffix(f".{target_format}")
            shutil.copy2(input_path, final_path)
            return final_path

        # Execution pipeline
        current_input = input_path
        temp_files = []

        try:
            for i, converter in enumerate(path):
                # Create a temporary file for intermediate steps
                # If it's the last step, we might want to use the final requested path, 
                # but here the 'convert' method is generic, so we use a temp file and 
                # the API layer will handle the final rename.
                fd, temp_path_str = tempfile.mkstemp(suffix=f".{converter.target_format}")
                os.close(fd)
                temp_path = Path(temp_path_str)
                temp_files.append(temp_path)

                await converter.convert(current_input, temp_path)
                current_input = temp_path

            return current_input
        except Exception as e:
            # Cleanup temp files on failure
            for f in temp_files:
                if f.exists():
                    f.unlink()
            raise e

engine = ConversionEngine()
