import logging


logger = logging.getLogger("dakara_manager")


class DakaraManager:
    """Manager for the Dakara player

    This object is a high-level manager for the Dakara player. It controls the
    different elements of the project with simple commands.

    Args:
        font_loader (font_loader.FontLoader): object for font
            installation/deinstallation.
        vlc_player (vlc_player.VlcPlayer): interface to VLC.
        dakara_server_http (dakara_server.DakaraServerHTTPConnection):
            interface to the Dakara server for the HTTP protocol.
        dakara_server_websocket
            (dakara_server.DakaraServerWebSocketConnection): interface to the
            Dakara server for the Websocket protocol.
    """

    def __init__(
        self, font_loader, vlc_player, dakara_server_http, dakara_server_websocket
    ):
        # set modules up
        self.font_loader = font_loader
        self.vlc_player = vlc_player
        self.dakara_server_http = dakara_server_http
        self.dakara_server_websocket = dakara_server_websocket

        # set player callbacks
        self.vlc_player.set_callback(
            "started_transition", self.handle_started_transition
        )
        self.vlc_player.set_callback("started_song", self.handle_started_song)
        self.vlc_player.set_callback("could_not_play", self.handle_could_not_play)
        self.vlc_player.set_callback("finished", self.handle_finished)
        self.vlc_player.set_callback("paused", self.handle_paused)
        self.vlc_player.set_callback("resumed", self.handle_resumed)
        self.vlc_player.set_callback("error", self.handle_error)

        # set dakara server websocket callbacks
        self.dakara_server_websocket.set_idle_callback(self.play_idle_screen)
        self.dakara_server_websocket.set_playlist_entry_callback(
            self.play_playlist_entry
        )
        self.dakara_server_websocket.set_command_callback(self.do_command)
        self.dakara_server_websocket.set_connection_lost_callback(self.play_idle_screen)

    def handle_error(self, playlist_entry_id, message):
        """Callback when a VLC error occurs

        Args:
            playlist_entry_id (int): playlist entry ID.
            message (str): text describing the error.
        """
        self.dakara_server_http.create_player_error(playlist_entry_id, message)

    def handle_finished(self, playlist_entry_id):
        """Callback when a playlist entry finishes

        Args:
            playlist_entry_id (int): playlist entry ID.
        """
        self.dakara_server_http.update_finished(playlist_entry_id)

    def handle_started_transition(self, playlist_entry_id):
        """Callback when the transition of a playlist entry starts

        Args:
            playlist_entry_id (int): playlist entry ID.
        """
        self.dakara_server_http.update_started_transition(playlist_entry_id)

    def handle_started_song(self, playlist_entry_id):
        """Callback when the song of a playlist entry starts

        Args:
            playlist_entry_id (int): playlist entry ID.
        """
        self.dakara_server_http.update_started_song(playlist_entry_id)

    def handle_could_not_play(self, playlist_entry_id):
        """Callback when a playlist entry could not play

        Args:
            playlist_entry_id (int): playlist entry ID.
        """
        self.dakara_server_http.update_could_not_play(playlist_entry_id)

    def handle_paused(self, playlist_entry_id, timing):
        """Callback when the player is paused

        Args:
            playlist_entry_id (int): playlist entry ID.
            timing (int): position of the player in seconds.
        """
        self.dakara_server_http.update_paused(playlist_entry_id, timing)

    def handle_resumed(self, playlist_entry_id, timing):
        """Callback when the player resumed playing

        Args:
            playlist_entry_id (int): playlist entry ID.
            timing (int): position of the player in seconds.
        """
        self.dakara_server_http.update_resumed(playlist_entry_id, timing)

    def play_playlist_entry(self, playlist_entry):
        """Play the requested playlist entry

        Args:
            playlist_entry (dict): dictionary of the playlist entry.
        """
        self.vlc_player.play_playlist_entry(playlist_entry)

    def play_idle_screen(self):
        """Play the idle screen
        """
        self.vlc_player.play_idle_screen()

    def do_command(self, command):
        """Execute a player command

        Args:
            command (str): name of the command to execute.

        Raises:
            ValueError: if the command is not known.
        """
        if command not in ("pause", "play", "skip"):
            raise ValueError("Unknown command requested: '{}'".format(command))

        if command == "pause":
            self.vlc_player.set_pause(True)
            return

        if command == "play":
            self.vlc_player.set_pause(False)
            return

        if command == "skip":
            self.handle_finished(self.vlc_player.playing_id)
            self.play_idle_screen()
