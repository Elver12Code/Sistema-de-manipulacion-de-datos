from flask import Flask, request, render_template, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from transform import transform_excel
from config import Config
import os
from io import BytesIO
import pyodbc
import pandas as pd
import hashlib
import warnings
from datetime import datetime

# Suprimir advertencias
warnings.filterwarnings('ignore')

# Inicializar Flask
app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# Crear directorios si no existen
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['TRANSFORMED_FOLDER']):
    os.makedirs(app.config['TRANSFORMED_FOLDER'])

# Verificar extensión del archivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Función para crear o recrear la tabla egresos
def create_or_recreate_table(df, conn):
    cursor = conn.cursor()
    # Dropear la tabla si existe
    cursor.execute("IF OBJECT_ID('egresos', 'U') IS NOT NULL DROP TABLE egresos")
    print("Tabla egresos dropeada o no existía.")
    columns = []
    for column in df.columns:
        if column == 'totalest':
            sql_type = 'NVARCHAR(100)'
        else:
            sql_type = 'NVARCHAR(255)'  # Usar NVARCHAR para todas las columnas por consistencia
        columns.append(f"{column} {sql_type}")
    columns_str = ', '.join(columns)
    query = f"CREATE TABLE egresos ({columns_str})"
    cursor.execute(query)
    print(f"Tabla egresos creada con columnas: {columns_str}")
    conn.commit()

# Función para calcular hash del DataFrame
def calculate_dataframe_hash(df):
    return hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()

# Función para obtener el nombre del mes
def get_month_name(month_num):
    months = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    return months.get(int(month_num), 'Desconocido')

# Ruta principal para subir y transformar archivos
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    print("Entrando en upload_file, método:", request.method)
    if request.method == 'POST':
        print("Procesando solicitud POST")
        if 'file' not in request.files:
            print("No se encontró el campo 'file' en la solicitud")
            return render_template('index.html', error='No se seleccionó ningún archivo')
        file = request.files['file']
        print(f"Archivo recibido: {file.filename if file else 'Ningún archivo'}")
        if file.filename == '':
            print("No se seleccionó ningún archivo")
            return render_template('index.html', error='No se seleccionó ningún archivo')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Guardando archivo en: {file_path}")
            file.save(file_path)
            session.clear()
            session['uploaded_file'] = file_path
            print("Session después de subir:", session)
            return render_template('index.html', error=None, message='Archivo subido correctamente. Haz clic en Transformar.', uploaded_files=session.get('uploaded_files', {}))
        else:
            print(f"Extensión no permitida: {file.filename}")
            return render_template('index.html', error='Formato de archivo no permitido. Usa .xls, .xlsx o .csv.')
    return render_template('index.html', error=None, message=None, uploaded_files=session.get('uploaded_files', {}))

# Ruta para transformar el archivo
@app.route('/transform', methods=['POST'])
def transform():
    print("Entrando en transform")
    if 'uploaded_file' not in session:
        print("No hay archivo subido en la sesión")
        return render_template('index.html', error='No hay archivo subido. Por favor, sube un archivo nuevo para transformarlo.', uploaded_files=session.get('uploaded_files', {}))
    
    file_path = session['uploaded_file']
    print(f"Transformando archivo: {file_path}")
    if not os.path.exists(file_path):
        print(f"Error: El archivo {file_path} no existe")
        session.clear()
        return render_template('index.html', error='El archivo no se encuentra. Sube un nuevo archivo.', uploaded_files=session.get('uploaded_files', {}))
    
    try:
        df_final = transform_excel(file_path)

        output_format = request.form.get('output_format', 'csv')
        print(f"Formato seleccionado: {output_format}")
        if output_format == 'xlsx':
            transformed_filename = 'egresos_transformado.xlsx'
            df_final.to_excel(os.path.join(app.config['TRANSFORMED_FOLDER'], transformed_filename), index=False, engine='openpyxl')
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            transformed_filename = 'egresos_transformado.csv'
            df_final.to_csv(os.path.join(app.config['TRANSFORMED_FOLDER'], transformed_filename), index=False, encoding='utf-8')
            mime_type = 'text/csv'

        os.remove(file_path)
        print(f"Archivo transformado guardado en: {os.path.join(app.config['TRANSFORMED_FOLDER'], transformed_filename)}")
        print("Transformación completada, archivo temporal eliminado")

        session['transformed_filename'] = transformed_filename
        session['transformed_mime_type'] = mime_type
        print("Session después de transformar:", session)

        return render_template('index.html', message='Transformación completada. Haz clic en Descargar o Subir a DB.', uploaded_files=session.get('uploaded_files', {}))
    except Exception as e:
        print(f"Error en la transformación: {str(e)}")
        os.remove(file_path) if os.path.exists(file_path) else None
        return render_template('index.html', error=f'Error al procesar el archivo: {str(e)}', uploaded_files=session.get('uploaded_files', {}))

# Ruta para descargar el archivo
@app.route('/download', methods=['GET'])
def download():
    print("Entrando en download")
    print(f"Session in download: {session}")
    if 'transformed_filename' not in session or 'transformed_mime_type' not in session:
        print("No hay archivo transformado para descargar - Contenido de session:", session)
        return render_template('index.html', error='No hay archivo transformado para descargar', uploaded_files=session.get('uploaded_files', {}))
    
    transformed_filename = session['transformed_filename']
    mime_type = session['transformed_mime_type']
    file_path = os.path.join(app.config['TRANSFORMED_FOLDER'], transformed_filename)
    print(f"Descargando archivo: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Archivo no encontrado en: {file_path}")
        return render_template('index.html', error='Archivo transformado no encontrado', uploaded_files=session.get('uploaded_files', {}))

    response = send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=transformed_filename
    )
    print("Descarga completada. Por favor, elimina manualmente el archivo en 'transformed/' si no se elimina automáticamente.")
    session.clear()
    print("Sesión limpiada después de la descarga:", session)

    return response

# Nueva ruta para subir el archivo transformado a SQL Server
@app.route('/upload_to_db', methods=['POST'])
def upload_to_db():
    print("Entrando en upload_to_db")
    if 'transformed_filename' not in session or 'transformed_mime_type' not in session:
        print("No hay archivo transformado para subir a la base de datos - Contenido de session:", session)
        return render_template('index.html', error='No hay archivo transformado para subir a la base de datos', uploaded_files=session.get('uploaded_files', {}))
    
    transformed_filename = session['transformed_filename']
    file_path = os.path.join(app.config['TRANSFORMED_FOLDER'], transformed_filename)
    print(f"Subiendo archivo transformado: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Archivo no encontrado en: {file_path}")
        return render_template('index.html', error='Archivo transformado no encontrado', uploaded_files=session.get('uploaded_files', {}))
    
    try:
        # Leer el archivo transformado
        if transformed_filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif transformed_filename.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            return render_template('index.html', error='Formato de archivo transformado no soportado', uploaded_files=session.get('uploaded_files', {}))

        # Depuración
        print(f"Columnas de df: {df.columns.tolist()}")
        print(f"Tipos de datos de df: {df.dtypes}")
        print(f"Valores de totalest: {df['totalest'].head().to_string()}")
        print(f"Valores únicos de totalest: {df['totalest'].unique()}")
        print(f"Valores de la fila 0 como lista: {list(df.iloc[0])}")

        # Convertir todas las columnas a string para evitar problemas con nan
        for column in df.columns:
            df[column] = df[column].astype(str).replace('nan', '').fillna('')

        # Obtener mes y año representativos (primer registro como referencia)
        month = int(df['mes'].iloc[0]) if df['mes'].iloc[0].isdigit() else 1
        year = int(df['anio'].iloc[0]) if df['anio'].iloc[0].isdigit() else datetime.now().year
        session['last_month'] = str(month)
        session['last_year'] = str(year)

        # Verificar si los registros ya existen en la base de datos
        conn_str = app.config['DATABASE']
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        existing_records = 0
        for index, row in df.iterrows():
            query = "SELECT COUNT(*) FROM egresos WHERE anio = ? AND mes = ? AND numhc = ?"
            cursor.execute(query, (row['anio'], row['mes'], row['numhc']))
            if cursor.fetchone()[0] > 0:
                existing_records += 1
        conn.close()

        if existing_records == len(df):
            return render_template('index.html', error=f'El archivo {transformed_filename} contiene registros del mes de {get_month_name(month)} del año {year} que ya existen en la base de datos. No se realizará una nueva inserción.', uploaded_files=session.get('uploaded_files', {}))
        elif existing_records > 0:
            return render_template('index.html', error=f'El archivo {transformed_filename} contiene {existing_records} registros del mes de {get_month_name(month)} del año {year} que ya existen en la base de datos. Se insertarán los registros nuevos.', uploaded_files=session.get('uploaded_files', {}))

        # Conectar a SQL Server y recrear tabla si es necesario
        conn = pyodbc.connect(conn_str)
        create_or_recreate_table(df, conn)
        cursor = conn.cursor()
        cursor.fast_executemany = True
        row_count = 0
        for index, row in df.iterrows():
            print(f"Insertando fila {index}: {list(row)}")  # Depuración de cada fila
            columns = ', '.join(df.columns)
            placeholders = ', '.join(['?' for _ in df.columns])
            query = f"INSERT INTO egresos ({columns}) VALUES ({placeholders})"
            cursor.execute(query, list(row))
            row_count += 1
        conn.commit()
        conn.close()

        # Actualizar lista de archivos subidos
        uploaded_files = session.get('uploaded_files', {})
        current_hash = calculate_dataframe_hash(df)
        uploaded_files[transformed_filename] = current_hash
        session['uploaded_files'] = uploaded_files

        # Mensaje de éxito con mes y año
        message = f'Archivo {transformed_filename} subido satisfactoriamente a SQL Server. Se insertaron {row_count} registros del mes de {get_month_name(month)} del año {year}.'
        print(message)
        return render_template('index.html', message=message, uploaded_files=session.get('uploaded_files', {}))

    except pyodbc.Error as e:
        print(f"Error de conexión a SQL Server: {str(e)}")
        return render_template('index.html', error=f'Error al conectar a SQL Server: {str(e)}. Verifica la configuración en config.py.', uploaded_files=session.get('uploaded_files', {}))
    except Exception as e:
        print(f"Error al subir a la base de datos: {str(e)}")
        return render_template('index.html', error=f'Error al subir el archivo a la base de datos: {str(e)}', uploaded_files=session.get('uploaded_files', {}))

# Ruta para eliminar un registro subido
@app.route('/delete_uploaded', methods=['POST'])
def delete_uploaded():
    if 'uploaded_files' not in session or not session['uploaded_files']:
        return render_template('index.html', error='No hay registros subidos para eliminar.', uploaded_files=session.get('uploaded_files', {}))
    
    filename = request.form.get('filename')
    confirm_delete = request.form.get('confirm_delete') == 'yes'
    
    if filename and filename in session['uploaded_files']:
        file_path = os.path.join(app.config['TRANSFORMED_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if not confirm_delete:
            return render_template('index.html', message=f'La eliminación de {filename} requiere confirmación. Por favor, confirma en el modal.', uploaded_files=session.get('uploaded_files', {}))

        # Conectar a SQL Server y eliminar registros asociados
        conn_str = app.config['DATABASE']
        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            
            # Usar los valores de mes y año almacenados en la sesión
            month = session.get('last_month', '01')
            year = session.get('last_year', str(datetime.now().year))
            print(f"Intentando eliminar registros con anio={year} y mes={month}")

            # Eliminar registros basados en anio y mes
            query = "DELETE FROM egresos WHERE anio = ? AND mes = ?"
            rows_affected = cursor.execute(query, (year, month)).rowcount
            print(f"Filas eliminadas: {rows_affected}")
            conn.commit()
            conn.close()
            
            if rows_affected == 0:
                print("No se encontraron registros para eliminar con los criterios dados.")
        except pyodbc.Error as e:
            print(f"Error al eliminar registros de la base de datos: {str(e)}")
            conn.close()  # Asegurar cierre incluso con error
            return render_template('index.html', error=f'Error al eliminar registros de la base de datos: {str(e)}', uploaded_files=session.get('uploaded_files', {}))

        # Eliminar de la sesión
        del session['uploaded_files'][filename]
        if not session['uploaded_files']:
            session.pop('uploaded_files')
        
        return render_template('index.html', message=f'Registro {filename} y sus datos en la base de datos eliminados exitosamente. Filas afectadas: {rows_affected}.', uploaded_files=session.get('uploaded_files', {}))
    return render_template('index.html', error='Archivo no encontrado o no se pudo eliminar.', uploaded_files=session.get('uploaded_files', {}))

# Nueva ruta para el historial
@app.route('/history', methods=['GET'])
def history():
    print("Entrando en history")
    uploaded_files = session.get('uploaded_files', {})
    print(f"Historial de archivos: {uploaded_files}")
    if not uploaded_files:
        return render_template('index.html', error='No hay historial de registros subidos.', uploaded_files=uploaded_files)
    return render_template('index.html', message='Historial de registros subidos:', uploaded_files=uploaded_files)

if __name__ == '__main__':
    app.run(debug=True)