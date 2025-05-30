import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup, Comment
import lxml

# Configuración general de la app
st.set_page_config(page_title="Análisis FBref - La Liga", page_icon="⚽", layout="wide")

# Título principal
st.title("📊 FBREF Scraper y Análisis de los Jugadores en La Liga 2024-25")


class LeagueManager:
    """
    Clase para gestionar ligas de fútbol y generar URLs de estadísticas de jugadores desde FBref.
    """
    def __init__(self):
        """
        Inicializa los atributos necesarios para acceder a las ligas, temporadas y tipos de estadísticas disponibles.
        """
        self.base_url = "https://fbref.com/en/comps/"
        # Diccionario con ligas disponibles, cada una con su ID, slug para la URL y temporadas disponibles
        self.possible_leagues = {
            'Fbref': {
                'Premier League': {
                    'id': 9,
                    'slug': 'Premier-League',
                    'seasons': ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021']
                },
                'La Liga': {
                    'id': 12,
                    'slug': 'La-Liga',
                    'seasons': ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021']
                },
                'Ligue 1': {
                    'id': 13,
                    'slug': 'Ligue-1',
                    'seasons': ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021']    
                },
                'Bundesliga': {
                    'id': 20,
                    'slug': 'Bundesliga',
                    'seasons': ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021']
                },
                'Serie A': {
                    'id': 11,
                    'slug': 'Serie-A',
                    'seasons': ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021']
                },
                'Big 5 European Leagues': {
                    'id': 'Big5',
                    'slug': 'Big-5-European-Leagues',
                    'seasons': ['2024-2025', '2023-2024', '2022-2023', '2021-2022', '2020-2021']
                },
            }
        }

        # Tipos de estadísticas disponibles para jugadores
        self.player_tables = {
            "Standard Stats": "stats/players",
            "Goalkeeping": "keepers/players",
            "Advanced Goalkeeping": "keepersadv/players",
            "Shooting": "shooting/players",
            "Passing": "passing/players",
            "Pass Types": "passing_types/players",
            "Goal and Shot Creation": "gca/players",
            "Defensive Actions": "defense/players",
            "Possession": "possession/players",
            "Playing Time": "playingtime/players",
            "Miscellaneous Stats": "misc/players",
        }

    def get_available_leagues(self):
        """
        Devuelve un diccionario con las ligas disponibles, sus identificadores y temporadas.

        Return:
            dict: Ligas disponibles con su ID y temporadas.
        """
        return {
            league_name: {
                'id': data['id'],
                'seasons': data['seasons']
            }
            for league_name, data in self.possible_leagues['Fbref'].items()
        }

    def get_league_info(self, league_name):
        """
        Devuelve la información de una liga específica.

        Args:
            league_name (str): Nombre de la liga.

        Return:
            dict or None: Información de la liga seleccionada (id, slug, seasons) o None si no existe.
        """
        return self.possible_leagues['Fbref'].get(league_name)

    def get_all_league_names(self):
        """
        Devuelve la lista de nombres de todas las ligas disponibles.

        Return:
            list: Nombres de las ligas.
        """
        return list(self.possible_leagues['Fbref'].keys())

    def generate_player_urls(self):
        """
        Genera URLs completas para acceder a estadísticas de jugadores por liga, temporada y tipo de estadística.

        Return:
            dict: Diccionario anidado con URLs organizadas por liga y temporada.
                  Formato: {liga: {temporada: {tipo_estadistica: url}}}
        """
        urls = {}

        for league_name, league_data in self.possible_leagues['Fbref'].items():
            league_id = league_data['id']
            seasons = league_data['seasons']
            urls[league_name] = {}

            for season in seasons:
                season_urls = {}
                for stat_name, path in self.player_tables.items():
                    url = (
                        f"{self.base_url}{league_id}/{path}/{season}/"
                        f"{league_name.replace(' ', '-')}-Stats"
                    )
                    season_urls[stat_name] = url

                urls[league_name][season] = season_urls

        return urls

def format_dataframe_columns(df, stat_category):
    """
    Reformatea las columnas de un DataFrame eliminando los niveles de índice
    y añadiendo un sufijo basado en la estadística.

    Args:
        df (pd.DataFrame): El DataFrame original con columnas multinivel.
        stat_category (str): La estadística que se añadirá como sufijo a las columnas.

    Returns:
        pd.DataFrame: El DataFrame con columnas reformateadas.
    """
    # Verifica si las columnas del DataFrame tienen múltiples niveles (MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        # Si tienen múltiples niveles, crea nombres planos combinando el segundo nivel (nombre de columna)
        # con el primero (categoría), junto con el sufijo proporcionado por stat_category
        df.columns = [f"{col[1]} ({col[0]} - {stat_category})" for col in df.columns]
    else:
        # Si las columnas no son multinivel, simplemente añade el sufijo con stat_category a cada nombre
        df.columns = [f"{col} ({stat_category})" for col in df.columns]
    # Devuelve el DataFrame con los nuevos nombres de columnas
    return df

def formatear_datos(df):
    """
    Renombra las columnas de un DataFrame de estadísticas futbolísticas avanzadas 
    obtenidas de FBref, mapeando los nombres técnicos largos a versiones más comprensibles en español.
    Posteriormente se hace la limpieza de las columnas para que sean más legibles y útiles.
    Args:
        df (pd.DataFrame): DataFrame con las estadísticas originales de FBref.
    Returns:
        pd.DataFrame: DataFrame con las columnas renombradas y procesadas.

    """
    mapeo_columns= {
    'Player (Unnamed: 1_level_0 - Standard Stats)': 'Player',
    'Nation (Unnamed: 2_level_0 - Standard Stats)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Standard Stats)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Standard Stats)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Standard Stats)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Standard Stats)': 'Edad',
    'Born (Unnamed: 7_level_0 - Standard Stats)': 'Nacimiento',
    'MP (Playing Time - Standard Stats)': 'Partidos jugados',
    'Starts (Playing Time - Standard Stats)': 'Alineaciones',
    'Min (Playing Time - Standard Stats)': 'Minutos jugados',
    '90s (Playing Time - Standard Stats)': 'Minutos jugados/90',
    'Gls (Performance - Standard Stats)': 'Goles',
    'Ast (Performance - Standard Stats)':'Asistencias',
    'G+A (Performance - Standard Stats)': 'Goles + Asistencias',
    'G-PK (Performance - Standard Stats)': 'Goles sin penaltis',
    'PK (Performance - Standard Stats)': 'Penalits creados',
    'PKatt (Performance - Standard Stats)': 'Penaltis intentados',
    'CrdY (Performance - Standard Stats)': 'Tarjetas amarillas',
    'CrdR (Performance - Standard Stats)': 'Tarjetas rojas',
    'xG (Expected - Standard Stats)': 'xG',
    'npxG (Expected - Standard Stats)': 'xG sin penaltis',
    'xAG (Expected - Standard Stats)': 'xAG',
    'npxG+xAG (Expected - Standard Stats)': 'xG + xAG sin penaltis',
    'PrgC (Progression - Standard Stats)': 'Acarreos progresivos',
    'PrgP (Progression - Standard Stats)': 'Pases progresivos',
    'PrgR (Progression - Standard Stats)': 'Pases recividos progresivos',
    'Gls (Per 90 Minutes - Standard Stats)': 'Goles/90',
    'Ast (Per 90 Minutes - Standard Stats)':' Asistencias/90',
    'G+A (Per 90 Minutes - Standard Stats)': 'Goles + Asistencias/90',
    'G-PK (Per 90 Minutes - Standard Stats)': 'Goles sin penaltis/90',
    'G+A-PK (Per 90 Minutes - Standard Stats)': 'Goles + Asistencias sin penaltis/90',
    'xG (Per 90 Minutes - Standard Stats)': 'xG/90',
    'xAG (Per 90 Minutes - Standard Stats)': 'xAG/90',
    'xG+xAG (Per 90 Minutes - Standard Stats)': 'xG+xAG/90',
    'npxG (Per 90 Minutes - Standard Stats)': 'xG sin penaltis/90',
    'npxG+xAG (Per 90 Minutes - Standard Stats)': 'xG + xAG sin penalits/90',
    
    'Player (Unnamed: 1_level_0 - Shooting)': 'Player',
    'Nation (Unnamed: 2_level_0 - Shooting)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Shooting)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Shooting)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Shooting)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Shooting)': 'Edad',
    'Born (Unnamed: 7_level_0 - Shooting)':'Año',
    '90s (Unnamed: 8_level_0 - Shooting)': 'Minutos jugados/90', 'Gls (Standard - Shooting)': 'Goles',
    'Sh (Standard - Shooting)': 'Tiros totales', 'SoT (Standard - Shooting)': 'Tiros a puerta',
    'SoT% (Standard - Shooting)': '% Tiros a puerta', 'Sh/90 (Standard - Shooting)': 'Tiros totales/90',
    'SoT/90 (Standard - Shooting)': 'Tiros a puerta/90', 'G/Sh (Standard - Shooting)': 'Goles/Tiros totales' ,
    'G/SoT (Standard - Shooting)': 'Goles/Tiros a puerta', 'Dist (Standard - Shooting)': 'Distancia promedio tiros',
    'FK (Standard - Shooting)': 'Tiros libres', 'PK (Standard - Shooting)': 'Penaltis anotados',
    'PKatt (Standard - Shooting)': 'Penaltis intentados', 'xG (Expected - Shooting)': 'xG',
    'npxG (Expected - Shooting)': 'xG sin penaltis', 'npxG/Sh (Expected - Shooting)': 'xG sin penaltis/Tiros totales',
    'G-xG (Expected - Shooting)': 'Goles-xG', 'np:G-xG (Expected - Shooting)':'Goles sin penaltis/xG',
    
    'Player (Unnamed: 1_level_0 - Passing)':'Player',
    'Nation (Unnamed: 2_level_0 - Passing)':'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Passing)':'Posicion',
    'Squad (Unnamed: 4_level_0 - Passing)':'Equipo',
    'Comp (Unnamed: 5_level_0 - Passing)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Passing)': 'Edad',
    'Born (Unnamed: 7_level_0 - Passing)': 'Año',
    '90s (Unnamed: 8_level_0 - Passing)': 'Minutos jugados/90', 'Cmp (Total - Passing)': 'Pases completados',
    'Att (Total - Passing)': 'Pases intentados', 'Cmp% (Total - Passing)': '% Pases completados',
    'TotDist (Total - Passing)': 'Distancia total pases', 'PrgDist (Total - Passing)': 'Distancia pases progresivos',
    'Cmp (Short - Passing)': 'Pases cortos completados', 'Att (Short - Passing)': 'Pases cortos intentados',
    'Cmp% (Short - Passing)': '% pases cortos completados', 'Cmp (Medium - Passing)':'Pases medios completados',
    'Att (Medium - Passing)':'Pases medios intentados', 'Cmp% (Medium - Passing)':'% pases medios completados',
    'Cmp (Long - Passing)':'Pases largos completados', 'Att (Long - Passing)':'Pases largos intentados', 'Cmp% (Long - Passing)':'% pases largos completados',
    'Ast (Unnamed: 23_level_0 - Passing)':'Asistencias',
    'xAG (Unnamed: 24_level_0 - Passing)': 'xAG', 'xA (Expected - Passing)': 'xA',
    'A-xAG (Expected - Passing)': 'Asistencias-xAG', 'KP (Unnamed: 27_level_0 - Passing)': 'Pases clave',
    '1/3 (Unnamed: 28_level_0 - Passing)':'Pases último tercio campo',
    'PPA (Unnamed: 29_level_0 - Passing)': 'Pases área de penalti',
    'CrsPA (Unnamed: 30_level_0 - Passing)': 'Centros área de penalti',
    'PrgP (Unnamed: 31_level_0 - Passing)': 'Pases progresivos',
    
    'Player (Unnamed: 1_level_0 - Pass Types)': 'Player',
    'Nation (Unnamed: 2_level_0 - Pass Types)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Pass Types)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Pass Types)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Pass Types)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Pass Types)': 'Edad',
    'Born (Unnamed: 7_level_0 - Pass Types)': 'Año',
    '90s (Unnamed: 8_level_0 - Pass Types)':'Minutos jugados/90',
    'Att (Unnamed: 9_level_0 - Pass Types)': 'Pases intentados',
    'Live (Pass Types - Pass Types)': 'Pases balón vivo', 'Dead (Pass Types - Pass Types)': 'Pases balón muerto',
    'FK (Pass Types - Pass Types)': 'Pases de tiros libres', 'TB (Pass Types - Pass Types)':'Pases largos',
    'Sw (Pass Types - Pass Types)':'Cambios de juego (pases)', 'Crs (Pass Types - Pass Types)':'Pases cruzados',
    'TI (Pass Types - Pass Types)':'Saques de banda', 'CK (Pass Types - Pass Types)':'Saques esquina',
    'In (Corner Kicks - Pass Types)':'Saques esquina hacia dentro', 'Out (Corner Kicks - Pass Types)':'Saques de esquina hacia fuera',
    'Str (Corner Kicks - Pass Types)':'Saques de esquina rectos', 'Cmp (Outcomes - Pass Types)':'Pases completados',
    'Off (Outcomes - Pass Types)': 'Pases fuera de juego', 'Blocks (Outcomes - Pass Types)': 'Pases bloqueados',
    
    'Player (Unnamed: 1_level_0 - Goal and Shot Creation)': 'Player',
    'Nation (Unnamed: 2_level_0 - Goal and Shot Creation)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Goal and Shot Creation)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Goal and Shot Creation)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Goal and Shot Creation)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Goal and Shot Creation)': 'Edad',
    'Born (Unnamed: 7_level_0 - Goal and Shot Creation)': 'Año',
    '90s (Unnamed: 8_level_0 - Goal and Shot Creation)': 'Minutos jugados/90',
    'SCA (SCA - Goal and Shot Creation)': 'Acciones creadores de tiros',
    'SCA90 (SCA - Goal and Shot Creation)':'Acciones creadores de tiros/90',
    'PassLive (SCA Types - Goal and Shot Creation)': 'SCA (Pases de balón vivo)',
    'PassDead (SCA Types - Goal and Shot Creation)': 'SCA (Pases de balón muerto)',
    'TO (SCA Types - Goal and Shot Creation)': 'SCA (Toma)',
    'Sh (SCA Types - Goal and Shot Creation)': 'SCA (Tiros)',
    'Fld (SCA Types - Goal and Shot Creation)': 'SCA (Faltas recibidas)',
    'Def (SCA Types - Goal and Shot Creation)': 'SCA (Acción defensiva)',
    'GCA (GCA - Goal and Shot Creation)':'Acciones creadores de goles',
    'GCA90 (GCA - Goal and Shot Creation)':'Acciones creadores de goles/90',
    'PassLive (GCA Types - Goal and Shot Creation)':'GCA (Pases de balón vivos)',
    'PassDead (GCA Types - Goal and Shot Creation)':'GCA (Pases de balón muerto)',
    'TO (GCA Types - Goal and Shot Creation)':'GCA (Toma)',
    'Sh (GCA Types - Goal and Shot Creation)':'GCA (Tiros)',
    'Fld (GCA Types - Goal and Shot Creation)': 'GCA (Faltas recibidas)',
    'Def (GCA Types - Goal and Shot Creation)':'GCA (Acción defensiva)',

    'Player (Unnamed: 1_level_0 - Defensive Actions)': 'Player',
    'Nation (Unnamed: 2_level_0 - Defensive Actions)':'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Defensive Actions)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Defensive Actions)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Defensive Actions)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Defensive Actions)': 'Edad',
    'Born (Unnamed: 7_level_0 - Defensive Actions)': 'Año',
    '90s (Unnamed: 8_level_0 - Defensive Actions)': 'Minutos jugados/90',
    'Tkl (Tackles - Defensive Actions)': 'Derribos',
    'TklW (Tackles - Defensive Actions)': 'Derribos ganados',
    'Def 3rd (Tackles - Defensive Actions)': 'Derribos (Def 3rd)',
    'Mid 3rd (Tackles - Defensive Actions)':'Derribos (Mid 3rd)',
    'Att 3rd (Tackles - Defensive Actions)':'Derribos (Att 3rd)',
    'Tkl (Challenges - Defensive Actions)': 'Regateadores tackleados',
    'Att (Challenges - Defensive Actions)': 'Regateos intentados',
    'Tkl% (Challenges - Defensive Actions)': '% Dribladorees derribados',
    'Lost (Challenges - Defensive Actions)': 'Desafios perdidos',
    'Blocks (Blocks - Defensive Actions)': 'Bloqueos',
    'Sh (Blocks - Defensive Actions)': 'Tiros bloqueados', 'Pass (Blocks - Defensive Actions)':'Pases bloqueados',
    'Int (Unnamed: 21_level_0 - Defensive Actions)': 'Intercepciones',
    'Tkl+Int (Unnamed: 22_level_0 - Defensive Actions)':'Derribos + Intercepciones',
    'Clr (Unnamed: 23_level_0 - Defensive Actions)': 'Despejes',
    'Err (Unnamed: 24_level_0 - Defensive Actions)': 'Errores defensivos',

    'Player (Unnamed: 1_level_0 - Possession)': 'Player',
    'Nation (Unnamed: 2_level_0 - Possession)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Possession)':'Posicion',
    'Squad (Unnamed: 4_level_0 - Possession)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Possession)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Possession)': 'Edad',
    'Born (Unnamed: 7_level_0 - Possession)':'Año',
    '90s (Unnamed: 8_level_0 - Possession)': 'Minutos jugados/90',
    'Touches (Touches - Possession)': 'Toques', 'Def Pen (Touches - Possession)': 'Toques (Def pen)',
    'Def 3rd (Touches - Possession)':'Toques (Def 3rd)', 'Mid 3rd (Touches - Possession)':'Toques (Mid 3rd)',
    'Att 3rd (Touches - Possession)':'Toques (Att 3rd)', 'Att Pen (Touches - Possession)':'Toques (Att pen)',
    'Live (Touches - Possession)': 'Toques (Pelota activa)', 'Att (Take-Ons - Possession)': 'Tomas Intentados',
    'Succ (Take-Ons - Possession)': 'Tomas exitosas', 'Succ% (Take-Ons - Possession)': '% Tomas exitosas',
    'Tkld (Take-Ons - Possession)' :'Veces regateos', 'Tkld% (Take-Ons - Possession)' : '% veces regateos',
    'Carries (Carries - Possession)': 'Total de transportes balón', 'TotDist (Carries - Possession)': 'Distancia total trasporte balón',
    'PrgDist (Carries - Possession)': 'Distancia trasporte balón progresivo', 'PrgC (Carries - Possession)': 'Acarreos progresivos',
    '1/3 (Carries - Possession)': 'Transporte balón último tercio', 'CPA (Carries - Possession)': 'Transporte balón area penalti',
    'Mis (Carries - Possession)': 'Errores de control balón', 'Dis (Carries - Possession)': 'Desposeido del balón',
    'Rec (Receiving - Possession)': 'Pases recibidos' , 'PrgR (Receiving - Possession)': 'Pases progresivos recibidos',

    'Player (Unnamed: 1_level_0 - Miscellaneous Stats)': 'Player',
    'Nation (Unnamed: 2_level_0 - Miscellaneous Stats)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Miscellaneous Stats)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Miscellaneous Stats)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Miscellaneous Stats)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Miscellaneous Stats)': 'Edad',
    'Born (Unnamed: 7_level_0 - Miscellaneous Stats)': 'Año',
    '90s (Unnamed: 8_level_0 - Miscellaneous Stats)': 'Minutos jugados/90',
    'CrdY (Performance - Miscellaneous Stats)': 'Tarjetas amarillas',
    'CrdR (Performance - Miscellaneous Stats)': 'Tarjetas rojas',
    '2CrdY (Performance - Miscellaneous Stats)': 'Segunda tarjeta amarilla',
    'Fls (Performance - Miscellaneous Stats)': 'Faltas cometidas',
    'Fld (Performance - Miscellaneous Stats)': 'Faltas recibidas',
    'Off (Performance - Miscellaneous Stats)': 'Posicion adelantada (fuera de juego)',
    'Crs (Performance - Miscellaneous Stats)': 'Pases cruzados',
    'Int (Performance - Miscellaneous Stats)': 'Intercepciones',
    'TklW (Performance - Miscellaneous Stats)':'Derribos ganados',
    'PKwon (Performance - Miscellaneous Stats)': 'Penaltis ejecutados',
    'PKcon (Performance - Miscellaneous Stats)': 'Penaltis concedidos',
    'OG (Performance - Miscellaneous Stats)': 'Goles en propia',
    'Recov (Performance - Miscellaneous Stats)': 'Recuperaciones',
    'Won (Aerial Duels - Miscellaneous Stats)': 'Duelos aéreos ganados',
    'Lost (Aerial Duels - Miscellaneous Stats)':'Duelos aéreos perdidos',
    'Won% (Aerial Duels - Miscellaneous Stats)':'% Duelos aéreos ganados',

    'Player (Unnamed: 1_level_0 - Playing Time)': 'Player',
    'Nation (Unnamed: 2_level_0 - Playing Time)':'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Playing Time)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Playing Time)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Playing Time)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Playing Time)': 'Edad',
    'Born (Unnamed: 7_level_0 - Playing Time)': 'Año',
    'MP (Playing Time - Playing Time)': 'Partidos jugados', 'Min (Playing Time - Playing Time)': 'Minutos jugados',
    'Mn/MP (Playing Time - Playing Time)': 'Minutos jugados/Partidos jugados',
    'Min% (Playing Time - Playing Time)': '% Minutos jugados',
    '90s (Playing Time - Playing Time)': 'Minutos jugados/90', 'Starts (Starts - Playing Time)': 'Alineaciones',
    'Mn/Start (Starts - Playing Time)': 'Minutos jugados/Alineaciones', 'Compl (Starts - Playing Time)': 'Partidos completos',
    'Subs (Subs - Playing Time)': 'Partidos suplente', 'Mn/Sub (Subs - Playing Time)': 'Minutos jugados/Partidos suplente',
    'unSub (Subs - Playing Time)': 'Partidos suplente pero no sale', 'PPM (Team Success - Playing Time)': 'Puntos por partido aportado al equipo',
    'onG (Team Success - Playing Time)': 'Goles marcados equipo en él',
    'onGA (Team Success - Playing Time)': 'Goles permitidos equipo con él',
    '+/- (Team Success - Playing Time)':'Goles marcados-Goles permitidos equipo en él',
    '+/-90 (Team Success - Playing Time)':'Goles marcados-Goles permitidos equipo en él/90',
    'On-Off (Team Success - Playing Time)':'Goles neto/90 jugador dentro-fuera campo',
    'onxG (Team Success (xG) - Playing Time)':'xG marcados equipo en él',
    'onxGA (Team Success (xG) - Playing Time)':'xGA marcados equipo en él',
    'xG+/- (Team Success (xG) - Playing Time)':'xG marcados-xGA permitidos equipo en él',
    'xG+/-90 (Team Success (xG) - Playing Time)':'xG marcados-xGA permitidos equipo en él',
    'On-Off (Team Success (xG) - Playing Time)': 'xG neto/90 jugador dentro-fuera campo',

       
    

    'Player (Unnamed: 1_level_0 - Goalkeeping)': 'Player',
    'Nation (Unnamed: 2_level_0 - Goalkeeping)': 'Nacionalidad',
    'Pos (Unnamed: 3_level_0 - Goalkeeping)': 'Posicion',
    'Squad (Unnamed: 4_level_0 - Goalkeeping)': 'Equipo',
    'Comp (Unnamed: 5_level_0 - Goalkeeping)': 'Competicion',
    'Age (Unnamed: 6_level_0 - Goalkeeping)': 'Edad',
    'Born (Unnamed: 7_level_0 - Goalkeeping)': 'Año',
    'MP (Playing Time - Goalkeeping)':'Partidos jugados',
    'Starts (Playing Time - Goalkeeping)': 'Alineaciones',
    'Min (Playing Time - Goalkeeping)':'Minutos jugados',
    '90s (Unnamed: 11_level_0 - Goalkeeping)':'Minutos jugados/90',
    'GA (Performance - Goalkeeping)':'Goles encajados' , 'GA90 (Performance - Goalkeeping)': 'Goles ecajados/90',
    'SoTA (Performance - Goalkeeping)':'Tiros puerta recibidos', 'Saves (Performance - Goalkeeping)':'Paradas',
    'Save% (Performance - Goalkeeping)':'% Paradas', 'W (Performance - Goalkeeping)':'Partidos ganados',
    'D (Performance - Goalkeeping)':'Partidos empatados', 'L (Performance - Goalkeeping)':'Partidos perdidos',
    'CS (Performance - Goalkeeping)':'Porteria a cero', 'CS% (Performance - Goalkeeping)':'% Porteria a cero',
    'PKatt (Penalty Kicks - Goalkeeping)':'Pentaltis provocados',
    'PKA (Penalty Kicks - Goalkeeping)':'Penalti encajado',
    'PKsv (Penalty Kicks - Goalkeeping)':'Penaltis parados',
    'PKm (Penalty Kicks - Goalkeeping)':'Penaltis fallados',
    'Save% (Penalty Kicks - Goalkeeping)':'% Penaltis parados',

       'Player (Unnamed: 1_level_0 - Advanced Goalkeeping)': 'Player',
       'Nation (Unnamed: 2_level_0 - Advanced Goalkeeping)': 'Nacionalidad',
       'Pos (Unnamed: 3_level_0 - Advanced Goalkeeping)': 'Posicion',
       'Squad (Unnamed: 4_level_0 - Advanced Goalkeeping)': 'Equipo',
       'Comp (Unnamed: 5_level_0 - Advanced Goalkeeping)': 'Competicion',
       'Age (Unnamed: 6_level_0 - Advanced Goalkeeping)': 'Edad',
       'Born (Unnamed: 7_level_0 - Advanced Goalkeeping)': 'Año',
       '90s (Unnamed: 8_level_0 - Advanced Goalkeeping)': 'Minutos jugados/90' ,
       'GA (Goals - Advanced Goalkeeping)':'Goles encajados',
       'PKA (Goals - Advanced Goalkeeping)':'Penaltis encajados',
       'FK (Goals - Advanced Goalkeeping)':'Tiros libres encajados',
       'CK (Goals - Advanced Goalkeeping)':'Corners encajados',
       'OG (Goals - Advanced Goalkeeping)':'Goles propia meta' ,
       'PSxG (Expected - Advanced Goalkeeping)':'xGOT recibido',
       'PSxG/SoT (Expected - Advanced Goalkeeping)':'xGOT recibido/Tiro a puerta',
       'PSxG+/- (Expected - Advanced Goalkeeping)':'xGOT recibido-Goles encajados',
       '/90 (Expected - Advanced Goalkeeping)':'xGOT recibido-Goles encajados/90',
       'Cmp (Launched - Advanced Goalkeeping)':'Pases largos',
       'Att (Launched - Advanced Goalkeeping)':'Pases largos exito',
       'Cmp% (Launched - Advanced Goalkeeping)':'% Pases largos exito',
       'Att (GK) (Passes - Advanced Goalkeeping)':'Pases de portero ',
       'Thr (Passes - Advanced Goalkeeping)':'Lanzamientos',
       'Launch% (Passes - Advanced Goalkeeping)':'% pases portero completados',
       'AvgLen (Passes - Advanced Goalkeeping)':'Promedio distancia pases',
       'Att (Goal Kicks - Advanced Goalkeeping)':'Tiros de puerta',
       'Launch% (Goal Kicks - Advanced Goalkeeping)':'% Tiros puerta completados',
       'AvgLen (Goal Kicks - Advanced Goalkeeping)':'Promedio distancia tiros puerta',
       'Opp (Crosses - Advanced Goalkeeping)':'Centros oponentes intentados',
       'Stp (Crosses - Advanced Goalkeeping)': 'Centros detenidos',
       'Stp% (Crosses - Advanced Goalkeeping)':'% Centros detenidos',
       '#OPA (Sweeper - Advanced Goalkeeping)':'Acciones defensivas fuera area penalti',
       '#OPA/90 (Sweeper - Advanced Goalkeeping)':'Acciones defensivas fuera area penalti/90',
       'AvgDist (Sweeper - Advanced Goalkeeping)':'Promedio de distancia Acc. def. fuera area penalti'  
       
        }
    df.columns = [mapeo_columns[col] if col in mapeo_columns else col for col in df.columns]

    
    # Procesar columnas después de renombrarlas
    if 'Nacionalidad' in df.columns:
        # Extraer la nacionalidad de la columna 'Nacionalidad'
        df["Nacionalidad"] = df["Nacionalidad"].astype(str).str.extract(r'([A-Z]+)$')
    if "Edad" in df.columns:
    # Extraer la edad de la columna 'Edad' y convertirla a string
        df["Edad"] = df["Edad"].astype(str).str.split('-').str[0]
    if "Competicion" in df.columns:
        # Extraer la competición de la columna 'Competicion'
        df["Competicion"] = df["Competicion"].astype(str).str.extract(r'\s(.+)')

    return df

def procesar_posiciones(df, columna='Posicion'):
    """
    Procesa la columna de posiciones dividiéndola en 'Posicion_principal' y 'Posicion_2',
    y reemplaza las abreviaturas por nombres completos.

    Args:
        df (pd.DataFrame): DataFrame que contiene la columna de posiciones.
        columna (str): Nombre de la columna a procesar (por defecto 'Posicion').

    Returns:
        pd.DataFrame: DataFrame con columnas 'Posicion_principal' y 'Posicion_2' añadidas,
                      y la columna original eliminada.
    """
    # Diccionario de reemplazo
    mapping = {
        'MF': 'Midfielder',
        'DF': 'Defender',
        'FW': 'Forward',
        'GK': 'Goalkeeper'
    }

    df = df.copy()

    # Separar y mapear
    df['Posicion_principal'] = df[columna].str[:2].replace(mapping)
    df['Posicion_2'] = df[columna].str[3:].replace(mapping)

    # Eliminar columna original
    df = df.drop(columns=[columna])

    return df

#Llamada a la clase LeagueManager para generar URLs de jugadores
manager = LeagueManager()
player_urls = manager.generate_player_urls()
# Ver las URLs de La Liga 2024-2025
for stat, url in player_urls['La Liga']['2024-2025'].items():
    print(stat, "->", url)


def scrape_stats_player(league ='Premier League', season= '2024-2025',stat= 'Goalkeeping',team_type="players"):
    
     # Accedemos al diccionario de URLs
    league_data = player_urls[league]
        
    # Verificamos si la temporada existe en la liga
    if season not in league_data:
        raise ValueError(f"La temporada '{season}' no está disponible para la liga '{league}'.")

    # Accedemos a las URLs de la temporada
    season_data = league_data[season]

    # Devolvemos la URL correspondiente
    return season_data[stat]


def extract_tables(league='La Liga', season='2024-2025', stat='Goalkeeping', save_excel=False):
    """
    Extrae las tablas de estadísticas de FBRef.

    Args:
        league (str): Liga a extraer (ejemplo: 'Big 5 European Leagues').
        season (str): Temporada específica.
        stat (str): Tipo de estadística.
        team_type (str): Tipo de datos ('players', 'teams', etc.).
        save_excel (bool): Si se debe guardar el DataFrame como un archivo Excel.

    Return:
        tuple: DataFrame con los datos extraídos y la URL de origen.
    """
    # Iniciar `df` y `url` por defecto como None
    df = None
    url = None

    # Obtener la URL usando la función `scrape_stats_player`
    try:
        url = scrape_stats_player(league, season, stat)
        if not url:
            print("❌ No se pudo generar la URL.")
            return df, url
        print(f"URL generada: {url}")
    except Exception as e:
        print(f"Error al obtener la URL: {e}")
        return df, url  # Aseguramos que se devuelvan None si hay error

    # Intentar leer las tablas visibles con pandas.read_html
    try:
        tables = pd.read_html(url)

        if "Big5" in url and tables:
            print(f"Scraping datos de {stat} desde FBRef...")
            df = tables[0].fillna(0)

            # Reformatear columnas
            df = format_dataframe_columns(df, stat)
            df = df[df.iloc[:, 0] != 'Rk'].reset_index(drop=True)
            df = df.loc[:, ~df.columns.str.contains('matches', case=False)]
            df = df.loc[:, ~df.columns.str.contains('Rk', case=False)]

            return df, url  # ⬅ Devuelve correctamente el DataFrame y la URL

    except Exception as e:
        print(f"Error con pandas.read_html: {e}")
        return df, url  # En caso de error, retorna `df` como None

    # 🔹 Si `read_html` falla, intenta con BeautifulSoup
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        comment_tables = soup.find_all(string=lambda t: isinstance(t, Comment))
        comment_table = None
        for c in comment_tables:
            if '<div class="table_container"' in c:
                comment_table = c
                break

        if not comment_table:
            raise ValueError("No se encontró ninguna tabla en comentarios.")

        # Parsear HTML dentro del comentario
        comment_html = BeautifulSoup(comment_table, 'html.parser')
        table = comment_html.find('table')
        if not table:
            raise ValueError("No se encontró una tabla en el HTML.")

        # Extraer datos
        headings = [th.get_text() for th in table.find_all("th", scope="col")]
        data = []
        for row in table.find('tbody').find_all('tr'):
            cols = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
            data.append(cols)

        df = pd.DataFrame(data, columns=headings).fillna(0).reset_index(drop=True)

        # Agregar la columna 'Comp' si no es "Big 5 European Leagues"
        if league != 'Big 5 European Leagues':
            df.insert(4, 'Comp', [league] * len(df))

        # Reformatear columnas
        df = format_dataframe_columns(df, stat)
        df = df[df.iloc[:, 0] != 'Rk'].reset_index(drop=True)
        df = df.loc[:, ~df.columns.str.contains('matches', case=False)]
        df = df.loc[:, ~df.columns.str.contains('Rk', case=False)]

        if save_excel:
            df.to_excel(f'{league} - {season} - {stat} - player stats.xlsx')

        return df, url  # ⬅ Devuelve correctamente el DataFrame y la URL

    except Exception as e:
        print(f"Error con BeautifulSoup: {e}")
        return df, url  # Devuelve `df` como None si hubo error, pero mantiene la URL
    
@st.cache_data
def obtener_foramtear_playingtime_jugadores(league='Big 5 European Leagues', season="2024-2025", stat="Playing Time"):
    """
    Obtiene y formatea la tabla de 'Playing Time' (tiempo de juego) de jugadores 
    desde la fuente especificada para una temporada y liga determinadas.
    
    Args:
        league (str): Liga de la que se extraerán los datos.
        season (str): Temporada de la que se extraerán los datos.
        stat (str): Tipo de estadística a extraer, en este caso "Playing Time".
        
    Return:
        pd.DataFrame: DataFrame con los datos de tiempo de juego de los jugadores, 
                      filtrado para incluir solo aquellos con al menos 1 minuto jugado.
    """
    
    df_playingtime, url_playingtime_j = extract_tables(league='Big 5 European Leagues', season="2024-2025", stat="Playing Time")
    df_playingtime.loc[:, 'MP (Playing Time - Playing Time)'] = pd.to_numeric(df_playingtime['MP (Playing Time - Playing Time)'], errors='coerce')
    df_playingtime=df_playingtime[df_playingtime['MP (Playing Time - Playing Time)']>= 1]
    df_playingtime= df_playingtime.reset_index(drop=True)
    return df_playingtime


@st.cache_data
def creacion_df_general_fbref(league='Big 5 European Leagues', season="2024-2025", stat=["Standard Stats","Shooting","Passing", "Pass Types", 
                                                                       "Goal and Shot Creation", "Defensive Actions","Possession", "Miscellaneous Stats"]):
    """
    Crea un DataFrame general combinando múltiples estadísticas avanzadas de jugadores desde FBref.

    Esta función:
    - Extrae tablas correspondientes a diferentes tipos de estadísticas (estándar, disparos, pases, defensa, etc.).
    - Aplica un proceso de formateo común a cada DataFrame extraído.
    - Incluye datos de tiempo de juego formateados.
    - Combina todos los DataFrames en uno solo, eliminando columnas duplicadas y asegurando tipo numérico donde sea necesario.
    
    Args:
        league (str): Liga de la que se extraerán los datos.
        season (str): Temporada de la que se extraerán los datos.
        stat (list): Lista de tipos de estadísticas a extraer.
    Return:
        pd.DataFrame: DataFrame combinado con estadísticas de jugadores de la liga especificada.
    
    """
    
    df_stats, url = extract_tables(league=league, season="2024-2025", stat="Standard Stats")
    print(df_stats)
    print(df_stats.columns)
    df_general_stats= formatear_datos(df_stats)
    
    df_shooting, url = extract_tables(league=league, season="2024-2025", stat="Shooting")
    df_general_shooting = formatear_datos(df_shooting)
    
    df_passing, url = extract_tables(league=league, season="2024-2025", stat="Passing")
    df_general_passing = formatear_datos(df_passing)

    df_passingtype, url = extract_tables(league=league, season="2024-2025", stat="Pass Types")
    df_general_passingtype = formatear_datos(df_passingtype)

    df_gca, url = extract_tables(league=league, season="2024-2025", stat="Goal and Shot Creation")
    df_general_gca = formatear_datos(df_gca)

    df_defensiveactions, url = extract_tables(league=league, season="2024-2025", stat="Defensive Actions")
    df_general_df_defensiveactions = formatear_datos(df_defensiveactions)

    df_possession, url = extract_tables(league=league, season="2024-2025", stat="Possession")
    df_general_possession = formatear_datos(df_possession)
    
    df_misc, url = extract_tables(league=league, season="2024-2025", stat="Miscellaneous Stats")
    df_general_misc = formatear_datos(df_misc)

    df_playingtime= obtener_foramtear_playingtime_jugadores(league='Big 5 European Leagues', season="2024-2025", stat="Playing Time")
    df_playingtime_jugadores= formatear_datos(df_playingtime)
    

    df_general_final= pd.concat([df_general_stats, df_general_shooting, df_general_passing,df_general_passingtype,
                             df_general_gca, df_general_df_defensiveactions, df_general_possession, df_general_misc, df_playingtime_jugadores], axis=1)
    df_general_final = df_general_final.loc[:, ~df_general_final.columns.duplicated(keep='first')]
    df_general_final.loc[:, df_general_final.columns[7:]] = df_general_final.loc[:, df_general_final.columns[7:]].apply(pd.to_numeric, errors='coerce')
    return df_general_final

#SE EJECUTA LA FUNCIÓN PARA CREAR EL DF GENERAL
df_general_final= creacion_df_general_fbref(league='Big 5 European Leagues', season="2024-2025",
                                             stat=["Standard Stats","Shooting","Passing", "Pass Types", 
                                                        "Goal and Shot Creation", "Defensive Actions","Possession", "Miscellaneous Stats"]) 

# Procesar las posiciones de los jugadores
df_general_final = procesar_posiciones(df_general_final, columna='Posicion')

# Filtrar jugadores de La Liga: ES EL QUE SE VA USAR PARA EL ANALISIS DE JUGADORES DE CAMPO
df_jugadores_total_liga= df_general_final[df_general_final['Competicion']=='La Liga'].reset_index(drop=True)

@st.cache_data
#Obteniendo los porteros de La Liga
def creacion_df_porteros_fbref(league='Big 5 European Leagues', season="2024-2025", stat=["Goalkeeping", 'Advanced Goalkeeping']):
    """ 
    Crea un DataFrame de porteros combinando estadísticas de Goalkeeping y Advanced Goalkeeping desde FBref.
    Esta función:
    - Extrae las tablas correspondientes a las estadísticas de porteros.
    - Aplica un proceso de formateo común a cada DataFrame extraído.
    - Combina ambos DataFrames en uno solo, eliminando columnas duplicadas y asegurando tipo numérico donde sea necesario.

    Args:
        league (str): Liga de la que se extraerán los datos.
        season (str): Temporada de la que se extraerán los datos.
        stat (list): Lista de tipos de estadísticas a extraer, en este caso "Goalkeeping" y "Advanced Goalkeeping".

    Return:
        pd.DataFrame: DataFrame combinado con estadísticas de porteros de la liga especificada.
    """
    df_goalkeepers, url = extract_tables(league=league, season="2024-2025", stat="Goalkeeping")
    df_goalkeepers= formatear_datos(df_goalkeepers)
    
    df_advgoalkeepers, url = extract_tables(league=league, season="2024-2025", stat="Advanced Goalkeeping")
    df_advgoalkeepers = formatear_datos(df_advgoalkeepers)
     

    df_goalkeepers_final= pd.concat([df_goalkeepers,df_advgoalkeepers], axis=1)
    df_goalkeepers_final = df_goalkeepers_final.loc[:, ~df_goalkeepers_final.columns.duplicated(keep='first')]
    df_goalkeepers_final.loc[:, df_goalkeepers_final.columns[7:]] = df_goalkeepers_final.loc[:, df_goalkeepers_final.columns[7:]].apply(pd.to_numeric, errors='coerce')
    return df_goalkeepers_final

# SE EJECUTA LA FUNCIÓN PARA CREAR EL DF DE PORTEROS
df_goalkeepers_final= creacion_df_porteros_fbref(league='Big 5 European Leagues', season="2024-2025",
                                             stat=["Goalkeeping", 'Advanced Goalkeeping'])

# Filtrar porteros de La Liga: ES EL QUE SE VA USAR PARA EL ANALISIS DE PORTEROS
df_porteros_liga= df_goalkeepers_final[df_goalkeepers_final['Competicion']=='La Liga'].reset_index(drop=True)

def convertir_columnas_numericas_goalkeepers(df, columna_inicio):
    """
    Convierte a valores numéricos todas las columnas desde la columna dada (sin incluirla) hasta el final.
    Reemplaza comas por puntos y elimina porcentajes si los hay.

    Args:
        df (pd.DataFrame): DataFrame al que aplicar la conversión.
        columna_inicio (str): Nombre de la columna a partir de la cual (sin incluir) se empieza a convertir.

    Returns:
        pd.DataFrame: DataFrame con columnas convertidas.
    """
    cols_convertir = [col for col in df.columns[df.columns.get_loc(columna_inicio) + 1:]]
    df[cols_convertir] = df[cols_convertir].apply(
        lambda col: pd.to_numeric(col.replace({',': '.', '%': ''}, regex=True), errors='coerce')
    )
    return df

def convertir_columnas_numericas_jugadores(df, columna_inicio):
    """
    Convierte a valores numéricos todas las columnas desde la columna dada (sin incluirla)
    hasta dos columnas antes del final. Reemplaza comas por puntos y elimina porcentajes.

    Args:
        df (pd.DataFrame): DataFrame al que aplicar la conversión.
        columna_inicio (str): Nombre de la columna a partir de la cual (sin incluir) se empieza a convertir.

    Returns:
        pd.DataFrame: DataFrame con columnas convertidas.
    """
    # Lista de columnas a convertir, excluyendo las dos últimas
    cols_convertir = df.columns[df.columns.get_loc(columna_inicio) + 1 : -2]

    df[cols_convertir] = df[cols_convertir].apply(
        lambda col: pd.to_numeric(col.replace({',': '.', '%': ''}, regex=True), errors='coerce')
    )
    return df

#FUNCIONES PARA EL ANALISIS DE PORTEROS
def preparar_datos_porteros(df_porteros_liga, percentil= 0.60):
            """
            Filtra el DataFrame de porteros según el percentil de alineaciones y devuelve las columnas necesarias.

            Parámetros:
            - df_porteros_liga: DataFrame original con datos de porteros
            - percentil: valor entre 0 y 1 para filtrar por número de alineaciones

            Devuelve:
            - df_mask: DataFrame filtrado con columnas relevantes para el análisis
            """
            # Calcular valor del percentil
            percentil_val = df_porteros_liga['Alineaciones'].quantile(percentil)

            # Filtrar porteros con suficientes alineaciones
            df_filtrado = df_porteros_liga[df_porteros_liga['Alineaciones'] >= percentil_val].copy()

            # Selección de columnas relevantes
            df_mask = df_filtrado[['Player', 'Alineaciones', 'Tiros puerta recibidos', '% Paradas']].copy()

            return df_mask, percentil_val


def graficar_tiros_vs_paradas(df_mask, percentil = 0.60):
    """
    Genera un gráfico de dispersión entre tiros a puerta recibidos y % de paradas, con línea de tendencia.

    Parámetros:
    - df_mask: DataFrame preparado con las columnas necesarias
    - percentil: percentil usado en el filtrado (solo para mostrarlo en el título)

    Devuelve:
    - fig: objeto de gráfico Plotly
    """
    fig = px.scatter(
        df_mask,
        x='Tiros puerta recibidos',
        y='% Paradas',
        text='Player',
        hover_data=['Alineaciones'],
        title=f'Relación entre Tiros a Puerta Recibidos y % de Paradas.',
        labels={
            'Tiros puerta recibidos': 'Tiros a Puerta Recibidos',
            '% Paradas': '% de Paradas'
        },
        template='plotly_white',
        trendline='ols',  # 🔥 Aquí se activa la regresión lineal
        trendline_color_override='red'
    )

    fig.update_traces(textposition='top center')
    fig.update_layout(title_font_size=18, height=600)

    return fig

#FUNCIONES PARA EL ANALISIS DE DEFENSAS
def preparar_df_defensores_sub25(df_def, percentil= 0.75):
    """
    Filtra y prepara el DataFrame con defensores Sub-25 que han jugado al menos el percentil 75 de minutos (26.0),
    y selecciona solo las columnas relevantes para el análisis de derribos.

    Parámetros:
    - df_def (DataFrame): DataFrame original con columnas de edad, minutos y derribos.ç
    -percentil: se define el percentil a aplicar para el filtro. 

    Retorna:
    - df_filtrado (DataFrame): DataFrame preparado y ordenado.
    -Percentil_minutos: valor del percentil 75
    """
    
    # Calcular valor del percentil
    percentil_minutos= df_def['Minutos jugados/90'].quantile(percentil)
    # Filtro por edad y minutos jugados
    df_filtrado = df_def[(df_def['Edad'] <= 25.0) & (df_def['Minutos jugados/90'] >= percentil_minutos)].copy()

    # Selección de columnas y orden
    columnas = [
        'Player', 'Equipo', 'Edad', 'Minutos jugados/90',
        'Derribos', 'Derribos (Def 3rd)', 'Derribos (Mid 3rd)', 'Derribos (Att 3rd)'
    ]
    df_filtrado = df_filtrado[columnas].sort_values(by='Derribos', ascending=False).reset_index(drop=True)

    return df_filtrado, percentil_minutos

def grafico_distribucion_derribos(df_defensores):
    """
    Visualiza la distribución de derribos por tercio del campo para defensores Sub-25.

    Parámetros:
    - df_defensores (DataFrame): DataFrame con columnas
      ['Player', 'Derribos (Def 3rd)', 'Derribos (Mid 3rd)', 'Derribos (Att 3rd)']

    Retorna:
    - fig (plotly.graph_objects.Figure): gráfico de barras apiladas
    """

    # Columnas a usar
    derribos_cols = ['Derribos (Def 3rd)', 'Derribos (Mid 3rd)', 'Derribos (Att 3rd)']
    df_plot = df_defensores.copy()

    # Calcular porcentajes
    df_plot[derribos_cols] =df_plot[derribos_cols].div(df_plot[derribos_cols].sum(axis=1), axis=0)
    
    # Convertir a formato largo
    df_long = df_plot.melt(
        id_vars='Player',
        value_vars=derribos_cols,
        var_name='Tercio del Campo',
        value_name='Porcentaje'
    )

    # Ordenar jugadores por derribos en tercio defensivo
    orden_jugadores = df_plot.sort_values(by='Derribos (Def 3rd)', ascending=True)['Player']
    df_long['Player'] = pd.Categorical(df_long['Player'], categories=orden_jugadores, ordered=True)

    # Colores personalizados
    colores_tercios = {
        'Derribos (Def 3rd)': '#1f77b4',
        'Derribos (Mid 3rd)': '#ff7f0e',
        'Derribos (Att 3rd)': '#2ca02c'
    }

    # Crear gráfico interactivo
    fig = px.bar(
        df_long,
        x='Porcentaje',
        y='Player',
        color='Tercio del Campo',
        color_discrete_map=colores_tercios,
        orientation='h',
        title='',
        labels={'Porcentaje': 'Derribos (%)', 'Player': 'Jugador'}
    )

    fig.update_layout(
    barmode='stack',
    yaxis={'categoryorder': 'array', 'categoryarray': list(orden_jugadores)},
    xaxis_tickformat='%',
    height=30 * len(orden_jugadores)  # Ajusta 30px por jugador; puedes cambiar este valor
)

    return fig,df_plot

#FUNCIONES PARA EL ANALISIS DE CENTROCAMPISTAS
def filtros_centrocampistas(df, percentil= 0.85):
    """
    Filtra el DataFrame de centrocampistas según los criterios especificados:
        - Minutos jugados/90 superior al percentil 85 de la columna 'Minutos jugados/90'.
       
    Args:
        df (pd.DataFrame): DataFrame de centrocampistas.
        percentil_85_centrocampistas (float): Percentil para filtrar minutos jugados/90.
        
    Returns:
        pd.DataFrame: DataFrame filtrado de centrocampistas.
    """
    percentil_ccampista_85= round(df['Minutos jugados/90'].quantile(percentil),2)
    df_filtro= df[df['Minutos jugados/90'] >= percentil_ccampista_85].reset_index(drop=True)
    df_mask_centrocampistas= df_filtro[['Player', 'Minutos jugados/90', "Pases progresivos", "Acciones creadores de goles/90", 'Pases clave']]
    
    return df_mask_centrocampistas, percentil_ccampista_85



def visualizar_creadores_ofensivos_centrocampistas(df):
    """
    Visualiza la relación entre pases progresivos y acciones creadoras de goles por 90 (GCA/90),
    usando pases clave como tamaño y color del punto. Incluye líneas de media con los valores numéricos.
    """

    # Calcular medias
    x_mean = df["Pases progresivos"].mean()
    y_mean = df["Acciones creadores de goles/90"].mean()

    # Crear scatter plot
    fig = px.scatter(
        df,
        x="Pases progresivos",
        y="Acciones creadores de goles/90",
        color="Pases clave",
        size="Pases clave",
        hover_name="Player",
        title="",
        labels={
            "Pases progresivos": "Pases progresivos",
            "Acciones creadores de goles/90": "GCA/90",
            "Pases clave": "Pases clave"
        },
        template="plotly_white",
        color_continuous_scale="Viridis"
    )

    # Añadir líneas de media
    fig.add_shape(
        type="line",
        x0=x_mean, x1=x_mean,
        y0=df["Acciones creadores de goles/90"].min(), y1=df["Acciones creadores de goles/90"].max(),
        line=dict(color="red", dash="dash")
    )

    fig.add_shape(
        type="line",
        x0=df["Pases progresivos"].min(), x1=df["Pases progresivos"].max(),
        y0=y_mean, y1=y_mean,
        line=dict(color="blue", dash="dash")
    )

    # Mostrar valores de media en anotaciones
    fig.add_annotation(
        x=x_mean, y=df["Acciones creadores de goles/90"].max(),
        text=f"Media= {x_mean:.2f}",
        showarrow=False,
        yshift=10,
        font=dict(color="red")
    )

    fig.add_annotation(
        x=df["Pases progresivos"].max()+4, y=y_mean,
        text=f"Media= {y_mean:.2f}",
        showarrow=False,
        xshift=10,
        font=dict(color="blue")
    )

    return fig


#FUNCIONES PARA EL ANALISIS DE DELTANTEROS
def calcular_diferencia_goles_xg(df, percentil=0.85):
    """
    Filtra jugadores por encima del percentil en Minutos jugados/90,
    calcula la diferencia Goles - xG (sin penaltis), y ordena de menor a mayor.
    
    Parámetros:
    - df: DataFrame con columnas ['Player', 'Minutos jugados/90', 'Goles sin penaltis', 'xG sin penaltis']
    - percentil: umbral para filtrar jugadores según Minutos jugados/90 (default = 0.85)
    
    Retorna:
    - DataFrame ordenado por 'Diferencia_Goles_xG' con 1 decimal en las métricas
    """
    percentil_valor = df['Minutos jugados/90'].quantile(percentil)
    
    df_filtrado = df[df['Minutos jugados/90'] >= percentil_valor].reset_index(drop=True).copy()
    
    df_mask = df_filtrado[['Player', 'Minutos jugados/90', 'Goles sin penaltis', 'xG sin penaltis']].copy()
    df_mask['Diferencia_Goles_xG'] = df_mask['Goles sin penaltis'] - df_mask['xG sin penaltis']
    
    df_ordenado = df_mask.sort_values('Diferencia_Goles_xG', ascending=True).reset_index(drop=True)

    # Redondear a 1 decimal todas las columnas numéricas
    cols_numericas = df_ordenado.select_dtypes(include='number').columns
    df_ordenado[cols_numericas] = df_ordenado[cols_numericas].round(1)
    
    return df_ordenado, percentil_valor


def generar_grafico_diferencia_plotly(df_ordenado):
    df_ordenado = df_ordenado.copy()
    df_ordenado['Color'] = df_ordenado['Diferencia_Goles_xG'].apply(lambda x: 'green' if x > 0 else 'red')
    df_ordenado['Etiqueta'] = df_ordenado['Diferencia_Goles_xG'].round(2)

    fig = px.bar(
        df_ordenado,
        x='Diferencia_Goles_xG',
        y='Player',
        orientation='h',
        color='Color',
        color_discrete_map={'green': ' green', 'red': ' red'},
        text='Etiqueta',
        labels={ 'Player': 'Jugador', 'Diferencia_Goles_xG': 'Diferencia Goles - xG'},
    )

    fig.update_traces(
        textposition='outside',
        insidetextanchor='start',
        marker_line_width=0.5,
        textfont_size=11
    )

    fig.add_vline(x=0, line_dash="dash", line_color="black", line_width=1)

    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
        height=600,
        title_text='',
        title_x=0,
    )

    return fig

# Crear pestañas para organizar la presentación del proyecto
tabs = st.tabs(["📌 Introducción", "🧪 Metodología", "🔍 Espacio de Hipótesis Analizadas", "📈 Análisis y Visualización", "🧠 Interpretación y Conclusiones"])

# Contenido de la pestaña de introducción
with tabs[0]:
    st.markdown("""
    El objetivo de este proyecto es **analizar el rendimiento de los jugadores de La Liga al finalizar la temporada 2024-25**, agrupándolos según su posición en el campo:

    - 🧤 **Porteros**
    - 🛡️ **Defensas**
    - 🧠 **Centrocampistas**
    - 🎯 **Delanteros**

    A partir de este análisis, se estudiarán diferentes **hipótesis** relacionadas con **métricas de rendimiento variadas**, que pueden incluir tanto:

    - 📌 **Métricas tradicionales**: Goles, derribos, minutos por 90...
    - 📈 **Métricas más modernas**: xG sin penaltis, xAG, pases progresivos, acciones que generan goles por 90 minutos (GCA/90) , etc.

    Cada hipótesis se someterá a un pequeño estudio para determinar si los datos **la respaldan o la contradicen**, con el fin de:

    ✅ **Resolver la incertidumbre** planteada en cada caso.  
    🔍 **Ofrecer una visión clara y fundamentada** sobre el impacto de los jugadores a lo largo de la temporada.

    ---
    ### 🛠️ Tecnologías utilizadas:
    - 🐍 **Python**
    - 📦 **Entorno virtual**
    - 📊 **Pandas**
    - 🔢 **NumPy**             
    - 🧼 **BeautifulSoup**
    - 🖥️ **Streamlit**          

    """)

# Contenido de la pestaña de metodología
with tabs[1]:
    st.markdown("""
        El desarrollo del proyecto ha seguido una serie de pasos estructurados para asegurar un análisis riguroso y reproducible. A continuación se detalla el proceso:

        ### 1. 📥 **Extracción de Datos**
        - Se ha utilizado el sitio web [FBref](https://fbref.com) como fuente principal de estadísticas.
        - Se desarrolló un **scraper personalizado** para extraer tablas detalladas de rendimiento de jugadores (usando clases como `LeagueManager` y funciones como `extract_tables`).
        - Se extrajeron estadísticas de diferentes categorías, como:
            - 🏃‍♂️ **Estadísticas generales** (goles, asistencias, minutos jugados...).
            - 🎯 **Shooting** (xG, tiros a puerta...).
            - 📊 **Passing** (pases completados, progresiones...).
            - 🛡️ **Defensive Actions** (intercepciones, duelos ganados...).
            - ⚽ **Goal and Shot Creation** (contribuciones al xG...).
            - 🧤 **Goalkeeping** (paradas, goles concedidos...).
            - 🏃‍♂️ **Playing Time** (minutos jugados, partidos disputados...).
            
        
        - Se guardaron los datos en un DataFrame de Pandas para su posterior análisis, uno para los jugadores y otro para los porteros.
        - Todas las estadísticas se combinan para cada jugador y aportar una visión completa de su rendimiento a lo largo de la temporada.
    
        
        ### 2. 🧹 **Limpieza y Preparación**
        - Se hizo un mapeo de los nombres de las columnas para estandarizar y facilitar el análisis.
        - Se limpio ciertas columnas con datos sucios para asegurar la consistencia.
        - Se eliminaron columnas innecesarias (duplicadas) y se renombraron otras para mayor claridad.
        - Se adaptaron y descompusieron posiciones de jugadores para análisis específicos.
        - Se eliminaron filas con datos irrelevantes o no aplicables (por ejemplo, jugadores sin minutos jugados).

        ### 3. 🧮 **Organización por Posición**
        - Los jugadores fueron agrupados por posición principal donde se le aplica el filtro en la propia app:
            - 🧤 Porteros
            - 🛡️ Defensas 
            - 🧠 Centrocampistas
            - 🎯 Delanteros
        - Se analizaron métricas relevantes dentro de cada grupo, según el rol en el campo, y así formular las diferentes hipótesis.

        ### 4. 📊 **Formulación de Hipótesis**
        - Se definieron hipótesis relacionadas con tendencias observadas o preguntas comunes del juego.
        - Por ejemplo:  
        *"No existe una relación significativa entre la cantidad de tiros a puerta recibidos y el porcentaje de paradas realizadas por los porteros."*  
        *" Los delanteros con mucho xG pero pocos goles están siendo eficientes."*

        ### 5. 📈 **Análisis Estadístico**
        - Se aplican filtros para seleccionar jugadores con un mínimo requerido para no tener sesgos en los datos (por ejemplo, un percentil de minutos jugados).
        - Se seleccionan columnas relevantes para cada hipótesis.
        - Se realizaron comparaciones, visualizaciones y análisis de datos para validar o rechazar hipótesis.
        - Se usaron tanto métricas acumuladas como normalizadas por 90 minutos.

        ### 6. ✅ **Interpretación y Conclusión**
        - Se resumieron los hallazgos clave de cada hipótesis.
        - Se presentaron conclusiones basadas en los datos, sin sesgos ni suposiciones externas.

        ---
        """)

# Contenido de la pestaña de hipótesis analizadas
with tabs[2]:
    st.markdown("""
    En esta sección se detallan las hipótesis planteadas sobre el rendimiento de los jugadores durante la temporada 2024-25, organizadas por posición en el campo.

    Cada hipótesis ha sido diseñada para resolver una incertidumbre mediante datos cuantitativos, ya sean métricas tradicionales o más contextuales.

    ---
    """)

    # 🧤 PORTEROS
    st.markdown("### 🧤 Porteros")
    with st.expander("📌 Hipótesis 1: No existe una relación significativa entre la cantidad de tiros a puerta recibidos y el porcentaje de paradas realizadas por los porteros."):
        st.markdown("""
        **Descripción:**  
        En el análisis del rendimiento de los porteros, el porcentaje de paradas suele utilizarse como un indicador directo de efectividad. Sin embargo, este porcentaje puede estar condicionado por el volumen de tiros que el portero enfrenta:  
        - Un portero con pocos tiros puede mostrar un % de paradas muy alto si encaja solo uno, aunque no haya tenido gran exigencia.  
        - Por el contrario, un portero con muchos tiros puede tener un % más bajo a pesar de realizar un gran número de paradas.

        **Métricas utilizadas:**  
        - Tiros a puerta recibidos  
        - % Paradas

        **Objetivo:**  
        Testear si la carga de trabajo defensivo (número de tiros recibidos) se asocia con la efectividad en las paradas, y visualizar dicha relación.
        """)

    # 🛡️ DEFENSAS
    st.markdown("### 🛡️ Defensores")
    with st.expander("📌 Hipótesis 2: Los defensores Sub-25 concentran la mayoría de sus derribos en el tercio defensivo del campo, lo que indicaría un perfil más conservador y anclado a tareas de contención."):
        st.markdown("""
        **Descripción:**  
        En el análisis del comportamiento defensivo, la distribución de derribos por zonas del campo ofrece información clave sobre el rol y perfil táctico de un defensor. No todos los defensores intervienen en las mismas zonas ni con el mismo enfoque:

        - Un defensor con alta concentración de derribos en el **tercio defensivo** suele estar más ligado a un perfil de **bloque bajo**, enfocado en la contención cerca de su propia portería.
        - En cambio, aquellos con mayor proporción en el **tercio medio o ofensivo** pueden reflejar un estilo de juego más agresivo, asociado a presión alta o participación en fases de recuperación adelantada.

        **Métricas utilizadas:**  
        - Número total de derribos 
        - % de derribos: 
            - Derribos (Def 3rd)  
            - Derribos (Mid 3rd)  
            - Derribos (Att 3rd)  

        **Objetivo:**  
        Evaluar si los defensores Sub-25 muestran una tendencia sistemática hacia un comportamiento conservador (alto % en el tercio defensivo) y cómo varía este patrón entre distintos perfiles o roles dentro de la línea defensiva.
        """)

    # 🎯 CENTROCAMPISTAS
    st.markdown("### 🎯 Centrocampistas")
    with st.expander("📌 Hipótesis 3: Los centrocampistas con un mayor número de pases progresivos no siempre son los que generan más acciones creadoras de goles por 90 minutos (GCA/90), lo que sugiere distintos perfiles creativos: algunos como constructores del juego y otros como finalizadores de jugadas. "):
        st.markdown("""
        **Descripción:**  

        Se analiza la relación entre el volumen de pases progresivos y la generación de acciones que conducen a goles por 90 minutos (GCA/90) entre centrocampistas. El objetivo es identificar perfiles diferenciados: aquellos que construyen el juego desde zonas más retrasadas (alta progresión, bajo GCA/90) frente a los que finalizan jugadas o participan en acciones clave más cercanas al área rival (bajo volumen de progresión pero alto GCA/90).

        **Métricas utilizadas:**  
        - Pases progresivos totales  
        - Acciones que generan goles por 90 minutos (GCA/90)  
        - Pases clave (como dimensión adicional de impacto ofensivo)  
        - Minutos jugados/90

        **Objetivo:**  
        Corroborar la hipótesis de que existen **diferentes perfiles creativos** entre los centrocampistas ofensivos: **constructores del juego** vs **finalizadores de jugadas**, analizando el equilibrio entre volumen de progresión y contribución directa al gol.
        """)

    # ⚔️ DELANTEROS
    st.markdown("### ⚔️ Delanteros")
    with st.expander("📌 Hipótesis 4: Los delanteros con mucho xG pero pocos goles están siendo eficientes."):
        st.markdown("""
        **Descripción:**  
        
        "Se analiza poder identificar a aquellos jugadores que generan muchas oportunidades de gol (xG sin penaltis alto) pero no las convierten (goles sin penaltis bajos), lo que se traduce en una diferencia negativa (underperformance)."

        **Métricas utilizadas:**  
        - Minutos jugados/90
        - Goles sin penaltis
        - xG sin penaltis

        **Objetivo:**  
        Corroborar la diferencia underperformance o overperformance de los jugadores.
        """)

# Contenido de la pestaña de análisis y visualización
with tabs[3]:
    # Se convierte el DataFrame de porteros a formato numérico
    df_jugadores_total_liga= convertir_columnas_numericas_jugadores(df_jugadores_total_liga, columna_inicio='Competicion')
    #Se convierte la columna de Nacimiento a string para evitar problemas de visualización
    df_jugadores_total_liga['Nacimiento'] = df_jugadores_total_liga['Nacimiento'].astype(str)

    # Mostrar análisis para defensores
    def mostrar_analisis_defensores(df):
            
            st.subheader("🛡️ Análisis para Defensores")
            
            # Preparar el DataFrame de defensores Sub-25
            df_filtro_def, percentil_minutos= preparar_df_defensores_sub25(df, percentil= 0.75)
            # Calcular el valor del percentil para mostrarlo en la interfaz
            valor_percentil_def= round(percentil_minutos,2)
        
            st.markdown("""
            **Recordatorio de la hipótesis:**
                
                "Los defensores Sub-25 concentran la mayoría de sus derribos en el tercio defensivo del campo, lo que indicaría un perfil más conservador y anclado a tareas de contención."
            """)
                        
            st.info(f'Se ha hecho un filtro previo de esos jugadores que estan por encima del cuartil 75 (**{valor_percentil_def:.1f}**) en minutos jugados /90 y se han ordenado de mayor a menor en la metrica de derribos en Derribos (Def 3rd)')
            
            st.markdown("""
                <h5 style='text-align: center; color: white;'>
                Distribución de Derribos por Tercio del Campo (Defensores Sub-25)
                </h5>
                """, unsafe_allow_html=True)
            
            # Visualizar la distribución de derribos por tercio del campo
            fig_def, df_plot= grafico_distribucion_derribos(df_filtro_def)
            # Mostrar el gráfico
            st.plotly_chart(fig_def, use_container_width=True) 

            st.markdown("""
            🔎 **Análisis de resultados visuales**

                📉 Defensores más conservadores (mayor % de derribos en tercio defensivo):

                - Cristhian Mosquera (73.2%): Anclado en zona baja. Participación casi exclusiva en tareas de contención.
                - Omar El Hilali (72.93%): Perfil muy defensivo, mínima participación en presiones altas.
                - Carlos Romero, Enzo Boyomo, Carmona…: Superan el 60% de derribos en su propio tercio.

                📈 Defensores con mayor presencia en zonas medias y ofensivas (perfil más mixto):

                - Manu Sánchez (48.2% Def 3rd / 39.8% Mid 3rd): Participación más repartida. Lateral con proyección y presencia en campo rival.
                - Mika Mármol, Daniel Vivian: Cerca del 57-58% defensivo, pero con valores significativos en zonas avanzadas (Mid y Att 3rd).

            """) 
    # Mostrar análisis para centrocampistas
    def mostrar_analisis_centrocampistas(df):
            st.subheader("🧠 Análisis para Centrocampistas")          
            df_mask_centrocampitas, valor_percentil_centrocampistas= filtros_centrocampistas(df, percentil= 0.85)

            st.markdown("""
            **Recordatorio de la hipótesis:**
                
                "Los centrocampistas con un mayor número de pases progresivos no siempre son los que generan más acciones creadoras de goles por 90 minutos (GCA/90), lo que sugiere distintos perfiles creativos: algunos como constructores del juego y otros como finalizadores de jugadas. "
            """)
                        
            st.info(f'Se ha hecho un filtro previo de esos jugadores que estan por encima del cuartil 85 (**{valor_percentil_centrocampistas:.1f}**) en minutos jugados /90')
            
            st.markdown("""
                <h5 style='text-align: center; color: white;'>
                Relación entre Pases Progresivos y GCA/90
                </h5>
                """, unsafe_allow_html=True)
            
            fig_centrocampistas= visualizar_creadores_ofensivos_centrocampistas(df_mask_centrocampitas)
            st.plotly_chart(fig_centrocampistas, use_container_width=True) 

            
            st.markdown("""
            🔎 **Análisis de resultados visuales**

                📈 Jugadores más completos ofensivamente (alta progresión y creatividad):

                - Pedri: 360 pases progresivos, 0.53 GCA/90 y 70 pases clave. Brilla en todas las métricas. Generador total.
                - Álex Baena: 247 pases progresivos, 0.54 GCA/90 y 95 pases clave. Volumen altísimo en pase clave.
                - Federico Valverde: 258 pases progresivos, 0.39 GCA/90. Perfil mixto, excelente en progresión y llegada.

                📉 Jugadores con mucha progresión pero bajo impacto final (bajo GCA/90):

                - Jugadores con +200 pases progresivos pero <0.2 GCA/90.
                - Posibles perfiles organizadores o interiores más posicionales.
                
                ⚠️ Jugadores con bajo volumen pero alto impacto (eficientes):

                - Jugadores que, con pocos pases progresivos, logran alto GCA/90.
                - Posibles media puntas, extremos o perfiles con menor participación en salida pero decisivos en últimos metros.
                - Ideal para contextos donde se busca eficiencia ofensiva en pocos toques.

                💤 Jugadores con bajo impacto ofensivo general:

                - Por debajo de la media tanto en progresión como en generación.
                - Posibles perfiles más defensivos o con rol de contención.
                - No destacan ni en volumen ni en contribución directa al gol.

            """)

    # Mostrar análisis para delanteros
    def mostrar_analisis_delanteros(df):
            st.subheader("🎯 Análisis para Delanteros")
            
            df_ordenado, percentil_valor= calcular_diferencia_goles_xg(df, percentil=0.85)
            
            df_ordenado[df_ordenado.select_dtypes(include='number').columns] = df_ordenado.select_dtypes(include='number').round(1)
            valor_percentil= round(percentil_valor,2)
            
            st.markdown("""
            **Recordatorio de la hipótesis:**
                
                "Delanteros con mucho xG pero pocos goles están siendo ineficientes."
            """)
            
            st.info(f'Se ha hecho un filtro previo de esos jugadores que estan por encima del cuartil 85 (**{valor_percentil:.1f}**) en minutos jugados /90 y se han ordenado de mayor a menor diferencia en esas dos metricas')
            
            st.markdown("""
                <h5 style='text-align: center; color: white;'>
                Gráfico de diferencia Goles - xG
                </h5>
                """, unsafe_allow_html=True)

            fig_delanteros = generar_grafico_diferencia_plotly(df_ordenado)
            st.plotly_chart(fig_delanteros, use_container_width=True)  

            st.markdown("""
            🔎 **Análisis de resultados visuales**

                📉 Jugadores con peor diferencia Goles - xG (underperformance):

                - Álvaro García (-3.6): Extremadamente ineficiente. 4 goles vs 7.6 xG.
                - Isaac Romero, Oyarzabal, Barry, Raphinha...: Todos muestran underperformance notable.
                - Lamine Yamal (-0.8): Juventud y protagonismo, pero margen de mejora en definición.

                📈 Jugadores con mejor diferencia (overperformance):
                        
                - Kylian Mbappé (+5.4): Letal. 24 goles con solo 18.6 xG.
                - Kiké, Juan Cruz, Julián Álvarez...: Alta conversión vs volumen generado.

            """)  
            

    # Diccionario de traducción de posiciones
    traduccion_posiciones = {
        'Midfielder': 'Centrocampista',
        'Defender': 'Defensa',
        'Forward': 'Delantero',
        'Goalkeeper': 'Portero',
        # añade más si tu DataFrame incluye otros
    }

    # Lista original de posiciones (en inglés)
    posiciones_originales = df_jugadores_total_liga['Posicion_principal'].unique().tolist()

    # Traducción visible al usuario
    posiciones_traducidas = [traduccion_posiciones.get(pos, pos) for pos in posiciones_originales]

    # Mostrar selectbox con posiciones en castellano
    posicion_traducida = st.selectbox("Selecciona una posición para visualizar el análisis:", posiciones_traducidas)

    # Obtener la posición original (en inglés) seleccionada por el usuario
    # Esto es clave para usarla luego en filtros del DataFrame
    posicion_seleccionada = [k for k, v in traduccion_posiciones.items() if v == posicion_traducida][0]

    # Mostrar contenido según la posición seleccionada
    if posicion_seleccionada == "Goalkeeper":
        st.subheader("🧤 Análisis para Porteros")

        df_porteros_final = convertir_columnas_numericas_goalkeepers(df_porteros_liga, 'Competicion')
        
        df_filtro_porteros, percentil_val= preparar_datos_porteros(df_porteros_liga, percentil= 0.60)
        valor_percentil_porteros= round(percentil_val,2)

        st.markdown("""
            **Recordatorio de la hipótesis:**
                
                "No existe una relación significativa entre la cantidad de tiros a puerta recibidos y el porcentaje de paradas realizadas por los porteros."
            """)
        
        st.info(f'Se ha hecho un filtro previo de esos jugadores que estan por encima del cuartil 60 (**{valor_percentil_porteros:.1f}**) en ser alineados.')
        
        
        fig_porteros= graficar_tiros_vs_paradas(df_filtro_porteros, percentil= valor_percentil_porteros)
        st.plotly_chart(fig_porteros, use_container_width=True)  

        st.markdown("""
            🔎 **Análisis de resultados visuales**

                Relación entre Tiros a Puerta Recibidos y % de Paradas:

                - La línea de tendencia negativa sugiere que, en general, a mayor cantidad de tiros a puerta recibidos, menor es el % de paradas. Esto respalda parcialmente la hipótesis de que los porteros más exigidos pueden tener dificultades para mantener altos niveles de eficiencia.

                - No obstante, hay **excepciones notables** que desafían esta tendencia:

                    📈 Porteros con alto % de paradas pese a volumen elevado:
                    - Unai Simón (79%): Destaca con el mayor % de paradas, aunque no es de los más exigidos en volumen.
                    - Sergio Herrera (75.3%) y Joan García (75.5%): Con más de 180 y 190 tiros recibidos respectivamente, logran un gran rendimiento.
                    - David Soria y Augusto Batalla (~75.2%): También sobresalen entre los más exigidos.

                            
                    📉 Porteros con bajo % de paradas pese a menos tiros:
                    - Karl Jakob Hein (60.7%) y Vicente Guaita (64.6%): Reciben un volumen alto pero muestran poca eficacia.
                    - Diego Conde (68.1%) y Nyland (67.9%): Niveles de parada por debajo del promedio, con volumen moderado.

            """) 
    # Mostrar análisis según la posición seleccionada
    elif posicion_seleccionada == "Defender":
        # Filtro para defensores respectando la posición principal elegida
        df_def = df_jugadores_total_liga[df_jugadores_total_liga['Posicion_principal'] == 'Defender'].copy()
        # Aplicar limpieza a la columna 'Posicion_2' para evitar valores nulos o vacíos
        df_def['Posicion_2'] = df_def['Posicion_2'].fillna('').apply(lambda x: x if x.strip() else 'No encontrado')
        # Mostrar análisis para defensores
        mostrar_analisis_defensores(df_def.reset_index(drop=True))

    elif posicion_seleccionada == "Midfielder":
        df_mid = df_jugadores_total_liga[df_jugadores_total_liga['Posicion_principal'] == 'Midfielder'].copy()
        df_mid['Posicion_2'] = df_mid['Posicion_2'].fillna('').apply(lambda x: x if x.strip() else 'No encontrado')
        mostrar_analisis_centrocampistas(df_mid.reset_index(drop=True))

    elif posicion_seleccionada == "Forward":
        df_fw = df_jugadores_total_liga[df_jugadores_total_liga['Posicion_principal'] == 'Forward'].copy()
        df_fw['Posicion_2'] = df_fw['Posicion_2'].fillna('').apply(lambda x: x if x.strip() else 'No encontrado')
        mostrar_analisis_delanteros(df_fw.reset_index(drop=True))
        
# Contenido de la pestaña de interpretación y conclusiones
with tabs[4]:
    st.subheader("Conclusiones")

    # Interpretación de los resultados obtenidos en cada posición, donde se expande cada valoración del estudio.
    with st.expander("PORTEROS"):
        
        st.markdown("""
        
        **✅ El análisis confirma la hipótesis:** No se observa una relación fuerte ni consistente entre la cantidad de tiros a puerta recibidos y el porcentaje de paradas realizadas por los porteros.

        **Tendencia general débil**:
        - Aunque la regresión es negativa, la dispersión de datos es muy amplia.
        - La eficacia de un portero no parece depender directamente del volumen de trabajo recibido.

        🧩 **Casos destacables a estudiar**:

        - **Unai Simón y Jan Oblak**: altos % de paradas con pocos tiros recibidos.
        - **Sergio Herrera y Joan García**: mantienen un % elevado pese a recibir muchos tiros.
        - **Karl Jakob Hein**: bajo rendimiento individual, incluso con alto volumen de trabajo.

        ⚙️ **Aplicaciones prácticas**:

        - **Entrenadores**: deben evaluar el rendimiento de porteros más allá del volumen de tiros recibidos.
        - **Scouting**: priorizar porteros con alta eficacia relativa, independientemente del contexto defensivo.
        """) 

    with st.expander("DEFENSAS"):
        st.markdown("""
            **✅ El análisis confirma la hipótesis:** La visualización evidencia que los defensores Sub-25 concentran la mayoría de sus derribos en el tercio defensivo, lo que respalda un perfil conservador y centrado en tareas de contención.

            🧩 **Casos destacables a estudiar**:

            - **Cristhian Mosquera y Omar El Hilali**: máximos exponentes del perfil defensivo anclado al tercio propio (71%+ de derribos en esa zona).
            - **Manu Sánchez y Daniel Vivian**: más activos en tercio medio y ofensivo, perfil más dinámico o adaptable a presión alta.

            ⚙️ **Aplicaciones prácticas**:

            - **Técnicos**: ajustar líneas defensivas según perfil — algunos jugadores podrían adaptarse a presión adelantada, otros requieren bloque bajo.
            - **Scouting**: detectar centrales o laterales con proyección ofensiva vs especialistas defensivos, según modelo de juego.  """)

    with st.expander("CENTROCAMPISTAS"):
        st.markdown("""
             **✅ El análisis respalda la hipótesis:** La visualización muestra que no todos los centrocampistas con alto volumen de pases progresivos destacan en acciones creadoras de goles por 90 minutos (GCA/90), lo que evidencia la existencia de perfiles diferenciados: **constructores** del juego vs **finalizadores** de jugadas.

            🧩 **Casos destacables a estudiar**:

            - **Álex Baena y Pedri**: sobresalen en ambas métricas, encajando en el perfil más completo de centrocampistas creativos, capaces tanto de progresar como de generar ocasiones claras.
            - **Federico Valverde**: destaca en progresión pero con impacto moderado en GCA/90, perfil mixto más enfocado a transiciones y apoyo en construcción.
            - **Jugadores con bajo volumen de pases progresivos pero alto GCA/90** (zona inferior derecha del gráfico): pueden representar roles más avanzados, como interiores ofensivos o mediapuntas.

            ⚙️ **Aplicaciones prácticas**:

            - **Técnicos**: adaptar el sistema de juego en función del perfil del centrocampista — no todos los jugadores creativos lo son desde la base; algunos brillan más cerca del área.
            - **Scouting**: identificar tipos de centrocampistas según su rol en la fase ofensiva: distribuidores profundos (pases progresivos), generadores últimos (GCA/90), o perfiles híbridos.
            - **Modelado de rendimiento**: utilizar esta segmentación para ajustar expectativas y métricas según la función táctica esperada del jugador.
        """)

    with st.expander("DELANTEROS"):
        st.markdown("""
                               
            **✅ El análisis confirma la hipótesis:** La gráfica  identifica que algunos delanteros con alto volumen de xG no convierten a la par, revelando ineficiencia.

            🧩 **Casos destacables a estudiar**:
                    
            - **Mbappé y Kiké**: ejemplos de máxima eficiencia ofensiva.
            - **Álvaro García y Oyarzabal**: podrían enfrentar problemas de definición o toma de decisiones.

            ⚙️ **Aplicaciones prácticas**:
                    
            - **Técnicos**: ajustar roles ofensivos, identificar finalizadores vs generadores de xG.
            - **Scouting**: buscar perfiles eficientes según necesidades tácticas.
            """)  
