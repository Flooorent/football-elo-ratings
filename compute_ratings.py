from os import listdir
import pickle
import pandas as pd


data_dir = '/Users/florentmoiny/perso/github/football-elo-ratings/data'

countries_dir = '{}/countries'.format(data_dir)
all_time_results_filepath = '{}/all_time_results.csv'.format(data_dir)
club_to_countries_path = '{}/club_to_countries.pkl'.format(data_dir)
all_time_ratings_path = '{}/all_time_ratings.csv'.format(data_dir)

result_header = ['date', 'score', 'home_team', 'away_team']
all_time_results_header = ['date', 'country', 'home_team', 'score', 'away_team']  # add country and reorder columns


K = 32
default_elo_rating = 1800


def load_all_country_results(country_dir):
    """
    Load all matches from a country directory. country_dir will contain one file
    per year.

    :param country_dir: country directory where results files are stored
    :type country_dir: str

    :returns: a dataframe of all matches results, with columns 'date', 'score',
    'home_team', and 'away_team'.
    """
    filenames = listdir(country_dir)
    filepaths = ['{}/{}'.format(country_dir, filename) for filename in filenames]
    all_results = [pd.read_csv(filepath, sep=',', header=0) for filepath in filepaths]
    return pd.concat(all_results, ignore_index=True)


# TODO: rewrite to prevent stupid mistakes
def get_expected_score(ratingA, ratingB):
    """
    Compute expected score for the team with rating ratingA.

    :param ratingA: rating of the team for which we want to compute the expected score
    :type ratingA: int

    :param ratingB: opponent's rating
    :type ratingB: int

    :returns: the expected score for the team with rating ratingA.
    """
    return 1.0 / (1 + pow(10, (ratingB - ratingA) / 400.0))


def get_actual_score(home_score, away_score, for_home_team):
    """
    Compute the actual score for the desired team for a specific match score.

    :param home_score: home team's score
    :type home_score: int

    :param away_score: away team's score
    :type away_score: int

    :param for_home_team: True to compute the actual score for the home team,
    False otherwise
    :type for_home_team: bool

    :returns: for the desired team: 1 for a win, 0.5 for a draw, 0 for a loss.
    """
    diff = home_score - away_score
    home_team_actual_score = 1 if diff > 0 else (0.5 if diff == 0 else 0)
    if for_home_team:
        return home_team_actual_score
    else:
        return 1 - home_team_actual_score


def update_rating(rating, actual_score, expected_score, k=K):
    """
    Update a team's rating.

    :param rating: a team's initial rating
    :type rating: int

    :param actual_score: actual score from a match
    :type actual_score: int

    :param expected_score: expected score for a match
    :type expected_score: int

    :param k: K-factor in the elo updating formula that controls how wide the
    update will be.
    :type k: int

    :returns: the team's new rating
    """
    return int(rating + k * (actual_score - expected_score))


def update_ratings(home_team_rating, away_team_rating, home_team_score, away_team_score, k=K):
    """
    Update both teams' ratings.

    :param home_team_rating: home team's rating
    :type home_team_rating: int

    :param away_team_rating: away team's rating
    :type away_team_rating: int

    :param home_team_score: home team's score
    :type home_team_score: int

    :param away_team_score: away team's score
    :param away_team_score: int

    :param k: K-factor in the elo updating formula that controls how wide the
    update will be.
    :type k: int

    :returns: a tuple of the home team new rating and the away team new rating
    """
    home_team_expected_score = get_expected_score(home_team_rating, away_team_rating)
    away_team_expected_score = get_expected_score(away_team_rating, home_team_rating)
    home_team_actual_score = get_actual_score(home_team_score, away_team_score, for_home_team=True)
    away_team_actual_score = get_actual_score(home_team_score, away_team_score, for_home_team=False)
    home_team_new_rating = update_rating(home_team_rating, home_team_actual_score, home_team_expected_score)
    away_team_new_rating = update_rating(away_team_rating, away_team_actual_score, away_team_expected_score)
    return (home_team_new_rating, away_team_new_rating)


def decode_score(score):
    """
    Helper function to 'decode' a score of the form '3 - 1'.

    :param score: a match score of the form '3 - 1'
    :type score: str

    :returns: a tuple with the home team's score and the away team's score
    """
    home_score, away_score = score.replace(' ', '').split('-')
    return (int(home_score), int(away_score))


##################

# load all results

##################


countries = listdir(countries_dir)

all_time_results = pd.DataFrame(columns=all_time_results_header)
club_to_countries = {}

for country in countries:
    print('Working on country {}'.format(country))

    country_dir = '{}/{}'.format(countries_dir, country)
    country_results = load_all_country_results(country_dir)
    country_results['country'] = country

    all_time_results = all_time_results.append(country_results[all_time_results_header])

    # save country for each team
    if country != 'Europe':
        teams = country_results['home_team'].unique()  # no need to use away teams since they are the same
        for team in teams:
            if team in club_to_countries:
                club_to_countries[team].add(country)
            else:
                club_to_countries[team] = set([country])


all_time_results.to_csv(all_time_results_filepath, sep=',', header=True, index=False)

# check for collisions
[(key, value) for key, value in club_to_countries.items() if len(value) > 1]
# [('Aris', {'Greece', 'Cyprus'}), ('Atromitos', {'Greece', 'Cyprus'})]


with open(club_to_countries_path, 'wb') as f:
    pickle.dump(club_to_countries, f, pickle.HIGHEST_PROTOCOL)


with open(club_to_countries_path, 'rb') as f:
    club_to_countries =  pickle.load(f)


#################

# compute ratings

#################


all_time_results = pd.read_csv(all_time_results_filepath, sep=',', header=0)
all_time_results['date'] = all_time_results['date'].apply(lambda date: '/'.join(date.split('/')[::-1]))  # initial date is of the form dd/mm/yyyy
all_time_results.sort_values(by=['date'], inplace=True)

all_time_raw_ratings = []
current_ratings = {}

nb_matches = all_time_results.shape[0]

for index, match in all_time_results.iterrows():
    home_team = match['home_team']
    away_team = match['away_team']

    if home_team in club_to_countries and away_team in club_to_countries:
        try:  # some scores don't exist (match not played yet or cancelled)
            home_team_rating = current_ratings.get(home_team, default_elo_rating)
            away_team_rating = current_ratings.get(away_team, default_elo_rating)

            home_team_score, away_team_score = decode_score(match['score'])

            home_team_new_rating, away_team_new_rating = update_ratings(home_team_rating, away_team_rating, home_team_score, away_team_score, k=k)

            home_team_country = next(iter(club_to_countries[home_team])) if match['country'] == 'Europe' else match['country']  # TODO: improve to get the right country
            away_team_country = next(iter(club_to_countries[away_team])) if match['country'] == 'Europe' else match['country']  # TODO: same

            all_time_raw_ratings.append({
                'date': match['date'],
                'country': home_team_country,
                'team': home_team,
                'rating': home_team_new_rating})

            all_time_raw_ratings.append({
                'date': match['date'],
                'country': away_team_country,
                'team': away_team,
                'rating': away_team_new_rating})
            current_ratings[home_team] = home_team_new_rating  # TODO: problem with both clubs from Greece and Cyprus
            current_ratings[away_team] = away_team_new_rating
        except:
            pass  # print(match)
    if index + 1 % 1000 == 0:
        print('DONE: {}/{}'.format(index + 1, nb_matches))

all_time_ratings = pd.DataFrame(all_time_raw_ratings)[['date', 'country', 'team', 'rating']]
all_time_ratings.to_csv(all_time_ratings_path, sep=',', header=True, index=False)

madrid = all_time_ratings[all_time_ratings['team'] == 'Real Madrid']
madrid['rating']

psg = all_time_ratings[all_time_ratings['team'] == 'PSG']
psg['rating']

france = all_time_ratings[all_time_ratings['country'] == 'France']
