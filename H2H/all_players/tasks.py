import os
import django
import requests
import pytz
from datetime import datetime, date, timedelta

# Ensure Django settings are loaded
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "head2head.settings")
#django.setup()  # Initializes Django (uncomment if required to load Django models)

from .espn_api import fetch_espn_data, get_game_stats, fetch_player_positions, get_stats, game_details, get_def_stats, fetch_def_info
from .models import Player, Game, Player_Stats, Def_Stats

team_id = [(1, 'Falcons'), (2, 'Bills'), (3, 'Bears'), (4, 'Bengals'), (5, 'Browns'), (6, 'Cowboys'), (7, 'Broncos'), (8, 'Lions'), (9, 'Packers'), (34, 'Texans'), (11, 'Colts'), (30, 'Jaguars'), (12, 'Chiefs'), (14, 'Rams'), (24, 'Chargers'), (15, 'Dolphins'), (16, 'Vikings'), (17, 'Patriots'), (18, 'Saints'), (19, 'Giants'), (20, 'Jets'), (13, 'Raiders'), (21, 'Eagles'), (23, 'Steelers'), (25, '49ers'), (26, 'Seahawks'), (27, 'Buccaneers'), (10, 'Titans'), (22, 'Cardinals'), (28, 'Commanders'), (33, 'Ravens'), (29, 'Panthers')]
team_dict = {name: id for id, name in team_id}

# Updates ESPN player data once a year, ensuring the database has the latest active players
def update_espn_data():
    data = fetch_espn_data()  # Fetch player data from the ESPN API
    players = data["items"]  # Extract the list of players

    # Loop through players and update or create records for active players
    for player in players:
        Player.objects.update_or_create(
            id=player['id'],  # Use player ID as the primary key
            defaults={
                'firstName': player.get('firstName', ''),
                'lastName': player.get('lastName', ''),
                'weight': player.get('weight', 0),
                'displayHeight': player.get('displayHeight', ''),
                'age': player.get('age', 0),
                'experience': player.get('experience', ''),
                'jersey': player.get('jersey', 0)
            }
        )

# Updates player positions and team data by fetching additional information
def update_player_positions():
    for player in Player.objects.all():  # Loop through all players in the database
        result = fetch_player_positions(player.id)  # Fetch position and team details
        if result == 1:
            print(player.id, " problem !!!!!!!!!")
            continue
        athlete = result.get('athlete', {})  # Get athlete data

        # Extract position, team, and status information
        position = athlete.get('position', {}).get('name', '')
        team = athlete.get('team', {}).get('name', '')
        location = athlete.get('team', {}).get('location', '')

        # Determine player status (active or not) and handle injuries if present
        if athlete.get('active', '') == True:
            if 'injuries' in athlete:
                status = athlete.get('injuries', [])
                for s in status:
                    status = s.get('type', {}).get('name', '')
            else:
                status = 'Active'
        if athlete.get('active', '') == False:  # Remove inactive players
            Player.objects.filter(id=player.id).delete()
            print("Player deleted")
            continue

        # Update or create player data with new details
        Player.objects.update_or_create(
            id=player.id,
            defaults={
                'status': status,
                'team': team,
                'location': location,
                'position': position
            }
        )
        print("Player position added")

def delete_positionsNotNeeded():
    for players in Player.objects.all():
        if players.position == 'Quarterback' or players.position == 'Running Back' or players.position == 'Wide Receiver' or players.position == 'Tight End' or players.position == 'Place kicker' or players.position == 'Punter':
            continue
        else:
            print("player position: ", players.position)
            players.delete()

# Runs daily to check if there are any games scheduled for today
def live_update():
    print("Running daily task... live_update")
    today_player_ids = []  # List to store player IDs for today's games
    data, id, game_time = today_games()  # Get today's games and team IDs
    if data:
        for team in data:
            for players in Player.objects.all():
                if players.team in team:
                    today_player_ids.append(players.id)
    else:
        print('No games today')
    return today_player_ids, id, game_time

# Retrieves a list of teams playing today and their game IDs
def today_games():
    teams_playing_today = []
    teams_playing_ids = []
    game_times = []
    for games in Game.objects.all():
        date_string = games.date
        utc_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%MZ")
        utc_time = utc_time.replace(tzinfo=pytz.UTC)
        central_time = utc_time.astimezone(pytz.timezone("US/Central"))

        today = datetime.now(pytz.timezone("US/Central")).date()

        # comment in or out to simulate, change today to specific_date in if statement
        specific_date = date(2024, 9, 9)

        if central_time.date() == specific_date:
            teams_playing_ids.append(games.id)
            teams_playing_today.extend([games.home_team, games.away_team])
            time = central_time
            game_times.append(time)

    game_times.sort()
    if game_times:
        earliest_time = game_times[0]
    else:
        earliest_time = 0

    # comment in or out to simululate, change in return statement, earliest time to time
    time = datetime.now(pytz.timezone("US/Central")) + timedelta(minutes=1)

    return teams_playing_today, teams_playing_ids, time

# Updates player status and game data once a minute if there are games today
def update_player_status1(today_player_ids, game_id):

#___________Game Live Update____________

    print('its doing something')
    print(game_id)

    for ids in game_id:
        # Parse game data from the API
        response_data = game_details(ids)
        drives = response_data.get('drives', {})
        plays_list = drives.get('current', []) if 'current' in drives else drives.get('previous', [])

        # Extract play-by-play details
        home_score, away_score, text = 0, 0, "No plays available"

        plays = plays_list.get("plays", [])
        if plays:
            last_play = plays[-1]
            away_score = last_play.get('awayScore', 0)
            home_score = last_play.get('homeScore', 0)
            text = last_play.get('text', 'N/A')
        
        week = response_data.get('header', {}).get('week', 0)
        # Update or create Game object with live data
        Game.objects.update_or_create(
            id=ids,
            defaults={
                'home_score': home_score,
                'away_score': away_score,
                'current_play': text,
                'week': week
            }
        )
        
        obj = Game.objects.get(id = ids)
        print(vars(obj))

        teamz = []
        box = response_data.get('boxscore',{}).get('teams', [])
        for x in box:
            if 'team' in x:
                y = x.get('team', {})
                z = y.get('name', 0)
                teamz.append(z)

#___________Player Live Update____________

        
        for id in today_player_ids:
            players_team = Player.objects.get(id=id).team
            team_number = team_dict.get(players_team)

            first = Player.objects.get(id=id).firstName
            last = Player.objects.get(id=id).lastName

            if players_team not in teamz:
                continue
            
            # Call 2 different functions to get 1. player stats for game 2. team defensive stats for game

            print(first, ' ', last)
            player_instance = Player.objects.get(id=id)
            game_instance = Game.objects.get(id=ids)

            if Player.objects.get(id=id).position == 'DEF':

                def_stats_json = get_def_stats(ids, team_number)
                if def_stats_json == 1:
                    continue
                categ = def_stats_json.get('splits', {}).get('categories', [])
                for c in categ:
                    if c.get('name', '') == 'general':
                        ff = c.get('stats', [])
                        for f in ff:
                            if f.get('name', '') == 'fumblesForced':
                                forc_fum = f.get('value', 0)
                                break
                    elif c.get('name', '') == 'defensive':
                        def_stats = c.get('stats', [])
                        for defs in def_stats:
                            if defs.get('name','') == 'sacks':
                                def_sacks = defs.get('value',0)
                            elif defs.get('name', '') == 'safeties':
                                def_saf = defs.get('value', 0)
                            elif defs.get('name', '') == 'defensiveTouchdowns':
                                def_td = defs.get('value', 0)
                            elif defs.get('name', '') == 'pointsAllowed':
                                points_allowed = defs.get('value', 0)
                    elif c.get('name','') == 'defensiveInterceptions':
                        def_int_stats = c.get('stats', [])
                        for int in def_int_stats:
                            if int.get('name', '') == 'interceptions':
                                def_ints = int.get('value',0)
                                break
                    elif c.get('name', '') == 'returning':
                        def_ret = c.get('stats', [])
                        for r in def_ret:
                            if r.get('name', '') == 'defFumbleReturns':
                                fumble_rec = r.get('value', 0)
                                break

                fantasy_pts = fantasy_point_def(def_td, def_ints, fumble_rec, forc_fum, def_saf, def_sacks, points_allowed)
                
                Def_Stats.objects.update_or_create(
                    player = player_instance,
                    game = game_instance,
                    defaults={
                        'location': first,
                        'team': last,
                        'week': week,
                        'pts_allowed': points_allowed,
                        'inter': def_ints,
                        'sacks': def_sacks,
                        'safties': def_saf,
                        'touchdowns': def_td,
                        'forc_fum': forc_fum,
                        'fumble_rec': fumble_rec,
                        'total_fantasy_points': fantasy_pts
                    }
                )
            else:
                stats = get_stats(ids, team_number, id)
                if stats == 1:
                    continue
                                # Initialize all variables to 0 before use
                extra_points_attempts = extra_points_made = fg_attempts = fg_made = fg_perc = 0
                kick_1_19 = kick_20_29 = kick_30_39 = kick_40_49 = kick_50 = 0
                punt_return_td = kick_return_td = 0

                pass_att = completions = completions_perc = pass_yards = avg_pass_yards_completions = 0
                pass_tds = ints = sacks = pass_2pt = passing_fumbles = 0

                carrys = rush_yards = avg_rush_yards_perCarry = rush_tds = rush_2pt = rush_fumbles = 0

                catches = targets = recieving_yards = avg_recieving_yards_perCatch = 0
                receiving_tds = receiving_2pt = receiving_fumbles = 0

                competition = stats.get('splits', {}).get('categories', [])
                for cat in competition:
                    if cat.get('name', '') == 'passing':
                        passing_stats = cat.get('stats',[])
                        for passi in passing_stats:
                            if passi.get('name', '') == 'passingAttempts':
                                pass_att = passi.get('value', 0)
                            elif passi.get('name', '') == 'completions':
                                completions = passi.get('value', 0)
                            elif passi.get('name', '') == 'completionPct':
                                completions_perc = passi.get('value', 0)
                            elif passi.get('name', '') == 'passingYards':
                                pass_yards = passi.get('value', 0)
                            elif passi.get('name', '') == 'yardsPerCompletion':
                                avg_pass_yards_completions = passi.get('value', 0)
                            elif passi.get('name', '') == 'passingTouchdowns':
                                pass_tds = passi.get('value', 0)
                            elif passi.get('name', '') == 'interceptions':
                                ints = passi.get('value', 0)
                            elif passi.get('name', '') == 'sacks':
                                sacks = passi.get('value', 0)
                            elif passi.get('name', '') == 'twoPtPass':
                                pass_2pt = passi.get('value', 0)
                            elif passi.get('name', '') == 'passingFumbles':
                                passing_fumbles = passi.get('value', 0)
                    elif cat.get('name', '') == 'rushing':
                        rushing_stats = cat.get('stats', [])
                        for rush in rushing_stats:
                            if rush.get('name', '') == 'rushingAttempts':
                                carrys = rush.get('value', 0)
                            elif rush.get('name', '') == 'rushingYards':
                                rush_yards = rush.get('value', 0)
                            elif rush.get('name', '') == 'yardsPerRushAttempt':
                                avg_rush_yards_perCarry = rush.get('value', 0)
                            elif rush.get('name', '') == 'rushingTouchdowns':
                                rush_tds = rush.get('value', 0)
                            elif rush.get('name', '') == 'twoPtRush':
                                rush_2pt = rush.get('value', 0)
                            elif rush.get('name', '') == 'rushingFumbles':
                                rush_fumbles = rush.get('value', 0)
                    elif cat.get('name', '') == 'receiving':
                        receiving_stats = cat.get('stats', [])
                        for rec in receiving_stats:
                            if rec.get('name', '') == 'receptions':
                                catches = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingTargets':
                                targets = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingYards':
                                recieving_yards = rec.get('value', 0)
                            elif rec.get('name', '') == 'yardsPerReception':
                                avg_recieving_yards_perCatch = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingTouchdowns':
                                receiving_tds = rec.get('value', 0)
                            elif rec.get('name', '') == 'twoPtReception':
                                receiving_2pt = rec.get('value', 0)
                            elif rec.get('name', '') == 'receivingFumbles':
                                receiving_fumbles = rec.get('value', 0)
                    elif cat.get('name', '') == 'kicking':
                        kicking_stats = cat.get('stats', [])
                        for kick in kicking_stats:
                            if kick.get('name', '') == 'fieldGoalsMade1_19':
                                kick_1_19 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade20_29':
                                kick_20_29 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade30_39':
                                kick_30_39 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade40_49':
                                kick_40_49 = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade50':
                                kick_50 = kick.get('value', 0)
                            elif kick.get('name', '') == 'extraPointAttempts':
                                extra_points_attempts = kick.get('value', 0)
                            elif kick.get('name', '') == 'extraPointsMade':
                                extra_points_made = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalAttempts':
                                fg_attempts = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalPct':
                                fg_perc = kick.get('value', 0)
                            elif kick.get('name', '') == 'fieldGoalsMade':
                                fg_made = kick.get('value', 0)
                    elif cat.get('name', '') == 'returning':
                        return_stats = cat.get('stats', [])
                        for ret in return_stats:
                            if ret.get('name', '') == 'kickReturnTouchdowns':
                                kick_return_td = ret.get('value', 0)
                            elif ret.get('name', '') == 'puntReturnTouchdowns':
                                punt_return_td = ret.get('value', 0)

                return_tds = kick_return_td + punt_return_td

                if Player.objects.get(id=id).position == 'Quarterback':
                    fum = passing_fumbles + rush_fumbles
                    pt2 = rush_2pt + pass_2pt
                    Player_Stats.objects.update_or_create(
                        player=player_instance,
                        game=game_instance,
                        defaults={
                            'fumbles': fum,
                            'two_pt_made': pt2
                        })
                elif Player.objects.get(id=id).position == 'Running Back' or Player.objects.get(id=id).position == 'Place kicker':
                    fum = rush_fumbles
                    Player_Stats.objects.update_or_create(
                        player=player_instance,
                        game=game_instance,
                        defaults={
                            'fumbles': fum,
                            'two_pt_made': rush_2pt
                        })
                elif Player.objects.get(id=id).position == 'Wide Receiver' or Player.objects.get(id=id).position == 'Tight End':
                    fum = receiving_fumbles
                    Player_Stats.objects.update_or_create(
                        player=player_instance,
                        game=game_instance,
                        defaults={
                            'fumbles': fum,
                            'two_pt_made': receiving_2pt
                        })
                
                if Player.objects.get(id=id).position != 'Place kicker':
                    fantasy = fantasy_point_calculator_offense(pass_yards, pass_tds, ints, rush_yards, rush_tds, catches, recieving_yards, receiving_tds, return_tds, fum)
                elif Player.objects.get(id=id).position == 'Place kicker':
                    fantasy = fantasy_point_kicker(extra_points_made, kick_1_19, kick_20_29, kick_30_39, kick_40_49, kick_50)

                firstName = Player.objects.get(id=id).firstName
                lastName = Player.objects.get(id=id).lastName

                Player_Stats.objects.update_or_create(
                    player=player_instance,
                    game=game_instance,
                    defaults={
                        'firstName': firstName,
                        'lastName': lastName,
                        'week': week,
                        'pass_att': pass_att,
                        'completions': completions,
                        'completions_perc': completions_perc,
                        'pass_yards': pass_yards,
                        'avg_pass_yards_completions': avg_pass_yards_completions,
                        'pass_tds': pass_tds,
                        'ints': ints,
                        'sacks': sacks,
                        'catches': catches,
                        'targets': targets,
                        'avg_recieving_yards_perCatch': avg_recieving_yards_perCatch,
                        'receiving_yards': recieving_yards,
                        'receiving_tds': receiving_tds,
                        'carrys': carrys,
                        'rush_yards': rush_yards,
                        'avg_rush_yards_perCarry': avg_rush_yards_perCarry,
                        'rush_tds': rush_tds,
                        'return_td': return_tds,
                        'kick_1_19': kick_1_19,
                        'kick_20_29': kick_20_29,
                        'kick_30_39': kick_30_39,
                        'kick_40_49': kick_40_49,
                        'kick_50': kick_50,
                        'fg_perc': fg_perc,
                        'fg_attempts': fg_attempts,
                        'fg_made': fg_made,
                        'extra_points_made': extra_points_made,
                        'extra_points_attempts': extra_points_attempts,
                        'total_fantasy_points': fantasy
                    }

                )
                print("Player stats for a game added")

    print('round done')
    print(obj.home_score, ' ', obj.away_score, ' ', obj.current_play)

    # Update player statuses
    # for id in today_player_ids:
    #     result = fetch_player_positions(id)
    #     athlete = result.get('athlete', {})
    #     status = 'Active'  # Default status
    #     if 'injuries' in athlete:
    #         status = athlete.get('injuries', [])[0].get('type', {}).get('name', '')

    #     Player.objects.update_or_create(
    #         id=id,
    #         defaults={'status': status}
    #     )


def fantasy_point_calculator_offense(pass_y, pass_td, pass_i, rush_y ,rush_td, rec, rec_y, rec_td, ret_td, fums):
    pass_y_pt = pass_y * .04
    pass_td_pt = pass_td * 4
    pass_i_pt = pass_i * -2
    rush_y_pt = rush_y * .10
    touch = (rush_td + rec_td + ret_td) * 6
    rec_pt = rec * 1
    rec_y_pt = rec_y * .10
    fums * -2
    fantasy_points = pass_y_pt + pass_td_pt + pass_i_pt + rush_y_pt + touch + rec_pt + rec_y_pt
    return fantasy_points

def fantasy_point_kicker(extra, one, two, three, four, five):
    extra_pt = extra
    first = (one + two) * 3
    second = (three + four) * 4
    last = (five) * 5
    fantasy_points = extra_pt + first + second + last
    return fantasy_points

def fantasy_point_def(def_spc_td, int, fr, ff, saf, sack, pts_a):
    def_spc_td_pt = def_spc_td * 6
    int_pt = int * 2
    fr_pt = fr * 2
    ff_pt = ff * 0.5
    saf_pt = saf * 2
    sack_pt = sack * 1
    if pts_a == 0:
        pts_a_pt = 10
    elif 1 <= pts_a <=6:
        pts_a_pt = 7
    elif 7 <= pts_a <= 13:
        pts_a_pt = 4
    elif 14 <= pts_a <= 20:
        pts_a_pt = 1
    elif 21 <= pts_a <=27:
        pts_a_pt = 0
    elif 28 <= pts_a <= 34:
        pts_a_pt = -1
    else:
        pts_a_pt = -4
    fantasy_points = def_spc_td_pt + int_pt + fr_pt + ff_pt + saf_pt + sack_pt + pts_a_pt
    return fantasy_points

# Updates game data for the 2024 season
def update_game_data():
    season_2024 = [2024, 2025]
    for year in season_2024:
        data = get_game_stats(year)
        events = data.get("events", [])
        for event in events:
            id = event.get("id", "")
            date = event.get("date", "")
            season_type = event.get("season", {}).get("slug", "")
            if event.get("season", {}).get("year", 0) != 2024:
                continue
            for competition in event.get("competitions", []):
                home_team, away_team, home_score, away_score = "", "", "", ""
                for competitor in competition.get("competitors", []):
                    if competitor.get("homeAway") == "home":
                        home_team = competitor.get("team", {}).get("displayName", "")
                        home_score = competitor.get("score", "")
                    else:
                        away_team = competitor.get("team", {}).get("displayName", "")
                        away_score = competitor.get("score", "")

                # Update or create Game data
                Game.objects.update_or_create(
                    id=id,
                    defaults={
                        'season_type': season_type,
                        'date': date,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_score': home_score,
                        'away_score': away_score
                    }
                )
                print("Game data added")