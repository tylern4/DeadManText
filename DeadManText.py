import os
import subprocess
import requests
from datetime import datetime
import sys
import time
import argparse
import logging
from daemon import pidfile
import daemon


class Telegram:
    def __init__(self):
        import json
        with open('/var/lib/DeadManText/telegram') as json_file:
            data = json.load(json_file)

        self.url = "https://api.telegram.org/bot"
        self.bot_token = self.url + data['token']
        self.bot_chatID = "/sendMessage?chat_id=" + data['chatID']

    def message(self, out):
        mess = 'time : {} \n'.format(datetime.now().strftime("%a    %m/%d/%Y    %I:%M:%S%p"))

        for serv in out:
            mess += 'Error with:     {} \n'.format(serv)
        return mess

    def send_message(self, out):
        api_call = self.bot_token + self.bot_chatID + \
            '&parse_mode=Markdown&text=' + self.message(out)
        response = requests.get(api_call)
        if response.json()['ok']:
            return
        else:
            logger.error(response.json())


class PingServers:
    def __init__(self):
        import json
        with open('/var/lib/DeadManText/servers') as json_file:
            self.servers = json.load(json_file)

    def pingServers(self):
        bad_servers = []
        with open(os.devnull, "wb") as limbo:
            for server, ip in self.servers.items():
                result = subprocess.Popen(["ping", "-c", "1", "-n", "-W", "2", ip],
                                          stdout=limbo, stderr=limbo).wait()
                if result:
                    bad_servers.append(server)

        if not bad_servers:
            return False
        else:
            return bad_servers

    def remove_server(self, out):
        for serv in out:
            del self.servers[serv]


def main(logf):
    # Setup Logging
    logger = logging.getLogger('DeadManText')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logf)
    fh.setLevel(logging.INFO)
    formatstr = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(formatstr)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Setup telegram
    client = Telegram()
    ping = PingServers()

    while True:
        out = ping.pingServers()
        if out:
            # Log the event
            logger.error(str(out))
            # Send a message
            client.send_message(out)
            # Remove it from the list until the deamon is restarted
            # so it doesn't keep messaging me
            ping.remove_server(out)
        # Wait one hour
        time.sleep(60*30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Example daemon in Python")
    parser.add_argument('-t', '--test', dest='test', action='store_true')
    parser.add_argument('-p', '--pid-file', default='/var/run/DeadManText.pid')
    parser.add_argument('-l', '--log-file', default='/var/log/DeadManText.log')

    args = parser.parse_args()

    if args.test:
        main("local.out")
    else:
        with daemon.DaemonContext(working_directory='/var/lib/DeadManText',
                                  pidfile=pidfile.TimeoutPIDLockFile(
                                      args.pid_file),
                                  umask=0o002,
                                  ) as context:
            main(args.log_file)
