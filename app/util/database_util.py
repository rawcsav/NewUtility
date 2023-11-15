import sshtunnel
from app import config


def get_tunnel(max_attempts=3):
    attempt_count = 0
    sshtunnel.SSH_TIMEOUT = 5.0
    sshtunnel.TUNNEL_TIMEOUT = 5.0
    while attempt_count < max_attempts:
        try:
            tunnel = sshtunnel.SSHTunnelForwarder(
                (config.SSH_HOST),
                ssh_username=config.SSH_USER,
                ssh_password=config.SSH_PASS,
                remote_bind_address=(config.SQL_HOSTNAME, 3306)
            )
            tunnel.start()
            return tunnel
        except sshtunnel.BaseSSHTunnelForwarderError:
            attempt_count += 1
            if attempt_count == max_attempts:
                raise
