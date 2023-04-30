
import os
import discord
import asyncio
import socket
import datetime
import json
import psutil




class StatusBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.status_check())

    '''
        [overwrite] on_ready: prints information about the bot
        @param _ self (discord.Client class)
    '''
    async def on_ready(self):
        print(f'Status BOT(name: {self.user.name} id:{self.user.id})')

    '''
        status check: 
        @param _ self (discord.Client class)
    '''
    async def status_check(self):
        # wait until the discord.client is ready
        await self.wait_until_ready()
        # changes the activity (shown below the bot name)
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, 
            name=(conf.get('bot').get('what-am-i-doint'))))
        # loop throu until the bot process gets killed
        while not self.is_closed():
            for i in range(len(conf.get('service'))):
                # text channel hooked to the socket/process
                channel = self.get_channel(conf.get('service')[i].get('channel-id'))
                # socket checking
                if conf.get('service')[i].get('type') == 1:
                    status = (self.socket_check(conf.get('service')[i].get('url-or-process'), 
                        conf.get('service')[i].get('port'), conf.get('service')[i].get('timeout')))
                # process checking
                elif conf.get('service')[i].get('type') == 2:
                    status = (self.process_check(conf.get('service')[i].get('url-or-process')))
                # only type 1 or 2 are valid
                else:
                    print(f"[ERR] unknown type! ({conf.get('service')[i].get('type')}), ignoring checks")
                    continue
                # service is online (just do nothing)
                if(status):
                    service_status = conf.get('bot').get('reachable')
                # service is offline (notify if wanted) | should we also log that once with timestamp?
                else:
                    service_status = conf.get('bot').get('unreachable')
                    bchannel = self.get_channel(conf.get('bot').get('mention-channel-id'))
                    ch_name = conf.get('service')[i].get('name')
                    # get last message of text channel
                    messagea = await bchannel.fetch_message(bchannel.last_message_id)
                    future = messagea.created_at + datetime.timedelta(minutes=conf.get('bot').get('mention-time'))
                    # send msg if last one wasnt of the bot-user
                    if(messagea.author.name != self.user.name):
                        send = True
                    # wait for 'mention-time' to re-post it
                    else:
                        send = (future <= datetime.datetime.now())
                    # send message to 'mention-channel-id' if 'notification' is 'true'
                    if (bool(conf.get('service')[i].get('notification')) and send):
                        msg = '<@&' + str(conf.get('bot').get('mention-role-id')) + '> -> ' + ch_name \
                            + ' seems to be Offline! (timeout after ' + str(conf.get('service')[i].get('timeout')) + ' sec.)'
                        await bchannel.send(content=msg)
                # change the hooked channel name
                ch_n_name = conf.get('service')[i].get('name') + ': ' + service_status
                await channel.edit(name=ch_n_name)
            # wait until looping again
            await asyncio.sleep(conf.get('bot').get('check-delay') * 60)

    '''
        socket_check: checks the given params for reach-ability
        @param _ self (discord.Client class)
        @param 1 ip/url [string]
        @param 2 port [int]
        @param 3 timeout [int]
    '''
    def socket_check(self, ip, port, timeout):
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        a_socket.settimeout(timeout)
        location = (ip, port)

        result_of_check = a_socket.connect_ex(location)
        if result_of_check == 0:
            a_socket.close()
            return True
        else:
            a_socket.close()
            return False

    '''
        process_check: checks the given params for reach-ability
        @param _ self (discord.Client class)
        @param 1 process name [string]
    '''
    def process_check(self, process_name):
        for proc in psutil.process_iter():
            try:
                if process_name.lower() in proc.name().lower():
                    return True
            except (psutil.AccessDenied):
                print("[ERR] The Bot doesnt have access to check for process!")
                pass
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
        return False

'''
    Reads JSON configuration file
    @param 1 conf_file name [string] (optional)
'''
def read_config(conf_file="discord_status_bot.json"):
    try:
        with open(conf_file, "r") as jsonfile:
            data = json.load(jsonfile)
            print(f"Read: '{conf_file}'")
    except Exception as e:
        print(e)
        exit(1)
    return data

if __name__ == "__main__":
    conf=read_config()
    print(f"found {len(conf.get('service'))} services to listen")
    bot = StatusBot()
    bot.run(conf.get('bot').get('token'))
