# namespaces.py
from flask_socketio import emit, disconnect, join_room
from flask_socketio.namespace import Namespace
from flask_login import current_user


class GlobalNamespace(Namespace):
    def on_connect(self):
        # Check if the user is authenticated
        if not current_user.is_authenticated:
            print("Anonymous user attempted to connect to the global namespace. Disconnecting.")
            disconnect()
        else:
            print(f"Authenticated user {current_user.id} connected to the global namespace")
            join_room(str(current_user.id))

    def on_disconnect(self):
        print("Client disconnected from the global namespace")


class EmbeddingNamespace(Namespace):
    def on_connect(self):
        if not current_user.is_authenticated:
            disconnect()
        else:
            emit("my_response", {"data": "Connected to the namespace"})
            join_room(str(current_user.id))

    def on_disconnect(self):
        print("Client disconnected from the embedding namespace")


class ImageNamespace(Namespace):
    def on_connect(self):
        if not current_user.is_authenticated:
            disconnect()
        else:
            print(f"Authenticated user {current_user.id} connected to the image namespace")
            join_room(str(current_user.id))

    def on_disconnect(self):
        print("Client disconnected from the image namespace")


class AudioNamespace(Namespace):
    def on_connect(self):
        if not current_user.is_authenticated:
            disconnect()
        else:
            print(f"Authenticated user {current_user.id} connected to the audio namespace")
            join_room(str(current_user.id))

    def on_disconnect(self):
        print("Client disconnected from the audio namespace")
