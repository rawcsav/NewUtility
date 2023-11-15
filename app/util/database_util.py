import sshtunnel

from app import config


def get_tunnel():
    tunnel = sshtunnel.SSHTunnelForwarder(
        (config.SSH_HOST),
        ssh_username=config.SSH_USER,
        ssh_password=config.SSH_PASS,
        remote_bind_address=(
            config.SQL_HOSTNAME, 3306)
    )
    tunnel.start()
    return tunnel
