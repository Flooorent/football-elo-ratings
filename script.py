import os
import re

from bs4 import BeautifulSoup
import requests
import pandas as pd


output_data_dir = '/Users/florentmoiny/perso/github/football-elo-ratings/data/countries'

home_url = 'https://www.soccerpunter.com'
stats_url = '{}/soccer-statistics'.format(home_url)

countries_metadata = [
    ('France', 'Ligue-1'),
    ('Spain', 'La-Liga'),
    ('Portugal', 'Primeira-Liga'),
    ('Netherlands', 'Eredivisie'),
    ('Italy', 'Serie-A'),
    ('Germany', 'Bundesliga'),
    ('England', 'Premier-League')
    #('Andorra', '1a-Divisió'), # TODO: weird letters
    ('Austria', 'Bundesliga'),
    ('Belgium', 'First-Division-A'),
    ('Cyprus', '1.-Division'),
    ('Greece', 'Super-League'),
    ('Israel', 'Liga-Leumit'),
    ('Russia', 'Premier-League'),
    ('Scotland', 'Premiership'),
    #('Sweden', 'Allsvenskan'), # TODO: weird letters
    ('Switzerland', 'Super-League'),
    #('Turkey', 'Süper-Lig'), # TODO: weird letters
    ('Ukraine', 'Premier-League'),
    ('Europe', 'UEFA-Champions-League'),
    ('Europe', 'UEFA-Europa-League')
]


def get_results(result_url):
    html = requests.get(result_url).content
    soup = BeautifulSoup(html, 'html5lib')
    result_tags = soup.find_all('tr', {'data-match': True})
    raw_results = [get_raw_result(result_tag) for result_tag in result_tags]
    results = [result for result in raw_results if result]
    return results



def get_raw_result(result_tag):
    """
    :return: (week, date, score, home_team, away_team, half_time_score) tuple
    """
    try:
        date = result_tag.find('a', {'class': 'dateLink'}).text
        score = result_tag.find('td', {'class': 'score'}).text
        home_team = result_tag.find('td', {'class': 'teamHome'}).text
        away_team = result_tag.find('td', {'class': 'teamAway'}).text
        return (date, score, home_team, away_team)
    except:
        return None


# TODO: deal with weird letters
def is_right_ligue_link(ligue_link, right_ligue_name):
    m = re.match(r'(.*?)-\d{4}-\d{4}', ligue_link)
    if m:
        actual_ligue_name = m.group(1).split('/')[-1]
        return actual_ligue_name == right_ligue_name
    else:
        return False


for country, ligue_name in countries_metadata:
    print('Working on country {}'.format(country))

    country_dir = '{}/{}'.format(output_data_dir, country)

    if not os.path.exists(country_dir):
        os.makedirs(country_dir)

    country_url = '{}/{}'.format(stats_url, country)

    html = requests.get(country_url).content
    soup = BeautifulSoup(html, 'html5lib')

    raw_competition_links = soup.find_all('a', {'class': 'compLink'})
    competition_links = [raw_link['href'] for raw_link in raw_competition_links if is_right_ligue_link(raw_link['href'], ligue_name)]  # of the form '/soccer-statistics/France/Ligue-1-1994-1995'
    competition_urls = ['{}{}/results'.format(home_url, link) for link in competition_links]

    for competition_url in competition_urls:
        competition_name = competition_url.split('/')[-2]
        print('Working on {}-{}'.format(country, competition_name))
        results = get_results(competition_url)
        df = pd.DataFrame(results, columns=['date', 'score', 'home_team', 'away_team'])
        df.to_csv('{}/{}'.format(country_dir, competition_name), sep=',', header=True, index=False)

    print('Country (} done'.format(country))
