class Config:
    SECRET_KEY = 'tu_clave_secreta'
    UPLOAD_FOLDER = 'uploads'
    TRANSFORMED_FOLDER = 'transformed'
    DATABASE = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=ELVER;DATABASE=Diagnosticos;Trusted_Connection=yes'
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}