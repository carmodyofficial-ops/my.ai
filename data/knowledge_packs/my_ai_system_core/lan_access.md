# my.ai System Core — LAN Access

Trusted LAN devices should be able to access my.ai by LAN IP and port.

Security requirements:
- authentication must remain required
- LAN access must not imply public internet exposure
- router/firewall exposure should not be broadened without explicit instruction
- valid credentials are required for account access

Diagnostic commands:
systemctl --user status myai-lan-proxy --no-pager -l
curl -s -o /dev/null -w 'local app HTTP %{http_code}\n' http://127.0.0.1:7000/
curl -s -o /dev/null -w 'LAN app HTTP %{http_code}\n' http://<LAN_IP>:7000/
