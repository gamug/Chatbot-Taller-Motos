import os

db_config = {
    "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
    "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
    "aws_region": os.environ["AWS_REGION"],
    "s3_bucket": os.environ["AWS_S3_BUCKET"],
    "s3_index": os.environ["AWS_S3_INDEX"],
    "embeddings_model": os.environ["AWS_EMBEEDINGS_MODEL"],
    "file_source": "manuales_motos",
    "embed_truncate": int(os.environ["EMBEDD_TRUCATE"]),
    "chunk_size": int(os.environ["CHUNK_SIZE"]),
    "chunk_overlap": int(os.environ["CHUNK_OVERLAP"])
}


pattern = '(19[7-9][0-9]|20[0-3][0-9])'
pattern = '\({0,1}'+pattern+f'(\-{pattern})'+'{0,1}\){0,1}'+' {0,1}([A-Z])*'
brand_regexes = [
    '(\({0,1}ABS\){0,1} ){0,1}MA{0,1}N{0,1}N{0,1}U{0,1}A{0,1}U{0,1}L( DE){0,1} TALLER( V){0,1}( ESPAÑOL){0,1}( COMPLEMENTARIO){0,1}( SUM{0,1}PLEMENTARIO){0,1}( APENDICE ARGENTINA){0,1}( APENDICE){0,1}( \(DESARME MOTOR\)){0,1}( \(INYECCION ELECTRONICA\)){0,1}( \(MOTOR\)){0,1}( \(BICICLETA ELECTRICA\)){0,1}',
    '(\(NEW\) ){0,1}MA{0,1}N{0,1}UA{0,1}L( DE){0,1} L{0,1}PARTES( SIN-ABS){0,1}', '(\({0,1}ABS\){0,1} ){0,1}MANUAL( DE){0,1} USUAS{0,1}RI{0,1}IO',
    'MANUAL( DE){0,1} USUAS{0,1}RI{0,1}IO(L){0,1}PARTES( SIN-ABS){0,1}', 'MANUAL( DE){0,1} USUAS{0,1}RI{0,1}IO',
    'MANUAL ENSAMBLE', 'MANUAL( COMUN){0,1}( DE){0,1} SERVI{0,1}CIO', 'PRESENTACION', 'COMPARATIVO MODELOS'
    'ESPAÑOL', 'DATOS TECNICOS', 'WIRING DIAGRAM', 'DTC LIST', 'DIAGNOSTIC CODES', 'SCOOTER WIRING DIAGRAM',
    'DIAGRAMA ELECTRICO DIGITAL', 'MANUAL SETUP', 'MANUAL DE GARANTIA Y MANTENIMIENTO', 'MANUAL PREPARACION',
    'MANUAL COMUN DE SERVICIO', 'MANUAL DESEMBALAJE E INSTALACION', 'DIAGRAMA ELECTRICO',
    'MANUAL PROCEDIMIENTO SISTEMA DE PRESION DE ACEITE', 'BOLETIN TECNICO INTERCAMBIO DE TABLEROS',
    '\(FRENOS\)', '\(CABEZA DE FUERZA\)', '\(CABEZA DE FUERZA - CLOCHE - ELECTRICIDAD\)', 'ABS MANUAL TECNICO',
    'COMPARATIVO MODELOS', 'MANUAL', 'ESPAÑOL', '( 20)$', pattern
]