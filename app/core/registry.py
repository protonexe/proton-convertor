from typing import Dict, List, Set, Optional

class ConverterRegistry:
    """
    Registry that tracks all available converters in the system.
    Supports specific format pairs, families, and a global fallback.
    """
    def __init__(self):
        self._converters: Dict[str, List] = {}
        self._families: Dict[str, Set[str]] = {}
        self._fallback_converter = None

    def set_fallback(self, converter):
        """Sets the converter to use when no other path is found."""
        self._fallback_converter = converter

    def register_family(self, family_name: str, extensions: List[str]):
        """Groups extensions into a family."""
        self._families[family_name] = set(ext.lower() for ext in extensions)

    def register(self, converter):
        """Registers a converter instance."""
        src = converter.source_format.lower()
        if src not in self._converters:
            self._converters[src] = []
        self._converters[src].append(converter)

    def get_converters_for_format(self, source_format: str) -> List:
        """Returns all converters that can handle the given source format."""
        src = source_format.lower()
        results = self._converters.get(src, []).copy()
        
        for family, extensions in self._families.items():
            if src in extensions:
                results.extend(self._converters.get(family, []))
                
        if not results and self._fallback_converter:
            results.append(self._fallback_converter)
            
        return results

    def get_all_formats(self) -> List[str]:
        """Returns a list of all unique formats supported by the registry."""
        formats = set()
        for src, converters in self._converters.items():
            if src not in self._families:
                formats.add(src)
            for c in converters:
                formats.add(c.target_format.lower())
        for family, extensions in self._families.items():
            formats.update(extensions)
        return sorted(list(formats))
