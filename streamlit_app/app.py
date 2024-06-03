import os
import ast
import pandas as pd
import requests
import streamlit as st
import xgboost as xgb
from dotenv import load_dotenv
from steam_web_api import Steam

load_dotenv('../.env')
api_key = os.getenv('API_KEY')

steam_api_key = os.getenv('STEAM_API_KEY')
steam_client = Steam(steam_api_key)

def query_games(name, steam_client=steam_client):
    """
    This function takes in a query and searches the steam database/API
    for relevant games to that query. 
    """
    search_games_lst = steam_client.apps.search_games(name)
    games_lst = search_games_lst['apps']

    games_dct = {}

    for game in games_lst:
        # don't want game collections or empty id's
        if len(game['id']) == 1:
            games_dct[game['name']] = game['id'][0]

    # decode unicode escape sequences
    decoded_game_dict = {name.encode('latin1').decode('unicode_escape'): app_id for name, app_id in games_dct.items()}

    return decoded_game_dict

# helper function to make requests and prevent repetitive code
def request_game_data(endpoint, params):
    response = requests.get(endpoint, params=params)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return f'Error: {response.status_code}'

def get_game_id(appid, api_key=api_key, endpoint = 'https://api.isthereanydeal.com/games/lookup/v1'):
    params = {
        'key': api_key,
        'appid': appid
    }

    game_lookup = request_game_data(endpoint, params)
    
    return game_lookup['game']['id']

#with the kaggle data, we already have release dates, so this is unnecessary for now
def get_all_game_info(game_id, api_key=api_key, endpoint = 'https://api.isthereanydeal.com/games/info/v2'):
    params = {
        'key': api_key,
        'id': game_id
    }

    game_info = request_game_data(endpoint, params)
    
    return game_info


def process_raw_steam_data(steam_data):
    categories = steam_data['categories']
    game_categories = ''
    
    for cat in categories:
        game_categories += cat['description'] + ','
    
    game_categories = game_categories[:-1] # remove last comma

    game_supported_languages = steam_data['supported_languages']

    # to match the format of the original games_df,
    # remove white space and then split on the commas
    game_supported_languages = game_supported_languages.replace(' ', '').split(',')

    # mac and linux are True/False columns, so just need to check if empty
    if steam_data['mac_requirements']:
        mac = True
    else:
        mac = False

    if steam_data['linux_requirements']:
        linux = True
    else:
        linux = False

    return game_categories, game_supported_languages, mac, linux


def get_game_data(steam_app_id, any_deals_game_info, steam_game_details):
    release_date = any_deals_game_info['releaseDate']
    achievements = any_deals_game_info['achievements']
    tags = any_deals_game_info['tags']
    tags = [tag.replace(' ',  '-') for tag in batman_ex_info['tags']]
    ','.join(tags)

    steam_data = steam_game_details[f"{steam_app_id}"]['data']
    categories, supported_languages, mac, linux = process_raw_steam_data(steam_data)

    # need to turn lists into strings to convert to dataframe later
    supported_languages = str(supported_languages)

    return achievements, supported_languages, mac, linux, categories, tags, release_date


def main():
    st.title("Steam Game Search")

    # Input text box for user to enter a game name
    game_name = st.text_input("Search for a relevant game:")

    if game_name:
        # Query the games using the input text
        query_results_dct = query_games(game_name)

        # Display the list of game names (keys of the output dictionary)
        if query_results_dct:
            st.write("We found the following:")
            selected_game = st.selectbox("Select a game:", list(query_results_dct.keys()))
            
            if st.button("Predict how long until sale"):
                steam_app_id = query_results_dct[selected_game]

                game_id = get_game_id(steam_app_id, api_key)
                any_deals_game_info = get_all_game_info(game_id)

                #boxart = any_deals_game_info['assets']['boxart']

                steam_game_details = steam_client.apps.get_app_details(
                    app_id=steam_app_id, 
                    country='US', 
                    filters='basic,categories'
                )

                achievements, supported_languages, mac, linux, categories, tags, release_date = get_game_data(steam_app_id, any_deals_game_info, steam_game_details)
                selected_game_dct = {
                    'Achievements': achievements, 'Supported languages': supported_languages, 
                    'Mac': mac, 'Linux': linux, 'Categories': categories, 
                    'Tags': tags, 'ReleaseDate': release_date
                }
                selected_game_df = pd.DataFrame([selected_game_dct])
                st.write(selected_game_df)

        else:
            st.write("No results found for the entered game name.")

if __name__ == "__main__":
    main()