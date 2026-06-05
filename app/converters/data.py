import json
import csv
import yaml
import xmltodict
from pathlib import Path
from app.converters.base import BaseConverter
from app.core.registry_instance import registry

class DataFamilyConverter(BaseConverter):
    def __init__(self, target_fmt: str):
        self._target_fmt = target_fmt

    @property
    def source_format(self) -> str:
        return "data" # Registered as family

    @property
    def target_format(self) -> str:
        return self._target_fmt

    def _to_dict(self, input_path: Path):
        ext = input_path.suffix[1:].lower()
        with open(input_path, 'r', encoding='utf-8') as f:
            if ext == "json": return json.load(f)
            elif ext in ["yaml", "yml"]: return yaml.safe_load(f)
            elif ext == "xml": return xmltodict.parse(f.read())
            elif ext == "csv":
                return list(csv.DictReader(f))
        return {}

    def _from_dict(self, data, output_path: Path):
        target = self._target_fmt.lower()
        with open(output_path, 'w', encoding='utf-8') as f:
            if target == "json": json.dump(data, f, indent=2)
            elif target in ["yaml", "yml"]: yaml.dump(data, f)
            elif target == "xml": f.write(xmltodict.unparse({"root": data}, pretty=True))
            elif target == "csv":
                if data and isinstance(data, list) and isinstance(data[0], dict):
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader(); writer.writerows(data)
                else:
                    f.write(str(data))

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        data = self._to_dict(input_path)
        self._from_dict(data, output_path)
        return output_path

data_extensions = ["json", "csv", "yaml", "yml", "xml"]
registry.register_family("data", data_extensions)

for fmt in data_extensions:
    registry.register(DataFamilyConverter(fmt))
