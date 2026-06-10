import streamlit as st
import os
from modules import configBDD, calculoGrupos, analisis

def inicializa_estado():
    if 'bdActual' not in st.session_state:
        bdGuardada = configBDD.cargar_bd_activa()
        if bdGuardada:
            st.session_state['bdActual'] = bdGuardada

def muestra_barra_lateral():
    inicializa_estado()
    st.sidebar.title('Barra de navegación')
    st.sidebar.markdown('---')

    paginas = {
        'Página principal': 'principal',
        'Configuración de la base de datos': 'config',
        'Cálculo de grupos': 'calculo_grupos',
        'Análisis': 'analisis',
    }

    indiceActual = 0
    if 'paginaActual' in st.session_state:
        try:
            indiceActual = list(paginas.values()).index(st.session_state.paginaActual)
        except ValueError:
            indiceActual = 0

    paginaSeleccionada = st.sidebar.selectbox('Página', options = paginas.keys(), 
                    index = indiceActual)
    
    nuevaPagina = paginas[paginaSeleccionada]

    if 'paginaActual' not in st.session_state or st.session_state.paginaActual != nuevaPagina:
        st.session_state.paginaActual = nuevaPagina
        st.rerun()
        
    if st.session_state.paginaActual in ['calculo_grupos', 'analisis']:
        st.sidebar.markdown('---')
        if 'bdActual' in st.session_state and st.session_state['bdActual']:
            nombreBd = os.path.basename(st.session_state['bdActual'])
            st.sidebar.success(f"**Base de Datos activa:**\n\n`{nombreBd}`")
        else:
            st.sidebar.warning('**No hay ninguna base de datos activa.**')



def muestra_pantalla_principal():
    st.markdown("<h1 style='text-align: center'>Aplicación de Planificación Docente de la FCT</h1>", unsafe_allow_html = True)
    
    if 'bdActual' in st.session_state and st.session_state['bdActual']:
        nombreBd = os.path.basename(st.session_state['bdActual'])
        st.success(f"**Base de datos activa:** `{nombreBd}`")
    else:
        st.warning('**No hay ninguna base de datos activa.** Ve a **Configuración de la base de datos** para seleccionar o crear una.')

    st.markdown("""
                ### 📋 **Descripción General**

                Esta plataforma automatiza el cálculo de necesidades docentes, la distribución física de grupos y la estimación de aforos óptimos para las asignaturas de la Facultad de Ciencia y Tecnología (FCT), agilizando el proceso de planificación académica y la logística de espacios.
                """)
    

    
    st.markdown('---')

    st.markdown('### 🗺️ **Módulos de la Aplicación**')

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### 🗄️ **Configuración de Datos**
        Gestión del modelo de datos a partir de archivos Excel oficiales.
        
        - Creación y selección de bases de datos
        - Extracción e inyección de matrículas históricas
        - Actualización del plan docente
        """)

    with col2:
        st.markdown("""
        #### 🧮 **Cálculo de Grupos**
        Motor de distribución de alumnado por titulación e idioma.
        
        - Algoritmos de reparto equitativo de grupos
        - Ajuste dinámico de cupos de docencia
        - Consolidación y distribución física en aulas
        - Generación y descarga de la Tabla Azul oficial
        """)
        
    with col3:
        st.markdown("""
        #### 📊 **Análisis y Espacios**
        Herramientas de evaluación espacial y exportación de resultados.

        - Estimación visual de aforos mínimos requeridos
        - Análisis interactivo por grado, curso y cuatrimestre
        """)

    st.markdown('---')

    st.markdown("""
    ### 🚀 **Instrucciones de uso**

    1. **Inicia el entorno** seleccionando o creando una base de datos en *Configuración de la base de datos*.
    2. **Calcula y autoriza** los grupos propuestos por el sistema en *Cálculo de grupos*.
    3. **Visualiza la logística espacial** y descarga los documentos finales en la sección de *Análisis*.
    """, unsafe_allow_html = True)

    st.markdown("""
                <div style='text-align: center; color: #666; font-size: 0.9em; margin-top: 2rem;'>
                <p style='margin-bottom: 0.2em;'>Aplicación desarrollada por Mateo Vera Murillo</p>
                <p style='margin-top: 0.2em;'>Trabajo Fin de Máster</p>
                </div>
                """, unsafe_allow_html = True)

def muestra_menu_principal():
    muestra_barra_lateral()

    paginaActual = st.session_state.paginaActual

    if paginaActual == 'principal':
        muestra_pantalla_principal()

    elif paginaActual == 'config':
        configBDD.muestra_pagina_config()
        
    elif paginaActual == 'calculo_grupos':
        calculoGrupos.muestra_pagina_calculo()
    
    elif paginaActual == 'analisis':
        analisis.muestra_pagina_analisis()