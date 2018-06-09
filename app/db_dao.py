from configparser import ConfigParser
from sqlalchemy import select, and_, delete
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime


class GameDao:
    def __init__(self, armada_db_meta):
        self.tables = {
            'fleets': armada_db_meta.tables['fleets'],
            'fleet_membership': armada_db_meta.tables['fleet_membership'],
            'game_membership': armada_db_meta.tables['game_membership'],
            'games': armada_db_meta.tables['games'],
            'objectives': armada_db_meta.tables['objectives'],
            'ships': armada_db_meta.tables['ships'],
            'squadrons': armada_db_meta.tables['squadrons'],
            'systems': armada_db_meta.tables['systems'],
            'turn': armada_db_meta.tables['turn'],
            'turn_log': armada_db_meta.tables['turn_log'],
            'upgrades': armada_db_meta.tables['upgrades'],
            'users': armada_db_meta.tables['users'],
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def create_game(self, game_name, user_id, team, player_count):
        """
        Create a game and add the requesting player to that game
        :param game_name:
            Name of the game
        :param user_id:
            ID of the user who requested that the game be made
        :param team:
            ID of the faction the team should be on
            0 = Rebel
            1 = Imperial
        :param player_count:
            Number of players in the game
        :return:
            N/A
        """
        data = {
            'name': game_name,
            'start_date': datetime.today(),
            'turn': 0,
            'phase': 'SETUP',
            'status': 'PENDING',
            'player_count': player_count,
        }
        game_id = self.tables['games'].insert(data).execute().inserted_primary_key()
        self.add_player(game_id, user_id, team)

    def add_player(self, user_id, game_id, team):
        """
        Add a player to an existing game
        :param user_id:
            ID of the user joining the game
        :param game_id:
            ID of the game the user is joining
        :param team:
            ID of the faction the player is joining
            0 = Rebel
            1 = Imperial
        :return:
            N/A
        """
        if self.player_in_game(user_id, game_id):
            raise Exception("Player is already in game")
        data = {
            'game_id': game_id,
            'user_id': user_id,
            'team': team,
            'points': 0,
        }
        self.tables['game_membership'].insert(data).execute()

    def player_in_game(self, user_id, game_id):
        """
        Check if a user is in a game
        :param user_id:
            ID of the user to check for game membership
        :param game_id:
            ID of the game to check for membership in
        :return:
            True if the user is in the game, False if they are not
        """
        try:
            select(
                self.tables['game_membership']
            ).where(
                and_(
                    self.tables['game_membership'].c.user_id == user_id,
                    self.tables['game_membership'].c.game_id == game_id,
                )
            ).execute().one()
        except NoResultFound:
            return False
        return True

    def remove_player(self, user_id, game_id):
        """
        Remove a player from an existing game
        :param user_id:
            ID of the user leaving the game
        :param game_id:
            ID of the game the user is leaving
        :return:
            N/A
        """
        if not self.player_in_game(user_id, game_id):
            raise Exception("Player is not in game")
        delete(
            self.tables['game_membership'],
            and_(
                self.tables['game_membership'].c.user_id == user_id,
                self.tables['game_membership'].c.game_id == game_id,
            )
        ).execute()

    def advance_phase(self, game_id):
        """
            Moves a game phase up by one, advancing the turn as required
        :param game_id:
            ID of the game to advance the phase of
        :return:
            N/A
        """
        """
        PHASES
            Setup
                Only happens once
                Players join, initial fleets are constructed
            Strategy Phase
                Attacks are declared
                Diplomat tokens are spent
            Battle Phase
                Battles occur
            Management Phase
                Battle effects are determined
                Resources are gained
                New bases and outposts are built
                Fleets are refitted and expanded
        """
        current_phase, turn = select([
            self.tables['games'].c.phase,
            self.tables['games'].c.turn,
        ]).where(
            self.tables['games'].c.game_id == game_id,
        ).execute().one()

        if current_phase == 'SETUP':
            data = {
                'turn': 1,
                'phase': 'STRATEGY',
            }
        elif current_phase == 'STRATEGY':
            data = {
                'phase': 'BATTLE',
            }
        elif current_phase == 'BATTLE':
            data = {
                'phase': 'MANAGEMENT',
            }
        elif current_phase == 'MANAGEMENT':
            data = {
                'turn': turn + 1,
                'phase': 'STRATEGY',
            }
        else:
            raise Exception("The game is in an unknown phase!")
        self.tables['games'].update(
            self.tables['games'].c.game_id == game_id,
            data
        ).execute()

    def get_turn(self, game_id):
        """
        Looks up the turn and phase of a game
        :param game_id:
            ID of the game to return info about
        :return:
            turn, phase
        """
        return list(select([
            self.tables['games'].c.turn,
            self.tables['games'].c.phase,
        ]).where(
            self.tables['games'].c.game_id == game_id,
        ).execute().one())

    def get_players(self, game_id):
        """
        Gets a list of players in a game
        :param game_id:
            ID of the game to return info about
        :return:
            list of id, name, team, points of players in game
        """
        players = []
        results = select([
            self.tables['game_membership'].c.user_id,
            self.tables['game_membership'].c.team,
            self.tables['game_membership'].c.points,
            self.tables['users'].c.name,
        ]).select_from(
            self.tables['game_membership'].join(
                self.tables['users'],
                self.tables['users'].c.id == self.tables['game_membership'].c.user_id,
            )
        ).where(
            self.tables['game_membership'].c.game_id == game_id,
        ).execute().fetchall()

        for result in results:
            players.append((result.user_id, result.name, result.team, result.points))
        return players

    def get_fleets(self, user_id, game_id, team_id=None):
        """
        Retrieve all fleets in a game for a specific team
        :param user_id:
        :param game_id:
        :param team_id:
        :return:
        """

        raise Exception("Not implemented yet")
        ships = []
        squadrons = []

        # Make some pre-flight requests to gather all available ships and squadrons
        results = select([
            self.tables['ships'].c.id,
            self.tables['ships'].c.name,
            self.tables['ships'].c.cost,
            self.tables['ships'].c.upgrades,
            self.tables['ships'].c.faction,
        ]).execute().fetchall()

        for result in results:
            ships.append({
                'id': result.id,
                'name': result.name,
                'cost': result.cost,
                'upgrades': result.upgrades,
                'faction': result.faction,
            })

        results = select([
            self.tables['squadrons'].c.id,
            self.tables['squadrons'].c.name,
            self.tables['squadrons'].c.cost,
            self.tables['squadrons'].c.unique,
            self.tables['squadrons'].c.faction,
        ]).execute().fetchall()

        for result in results:
            ships.append({
                'id': result.id,
                'name': result.name,
                'cost': result.cost,
                'unique': result.unique,
                'faction': result.faction,
            })

        fleets = []
        where_clause = [
            self.tables['game_membership'].c.game_id == game_id
        ]
        if team_id:
            where_clause.append(
                self.tables['game_membership'].c.team == team_id
            )

        fleet_results = select([
            self.tables['fleets'].c.id,
            self.tables['fleets'].c.name,
            self.tables['fleets'].c.user_id,
            self.tables['fleets'].c.max_points,
            self.tables['fleets'].c.commander,
        ]).select_from(
            self.tables['fleets'].join(
                self.tables['game_membership'],
                and_(
                    self.tables['game_membership'].c.user_id == self.tables['fleets'].c.user_id,
                    self.tables['game_membership'].c.game_id == game_id,
                )
            )
        ).where(
            *where_clause
        ).execute().fetchall()

    def create_fleet(self, name, user_id, game_id, commander_id):
        """
        Create a fleet for a user in a game
        :param name:
            Name of the fleet
        :param user_id:
            ID of the user who owns the fleet
        :param game_id:
            ID of the game in which the fleet will be
        :param commander_id:
            ID of the commander
        :return:
            ID of the fleet which was just created
        """
        # TODO: verify that the user does not already have an active fleet in the game
        # TODO: figure out how to support upgrades purchased but not applied to a fleet
        data = {
            'name': name,
            'user_id': user_id,
            'game_id': game_id,
            'max_points': 400,
            'commander': commander_id,
            'status': 0,
        }
        return self.tables['fleets'].insert(data).execute().inserted_primary_key()

    def modify_fleet(self, fleet_id, ships, squadrons):
        pass

    def retire_fleet(self, fleet_id):
        """
        :fleet_id:
            ID of the fleet to retire
        :return:
            N/A
        """
        try:
            self.tables['fleet'].update(
                self.tables['fleet'].c.fleet_id == fleet_id,
                {'status': 2},
            ).execute()
        except Exception as e:
            raise Exception("Failed to retire the fleet: {}".format(e))

    def declare_attack(self):
        pass

    def get_status(self):
        pass


class FleetDao:
    def __init__(self):
        pass
