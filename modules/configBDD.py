import streamlit as st
import os
import glob
import pandas as pd
import sqlite3
import re

from modules.calculoGrupos import recalcula_distribucion_total

directorioBase = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_CONFIG_APP = os.path.join(directorioBase, '.app_config.txt')

def guardar_bd_activa(ruta_bd):
    try:
        with open(ARCHIVO_CONFIG_APP, 'w', encoding = 'utf-8') as f:
            if ruta_bd:
                f.write(ruta_bd)
            else:
                f.write('')
    except Exception:
        pass

def cargar_bd_activa():
    try:
        if os.path.exists(ARCHIVO_CONFIG_APP):
            with open(ARCHIVO_CONFIG_APP, 'r', encoding = 'utf-8') as f:
                ruta = f.read().strip()
                if ruta and os.path.exists(ruta):
                    return ruta
    except Exception:
        pass
    return None

def crea_bdd_excel(archivoSubido, nombreBd):
    try:
        excel = pd.ExcelFile(archivoSubido)
        
        hojasEsperadas = ['ASIGNATURAS', 'PotAsignaturas', 'PPTAGREGR']
        for hoja in hojasEsperadas:
            if hoja not in excel.sheet_names:
                raise ValueError(f'El archivo Excel no tiene el formato esperado. Falta la hoja: \'{hoja}\'.')

        dfAsignaturas = pd.read_excel(excel, sheet_name = 'ASIGNATURAS')
        dfMatriculas = pd.read_excel(excel, sheet_name = 'PotAsignaturas')
        dfPPT = pd.read_excel(excel, sheet_name = 'PPTAGREGR')

        columnasAsig = ['Cod.Centro', 'Desc.Centro', 'Cod.Dpto', 'Desc.Dpto', 'Cod.Plan', 'Desc.Plan', 
                         'Cod.Asignatura', 'Any academico', 'Curso', 'Cuatrimestre', 'Clase', 'Linea curricular', 
                         'Compartida', 'Titulaciones comparten', 'M Patron', 'S Patron', 'GA Patron', 'GL Patron', 
                         'GO Patron', 'GCA Patron', 'GCL Patron', 'TA Patron', 'TI Patron']
        for col in columnasAsig:
            if col not in dfAsignaturas.columns:
                raise ValueError(f'Formato incorrecto. Falta la columna \'{col}\' en la hoja \'ASIGNATURAS\'.')

        columnasMatri = ['Cod.Asignatura', 'Desc.Asignatura', 'Creditos', 'Any academico', 
                          'Mat.Cas.', 'Mat.Cas. SALIENTE DE UPV/EHU', 'Mat.Cas. DE OTRAS UNIVER', 
                          'Mat.Eus.', 'Mat.Eus. SALIENTE DE UPV/EHU', 'Mat.Eus. DE OTRAS UNIVER', 
                          'Mat.Otr.', 'Mat.Otr. SALIENTE DE UPV/EHU', 'Mat.Otr. DE OTRAS UNIVER']
        for col in columnasMatri:
            if col not in dfMatriculas.columns:
                raise ValueError(f'Formato incorrecto. Falta la columna \'{col}\' en la hoja \'PotAsignaturas\'.')

        if not nombreBd.endswith('.db'):
            nombreBd += '.db'
            
        rutaBd = os.path.join(directorioBase, nombreBd)
        conexion = sqlite3.connect(rutaBd)
        cursor = conexion.cursor()

        cursor.execute('PRAGMA foreign_keys = OFF;')
        cursor.executescript('''
        DROP VIEW IF EXISTS Totales_Creditos;
        DROP TABLE IF EXISTS Distribucion_Grupos;
        DROP TABLE IF EXISTS Calculo_Grupos;
        DROP TABLE IF EXISTS Agrupacion_Grado;
        DROP TABLE IF EXISTS Agrupacion;
        DROP TABLE IF EXISTS Matricula;
        DROP TABLE IF EXISTS Asignatura_Grado_Dpto;
        DROP TABLE IF EXISTS Asignatura;
        DROP TABLE IF EXISTS Grado;
        DROP TABLE IF EXISTS Departamento;
        DROP TABLE IF EXISTS Centro;
        DROP TABLE IF EXISTS Idioma;
        DROP TABLE IF EXISTS Periodo_Academico;

        CREATE TABLE Centro (
            Cod_Centro INTEGER PRIMARY KEY,
            Desc_Centro TEXT NOT NULL
        );

        CREATE TABLE Departamento (
            Cod_Dpto INTEGER PRIMARY KEY,
            Desc_Dpto TEXT NOT NULL,
            Cod_Centro INTEGER,
            FOREIGN KEY (Cod_Centro) REFERENCES Centro(Cod_Centro)
        );

        CREATE TABLE Grado (
            Cod_Plan TEXT PRIMARY KEY,
            Desc_Plan TEXT NOT NULL,
            Cod_Centro INTEGER,
            FOREIGN KEY (Cod_Centro) REFERENCES Centro(Cod_Centro)
        );
                             
        CREATE TABLE Idioma (
            Cod_Idioma TEXT PRIMARY KEY,
            Desc_Idioma TEXT NOT NULL
        );

        CREATE TABLE Periodo_Academico (
            Cod_Periodo TEXT PRIMARY KEY,
            Any_Academico TEXT NOT NULL,
            Desc_Periodo TEXT
        );

        CREATE TABLE Asignatura (
            Cod_Asignatura INTEGER PRIMARY KEY,
            Desc_Asignatura TEXT NOT NULL,
            Creditos REAL
        );

        CREATE TABLE Asignatura_Grado_Dpto (
            Cod_Asignatura INTEGER,
            Cod_Plan TEXT,
            Cod_Dpto INTEGER,
            Any_Academico TEXT,
            Curso INTEGER,
            Cuatrimestre TEXT,
            Clase TEXT,
            Linea_Curricular TEXT,
            Compartida INTEGER,
            Titulaciones_Comparten TEXT,
            Horas_M FLOAT,
            Horas_S FLOAT,
            Horas_GA FLOAT,
            Horas_GL FLOAT,
            Horas_GO FLOAT,
            Horas_GCA FLOAT,
            Horas_GCL FLOAT,
            Horas_TA FLOAT,
            Horas_TI FLOAT,
            PRIMARY KEY (Cod_Asignatura, Cod_Plan, Any_Academico),
            FOREIGN KEY (Cod_Asignatura) REFERENCES Asignatura(Cod_Asignatura),
            FOREIGN KEY (Cod_Plan) REFERENCES Grado(Cod_Plan),
            FOREIGN KEY (Cod_Dpto) REFERENCES Departamento(Cod_Dpto)
        );
                             
        CREATE TABLE Matricula (
            Cod_Asignatura INTEGER,
            Cod_Plan TEXT,
            Cod_Periodo TEXT,
            Cod_Idioma TEXT,
            Matriculados INTEGER,
            Matriculados_Salientes_EHU INTEGER,
            Matriculados_Otras_Univer INTEGER,                     
            PRIMARY KEY (Cod_Asignatura, Cod_Plan, Cod_Idioma, Cod_Periodo),
            FOREIGN KEY (Cod_Asignatura) REFERENCES Asignatura(Cod_Asignatura),
            FOREIGN KEY (Cod_Plan) REFERENCES Grado(Cod_Plan),
            FOREIGN KEY (Cod_Idioma) REFERENCES Idioma(Cod_Idioma),
            FOREIGN KEY (Cod_Periodo) REFERENCES Periodo_Academico(Cod_Periodo)
        );
                             
        CREATE TABLE Agrupacion (
            ID_Agrupacion TEXT PRIMARY KEY,
            Desc_Agrupacion TEXT
        );

        CREATE TABLE Agrupacion_Grado (
            ID_Agrupacion TEXT,
            Cod_Plan TEXT,
            PRIMARY KEY (ID_Agrupacion, Cod_Plan),
            FOREIGN KEY (ID_Agrupacion) REFERENCES Agrupacion(ID_Agrupacion),
            FOREIGN KEY (Cod_Plan) REFERENCES Grado(Cod_Plan)
        );
                       
        CREATE TABLE Calculo_Grupos (
            Cod_Asignatura INTEGER,
            ID_Agrupacion TEXT,
            Cod_Periodo TEXT,
            Cod_Idioma TEXT,
            Tipo_Clase TEXT,
            Horas REAL,
            Total_Matriculados INTEGER,
            Grupos_Calculados INTEGER,
            Creditos_Calculados REAL,
            Grupos_Autorizados INTEGER,
            Creditos_Autorizados REAL,
            Grupos_Originales INTEGER,
            Creditos_Originales REAL,
            PRIMARY KEY (Cod_Asignatura, ID_Agrupacion, Cod_Idioma, Cod_Periodo, Tipo_Clase),
            FOREIGN KEY (Cod_Asignatura) REFERENCES Asignatura(Cod_Asignatura),
            FOREIGN KEY (ID_Agrupacion) REFERENCES Agrupacion(ID_Agrupacion),
            FOREIGN KEY (Cod_Idioma) REFERENCES Idioma(Cod_Idioma),
            FOREIGN KEY (Cod_Periodo) REFERENCES Periodo_Academico(Cod_Periodo)
        );
                             
        CREATE TABLE Distribucion_Grupos (
            Cod_Asignatura INTEGER,
            ID_Agrupacion TEXT,
            Cod_Periodo TEXT,
            Cod_Idioma TEXT,
            Tipo_Clase TEXT,
            Num_Grupo INTEGER,
            Nombre_Oficial TEXT,
            Alumnos_Asignados INTEGER,
            PRIMARY KEY (Cod_Asignatura, ID_Agrupacion, Cod_Idioma, Cod_Periodo, Tipo_Clase, Num_Grupo),
            FOREIGN KEY (Cod_Asignatura, ID_Agrupacion, Cod_Idioma, Cod_Periodo, Tipo_Clase) 
                REFERENCES Calculo_Grupos(Cod_Asignatura, ID_Agrupacion, Cod_Idioma, Cod_Periodo, Tipo_Clase) ON DELETE CASCADE
        );

        CREATE VIEW Totales_Creditos AS
        SELECT 
            Cod_Asignatura,
            ID_Agrupacion,
            Cod_Periodo,
            Cod_Idioma,
            SUM(Creditos_Calculados) AS Total_Creditos_Calculados,
            SUM(Creditos_Autorizados) AS Total_Creditos_Autorizados
        FROM Calculo_Grupos
        GROUP BY Cod_Asignatura, ID_Agrupacion, Cod_Periodo, Cod_Idioma;
        ''')
        conexion.commit()
        cursor.execute('PRAGMA foreign_keys = ON;')

        dfCentros = dfAsignaturas[['Cod.Centro', 'Desc.Centro']].drop_duplicates()
        dfCentros = dfCentros.rename(columns = {'Cod.Centro': 'Cod_Centro', 'Desc.Centro': 'Desc_Centro'})
        dfCentros.to_sql('Centro', conexion, if_exists = 'append', index = False)

        dfDptos = dfAsignaturas[['Cod.Dpto', 'Desc.Dpto', 'Cod.Centro']].drop_duplicates()
        dfDptos = dfDptos.rename(columns = {'Cod.Dpto': 'Cod_Dpto', 'Desc.Dpto': 'Desc_Dpto', 'Cod.Centro': 'Cod_Centro'})
        dfDptos.to_sql('Departamento', conexion, if_exists = 'append', index = False)

        dfGrados = dfAsignaturas[['Cod.Plan', 'Desc.Plan', 'Cod.Centro']].drop_duplicates()
        dfGrados = dfGrados.rename(columns = {'Cod.Plan': 'Cod_Plan', 'Desc.Plan': 'Desc_Plan', 'Cod.Centro': 'Cod_Centro'})
        dfGrados.to_sql('Grado', conexion, if_exists = 'append', index = False)

        dfAsigs = dfMatriculas[['Cod.Asignatura', 'Desc.Asignatura', 'Creditos']].drop_duplicates(subset = ['Cod.Asignatura']).copy()
        dfAsigs = dfAsigs.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Desc.Asignatura': 'Desc_Asignatura'})
        dfAsigs['Creditos'] = dfAsigs['Creditos'].astype(str).str.replace(',', '.')
        dfAsigs['Creditos'] = pd.to_numeric(dfAsigs['Creditos'], errors = 'coerce')
        dfAsigs.to_sql('Asignatura', conexion, if_exists = 'append', index = False)

        dfAsigGrado = dfAsignaturas[['Cod.Asignatura', 'Cod.Plan', 'Cod.Dpto', 'Any academico', 'Curso', 'Cuatrimestre', 'Clase', 'Linea curricular', 'Compartida', 'Titulaciones comparten', 'M Patron', 'S Patron', 'GA Patron', 'GL Patron', 'GO Patron', 'GCA Patron', 'GCL Patron', 'TA Patron', 'TI Patron']].drop_duplicates().copy()
        dfAsigGrado = dfAsigGrado.rename(columns = {
            'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Cod.Dpto': 'Cod_Dpto', 
            'Any academico': 'Any_Academico', 'Linea curricular': 'Linea_Curricular', 
            'Titulaciones comparten': 'Titulaciones_Comparten', 'M Patron': 'Horas_M', 
            'S Patron': 'Horas_S', 'GA Patron': 'Horas_GA', 'GL Patron': 'Horas_GL', 
            'GO Patron': 'Horas_GO', 'GCA Patron': 'Horas_GCA', 'GCL Patron': 'Horas_GCL', 
            'TA Patron': 'Horas_TA', 'TI Patron': 'Horas_TI'
        })
        dfAsigGrado['Compartida'] = (dfAsigGrado['Compartida'] == 'Si').astype(int)
        dfAsigGrado.to_sql('Asignatura_Grado_Dpto', conexion, if_exists = 'append', index = False)

        dfIdiomas = pd.DataFrame({'Cod_Idioma': ['C', 'E', 'I'], 'Desc_Idioma': ['Castellano', 'Euskara', 'Inglés']})
        dfIdiomas.to_sql('Idioma', conexion, if_exists = 'append', index = False)

        dfPeriodos = dfMatriculas[['Any academico']].drop_duplicates().copy()
        dfPeriodos = dfPeriodos.rename(columns = {'Any academico': 'Cod_Periodo'})
        dfPeriodos['Any_Academico'] = dfPeriodos['Cod_Periodo'].astype(str).apply(lambda x: x.split('.')[0])
        def describe_periodo(p):
            pStr = str(p)
            if '.1' in pStr: return 'Estimación primera'
            elif '.2' in pStr: return 'Cálculo final'
            return 'Periodo general'
        dfPeriodos['Desc_Periodo'] = dfPeriodos['Cod_Periodo'].apply(describe_periodo)
        dfPeriodos.to_sql('Periodo_Academico', conexion, if_exists = 'append', index = False)

        dfMatriCas = dfMatriculas.loc[dfMatriculas['Mat.Cas.'].notna(), ['Cod.Asignatura', 'Cod.Plan', 'Any academico', 'Mat.Cas.', 'Mat.Cas. SALIENTE DE UPV/EHU', 'Mat.Cas. DE OTRAS UNIVER']].copy()
        dfMatriCas['Cod_Idioma'] = 'C'
        dfMatriCas = dfMatriCas.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Any academico': 'Cod_Periodo', 'Mat.Cas.': 'Matriculados', 'Mat.Cas. SALIENTE DE UPV/EHU': 'Matriculados_Salientes_EHU', 'Mat.Cas. DE OTRAS UNIVER': 'Matriculados_Otras_Univer'})

        dfMatriEus = dfMatriculas.loc[dfMatriculas['Mat.Eus.'].notna(), ['Cod.Asignatura', 'Cod.Plan', 'Any academico', 'Mat.Eus.', 'Mat.Eus. SALIENTE DE UPV/EHU', 'Mat.Eus. DE OTRAS UNIVER']].copy()
        dfMatriEus['Cod_Idioma'] = 'E'
        dfMatriEus = dfMatriEus.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Any academico': 'Cod_Periodo', 'Mat.Eus.': 'Matriculados', 'Mat.Eus. SALIENTE DE UPV/EHU': 'Matriculados_Salientes_EHU', 'Mat.Eus. DE OTRAS UNIVER': 'Matriculados_Otras_Univer'})

        dfMatriOtr = dfMatriculas.loc[dfMatriculas['Mat.Otr.'].notna(), ['Cod.Asignatura', 'Cod.Plan', 'Any academico', 'Mat.Otr.', 'Mat.Otr. SALIENTE DE UPV/EHU', 'Mat.Otr. DE OTRAS UNIVER']].copy()
        dfMatriOtr['Cod_Idioma'] = 'I'
        dfMatriOtr = dfMatriOtr.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Any academico': 'Cod_Periodo', 'Mat.Otr.': 'Matriculados', 'Mat.Otr. SALIENTE DE UPV/EHU': 'Matriculados_Salientes_EHU', 'Mat.Otr. DE OTRAS UNIVER': 'Matriculados_Otras_Univer'})

        dfMatriTodas = pd.concat([dfMatriCas, dfMatriEus, dfMatriOtr], ignore_index = True).fillna(0)
        columnas = ['Matriculados', 'Matriculados_Salientes_EHU', 'Matriculados_Otras_Univer']
        dfMatriTodas[columnas] = dfMatriTodas[columnas].astype(int)
        
        dfMatriTodas = dfMatriTodas.merge(dfPeriodos[['Cod_Periodo', 'Any_Academico']], on = 'Cod_Periodo', how = 'left')

        clavesValidas = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Any_Academico FROM Asignatura_Grado_Dpto', conexion)
        dfMatriLimpio = dfMatriTodas.merge(clavesValidas, on = ['Cod_Asignatura', 'Cod_Plan', 'Any_Academico'], how = 'inner')
        dfMatriLimpio = dfMatriLimpio.drop(columns = ['Any_Academico'])
        dfMatriLimpio.to_sql('Matricula', conexion, if_exists = 'append', index = False)

        def crea_id_agrupacion(fila):
            if fila['Compartida'] in ['No', '0', 0]:
                return str(fila['Cod_Plan'])
            gradosLista = re.findall(r'[A-Z]{6}\d{2}', str(fila['Titulaciones_Comparten']))
            gradosLista.sort()
            return '_'.join(gradosLista)

        dfAgrup = dfAsignaturas[['Cod.Plan', 'Compartida', 'Titulaciones comparten']].copy()
        dfAgrup = dfAgrup.rename(columns = {'Cod.Plan': 'Cod_Plan', 'Titulaciones comparten': 'Titulaciones_Comparten'})
        dfAgrup['ID_Agrupacion'] = dfAgrup.apply(crea_id_agrupacion, axis = 1)

        agrupacionesUnicas = dfAgrup['ID_Agrupacion'].unique()
        filasAgrupacion = []
        filasAgrupacionGrado = []

        for idAgrup in agrupacionesUnicas:
            filasAgrupacion.append({'ID_Agrupacion': idAgrup})
            gradosPertenecen = str(idAgrup).split('_')
            for grado in gradosPertenecen:
                filasAgrupacionGrado.append({
                    'ID_Agrupacion': idAgrup,
                    'Cod_Plan': grado
                })

        pd.DataFrame(filasAgrupacion).to_sql('Agrupacion', conexion, if_exists = 'append', index = False)
        pd.DataFrame(filasAgrupacionGrado).to_sql('Agrupacion_Grado', conexion, if_exists = 'append', index = False)

        idioma_map = {'Cas': 'C', 'Eus': 'E', 'Otr': 'I'}
        gruposCols = []
        
        for col in dfPPT.columns:
            match = re.search(r'([A-Z]+)_autorizado\s*(Cas|Eus|Otr)', str(col), flags = re.IGNORECASE)
            if match:
                tipo = match.group(1).upper()
                lang_raw = match.group(2).capitalize()
                if tipo in ['M', 'GA', 'S', 'GL', 'GO', 'GCA']:
                    gruposCols.append({'col_name': col, 'tipo_clase': tipo, 'cod_idioma': idioma_map[lang_raw]})

        if gruposCols:
            dfAsigBD = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Compartida, Titulaciones_Comparten, Horas_M, Horas_GA, Horas_S, Horas_GL, Horas_GO, Horas_GCA FROM Asignatura_Grado_Dpto', conexion)
            dfAsigBD['ID_Agrupacion'] = dfAsigBD.apply(crea_id_agrupacion, axis = 1)
            
            dfMatBD_raw = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Cod_Idioma, Cod_Periodo, Matriculados FROM Matricula', conexion)
            dfMatBD = dfMatBD_raw.merge(dfAsigBD[['Cod_Asignatura', 'Cod_Plan', 'ID_Agrupacion']], on = ['Cod_Asignatura', 'Cod_Plan'])
            dfMatBD = dfMatBD.groupby(['Cod_Asignatura', 'ID_Agrupacion', 'Cod_Idioma', 'Cod_Periodo'])['Matriculados'].sum().reset_index()
            dfMatBD = dfMatBD.rename(columns = {'Matriculados': 'Total_Matriculados'})

            filasCalc = []
            
            periodoExcel = dfPeriodos['Cod_Periodo'].iloc[0] if not dfPeriodos.empty else 'DESC'

            for _, fila in dfPPT.iterrows():
                codAsigRaw = fila.get('Cod.Asignatura')
                if pd.isna(codAsigRaw): continue
                matchAsigRaw = re.match(r'(\d+)', str(codAsigRaw).strip())
                if not matchAsigRaw: continue
                codAsig = int(matchAsigRaw.group(1))

                matchAsig = dfAsigBD[dfAsigBD['Cod_Asignatura'] == codAsig]
                if matchAsig.empty: continue

                codPlanRaw = fila.get('Cod.Plan')
                if pd.notna(codPlanRaw):
                    matchPlan = matchAsig[matchAsig['Cod_Plan'].astype(str) == str(codPlanRaw).strip()]
                    if not matchPlan.empty:
                        matchAsig = matchPlan

                agrupacionesUnicas = matchAsig.drop_duplicates(subset = ['ID_Agrupacion'])

                for _, filaAgrup in agrupacionesUnicas.iterrows():
                    idAgrup = filaAgrup['ID_Agrupacion']

                    for gcol in gruposCols:
                        val = pd.to_numeric(fila.get(gcol['col_name']), errors = 'coerce')
                        if pd.notna(val) and val > 0:
                            tipo = gcol['tipo_clase']
                            idioma = gcol['cod_idioma']
                            
                            horas = filaAgrup.get(f'Horas_{tipo}', 0.0)
                            if pd.isna(horas): horas = 0.0
                            
                            matchMat = dfMatBD[(dfMatBD['Cod_Asignatura'] == codAsig) & (dfMatBD['ID_Agrupacion'] == idAgrup) & (dfMatBD['Cod_Idioma'] == idioma) & (dfMatBD['Cod_Periodo'] == periodoExcel)]
                            totalMat = matchMat.iloc[0]['Total_Matriculados'] if not matchMat.empty else 0
                            
                            creditosAut = (val * horas) / 10.0

                            filasCalc.append({'Cod_Asignatura': codAsig, 'ID_Agrupacion': idAgrup, 'Cod_Periodo': periodoExcel, 'Cod_Idioma': idioma, 'Tipo_Clase': tipo, 'Horas': horas, 'Total_Matriculados': totalMat, 'Grupos_Calculados': 0, 'Creditos_Calculados': 0.0, 'Grupos_Autorizados': int(val), 'Creditos_Autorizados': creditosAut, 'Grupos_Originales': int(val), 'Creditos_Originales': creditosAut})

            if filasCalc: upsert_df(pd.DataFrame(filasCalc).drop_duplicates(subset = ['Cod_Asignatura', 'ID_Agrupacion', 'Cod_Idioma', 'Cod_Periodo', 'Tipo_Clase']), 'Calculo_Grupos', conexion)

        if gruposCols:
            recalcula_distribucion_total(conexion, periodoExcel)

        conexion.close()
        return True, rutaBd

    except Exception as e:
        if 'conexion' in locals():
            conexion.close()
        return False, str(e)
    
def upsert_df(df, table_name, conexion):
    if df.empty:
        return
    temp_table = f'temp_{table_name}'
    df.to_sql(temp_table, conexion, if_exists = 'replace', index = False)
    columnas = ', '.join(f'"{col}"' for col in df.columns)
    cursor = conexion.cursor()
    cursor.execute(f'INSERT OR REPLACE INTO {table_name} ({columnas}) SELECT {columnas} FROM {temp_table}')
    cursor.execute(f'DROP TABLE {temp_table}')
    conexion.commit()

def actualiza_bdd_excel(archivoSubido, rutaBd):
    try:
        excel = pd.ExcelFile(archivoSubido)
        
        hojasEsperadas = ['ASIGNATURAS', 'PotAsignaturas', 'PPTAGREGR']
        for hoja in hojasEsperadas:
            if hoja not in excel.sheet_names:
                raise ValueError(f'El archivo Excel no tiene el formato esperado. Falta la hoja: \'{hoja}\'.')

        dfAsignaturas = pd.read_excel(excel, sheet_name = 'ASIGNATURAS')
        dfMatriculas = pd.read_excel(excel, sheet_name = 'PotAsignaturas')
        dfPPT = pd.read_excel(excel, sheet_name = 'PPTAGREGR')

        columnasAsig = ['Cod.Centro', 'Desc.Centro', 'Cod.Dpto', 'Desc.Dpto', 'Cod.Plan', 'Desc.Plan', 
                         'Cod.Asignatura', 'Any academico', 'Curso', 'Cuatrimestre', 'Clase', 'Linea curricular', 
                         'Compartida', 'Titulaciones comparten', 'M Patron', 'S Patron', 'GA Patron', 'GL Patron', 
                         'GO Patron', 'GCA Patron', 'GCL Patron', 'TA Patron', 'TI Patron']
        for col in columnasAsig:
            if col not in dfAsignaturas.columns:
                raise ValueError(f'Formato incorrecto. Falta la columna \'{col}\' en la hoja \'ASIGNATURAS\'.')

        columnasMatri = ['Cod.Asignatura', 'Desc.Asignatura', 'Creditos', 'Any academico', 
                          'Mat.Cas.', 'Mat.Cas. SALIENTE DE UPV/EHU', 'Mat.Cas. DE OTRAS UNIVER', 
                          'Mat.Eus.', 'Mat.Eus. SALIENTE DE UPV/EHU', 'Mat.Eus. DE OTRAS UNIVER', 
                          'Mat.Otr.', 'Mat.Otr. SALIENTE DE UPV/EHU', 'Mat.Otr. DE OTRAS UNIVER']
        for col in columnasMatri:
            if col not in dfMatriculas.columns:
                raise ValueError(f'Formato incorrecto. Falta la columna \'{col}\' en la hoja \'PotAsignaturas\'.')

        conexion = sqlite3.connect(rutaBd)

        dfCentros = dfAsignaturas[['Cod.Centro', 'Desc.Centro']].drop_duplicates().rename(columns = {'Cod.Centro': 'Cod_Centro', 'Desc.Centro': 'Desc_Centro'})
        upsert_df(dfCentros, 'Centro', conexion)

        dfDptos = dfAsignaturas[['Cod.Dpto', 'Desc.Dpto', 'Cod.Centro']].drop_duplicates().rename(columns = {'Cod.Dpto': 'Cod_Dpto', 'Desc.Dpto': 'Desc_Dpto', 'Cod.Centro': 'Cod_Centro'})
        upsert_df(dfDptos, 'Departamento', conexion)

        dfGrados = dfAsignaturas[['Cod.Plan', 'Desc.Plan', 'Cod.Centro']].drop_duplicates().rename(columns = {'Cod.Plan': 'Cod_Plan', 'Desc.Plan': 'Desc_Plan', 'Cod.Centro': 'Cod_Centro'})
        upsert_df(dfGrados, 'Grado', conexion)

        dfAsigs = dfMatriculas[['Cod.Asignatura', 'Desc.Asignatura', 'Creditos']].drop_duplicates(subset = ['Cod.Asignatura']).copy().rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Desc.Asignatura': 'Desc_Asignatura'})
        dfAsigs['Creditos'] = pd.to_numeric(dfAsigs['Creditos'].astype(str).str.replace(',', '.'), errors = 'coerce')
        upsert_df(dfAsigs, 'Asignatura', conexion)

        dfAsigGrado = dfAsignaturas[['Cod.Asignatura', 'Cod.Plan', 'Cod.Dpto', 'Any academico', 'Curso', 'Cuatrimestre', 'Clase', 'Linea curricular', 'Compartida', 'Titulaciones comparten', 'M Patron', 'S Patron', 'GA Patron', 'GL Patron', 'GO Patron', 'GCA Patron', 'GCL Patron', 'TA Patron', 'TI Patron']].drop_duplicates().copy()
        dfAsigGrado = dfAsigGrado.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Cod.Dpto': 'Cod_Dpto', 'Any academico': 'Any_Academico', 'Linea curricular': 'Linea_Curricular', 'Titulaciones comparten': 'Titulaciones_Comparten', 'M Patron': 'Horas_M', 'S Patron': 'Horas_S', 'GA Patron': 'Horas_GA', 'GL Patron': 'Horas_GL', 'GO Patron': 'Horas_GO', 'GCA Patron': 'Horas_GCA', 'GCL Patron': 'Horas_GCL', 'TA Patron': 'Horas_TA', 'TI Patron': 'Horas_TI'})
        dfAsigGrado['Compartida'] = (dfAsigGrado['Compartida'] == 'Si').astype(int)
        upsert_df(dfAsigGrado, 'Asignatura_Grado_Dpto', conexion)

        dfIdiomas = pd.DataFrame({'Cod_Idioma': ['C', 'E', 'I'], 'Desc_Idioma': ['Castellano', 'Euskara', 'Inglés']})
        upsert_df(dfIdiomas, 'Idioma', conexion)

        dfPeriodos = dfMatriculas[['Any academico']].drop_duplicates().copy().rename(columns = {'Any academico': 'Cod_Periodo'})
        dfPeriodos['Any_Academico'] = dfPeriodos['Cod_Periodo'].astype(str).apply(lambda x: x.split('.')[0])
        dfPeriodos['Desc_Periodo'] = dfPeriodos['Cod_Periodo'].apply(lambda p: 'Estimación primera' if '.1' in str(p) else ('Cálculo final' if '.2' in str(p) else 'Periodo general'))
        upsert_df(dfPeriodos, 'Periodo_Academico', conexion)

        dfMatriCas = dfMatriculas.loc[dfMatriculas['Mat.Cas.'].notna(), ['Cod.Asignatura', 'Cod.Plan', 'Any academico', 'Mat.Cas.', 'Mat.Cas. SALIENTE DE UPV/EHU', 'Mat.Cas. DE OTRAS UNIVER']].copy()
        dfMatriCas['Cod_Idioma'] = 'C'
        dfMatriCas = dfMatriCas.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Any academico': 'Cod_Periodo', 'Mat.Cas.': 'Matriculados', 'Mat.Cas. SALIENTE DE UPV/EHU': 'Matriculados_Salientes_EHU', 'Mat.Cas. DE OTRAS UNIVER': 'Matriculados_Otras_Univer'})
        dfMatriEus = dfMatriculas.loc[dfMatriculas['Mat.Eus.'].notna(), ['Cod.Asignatura', 'Cod.Plan', 'Any academico', 'Mat.Eus.', 'Mat.Eus. SALIENTE DE UPV/EHU', 'Mat.Eus. DE OTRAS UNIVER']].copy()
        dfMatriEus['Cod_Idioma'] = 'E'
        dfMatriEus = dfMatriEus.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Any academico': 'Cod_Periodo', 'Mat.Eus.': 'Matriculados', 'Mat.Eus. SALIENTE DE UPV/EHU': 'Matriculados_Salientes_EHU', 'Mat.Eus. DE OTRAS UNIVER': 'Matriculados_Otras_Univer'})
        dfMatriOtr = dfMatriculas.loc[dfMatriculas['Mat.Otr.'].notna(), ['Cod.Asignatura', 'Cod.Plan', 'Any academico', 'Mat.Otr.', 'Mat.Otr. SALIENTE DE UPV/EHU', 'Mat.Otr. DE OTRAS UNIVER']].copy()
        dfMatriOtr['Cod_Idioma'] = 'I'
        dfMatriOtr = dfMatriOtr.rename(columns = {'Cod.Asignatura': 'Cod_Asignatura', 'Cod.Plan': 'Cod_Plan', 'Any academico': 'Cod_Periodo', 'Mat.Otr.': 'Matriculados', 'Mat.Otr. SALIENTE DE UPV/EHU': 'Matriculados_Salientes_EHU', 'Mat.Otr. DE OTRAS UNIVER': 'Matriculados_Otras_Univer'})

        dfMatriTodas = pd.concat([dfMatriCas, dfMatriEus, dfMatriOtr], ignore_index = True).fillna(0)
        dfMatriTodas[['Matriculados', 'Matriculados_Salientes_EHU', 'Matriculados_Otras_Univer']] = dfMatriTodas[['Matriculados', 'Matriculados_Salientes_EHU', 'Matriculados_Otras_Univer']].astype(int)
        dfMatriTodas = dfMatriTodas.merge(dfPeriodos[['Cod_Periodo', 'Any_Academico']], on = 'Cod_Periodo', how = 'left')

        clavesValidas = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Any_Academico FROM Asignatura_Grado_Dpto', conexion)
        dfMatriLimpio = dfMatriTodas.merge(clavesValidas, on = ['Cod_Asignatura', 'Cod_Plan', 'Any_Academico'], how = 'inner').drop(columns = ['Any_Academico'])
        upsert_df(dfMatriLimpio, 'Matricula', conexion)

        dfAgrup = dfAsignaturas[['Cod.Plan', 'Compartida', 'Titulaciones comparten']].copy().rename(columns = {'Cod.Plan': 'Cod_Plan', 'Titulaciones comparten': 'Titulaciones_Comparten'})
        def crea_id_agrupacion(fila):
            if fila['Compartida'] in ['No', '0', 0]: return str(fila['Cod_Plan'])
            gradosLista = re.findall(r'[A-Z]{6}\d{2}', str(fila['Titulaciones_Comparten']))
            gradosLista.sort()
            return '_'.join(gradosLista)
        dfAgrup['ID_Agrupacion'] = dfAgrup.apply(crea_id_agrupacion, axis = 1)

        filasAgrupacion = [{'ID_Agrupacion': idA} for idA in dfAgrup['ID_Agrupacion'].unique()]
        filasAgrupacionGrado = [{'ID_Agrupacion': idA, 'Cod_Plan': gr} for idA in dfAgrup['ID_Agrupacion'].unique() for gr in str(idA).split('_')]
        upsert_df(pd.DataFrame(filasAgrupacion).drop_duplicates(), 'Agrupacion', conexion)
        upsert_df(pd.DataFrame(filasAgrupacionGrado).drop_duplicates(), 'Agrupacion_Grado', conexion)

        idioma_map = {'Cas': 'C', 'Eus': 'E', 'Otr': 'I'}
        gruposCols = []
        for col in dfPPT.columns:
            match = re.search(r'([A-Z]+)_autorizado\s*(Cas|Eus|Otr)', str(col), flags = re.IGNORECASE)
            if match:
                tipo = match.group(1).upper()
                lang_raw = match.group(2).capitalize()
                if tipo in ['M', 'GA', 'S', 'GL', 'GO', 'GCA']:
                    gruposCols.append({'col_name': col, 'tipo_clase': tipo, 'cod_idioma': idioma_map[lang_raw]})

        if gruposCols:
            dfAsigBD = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Compartida, Titulaciones_Comparten, Horas_M, Horas_GA, Horas_S, Horas_GL, Horas_GO, Horas_GCA FROM Asignatura_Grado_Dpto', conexion)
            dfAsigBD['ID_Agrupacion'] = dfAsigBD.apply(crea_id_agrupacion, axis = 1)
            
            dfMatBD_raw = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Cod_Idioma, Cod_Periodo, Matriculados FROM Matricula', conexion)
            dfMatBD = dfMatBD_raw.merge(dfAsigBD[['Cod_Asignatura', 'Cod_Plan', 'ID_Agrupacion']], on = ['Cod_Asignatura', 'Cod_Plan'])
            dfMatBD = dfMatBD.groupby(['Cod_Asignatura', 'ID_Agrupacion', 'Cod_Idioma', 'Cod_Periodo'])['Matriculados'].sum().reset_index()
            dfMatBD = dfMatBD.rename(columns = {'Matriculados': 'Total_Matriculados'})

            filasCalc = []

            periodoExcel = dfPeriodos['Cod_Periodo'].iloc[0] if not dfPeriodos.empty else 'DESC'

            for _, fila in dfPPT.iterrows():
                codAsigRaw = fila.get('Cod.Asignatura')
                if pd.isna(codAsigRaw): continue
                matchAsigRaw = re.match(r'(\d+)', str(codAsigRaw).strip())
                if not matchAsigRaw: continue
                codAsig = int(matchAsigRaw.group(1))

                matchAsig = dfAsigBD[dfAsigBD['Cod_Asignatura'] == codAsig]
                if matchAsig.empty: continue

                codPlanRaw = fila.get('Cod.Plan')
                if pd.notna(codPlanRaw):
                    matchPlan = matchAsig[matchAsig['Cod_Plan'].astype(str) == str(codPlanRaw).strip()]
                    if not matchPlan.empty:
                        matchAsig = matchPlan

                agrupacionesUnicas = matchAsig.drop_duplicates(subset = ['ID_Agrupacion'])

                for _, filaAgrup in agrupacionesUnicas.iterrows():
                    idAgrup = filaAgrup['ID_Agrupacion']

                    for gcol in gruposCols:
                        val = pd.to_numeric(fila.get(gcol['col_name']), errors = 'coerce')
                        if pd.notna(val) and val > 0:
                            tipo = gcol['tipo_clase']
                            idioma = gcol['cod_idioma']
                            
                            horas = filaAgrup.get(f'Horas_{tipo}', 0.0)
                            if pd.isna(horas): horas = 0.0
                            
                            matchMat = dfMatBD[(dfMatBD['Cod_Asignatura'] == codAsig) & (dfMatBD['ID_Agrupacion'] == idAgrup) & (dfMatBD['Cod_Idioma'] == idioma) & (dfMatBD['Cod_Periodo'] == periodoExcel)]
                            totalMat = matchMat.iloc[0]['Total_Matriculados'] if not matchMat.empty else 0
                            
                            creditosAut = (val * horas) / 10.0

                            filasCalc.append({'Cod_Asignatura': codAsig, 'ID_Agrupacion': idAgrup, 'Cod_Periodo': periodoExcel, 'Cod_Idioma': idioma, 'Tipo_Clase': tipo, 'Horas': horas, 'Total_Matriculados': totalMat, 'Grupos_Calculados': 0, 'Creditos_Calculados': 0.0, 'Grupos_Autorizados': int(val), 'Creditos_Autorizados': creditosAut, 'Grupos_Originales': int(val), 'Creditos_Originales': creditosAut})

            if filasCalc: upsert_df(pd.DataFrame(filasCalc).drop_duplicates(subset = ['Cod_Asignatura', 'ID_Agrupacion', 'Cod_Idioma', 'Cod_Periodo', 'Tipo_Clase']), 'Calculo_Grupos', conexion)

        if gruposCols:
            recalcula_distribucion_total(conexion, periodoExcel)

        conexion.close()
        return True, 'Base de datos actualizada con éxito.'
    except Exception as e:
        if 'conexion' in locals():
            conexion.close()
        return False, str(e)

def muestra_pagina_config():
    st.markdown('''
        <style>
        .block-container {
            text-align: center;
        }
        h1, h2, h3, h4, h5, h6, p, label {
            text-align: center !important;
            justify-content: center !important;
        }
        [data-testid="stMetric"] {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {
            text-align: center !important;
            justify-content: center !important;
        }
        .stButton {
            display: flex;
            justify-content: center;
        }
        [data-testid="stDataFrame"] {
            display: flex;
            justify-content: center;
        }
        </style>
    ''', unsafe_allow_html = True)

    st.markdown('<h1 style="text-align: center;">Configuración de la Base de Datos</h1>', unsafe_allow_html = True)
    
    archivosBd = glob.glob(os.path.join(directorioBase, '*.db'))
    
    if len(archivosBd) > 0:
        st.success(f'Se han encontrado {len(archivosBd)} base(s) de datos en el repositorio.')
        
        nombresBd = [os.path.basename(bd) for bd in archivosBd]
        
        indice_defecto = 0
        if 'bdActual' in st.session_state and st.session_state['bdActual']:
            nombre_actual = os.path.basename(st.session_state['bdActual'])
            if nombre_actual in nombresBd:
                indice_defecto = nombresBd.index(nombre_actual)
        
        bdSeleccionada = st.selectbox('Selecciona la base de datos a utilizar:', nombresBd, index = indice_defecto)
        
        if bdSeleccionada:
            st.info(f'Base de datos activa: {bdSeleccionada}')
            ruta_seleccionada = os.path.join(directorioBase, bdSeleccionada)
            if st.session_state.get('bdActual') != ruta_seleccionada:
                st.session_state['bdActual'] = ruta_seleccionada
                guardar_bd_activa(ruta_seleccionada)
        
        st.markdown('---')
        st.subheader('Crear una nueva base de datos')
        
        abrir_crear = 'uploader_crear' in st.session_state and st.session_state['uploader_crear'] is not None
        with st.expander('Haz clic aquí para subir un Excel y crear una nueva base de datos', expanded = abrir_crear):
            muestra_creacion_bdd()
            
        st.markdown('---')
        st.subheader('Añadir o actualizar datos de la base de datos')
        
        abrir_actualizar = 'uploader_actualizar' in st.session_state and st.session_state['uploader_actualizar'] is not None
        with st.expander('Haz clic aquí para subir un Excel y añadir o actualizar información a la base de datos activa', expanded = abrir_actualizar):
            if 'bdActual' in st.session_state and st.session_state['bdActual']:
                st.info(f'Los datos se inyectarán en la base de datos activa: **{os.path.basename(st.session_state["bdActual"])}**')
                archivoActualizar = st.file_uploader('Sube un archivo Excel (.xlsx, .xls) con el formato oficial', type = ['xlsx', 'xls'], key = 'uploader_actualizar')
                if archivoActualizar is not None:
                    if st.button('Añadir / Actualizar Datos', type = 'primary'):
                        with st.spinner('Procesando Excel e inyectando datos. Esto puede tardar unos segundos...'):
                            exito, mensaje = actualiza_bdd_excel(archivoActualizar, st.session_state['bdActual'])
                            if exito:
                                st.success(mensaje)
                                import time
                                time.sleep(1.5)
                                if hasattr(st, 'rerun'): st.rerun()
                                else: st.experimental_rerun()
                            else:
                                st.error(f'Error al actualizar la base de datos: {mensaje}')
            else:
                st.warning('Debes seleccionar una base de datos activa en la parte superior para poder añadirle información.')

        st.markdown('---')
        st.subheader('Eliminar bases de datos')
        with st.expander('Haz clic aquí para eliminar una base de datos existente'):
            bdAEliminar = st.selectbox('Selecciona la base de datos a eliminar:', nombresBd, key = 'select_eliminar')
            if st.button('Eliminar Base de Datos'):
                try:
                    rutaEliminar = os.path.join(directorioBase, bdAEliminar)
                    if 'bdActual' in st.session_state and st.session_state['bdActual'] == rutaEliminar:
                        st.session_state['bdActual'] = None
                        guardar_bd_activa(None)
                    os.remove(rutaEliminar)
                    st.success(f'Base de datos \'{bdAEliminar}\' eliminada.')
                    import time
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f'Error al eliminar la base de datos: {e}')
            
    else:
        st.warning('No se ha encontrado ninguna base de datos en el directorio del proyecto.')
        st.info('Por favor, sube un archivo Excel para generar una nueva base de datos.')
        muestra_creacion_bdd()

def muestra_creacion_bdd():
    archivoSubido = st.file_uploader('Sube un archivo Excel (.xlsx, .xls)', type = ['xlsx', 'xls'], key = 'uploader_crear')
    
    if archivoSubido is not None:
        nombreBd = st.text_input('Nombre para la nueva base de datos (sin extensión):', value = 'nueva_base_datos')
        
        if st.button('Crear Base de Datos', type = 'primary'):
            if nombreBd:
                with st.spinner('Construyendo la base de datos, calculando grupos y asignando espacios. Esto puede tardar unos segundos...'):
                    exito, resultado = crea_bdd_excel(archivoSubido, nombreBd)
                    if exito:
                        st.success(f'Base de datos \'{os.path.basename(resultado)}\' creada y seleccionada exitosamente.')
                        st.session_state['bdActual'] = resultado 
                        guardar_bd_activa(resultado)
                        import time
                        time.sleep(2.0) 
                        st.rerun()
                    else:
                        st.error(f'Error al crear la base de datos: {resultado}')
            else:
                st.error('Por favor, introduce un nombre para la base de datos.')