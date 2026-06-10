import streamlit as st

st.set_page_config(layout = 'wide')

from modules import menuApp

def main():
    menuApp.muestra_menu_principal()


if __name__ == '__main__':
    main()