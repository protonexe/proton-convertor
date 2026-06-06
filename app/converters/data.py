import json
import csv
import yaml
import xmltodict
import pandas as pd
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
        try:
            if ext == "json":
                with open(input_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif ext in ["yaml", "yml"]:
                with open(input_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            elif ext == "xml":
                with open(input_path, 'r', encoding='utf-8') as f:
                    return xmltodict.parse(f.read())
            elif ext == "csv":
                with open(input_path, 'r', encoding='utf-8') as f:
                    return list(csv.DictReader(f))
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(input_path)
                return df.to_dict(orient='records')
        except Exception as e:
            print(f"Error reading {ext} file: {e}")
        return {}

    def _from_dict(self, data, output_path: Path):
        target = self._target_fmt.lower()
        with open(output_path, 'w', encoding='utf-8') as f:
            if target == "json": json.dump(data, f, indent=2)
            elif target in ["yaml", "yml"]: yaml.dump(data, f)
            elif target == "xml": f.write(xmltodict.unparse({"root": data}, pretty=True))
            elif target == "csv":
                if isinstance(data, dict):
                    data = [data]
                elif not isinstance(data, list):
                    data = [{"value": str(data)}]
                
                if data and isinstance(data[0], dict):
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader(); writer.writerows(data)
                else:
                    f.write(str(data))

    async def convert(self, input_path: Path, output_path: Path) -> Path:
        data = self._to_dict(input_path)
        self._from_dict(data, output_path)
        return output_path

# Expanded data extensions to include Excel
data_extensions = ["json", "csv", "yaml", "yml", "xml", "xlsx", "xls"]
registry.register_family("data", data_extensions)

# Register target extensions including the 'txt' hub
target_extensions = data_extensions + ["txt", "md", "html"]
for fmt in target_extensions:
    registry.register(DataFamilyConverter(fmt))
