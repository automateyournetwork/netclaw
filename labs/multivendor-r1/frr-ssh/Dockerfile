FROM frrouting/frr:latest
# Add sshd so netmiko can reach it. FRR ships vtysh but no SSH server, which is
# why the existing netclaw-* containers are unreachable to a CLI driver.
RUN apk add --no-cache openssh-server openssh-keygen bash \
 && ssh-keygen -A \
 && adduser -D -s /bin/bash netops \
 && echo 'netops:netops123' | chpasswd \
 && adduser netops frr \
 && adduser netops frrvty \
 && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
 && sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
COPY start.sh /start.sh
RUN chmod +x /start.sh
ENTRYPOINT ["/start.sh"]
