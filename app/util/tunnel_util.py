import sshtunnel


def get_tunnel(SSH_HOST, SSH_USER, SSH_PASS, SQL_HOSTNAME, max_attempts=3):
    attempt_count = 0
    sshtunnel.SSH_TIMEOUT = 5.0
    sshtunnel.TUNNEL_TIMEOUT = 5.0
    while attempt_count < max_attempts:
        try:
            tunnel = sshtunnel.SSHTunnelForwarder(
                (SSH_HOST),
                ssh_username=SSH_USER,
                ssh_password=SSH_PASS,
                remote_bind_address=(SQL_HOSTNAME, 3306),
            )
            tunnel.start()
            return tunnel
        except sshtunnel.BaseSSHTunnelForwarderError:
            attempt_count += 1
            if attempt_count == max_attempts:
                raise
