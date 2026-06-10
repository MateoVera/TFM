import pandas as pd
import streamlit as st
import sqlite3
import plotly.express as px


diccionarioSiglas = {
    'GBIOLO30': 'BIO', 'GBIOQU30': 'BQ', 'GBIOTE30': 'BT',
    'GDFIIE30': 'FIE', 'GELECT30': 'IE', 'GFISIC30': 'FIS',
    'GGEOLO30': 'GEO', 'GINQUI30': 'IQ', 'GMATEM31': 'MAT',
    'GQUIMI30': 'QUIM'
}
siglasInvertidas = {v: k for k, v in diccionarioSiglas.items()}

def calcula_tamano_aula_ideal(conexion, periodoActivo):
    dfDist = pd.read_sql_query('SELECT Cod_Asignatura, ID_Agrupacion, Cod_Idioma, Tipo_Clase, Num_Grupo, Nombre_Oficial, Alumnos_Asignados FROM Distribucion_Grupos WHERE Cod_Periodo = ?', conexion, params = (periodoActivo,))
    dfMat = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Cod_Idioma, Matriculados FROM Matricula WHERE Cod_Periodo = ?', conexion, params = (periodoActivo,))
    dfAsig = pd.read_sql_query('SELECT Cod_Asignatura, Cod_Plan, Curso, Cuatrimestre FROM Asignatura_Grado_Dpto', conexion).drop_duplicates(subset = ['Cod_Asignatura', 'Cod_Plan'])

    if dfDist.empty:
        return pd.DataFrame()

    dfDist['Cod_Asignatura'] = dfDist['Cod_Asignatura'].astype(str).str.strip().str.replace('.0', '', regex = False)
    dfAsig['Cod_Asignatura'] = dfAsig['Cod_Asignatura'].astype(str).str.strip().str.replace('.0', '', regex = False)
    dfMat['Cod_Asignatura'] = dfMat['Cod_Asignatura'].astype(str).str.strip().str.replace('.0', '', regex = False)
    dfAsig['Cod_Plan'] = dfAsig['Cod_Plan'].astype(str).str.strip()

    def determinaAnfitrion(fila):
        nombre = str(fila['Nombre_Oficial']).strip()
        
        if pd.isna(fila['Nombre_Oficial']) or nombre == 'None' or ' ' not in nombre:
            agrupacion = str(fila['ID_Agrupacion']).strip()
            planes = agrupacion.split('_')
        else:
            parteSiglas = nombre.split(' ', 1)[1]
            siglas = parteSiglas.split('+')
            planes = [siglasInvertidas.get(s.strip(), s.strip()) for s in siglas]
            
        planAnfitrion = planes[0] if planes else None
        maxMatriculados = -1
        
        for p in planes:
            filaMat = dfMat[(dfMat['Cod_Asignatura'] == fila['Cod_Asignatura']) & 
                            (dfMat['Cod_Plan'] == p) & 
                            (dfMat['Cod_Idioma'] == fila['Cod_Idioma'])]
            if not filaMat.empty:
                valorMat = filaMat['Matriculados'].sum()
                if valorMat > maxMatriculados:
                    maxMatriculados = valorMat
                    planAnfitrion = p
        return planAnfitrion

    dfDist['Anf_Plan'] = dfDist.apply(determinaAnfitrion, axis = 1)

    dfFusionado = dfDist.merge(dfAsig, left_on = ['Cod_Asignatura', 'Anf_Plan'], right_on = ['Cod_Asignatura', 'Cod_Plan'], how = 'inner')

    dfFusionado['Curso'] = dfFusionado['Curso'].fillna('Sin Definir')
    dfFusionado['Cuatrimestre'] = dfFusionado['Cuatrimestre'].fillna('X')

    dfFusionado['Cuatrimestre_Clean'] = dfFusionado['Cuatrimestre'].astype(str).str.strip().str.upper()
    
    mascaraAnual = dfFusionado['Cuatrimestre_Clean'].isin(['A', '0', 'ANU', 'ANUAL'])
    
    dfAnuales = dfFusionado[mascaraAnual].copy()
    dfCuatrimestrales = dfFusionado[~mascaraAnual].copy()
    
    dfAnualesQ1 = dfAnuales.copy()
    dfAnualesQ1['Cuatrimestre'] = 'Primer cuatrimestre'
    dfAnualesQ2 = dfAnuales.copy()
    dfAnualesQ2['Cuatrimestre'] = 'Segundo cuatrimestre'
    
    dfFinalBruto = pd.concat([dfCuatrimestrales, dfAnualesQ1, dfAnualesQ2], ignore_index = True)

    dfFinalBruto['Alumnos_Asignados'] = pd.to_numeric(dfFinalBruto['Alumnos_Asignados'], errors = 'coerce').fillna(0)
    
    dfFinal = dfFinalBruto.groupby(['Anf_Plan', 'Curso', 'Cuatrimestre', 'Cod_Idioma'])['Alumnos_Asignados'].max().reset_index()
    
    dfFinal = dfFinal.rename(columns = {'Anf_Plan': 'Grado', 'Alumnos_Asignados': 'Aforo_Minimo_Aula'})
    dfFinal = dfFinal.sort_values(by = ['Grado', 'Curso', 'Cuatrimestre', 'Cod_Idioma'])
    
    return dfFinal


def muestra_pagina_analisis():
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

    st.markdown("<h1 style='text-align: center;'>Análisis y Logística de Espacios</h1>", unsafe_allow_html = True)
    
    if 'bdActual' not in st.session_state or not st.session_state['bdActual']:
        st.warning('Por favor, selecciona una base de datos en la página de Configuración antes de continuar.')
        return
        
    conexion = sqlite3.connect(st.session_state['bdActual'], timeout = 10.0)
    
    try:
        dfPeriodos = pd.read_sql_query('SELECT DISTINCT Cod_Periodo FROM Distribucion_Grupos', conexion)
        if dfPeriodos.empty:
            st.info('No hay datos de distribución generados. Ve a la pestaña de Cálculo de Grupos y autoriza los grupos primero.')
            return
            
        opcionesPeriodos = sorted(dfPeriodos['Cod_Periodo'].dropna().astype(str).tolist())
        
        if 'anaFiltPeriodo' not in st.session_state:
            st.session_state['anaFiltPeriodo'] = opcionesPeriodos[-1] if opcionesPeriodos else 'Todos'
        if st.session_state['anaFiltPeriodo'] not in opcionesPeriodos:
            st.session_state['anaFiltPeriodo'] = opcionesPeriodos[-1]
            
        periodoActivo = st.selectbox('Selecciona el Período Académico a analizar:', opcionesPeriodos, index = opcionesPeriodos.index(st.session_state['anaFiltPeriodo']), key = 'uiAnaPeriodo')
        st.session_state['anaFiltPeriodo'] = periodoActivo

        st.markdown('---')
        
        with st.spinner('Mapeando distribuciones físicas y evaluando aforos...'):
            dfAulasCompleto = calcula_tamano_aula_ideal(conexion, periodoActivo)
            
        if dfAulasCompleto.empty:
            st.info(f'No hay aulas calculadas para el período {periodoActivo}.')
            return

        st.subheader('Filtros Globales')
        
        if 'anaFiltGrado' not in st.session_state: st.session_state.anaFiltGrado = 'Todos'
        if 'anaFiltCurso' not in st.session_state: st.session_state.anaFiltCurso = 'Todos'
        if 'anaFiltCuat' not in st.session_state: st.session_state.anaFiltCuat = 'Todos'
        if 'anaFiltIdioma' not in st.session_state: st.session_state.anaFiltIdioma = 'Todos'

        gradoActual = st.session_state.anaFiltGrado
        cursoActual = st.session_state.anaFiltCurso
        cuatrimestreActual = st.session_state.anaFiltCuat
        idiomaActual = st.session_state.anaFiltIdioma

        def obtieneOpcionesAnalisis(columnaExcluida):
            dfTemporal = dfAulasCompleto.copy()
            if columnaExcluida != 'Grado' and gradoActual != 'Todos':
                dfTemporal = dfTemporal[dfTemporal['Grado'] == gradoActual]
            if columnaExcluida != 'Curso' and cursoActual != 'Todos':
                dfTemporal = dfTemporal[dfTemporal['Curso'].astype(str) == str(cursoActual)]
            if columnaExcluida != 'Cuatrimestre' and cuatrimestreActual != 'Todos':
                dfTemporal = dfTemporal[dfTemporal['Cuatrimestre'].astype(str) == str(cuatrimestreActual)]
            if columnaExcluida != 'Cod_Idioma' and idiomaActual != 'Todos':
                dfTemporal = dfTemporal[dfTemporal['Cod_Idioma'] == idiomaActual]
            return sorted(dfTemporal[columnaExcluida].dropna().astype(str).unique().tolist())

        opcionesGrado = ['Todos'] + obtieneOpcionesAnalisis('Grado')
        opcionesCurso = ['Todos'] + obtieneOpcionesAnalisis('Curso')
        opcionesCuatrimestre = ['Todos'] + obtieneOpcionesAnalisis('Cuatrimestre')
        opcionesIdioma = ['Todos'] + obtieneOpcionesAnalisis('Cod_Idioma')

        if str(gradoActual) not in opcionesGrado: gradoActual = 'Todos'; st.session_state.anaFiltGrado = 'Todos'
        if str(cursoActual) not in opcionesCurso: cursoActual = 'Todos'; st.session_state.anaFiltCurso = 'Todos'
        if str(cuatrimestreActual) not in opcionesCuatrimestre: cuatrimestreActual = 'Todos'; st.session_state.anaFiltCuat = 'Todos'
        if str(idiomaActual) not in opcionesIdioma: idiomaActual = 'Todos'; st.session_state.anaFiltIdioma = 'Todos'

        def actualizaGradoAnalisis(): st.session_state.anaFiltGrado = st.session_state.selAnaGrado
        def actualizaCursoAnalisis(): st.session_state.anaFiltCurso = st.session_state.selAnaCurso
        def actualizaCuatrimestreAnalisis(): st.session_state.anaFiltCuat = st.session_state.selAnaCuat
        def actualizaIdiomaAnalisis(): st.session_state.anaFiltIdioma = st.session_state.selAnaIdioma

        columna1, columna2, columna3, columna4 = st.columns(4)
        with columna1:
            st.selectbox('Grado', opcionesGrado, index = opcionesGrado.index(str(gradoActual)), key = 'selAnaGrado', on_change = actualizaGradoAnalisis)
        with columna2:
            st.selectbox('Curso', opcionesCurso, index = opcionesCurso.index(str(cursoActual)), key = 'selAnaCurso', on_change = actualizaCursoAnalisis)
        with columna3:
            st.selectbox('Cuatrimestre', opcionesCuatrimestre, index = opcionesCuatrimestre.index(str(cuatrimestreActual)), key = 'selAnaCuat', on_change = actualizaCuatrimestreAnalisis)
        with columna4:
            st.selectbox('Idioma', opcionesIdioma, index = opcionesIdioma.index(str(idiomaActual)), key = 'selAnaIdioma', on_change = actualizaIdiomaAnalisis)

        dfFiltrado = dfAulasCompleto.copy()
        if gradoActual != 'Todos': dfFiltrado = dfFiltrado[dfFiltrado['Grado'] == gradoActual]
        if cursoActual != 'Todos': dfFiltrado = dfFiltrado[dfFiltrado['Curso'].astype(str) == str(cursoActual)]
        if cuatrimestreActual != 'Todos': dfFiltrado = dfFiltrado[dfFiltrado['Cuatrimestre'].astype(str) == str(cuatrimestreActual)]
        if idiomaActual != 'Todos': dfFiltrado = dfFiltrado[dfFiltrado['Cod_Idioma'] == idiomaActual]

        st.info('**Logística Aplicada:** El aforo se asigna analizando los grupos físicos reales. Si dos grados comparten aula, la carga recae sobre el el grado que aporta más alumnos. Las anuales se tienen en cuenta para ambos cuatrimestres.')
        
        if dfFiltrado.empty:
            st.warning('No hay datos que coincidan con la combinación de filtros seleccionada.')
        else:
            st.markdown('### Visualización de Aforos Máximos')
            
            dfGrafico = dfFiltrado.copy()
            dfGrafico['Bloque'] = dfGrafico['Grado'] + ' | C' + dfGrafico['Curso'].astype(str) + ' | ' + dfGrafico['Cod_Idioma']
            dfGrafico['Cuatrimestre'] = dfGrafico['Cuatrimestre'].astype(str)
            
            try:
                import plotly.express as px
                
                figuraBarra = px.bar(
                    dfGrafico, 
                    x = 'Bloque', 
                    y = 'Aforo_Minimo_Aula', 
                    color = 'Cuatrimestre',
                    barmode = 'group',
                    text_auto = True, 
                    color_discrete_map = {'Primer cuatrimestre': '#636EFA', 'Segundo cuatrimestre': '#EF553B'},
                    labels = {'Aforo_Minimo_Aula': 'Aforo Mínimo Requerido', 'Bloque': 'Asignación (Grado | Curso | Idioma)'}
                )
                
                figuraBarra.update_layout(
                    title = {'text': 'Aforo Requerido por Bloque (Grado, Curso e Idioma) y Cuatrimestre', 'x': 0.5, 'xanchor': 'center'},
                    xaxis_tickangle = -45
                )
                
                st.plotly_chart(figuraBarra, use_container_width = True)
                
            except ImportError:
                st.warning('**Sugerencia visual:** Para ver el gráfico con barras agrupadas (lado a lado) y etiquetas interactivas, instala la librería Plotly abriendo la terminal y ejecutando: `pip install plotly`')
                st.bar_chart(data = dfGrafico, x = 'Bloque', y = 'Aforo_Minimo_Aula', color = 'Cuatrimestre')

            st.markdown('---')

            st.markdown('### Datos Detallados')
            st.dataframe(dfFiltrado, use_container_width = True, hide_index = True,
                         column_config = {
                             'Grado': st.column_config.TextColumn('Grado'),
                             'Curso': st.column_config.NumberColumn('Curso', format = '%d'),
                             'Cuatrimestre': st.column_config.TextColumn('Cuatrimestre'),
                             'Cod_Idioma': st.column_config.TextColumn('Idioma'),
                             'Aforo_Minimo_Aula': st.column_config.NumberColumn('Aforo Mínimo Aula', format = '%d')
                         })

    finally:
        conexion.close()