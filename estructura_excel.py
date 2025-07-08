import pandas as pd

# Leer el Excel fuente
archivo_entrada = 'Transponer archivo para SQL.xlsx'
archivo_salida = 'excel_transformado.xlsx'

# Cargar el archivo Excel fuente
df = pd.read_excel(archivo_entrada)

# Extraer año y mes de la columna fechareg
df['fechareg'] = pd.to_datetime(df['fechareg'], format='%m/%d/%y')
df['anio'] = df['fechareg'].dt.year
df['mes'] = df['fechareg'].dt.month

# Calcular idetareo basado en edad (asumiendo tipoedad=1 significa años)
# Categorías: 1: 0-11 años, 2: 12-17 años, 3: 18-29 años, 4: 30+ años
def calcular_idetareo(fila):
    edad = fila['edad']
    if edad <= 11:
        return 1
    elif 12 <= edad <= 17:
        return 2
    elif 18 <= edad <= 29:
        return 3
    else:
        return 4

df['idetareo'] = df.apply(calcular_idetareo, axis=1)

# Transformar las columnas de diagnósticos (coddiag1 a coddiag4) en una sola columna 'diag'
df_melted = pd.melt(
    df,
    id_vars=['anio', 'mes', 'numhc', 'doc_iden', 'etnia', 'sexo', 'edad', 'tipoedad', 'idetareo', 
             'ups', 'totalest', 'nomb', 'apell', 'ubigeo', 'condicion'],
    value_vars=['coddiag1', 'coddiag2', 'coddiag3', 'coddiag4'],
    var_name='tipo_diag',
    value_name='diag'
)

# Eliminar filas donde diag esté vacío o sea NaN
df_melted = df_melted[df_melted['diag'].notna() & (df_melted['diag'] != '')]

# Crear la columna numdiag basada en el tipo de diagnóstico
df_melted['numdiag'] = df_melted['tipo_diag'].map({
    'coddiag1': 1,
    'coddiag2': 2,
    'coddiag3': 3,
    'coddiag4': 4
})

# Seleccionar y ordenar las columnas para el formato final
columnas_salida = [
    'anio', 'mes', 'numhc', 'doc_iden', 'etnia', 'sexo', 'edad', 'tipoedad', 'idetareo',
    'ups', 'diag', 'numdiag', 'totalest', 'nomb', 'apell', 'ubigeo', 'condicion'
]
df_final = df_melted[columnas_salida]

# Ordenar por numhc y numdiag para consistencia
df_final = df_final.sort_values(by=['numhc', 'numdiag'])

# Guardar el resultado en un nuevo Excel
df_final.to_excel(archivo_salida, index=False)

print(f"Conversión completada. El archivo se guardó como {archivo_salida}")