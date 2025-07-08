import pandas as pd

def transform_excel(file_path):
    # Leer el archivo Excel
    df = pd.read_excel(file_path)

    # Extraer año y mes de la columna fecegr
    df['fecegr'] = pd.to_datetime(df['fecegr'], format='%m/%d/%y', errors='coerce')
    df['anio'] = df['fecegr'].dt.year
    df['mes'] = df['fecegr'].dt.month

    # Calcular idetareo basado en edad (asumiendo tipoedad=1 significa años)
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
        
    # ahora quiero que coloques algunas restricciones al momento de subir un archivo a la base de datos
    # por ejemplo: 
    # 1.- al momento de subir el primer archivo transformado a la base de datos quiero que me vote un mensaje que indique que se subio satisfactoriamente y la cantidad de registros 
    # 2.- al momento de subir el siguiente archivo quiero si se vuelve a subir el mismo archivo transformado quiero que vote una restriccion que indique que ya se subio ya que los registros son iguales, entonces no deberia de poder subirse
    # 3.- quiero q crees una interfaz en el html donde se pueda ver todos los registros subidos, x ejemplo egresos enero 2025, egresos febrero 2025, etc y haya la opcion de eliminar el registro que yo quiera por que talvez hay un error en los registros, entonces solo lo elimino y lo vuelvo a subir con los registros corregidos. 

    df['idetareo'] = df.apply(calcular_idetareo, axis=1)



    # Definir columnas para diagnósticos, morbilidades y códigos CPT
    diag_cols = ['coddiag1', 'coddiag2', 'coddiag3', 'coddiag4']
    morb_cols = ['cemorb1', 'cemorb2']
    cpt_cols = ['codcpt1', 'codcpt2', 'codcpt3', 'codcpt4']
    base_cols = ['anio', 'mes', 'numhc', 'doc_iden', 'etnia', 'sexo', 'edad', 'tipoedad', 'idetareo', 
                 'ups', 'totalest', 'nomb', 'apell', 'ubigeo', 'condicion']

    # Crear filas para cada diagnóstico, incluyendo cemorb y codcpt correspondientes
    rows = []
    for idx, row in df.iterrows():
        for i, diag_col in enumerate(diag_cols, 1):
            diag = row[diag_col]
            if pd.notna(diag) and diag != '':
                # Obtener cemorb correspondiente (si existe)
                cemorb = ''
                numcemorb = 0
                if i == 1 and len(morb_cols) > 0:
                    cemorb = row[morb_cols[0]] if pd.notna(row[morb_cols[0]]) and row[morb_cols[0]] != '' else ''
                    numcemorb = 1 if cemorb else 0
                elif i == 2 and len(morb_cols) > 1:
                    cemorb = row[morb_cols[1]] if pd.notna(row[morb_cols[1]]) and row[morb_cols[1]] != '' else ''
                    numcemorb = 2 if cemorb else 0

                # Obtener codcpt correspondiente (si existe)
                codcpt = row[cpt_cols[i-1]] if i-1 < len(cpt_cols) and pd.notna(row[cpt_cols[i-1]]) and row[cpt_cols[i-1]] != '' else ''
                numcodcpt = i if codcpt else 0

                # Crear fila con todos los datos
                new_row = {col: row[col] for col in base_cols}
                new_row.update({
                    'diag': diag,
                    'numdiag': i,
                    'cemorb': cemorb,
                    'numcemorb': numcemorb,
                    'codcpt': codcpt,
                    'numcodcpt': numcodcpt
                })
                rows.append(new_row)

    # Convertir las filas en un DataFrame
    df_final = pd.DataFrame(rows)

    # Reemplazar NaN en columnas específicas con valores vacíos o 0
    df_final['diag'] = df_final['diag'].fillna('')
    df_final['cemorb'] = df_final['cemorb'].fillna('')
    df_final['codcpt'] = df_final['codcpt'].fillna('')
    df_final['numdiag'] = df_final['numdiag'].fillna(0).astype(int)
    df_final['numcemorb'] = df_final['numcemorb'].fillna(0).astype(int)
    df_final['numcodcpt'] = df_final['numcodcpt'].fillna(0).astype(int)

    # Seleccionar y ordenar las columnas para el formato final
    columnas_salida = [
        'anio', 'mes', 'numhc', 'doc_iden', 'etnia', 'sexo', 'edad', 'tipoedad', 'idetareo',
        'ups', 'diag', 'numdiag', 'cemorb', 'numcemorb', 'codcpt', 'numcodcpt', 'totalest',
        'nomb', 'apell', 'ubigeo', 'condicion'
    ]
    df_final = df_final[columnas_salida]

    # Ordenar por nomb, apell, numdiag, numcemorb, numcodcpt
    df_final = df_final.sort_values(by=['nomb', 'apell', 'numdiag', 'numcemorb', 'numcodcpt'])

    return df_final