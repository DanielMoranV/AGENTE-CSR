"""
FoxPro DBF Reader - Parser robusto que lee más allá del marcador EOF.

Este parser es más robusto que dbfread porque:
1. Calcula registros reales por tamaño de archivo (no confía en el header)
2. Ignora el marcador EOF (0x1A) y continúa leyendo
3. Soporta campos Memo (.FPT y .DBT)
4. Maneja registros borrados correctamente
"""

import struct
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Iterator
from pathlib import Path

from loguru import logger


class DbfHeader:
    def __init__(self):
        self.version: int = 0
        self.last_update: datetime = None
        self.record_count: int = 0
        self.header_length: int = 0
        self.record_length: int = 0


class DbfField:
    def __init__(self):
        self.name: str = ""
        self.type: str = ""
        self.length: int = 0
        self.decimal_count: int = 0
        self.offset: int = 0


class DbfRecord:
    def __init__(self, is_deleted: bool, values: Dict[str, Any]):
        self.is_deleted = is_deleted
        self.values = values
    
    def get_value(self, field_name: str, default=None):
        """Obtiene el valor de un campo"""
        return self.values.get(field_name.upper(), default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el registro a diccionario"""
        result = dict(self.values)
        result['_is_deleted'] = self.is_deleted
        return result


class MemoFile:
    def __init__(self, stream, block_size: int, is_foxpro: bool, encoding: str):
        self.stream = stream
        self.block_size = block_size
        self.is_foxpro = is_foxpro
        self.encoding = encoding


class FoxProDbfReader:
    DELETED_FLAG = 0x2A  # '*'
    ACTIVE_FLAG = 0x20   # ' '
    EOF_MARKER = 0x1A
    
    def __init__(self, dbf_path: str, encoding: str = 'cp1252'):
        """
        Inicializa el lector de DBF
        
        Args:
            dbf_path: Ruta al archivo DBF
            encoding: Codificación del archivo (default: cp1252/latin1)
        """
        self.dbf_path = dbf_path
        self.encoding = encoding
        self._stream = open(dbf_path, 'rb')
        self._header: DbfHeader = None
        self._fields: List[DbfField] = []
        self._memo_files: Dict[str, MemoFile] = {}
        
        self._leer_estructura()
    
    def _leer_estructura(self):
        """Lee la estructura del archivo DBF"""
        # Leer header
        self._header = DbfHeader()
        self._header.version = struct.unpack('B', self._stream.read(1))[0]
        
        year, month, day = struct.unpack('BBB', self._stream.read(3))
        self._header.last_update = datetime(1900 + year, month, day)
        
        self._header.record_count = struct.unpack('<I', self._stream.read(4))[0]
        self._header.header_length = struct.unpack('<H', self._stream.read(2))[0]
        self._header.record_length = struct.unpack('<H', self._stream.read(2))[0]
        
        self._stream.read(20)  # Bytes reservados
        
        # Leer campos
        offset = 1  # Primer byte es delete flag
        
        while True:
            # Peek para verificar 0x0D
            pos = self._stream.tell()
            next_byte = self._stream.read(1)
            
            if not next_byte or next_byte[0] == 0x0D:
                break
            
            # Retroceder para leer el campo completo
            self._stream.seek(pos)
            
            field = DbfField()
            
            # Nombre del campo (11 bytes)
            name_buffer = self._stream.read(11)
            field.name = name_buffer.decode(self.encoding).rstrip('\x00').upper()
            
            # Tipo de campo
            field.type = chr(struct.unpack('B', self._stream.read(1))[0])
            
            self._stream.read(4)  # Dirección en memoria (ignorar)
            
            field.length = struct.unpack('B', self._stream.read(1))[0]
            field.decimal_count = struct.unpack('B', self._stream.read(1))[0]
            field.offset = offset
            
            offset += field.length
            
            self._stream.read(14)  # Bytes reservados
            
            self._fields.append(field)
            
            # Si es campo memo, abrir archivo memo
            if field.type == 'M':
                self._abrir_archivo_memo()
        
        # Leer el 0x0D si no lo hemos leído ya
        if next_byte and next_byte[0] == 0x0D:
            pass  # Ya lo leímos
        else:
            self._stream.read(1)
    
    def _abrir_archivo_memo(self):
        """Abre el archivo memo (.FPT o .DBT)"""
        if "MEMO" in self._memo_files:
            return
        
        # Intentar .FPT (FoxPro) primero, luego .DBT (dBase)
        extensiones = ['.fpt', '.FPT', '.dbt', '.DBT']
        
        for ext in extensiones:
            memo_path = Path(self.dbf_path).with_suffix(ext)
            
            if memo_path.exists():
                memo_stream = open(str(memo_path), 'rb')
                
                # Leer header del memo
                memo_stream.read(4)  # Next block
                memo_stream.read(2)  # Unused
                block_size_bytes = memo_stream.read(2)
                block_size = struct.unpack('>H', block_size_bytes)[0]
                
                if block_size == 0:
                    block_size = 64 if ext.lower() == '.fpt' else 512
                
                is_foxpro = ext.lower() == '.fpt'
                
                self._memo_files["MEMO"] = MemoFile(
                    memo_stream,
                    block_size,
                    is_foxpro,
                    self.encoding
                )
                
                logger.info(f"✓ Archivo memo detectado: {memo_path.name} (BlockSize: {block_size})")
                break
    
    def read_all_records(self, load_deleted: bool = True) -> Iterator[DbfRecord]:
        """
        Lee todos los registros del archivo DBF, ignorando el EOF marker
        
        Args:
            load_deleted: Si True, incluye registros borrados
            
        Yields:
            DbfRecord: Cada registro del archivo
        """
        # CLAVE: Calcular registros reales por tamaño de archivo
        # NO confiar en el RecordCount del header
        self._stream.seek(self._header.header_length)
        
        bytes_disponibles = os.path.getsize(self.dbf_path) - self._header.header_length
        registros_reales = bytes_disponibles // self._header.record_length
        
        logger.debug(f"Header indica: {self._header.record_count} registros")
        logger.debug(f"Calculados por tamaño: {registros_reales} registros")
        
        if registros_reales > self._header.record_count:
            logger.warning(f"Se encontraron {registros_reales - self._header.record_count} "
                  f"registros adicionales después del EOF marker")
        
        registros_leidos = 0
        file_size = os.path.getsize(self.dbf_path)
        
        # Leer TODOS los registros hasta el final real del archivo
        while self._stream.tell() < file_size - 1:
            delete_flag_bytes = self._stream.read(1)
            
            if not delete_flag_bytes:
                break
            
            delete_flag = delete_flag_bytes[0]
            
            # Si encontramos EOF marker, IGNORARLO y continuar
            if delete_flag == self.EOF_MARKER:
                posicion_actual = self._stream.tell()
                
                # Si estamos al final del archivo, terminar
                if posicion_actual >= file_size:
                    break
                
                # Si quedan bytes suficientes para otro registro, continuar
                if file_size - posicion_actual + 1 >= self._header.record_length:
                    logger.debug(f"EOF marker (0x1A) encontrado en posición {posicion_actual - 1}, "
                          f"pero hay más datos. Continuando...")
                    
                    # Retroceder y leer como registro normal
                    self._stream.seek(posicion_actual - 1)
                    
                    # Leer el registro completo para obtener el delete flag real
                    record_bytes = self._stream.read(self._header.record_length)
                    delete_flag = record_bytes[0]
                    
                    # Retroceder para procesar el registro completo
                    self._stream.seek(posicion_actual - 1)
                    delete_flag_bytes = self._stream.read(1)
                    delete_flag = delete_flag_bytes[0]
                else:
                    break  # EOF real
            
            is_deleted = delete_flag == self.DELETED_FLAG
            
            # Saltar si es borrado y no queremos borrados
            if is_deleted and not load_deleted:
                # Leer y descartar el resto del registro
                self._stream.read(self._header.record_length - 1)
                continue
            
            values = {}
            
            # Leer cada campo
            for field in self._fields:
                buffer = self._stream.read(field.length)
                
                # Parsear según tipo
                try:
                    if field.type == 'C':  # Character
                        raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                        value = raw_value
                    elif field.type in ('N', 'F'):  # Numeric/Float
                        raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                        value = self._parse_numeric(raw_value, field.decimal_count)
                    elif field.type == 'L':  # Logical
                        raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                        value = self._parse_logical(raw_value)
                    elif field.type == 'D':  # Date
                        raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                        value = self._parse_date(raw_value)
                    elif field.type == 'T':  # DateTime
                        value = self._parse_datetime(buffer)
                    elif field.type == 'M':  # Memo
                        # IMPORTANTE: Pasar el buffer RAW, no decodificado
                        value = self._leer_campo_memo(buffer)
                    elif field.type == 'I':  # Integer
                        value = struct.unpack('<i', buffer)[0] if len(buffer) == 4 else None
                    elif field.type == 'Y':  # Currency
                        value = struct.unpack('<q', buffer)[0] / 10000.0 if len(buffer) == 8 else None
                    else:
                        raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                        value = raw_value
                except Exception as e:
                    logger.debug(f"Error parseando campo {field.name}: {e}")
                    value = None
                
                values[field.name] = value
            
            registros_leidos += 1
            yield DbfRecord(is_deleted, values)
        
        logger.debug(f"Total de registros leídos: {registros_leidos}")
    
    def read_filtered_records(
        self,
        filter_field: str,
        filter_values: set,
        load_deleted: bool = False
    ) -> Iterator[DbfRecord]:
        """
        Lee registros filtrados por un campo específico (OPTIMIZADO).
        Evita parsear registros completos que no coinciden con el filtro.
        
        Args:
            filter_field: Nombre del campo para filtrar (ej: 'NUM_DOC', 'ID_PAC')
            filter_values: Set de valores a buscar (strings normalizados)
            load_deleted: Si True, incluye registros borrados
            
        Yields:
            DbfRecord: Cada registro que coincide con el filtro
        """
        # Encontrar el campo de filtro y su offset
        filter_field_def = None
        filter_offset = 0
        current_offset = 0
        
        for field in self._fields:
            if field.name.upper() == filter_field.upper():
                filter_field_def = field
                filter_offset = current_offset
                break
            current_offset += field.length
        
        if not filter_field_def:
            logger.warning(f"[FILTERED_READ] Campo {filter_field} no encontrado")
            return
        
        logger.info(f"[FILTERED_READ] Filtrando por {filter_field} (offset={filter_offset}, type={filter_field_def.type})")
        
        # Posicionarse al inicio de los datos
        self._stream.seek(self._header.header_length)
        
        file_size = os.path.getsize(self.dbf_path)
        record_data_length = self._header.record_length - 1  # Sin delete flag
        matches_found = 0
        records_scanned = 0
        
        # Leer registros hasta el final del archivo
        while self._stream.tell() < file_size - 1:
            delete_flag_bytes = self._stream.read(1)
            
            if not delete_flag_bytes:
                break
            
            delete_flag = delete_flag_bytes[0]
            
            # Manejar EOF marker
            if delete_flag == self.EOF_MARKER:
                posicion_actual = self._stream.tell()
                
                if posicion_actual >= file_size:
                    break
                
                if file_size - posicion_actual + 1 >= self._header.record_length:
                    # Continuar leyendo después del EOF
                    self._stream.seek(posicion_actual - 1)
                    delete_flag_bytes = self._stream.read(1)
                    delete_flag = delete_flag_bytes[0]
                else:
                    break
            
            is_deleted = delete_flag == self.DELETED_FLAG
            
            # Saltar si es borrado y no queremos borrados
            if is_deleted and not load_deleted:
                self._stream.read(record_data_length)
                continue
            
            # Leer el registro completo en buffer
            record_buffer = self._stream.read(record_data_length)
            
            if len(record_buffer) < record_data_length:
                break
            
            records_scanned += 1
            
            # OPTIMIZACIÓN: Extraer solo el campo de filtro primero
            filter_field_buffer = record_buffer[filter_offset:filter_offset + filter_field_def.length]
            
            try:
                # Parsear el campo de filtro
                if filter_field_def.type == 'C':  # Character
                    filter_value = filter_field_buffer.decode(self.encoding, errors='ignore').strip()
                elif filter_field_def.type in ('N', 'F'):  # Numeric
                    raw = filter_field_buffer.decode(self.encoding, errors='ignore').strip()
                    parsed = self._parse_numeric(raw, filter_field_def.decimal_count)
                    filter_value = str(parsed).strip() if parsed is not None else ""
                elif filter_field_def.type == 'I':  # Integer
                    parsed = struct.unpack('<i', filter_field_buffer)[0] if len(filter_field_buffer) == 4 else None
                    filter_value = str(parsed).strip() if parsed is not None else ""
                else:
                    filter_value = filter_field_buffer.decode(self.encoding, errors='ignore').strip()
                
                # Verificar si coincide con el filtro
                if filter_value not in filter_values:
                    continue  # NO MATCH - saltar sin parsear el resto
                
                # MATCH! - Parsear el registro completo
                matches_found += 1
                values = {}
                offset = 0
                
                for field in self._fields:
                    buffer = record_buffer[offset:offset + field.length]
                    offset += field.length
                    
                    try:
                        if field.type == 'C':  # Character
                            value = buffer.decode(self.encoding, errors='ignore').strip()
                        elif field.type in ('N', 'F'):  # Numeric/Float
                            raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                            value = self._parse_numeric(raw_value, field.decimal_count)
                        elif field.type == 'L':  # Logical
                            raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                            value = self._parse_logical(raw_value)
                        elif field.type == 'D':  # Date
                            raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                            value = self._parse_date(raw_value)
                        elif field.type == 'T':  # DateTime
                            value = self._parse_datetime(buffer)
                        elif field.type == 'M':  # Memo
                            value = self._leer_campo_memo(buffer)
                        elif field.type == 'I':  # Integer
                            value = struct.unpack('<i', buffer)[0] if len(buffer) == 4 else None
                        elif field.type == 'Y':  # Currency
                            value = struct.unpack('<q', buffer)[0] / 10000.0 if len(buffer) == 8 else None
                        else:
                            value = buffer.decode(self.encoding, errors='ignore').strip()
                    except Exception as e:
                        logger.debug(f"Error parseando campo {field.name}: {e}")
                        value = None
                    
                    values[field.name] = value
                
                yield DbfRecord(is_deleted, values)
                
            except Exception as e:
                logger.debug(f"Error filtrando registro: {e}")
                continue
        
        logger.success(f"[FILTERED_READ] ✓ Found {matches_found:,} matches (scanned {records_scanned:,} records)")

    def _find_field(self, field_name: str):
        """
        Localiza un campo por nombre y devuelve (definicion, offset) dentro del
        buffer de registro (sin el delete flag). Devuelve (None, 0) si no existe.
        """
        offset = 0
        for field in self._fields:
            if field.name.upper() == field_name.upper():
                return field, offset
            offset += field.length
        return None, 0

    def _parse_field(self, field, buffer: bytes) -> Any:
        """
        Parsea un campo individual segun su tipo. Centraliza la conversion que
        antes estaba duplicada en cada lector; los campos memo se resuelven aqui
        contra el .fpt, asi que este parseo no funciona sin el reader abierto.
        """
        try:
            if field.type == 'C':  # Character
                return buffer.decode(self.encoding, errors='ignore').strip()
            elif field.type in ('N', 'F'):  # Numeric/Float
                raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                return self._parse_numeric(raw_value, field.decimal_count)
            elif field.type == 'L':  # Logical
                raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                return self._parse_logical(raw_value)
            elif field.type == 'D':  # Date
                raw_value = buffer.decode(self.encoding, errors='ignore').strip()
                return self._parse_date(raw_value)
            elif field.type == 'T':  # DateTime
                return self._parse_datetime(buffer)
            elif field.type == 'M':  # Memo
                return self._leer_campo_memo(buffer)
            elif field.type == 'I':  # Integer
                return struct.unpack('<i', buffer)[0] if len(buffer) == 4 else None
            elif field.type == 'Y':  # Currency
                return struct.unpack('<q', buffer)[0] / 10000.0 if len(buffer) == 8 else None
            else:
                return buffer.decode(self.encoding, errors='ignore').strip()
        except Exception as e:
            logger.debug(f"Error parseando campo {field.name}: {e}")
            return None

    def _parse_record(self, record_buffer: bytes) -> Dict[str, Any]:
        """Parsea el registro completo campo por campo."""
        values = {}
        offset = 0
        for field in self._fields:
            buffer = record_buffer[offset:offset + field.length]
            offset += field.length
            values[field.name] = self._parse_field(field, buffer)
        return values

    def read_date_range_records(
        self,
        date_field: str,
        start_date,
        end_date,
        load_deleted: bool = False
    ) -> Iterator[DbfRecord]:
        """
        Lee registros cuya fecha cae dentro de un rango (OPTIMIZADO).

        Comprueba la fecha directamente en el buffer del registro y solo parsea
        los campos del resto cuando hay coincidencia. Esto evita materializar la
        tabla entera: sc0011.DBF (294 MB) se recorre para quedarse con los pocos
        dias del rango, en vez de cargar todos los registros y filtrar despues.

        A diferencia de un escaneo por offsets crudo, aqui los campos memo se
        resuelven contra el .fpt, asi que sirve tambien para las tablas con memo
        (sc0011, sc0033, sc00f7, Sh0500f).

        Args:
            date_field: Campo de fecha a filtrar (ej: 'FEC_DOC')
            start_date: Fecha inicio (inclusive), date o datetime
            end_date: Fecha fin (inclusive), date o datetime
            load_deleted: Si True, incluye registros borrados

        Yields:
            DbfRecord: Cada registro dentro del rango
        """
        date_field_def, date_offset = self._find_field(date_field)

        if not date_field_def:
            logger.warning(f"[DATE_RANGE_READ] Campo {date_field} no encontrado")
            return

        # Normalizar los limites a 'date': _parse_date/_parse_datetime devuelven
        # datetime, y comparar datetime con date lanza TypeError.
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        logger.info(
            f"[DATE_RANGE_READ] Filtrando por {date_field} "
            f"(offset={date_offset}, type={date_field_def.type}) "
            f"| Rango: {start_date} -> {end_date}"
        )

        self._stream.seek(self._header.header_length)

        file_size = os.path.getsize(self.dbf_path)
        record_data_length = self._header.record_length - 1  # Sin delete flag
        matches_found = 0
        records_scanned = 0

        while self._stream.tell() < file_size - 1:
            delete_flag_bytes = self._stream.read(1)

            if not delete_flag_bytes:
                break

            delete_flag = delete_flag_bytes[0]

            # Manejar EOF marker: hay tablas con registros validos despues del 0x1A
            if delete_flag == self.EOF_MARKER:
                posicion_actual = self._stream.tell()

                if posicion_actual >= file_size:
                    break

                if file_size - posicion_actual + 1 >= self._header.record_length:
                    self._stream.seek(posicion_actual - 1)
                    delete_flag_bytes = self._stream.read(1)
                    delete_flag = delete_flag_bytes[0]
                else:
                    break

            is_deleted = delete_flag == self.DELETED_FLAG

            if is_deleted and not load_deleted:
                self._stream.read(record_data_length)
                continue

            record_buffer = self._stream.read(record_data_length)

            if len(record_buffer) < record_data_length:
                break

            records_scanned += 1

            # OPTIMIZACION: parsear solo el campo de fecha antes de decidir
            date_buffer = record_buffer[date_offset:date_offset + date_field_def.length]

            try:
                record_date = self._parse_field(date_field_def, date_buffer)

                if record_date is None:
                    continue

                if isinstance(record_date, datetime):
                    record_date = record_date.date()

                if not (start_date <= record_date <= end_date):
                    continue  # FUERA DE RANGO - saltar sin parsear el resto

                # DENTRO DEL RANGO - parsear el registro completo
                matches_found += 1
                yield DbfRecord(is_deleted, self._parse_record(record_buffer))

            except (ValueError, TypeError) as e:
                logger.debug(f"Error filtrando registro por fecha: {e}")
                continue

        logger.success(
            f"[DATE_RANGE_READ] ✓ Found {matches_found:,} records in range "
            f"(scanned {records_scanned:,})"
        )

    def _leer_campo_memo(self, buffer: bytes) -> Optional[str]:
        """Lee el contenido de un campo memo"""
        if "MEMO" not in self._memo_files:
            return None
        
        try:
            # El campo Memo contiene un número de bloque de 4 bytes (little-endian integer)
            if len(buffer) < 4:
                return None
            
            # Leer el número de bloque como entero de 4 bytes
            block_number = struct.unpack('<I', buffer[:4])[0]
            
            if block_number <= 0:
                return None
        except (ValueError, struct.error) as e:
            logger.debug(f"Error extrayendo block_number: {e}")
            return None
        
        memo_file = self._memo_files["MEMO"]
        
        try:
            position = block_number * memo_file.block_size
            
            if position >= os.path.getsize(memo_file.stream.name):
                return None
            
            memo_file.stream.seek(position)
            
            if memo_file.is_foxpro:
                # Formato FoxPro (.FPT)
                tipo = struct.unpack('>I', memo_file.stream.read(4))[0]
                length = struct.unpack('>I', memo_file.stream.read(4))[0]
                
                if length <= 0 or length > 10 * 1024 * 1024:  # Límite 10MB
                    return None
                
                buffer = memo_file.stream.read(length)
                return buffer.decode(memo_file.encoding, errors='ignore')
            else:
                # Formato dBase (.DBT)
                texto = []
                while True:
                    byte = memo_file.stream.read(1)
                    if not byte or byte[0] == 0x1A:
                        break
                    texto.append(chr(byte[0]))
                
                return ''.join(texto)
        except Exception as e:
            logger.debug(f"Error leyendo memo: {e}")
            return None
    
    def _parse_numeric(self, value: str, decimals: int) -> Optional[float]:
        """Parsea un valor numérico"""
        if not value or value.strip() == '':
            return None
        
        try:
            if decimals > 0:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return None
    
    def _parse_logical(self, value: str) -> Optional[bool]:
        """Parsea un valor lógico"""
        if not value or value.strip() == '':
            return None
        
        c = value.strip().upper()[0] if value.strip() else ''
        
        if c in ('T', 'Y'):
            return True
        elif c in ('F', 'N'):
            return False
        else:
            return None
    
    def _parse_date(self, value: str) -> Optional[datetime]:
        """Parsea una fecha (formato YYYYMMDD)"""
        if not value or len(value.strip()) != 8:
            return None
        
        try:
            return datetime.strptime(value.strip(), '%Y%m%d')
        except ValueError:
            return None
    
    def _parse_datetime(self, buffer: bytes) -> Optional[datetime]:
        """Parsea un DateTime de FoxPro (8 bytes)"""
        if len(buffer) < 8:
            return None
        
        try:
            julian_date = struct.unpack('<i', buffer[0:4])[0]
            milliseconds = struct.unpack('<i', buffer[4:8])[0]
            
            base_date = datetime(1970, 1, 1)
            return base_date + timedelta(days=julian_date - 2440588, milliseconds=milliseconds)
        except Exception:
            return None
    
    def get_fields(self) -> List[DbfField]:
        """Retorna la lista de campos"""
        return self._fields
    
    def get_header(self) -> DbfHeader:
        """Retorna el header del DBF"""
        return self._header
    
    def close(self):
        """Cierra todos los archivos abiertos"""
        if self._stream:
            self._stream.close()
        
        for memo in self._memo_files.values():
            if memo.stream:
                memo.stream.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __del__(self):
        self.close()
