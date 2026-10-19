"""Lector experimental, estricto y de solo lectura para índices VFP CDX."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import struct
from threading import Lock
from typing import BinaryIO, Dict, List, Optional, Tuple


class CdxReadError(RuntimeError):
    pass


@dataclass(frozen=True)
class CdxTag:
    name: str
    header_offset: int
    root_offset: int
    key_length: int
    expression: str
    descending: bool


@dataclass(frozen=True)
class _Page:
    leaf: bool
    left: int
    right: int
    entries: List[Tuple[bytes, int, Optional[int]]]


class CdxReader:
    """Abre CDX con ``rb``; nunca reindexa ni escribe el archivo."""

    PAGE_SIZE = 512
    _cache = {}
    _cache_lock = Lock()

    def __init__(self, path: Path):
        self.path = Path(path)
        self._initial_stat = self._signature()
        self._data = self._cached_bytes()
        self.tags = self._read_tags()

    def _cached_bytes(self) -> bytes:
        key = str(self.path.resolve())
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached and cached[0] == self._initial_stat:
                return cached[1]
            # Una lectura secuencial evita decenas de seeks remotos sobre SMB.
            data = self.path.read_bytes()
            if self._signature() != self._initial_stat:
                raise CdxReadError(f"El CDX cambió mientras se cargaba: {self.path}")
            self._cache[key] = (self._initial_stat, data)
            return data

    def _open(self) -> BytesIO:
        return BytesIO(self._data)

    def _signature(self):
        stat = self.path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns

    def assert_unchanged(self):
        if self._signature() != self._initial_stat:
            raise CdxReadError(f"El CDX cambió durante la lectura: {self.path}")

    @staticmethod
    def _u16(data: bytes) -> int:
        return int.from_bytes(data, 'little')

    @staticmethod
    def _u32(data: bytes) -> int:
        return int.from_bytes(data, 'little')

    @staticmethod
    def _i32(data: bytes) -> int:
        return int.from_bytes(data, 'little', signed=True)

    def _read_exact(self, stream: BinaryIO, offset: int, size: int) -> bytes:
        stream.seek(offset)
        data = stream.read(size)
        if len(data) != size:
            raise CdxReadError(
                f"Lectura CDX incompleta offset={offset} esperado={size}"
            )
        return data

    def _read_tags(self) -> Dict[str, CdxTag]:
        with self._open() as stream:
            header = self._read_exact(stream, 0, self.PAGE_SIZE)
            root = self._u32(header[0:4])
            key_length = self._u16(header[12:14])
            master = self._read_page(stream, root, key_length, character=False)
            if not master.leaf:
                raise CdxReadError("El índice maestro CDX no cabe en una hoja")

            tags = {}
            for raw_name, tag_header_offset, _ in master.entries:
                raw = self._read_exact(stream, tag_header_offset, 1024)
                expression_length = self._u16(raw[504:506])
                expression = raw[
                    512:512 + max(0, expression_length - 1)
                ].decode('latin-1', errors='replace').strip()
                name = raw_name.rstrip(b'\0 ').decode('ascii', errors='replace')
                tags[name.upper()] = CdxTag(
                    name=name,
                    header_offset=tag_header_offset,
                    root_offset=self._u32(raw[0:4]),
                    key_length=self._u16(raw[12:14]),
                    expression=expression,
                    descending=bool(self._u16(raw[502:504])),
                )
        self.assert_unchanged()
        return tags

    def find_tag(self, *, name: Optional[str] = None,
                 expression: Optional[str] = None) -> Optional[CdxTag]:
        if name:
            return self.tags.get(name.upper())
        wanted = (expression or '').strip().lower()
        return next(
            (tag for tag in self.tags.values()
             if tag.expression.strip().lower() == wanted),
            None,
        )

    def seek_character(self, tag: CdxTag, value: str) -> List[int]:
        if tag.descending:
            raise CdxReadError("Los tags descendentes aún no están soportados")
        target = value.encode('latin-1', errors='strict')
        if len(target) > tag.key_length:
            return []
        target = target.ljust(tag.key_length, b' ')

        with self._open() as stream:
            page = self._descend(stream, tag, target)
            # Retroceder si los duplicados empezaron en la hoja anterior.
            while page.left >= 0 and page.entries and page.entries[0][0] == target:
                previous = self._read_page(
                    stream, page.left, tag.key_length, character=True
                )
                if not previous.entries or previous.entries[-1][0] != target:
                    break
                page = previous

            result = []
            while True:
                for key, record_number, _ in page.entries:
                    if key == target:
                        result.append(record_number)
                    elif key > target and result:
                        self.assert_unchanged()
                        return result
                if page.right < 0 or not page.entries or page.entries[-1][0] > target:
                    break
                page = self._read_page(
                    stream, page.right, tag.key_length, character=True
                )
        self.assert_unchanged()
        return result

    def _descend(self, stream: BinaryIO, tag: CdxTag, target: bytes) -> _Page:
        offset = tag.root_offset
        visited = set()
        while True:
            if offset in visited:
                raise CdxReadError("Ciclo detectado en el árbol CDX")
            visited.add(offset)
            page = self._read_page(
                stream, offset, tag.key_length, character=True
            )
            if page.leaf:
                return page
            if not page.entries:
                raise CdxReadError("Nodo interior CDX vacío")
            selected = page.entries[-1]
            for entry in page.entries:
                if entry[0] >= target:
                    selected = entry
                    break
            if selected[2] is None:
                raise CdxReadError("Nodo interior sin puntero hijo")
            offset = selected[2]

    def _read_page(self, stream: BinaryIO, offset: int, key_length: int,
                   character: bool) -> _Page:
        raw = self._read_exact(stream, offset, self.PAGE_SIZE)
        attributes, count = struct.unpack('<HH', raw[:4])
        left, right = struct.unpack('<ii', raw[4:12])
        leaf = bool(attributes & 2)
        if not leaf:
            entries = []
            width = key_length + 8
            for index in range(count):
                start = 12 + index * width
                end = start + width
                if end > self.PAGE_SIZE:
                    raise CdxReadError("Nodo interior CDX excede la página")
                key = raw[start:start + key_length]
                record_number = int.from_bytes(
                    raw[start + key_length:start + key_length + 4], 'big'
                )
                child = int.from_bytes(raw[end - 4:end], 'big')
                entries.append((key, record_number, child))
            return _Page(False, left, right, entries)

        record_mask = self._u32(raw[14:18])
        duplicate_mask, trailing_mask = raw[18], raw[19]
        duplicate_bits, trailing_bits, info_width = raw[21], raw[22], raw[23]
        if not info_width or info_width * count > 488:
            raise CdxReadError("Metadatos de hoja CDX inválidos")
        data = raw[24:]
        source = 488
        previous = b''
        entries = []
        shift = 16 - trailing_bits - duplicate_bits
        trail_byte = b' ' if character else b'\0'
        for index in range(count):
            pos = index * info_width
            encoded = data[pos + info_width - 2] | (
                data[pos + info_width - 1] << 8
            )
            packed = encoded >> shift
            duplicate = 0 if index == 0 else packed & duplicate_mask
            trailing = (packed >> duplicate_bits) & trailing_mask
            fresh = key_length - duplicate - trailing
            if fresh < 0:
                raise CdxReadError("Compresión de clave CDX inválida")
            source -= fresh
            key = previous[:duplicate] + data[source:source + fresh]
            key += trail_byte * trailing
            record_number = self._u32(data[pos:pos + 4]) & record_mask
            entries.append((key, record_number, None))
            previous = key
        return _Page(True, left, right, entries)
